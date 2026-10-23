#!/usr/bin/env python3
"""Credential-safe request helper for Quest Platform and the Store admin catalog reads.

This is the only way the quest-setup skill calls those services. The script resolves the
publisher credential itself, so the agent never reads `.env`, the environment or any
credential pattern, and never writes its own HTTP code.

Usage:
    python3 qp_request.py whoami
    python3 qp_request.py METHOD PATH [--body-file FILE] [--query k=v ...]
    python3 qp_request.py GET PATH --store [--query k=v ...]

Output: one JSON object on stdout.
Exit codes: 0 success (2xx), 1 HTTP or network failure, 2 refused before sending.
Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

QP_BASE = "https://quests-platform.xsolla.com"
STORE_BASE = "https://store.xsolla.com"
TIMEOUT_SECONDS = 20
MAX_TEXT_CHARS = 20000
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
MAX_BODY_FILE_BYTES = 1024 * 1024
MAX_DETAIL_CHARS = 200

ENV_MERCHANT = "XSOLLA_MERCHANT_ID"
ENV_PROJECT = "XSOLLA_PROJECT_ID"
ENV_KEY = "XSOLLA_PROJECT_API_KEY"
CREDENTIAL_NAMES = (ENV_MERCHANT, ENV_PROJECT, ENV_KEY)
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")

ID_PATTERN = re.compile(r"[0-9]+")
QP_PATH_PATTERN = re.compile(r"/api/v2/[A-Za-z0-9_./-]+")
STORE_PATH_PATTERN = re.compile(
    r"/api/v2/project/(\{project_id\}|[0-9]+)/admin/items/virtual_items(?:/sku/([A-Za-z0-9_.:-]+))?"
)
MERCHANT_SEGMENT = re.compile(r"/merchants/([^/]+)(?=/|$)")
PROJECT_SEGMENT = re.compile(r"/projects/([^/]+)(?=/|$)")
QUERY_KEY_PATTERN = re.compile(r"[A-Za-z0-9_.\[\]-]+")


class Refusal(Exception):
    """A request refused before anything was sent. `error` is the stable value printed."""

    def __init__(self, error: str) -> None:
        super().__init__(error)
        self.error = error


class Credentials:
    """Publisher credential set. repr() never shows the key."""

    def __init__(self, merchant_id: str, project_id: str, api_key: str) -> None:
        self.merchant_id = merchant_id
        self.project_id = project_id
        self._api_key = api_key

    def basic_token(self) -> str:
        return base64.b64encode(f"{self.merchant_id}:{self._api_key}".encode("utf-8")).decode("ascii")

    def scrub(self, text: str) -> str:
        for secret in (self._api_key, self.basic_token()):
            if secret:
                text = text.replace(secret, "[redacted]")
        return text

    def __repr__(self) -> str:
        return "Credentials(<redacted>)"


class _ArgParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise Refusal("usage")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow redirects: the Basic credential must not reach another host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


def _emit(obj: Dict[str, Any]) -> None:
    print(json.dumps(obj, ensure_ascii=False))


def read_dotenv(path: Path) -> Dict[str, str]:
    """Parse KEY=VALUE lines as text. Never executed or sourced."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    values: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key] = value
    return values


def _complete_set(values: Mapping[str, str]) -> Optional[Credentials]:
    picked = {name: str(values.get(name, "")).strip() for name in CREDENTIAL_NAMES}
    if not all(picked.values()):
        return None
    if not ID_PATTERN.fullmatch(picked[ENV_MERCHANT]) or not ID_PATTERN.fullmatch(picked[ENV_PROJECT]):
        return None
    return Credentials(picked[ENV_MERCHANT], picked[ENV_PROJECT], picked[ENV_KEY])


def resolve_credentials(environ: Mapping[str, str], cwd: Path) -> Credentials:
    """All-or-nothing: the process environment, else ./.env. Never mixed."""
    creds = _complete_set(environ)
    if creds is None:
        creds = _complete_set(read_dotenv(cwd / ".env"))
    if creds is None:
        raise Refusal("access_not_configured")
    return creds


def check_shape(method: str, path: str, store: bool) -> None:
    """Refuse anything that is not an allowed target, before credentials are read."""
    if method not in METHODS or not isinstance(path, str) or ".." in path:
        raise Refusal("target_not_allowed")
    if store:
        if method != "GET" or not STORE_PATH_PATTERN.fullmatch(path):
            raise Refusal("target_not_allowed")
        return
    if not QP_PATH_PATTERN.fullmatch(path) or "//" in path:
        raise Refusal("target_not_allowed")


def build_url(path: str, store: bool, creds: Credentials) -> str:
    """Build the target URL. Scope values in the path must equal the configured ids."""
    if store:
        match = STORE_PATH_PATTERN.fullmatch(path)
        if match is None:
            raise Refusal("target_not_allowed")
        project = match.group(1)
        if project != "{project_id}" and project != creds.project_id:
            raise Refusal("scope_mismatch")
        suffix = f"/sku/{match.group(2)}" if match.group(2) else ""
        return f"{STORE_BASE}/api/v2/project/{creds.project_id}/admin/items/virtual_items{suffix}"

    for merchant in MERCHANT_SEGMENT.findall(path):
        if merchant != creds.merchant_id:
            raise Refusal("scope_mismatch")
    for project in PROJECT_SEGMENT.findall(path):
        if project != creds.project_id:
            raise Refusal("scope_mismatch")
    return QP_BASE + path


def parse_query(pairs: List[str]) -> List[tuple]:
    query = []
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not QUERY_KEY_PATTERN.fullmatch(key):
            raise Refusal("invalid_query")
        query.append((key, value))
    return query


def load_body(path_text: str) -> bytes:
    path = Path(path_text)
    try:
        if not path.is_file() or path.stat().st_size > MAX_BODY_FILE_BYTES:
            raise Refusal("invalid_body")
        data = path.read_bytes()
        json.loads(data.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise Refusal("invalid_body") from None
    return data


def _network_detail(exc: BaseException, creds: Credentials) -> str:
    reason = getattr(exc, "reason", None) or exc
    text = creds.scrub(f"{type(exc).__name__}: {reason}")
    return text[:MAX_DETAIL_CHARS]


def _parse_body(raw: bytes, creds: Credentials) -> Any:
    text = creds.scrub(raw.decode("utf-8", errors="replace"))
    try:
        return json.loads(text)
    except ValueError:
        return text[:MAX_TEXT_CHARS]


def send(method: str, url: str, creds: Credentials, body: Optional[bytes]) -> Dict[str, Any]:
    headers = {"Authorization": "Basic " + creds.basic_token(), "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    urllib.request.install_opener(urllib.request.build_opener(_NoRedirect))
    try:
        response = urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS)
        try:
            status = int(response.status)
            raw = response.read(MAX_RESPONSE_BYTES)
        finally:
            response.close()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        try:
            raw = exc.read(MAX_RESPONSE_BYTES)
        except OSError:
            raw = b""
        finally:
            exc.close()
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": "network", "detail": _network_detail(exc, creds)}

    result: Dict[str, Any] = {
        "ok": 200 <= status < 300,
        "status": status,
        "body": _parse_body(raw, creds),
    }
    if status in (401, 403):
        result["error"] = "access_denied"
    return result


def main(argv: Optional[List[str]] = None, environ: Optional[Mapping[str, str]] = None,
         cwd: Optional[str] = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    env: Mapping[str, str] = os.environ if environ is None else environ
    folder = Path(cwd) if cwd is not None else Path.cwd()
    try:
        if args_list == ["whoami"]:
            creds = resolve_credentials(env, folder)
            _emit({"ok": True, "merchant_id": creds.merchant_id, "project_id": creds.project_id})
            return 0

        parser = _ArgParser(prog="qp_request.py", add_help=True)
        parser.add_argument("method")
        parser.add_argument("path")
        parser.add_argument("--body-file", default=None)
        parser.add_argument("--query", action="append", default=[], metavar="K=V")
        parser.add_argument("--store", action="store_true")
        args = parser.parse_args(args_list)

        method = args.method.upper()
        check_shape(method, args.path, args.store)
        query = parse_query(args.query)
        body = None
        if args.body_file is not None:
            if method == "GET" or args.store:
                raise Refusal("invalid_body")
            body = load_body(args.body_file)
        creds = resolve_credentials(env, folder)
        url = build_url(args.path, args.store, creds)
        if query:
            url += "?" + urllib.parse.urlencode(query)
        result = send(method, url, creds, body)
    except Refusal as refusal:
        _emit({"ok": False, "error": refusal.error})
        return 2
    except SystemExit as exc:  # argparse --help
        return int(exc.code or 0)

    _emit(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

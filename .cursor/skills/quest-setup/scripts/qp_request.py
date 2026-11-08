#!/usr/bin/env python3
"""Credential-safe request helper for Quest Platform and the Store admin catalog reads.

This is the only way the quest-setup skill calls those services. The script resolves the
publisher credential itself, so the agent never reads `.env`, the environment or any
credential pattern, and never writes its own HTTP code.

Quest Platform calls are the documented operations that accept the publisher key: the list,
methods, paths, query parameters and request bodies come from the OpenAPI document that qp_docs.py
caches, never from this file. The host comes from qp_config.py.

Usage:
    python3 qp_request.py whoami
    python3 qp_request.py ops
    python3 qp_request.py call OPERATION_ID [--param k=v ...] [--query k=v ...] [--body-file FILE]
    python3 qp_request.py METHOD PATH [--query k=v ...] [--body-file FILE]
    python3 qp_request.py catalog-list [--query limit=N --query offset=N]
    python3 qp_request.py catalog-item SKU

Output: one JSON object on stdout.
Exit codes: 0 success (2xx), 1 HTTP or network failure, 2 refused before sending.
Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import base64
import http.client
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import qp_config
import qp_docs

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
# The publisher key authenticates as HTTP Basic: only operations whose documented security
# accepts BasicAuth are callable. Scope parameters are always filled from the credential.
PUBLISHER_SECURITY = "BasicAuth"
SCOPE_PARAMS = {"merchant_id": "merchant_id", "project_id": "project_id"}
PATH_PARAM_VALUE = re.compile(r"[A-Za-z0-9_-]{1,128}")
TEMPLATE_PARAM = re.compile(r"\{([A-Za-z0-9_]+)\}")
# Store admin catalog reads are not part of the Quests docs; the item routes of the Store admin
# API are matched here and always scoped to the configured project.
STORE_PATH_PATTERN = re.compile(
    r"/api/v2/project/(\{project_id\}|[0-9]+)/admin/items/virtual_items(?:/sku/([A-Za-z0-9_.:-]+))?"
)
CATALOG_LIST = "/api/v2/project/{project_id}/admin/items/virtual_items"
CATALOG_ITEM = "/api/v2/project/{project_id}/admin/items/virtual_items/sku/{sku}"
CATALOG_QUERY_KEYS = frozenset({"limit", "offset"})
SKU_PATTERN = re.compile(r"[A-Za-z0-9_.:-]{1,255}")
QUERY_KEY_PATTERN = re.compile(r"[A-Za-z0-9_.\[\]-]+")
FORBIDDEN_QUERY_KEYS = frozenset({"merchant_id", "project_id", "merchant", "project"})


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
    source = "environment"
    if creds is None:
        creds = _complete_set(read_dotenv(cwd / ".env"))
        source = "folder"
    if creds is None:
        raise Refusal("access_not_configured")
    creds.source = source
    return creds


def configured_hosts(environ: Mapping[str, str], cwd: Path) -> Dict[str, str]:
    try:
        return qp_config.hosts(environ, cwd)
    except qp_config.UnknownEnvironment:
        raise Refusal("unknown_environment") from None


class Operation:
    """One documented operation the publisher key may call."""

    def __init__(self, op_id: str, method: str, template: str, summary: str,
                 query_keys: frozenset, body_schema: Optional[Dict[str, Any]], body_required: bool) -> None:
        self.op_id = op_id
        self.method = method
        self.template = template
        self.summary = summary
        self.query_keys = query_keys
        self.body_schema = body_schema
        self.body_required = body_required
        self.params = TEMPLATE_PARAM.findall(template)
        parts = TEMPLATE_PARAM.split(template)  # literal, name, literal, name, ...
        self._pattern = re.compile("".join(
            re.escape(part) if index % 2 == 0 else "([^/]+)" for index, part in enumerate(parts)))

    def match(self, path: str) -> Optional[Dict[str, str]]:
        found = self._pattern.fullmatch(path)
        return dict(zip(self.params, found.groups())) if found else None


def _resolve_ref(spec: Dict[str, Any], node: Any) -> Any:
    if isinstance(node, dict) and isinstance(node.get("$ref"), str) and node["$ref"].startswith("#/"):
        target: Any = spec
        for part in node["$ref"][2:].split("/"):
            target = target.get(part) if isinstance(target, dict) else None
        return target
    return node


def parse_operations(spec: Dict[str, Any]) -> Dict[str, Operation]:
    """Operations from an OpenAPI document whose security accepts the publisher key."""
    ops: Dict[str, Operation] = {}
    for template, item in (spec.get("paths") or {}).items():
        if not isinstance(item, dict) or not isinstance(template, str):
            continue
        for method, op in item.items():
            if method.upper() not in METHODS or not isinstance(op, dict):
                continue
            security = op.get("security", spec.get("security")) or []
            if not any(isinstance(entry, dict) and PUBLISHER_SECURITY in entry for entry in security):
                continue
            op_id = op.get("operationId")
            if not isinstance(op_id, str) or not op_id:
                continue
            query = frozenset(
                p.get("name") for p in (_resolve_ref(spec, x) for x in op.get("parameters") or [])
                if isinstance(p, dict) and p.get("in") == "query" and isinstance(p.get("name"), str)
            )
            body = _resolve_ref(spec, op.get("requestBody"))
            schema = None
            if isinstance(body, dict):
                content = (body.get("content") or {}).get("application/json") or {}
                schema = _resolve_ref(spec, content.get("schema"))
            ops[op_id] = Operation(op_id, method.upper(), template, str(op.get("summary") or ""),
                                   query, schema if isinstance(schema, dict) else None,
                                   bool(isinstance(body, dict) and body.get("required")))
    return ops


def load_operations(environ: Mapping[str, str], cwd: Path, home: Optional[str] = None) -> Dict[str, Operation]:
    """The documented operations, read from the docs cache that qp_docs.py writes."""
    base = environ.get(qp_docs.ENV_BASE_URL) or configured_hosts(environ, cwd)["docs"]
    path = qp_docs.cached_openapi(base, home or environ.get("HOME"))
    if path is None:
        raise Refusal("docs_unavailable")
    try:
        spec = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise Refusal("docs_unavailable") from None
    ops = parse_operations(spec if isinstance(spec, dict) else {})
    if not ops:
        raise Refusal("docs_unavailable")
    return ops


def check_raw_path(path: str) -> None:
    if not isinstance(path, str):
        raise Refusal("target_not_allowed")
    lowered = path.lower()
    if ".." in path or "//" in path or "%" in path or "\\" in path or "://" in path \
            or "publish" in lowered or "?" in path or "#" in path:
        raise Refusal("target_not_allowed")


def find_operation(method: str, path: str, ops: Mapping[str, Operation]) -> Tuple[Operation, Dict[str, str]]:
    """The documented operation a METHOD and path name, with its path parameters."""
    check_raw_path(path)
    # A literal segment wins over a parameter (quests/node-types is not quests/{id}).
    for op in sorted(ops.values(), key=lambda o: len(o.params)):
        params = op.match(path)
        if params is not None and op.method == method:
            return op, params
    raise Refusal("target_not_allowed")


def build_path(op: Operation, params: Mapping[str, str], creds: Credentials) -> str:
    """Fill the template. Scope parameters come from the credential and must match if given."""
    values: Dict[str, str] = {}
    for name in op.params:
        given = params.get(name)
        if name in SCOPE_PARAMS:
            own = getattr(creds, SCOPE_PARAMS[name])
            if given is not None and given not in (own, "{%s}" % name):
                raise Refusal("scope_mismatch")
            values[name] = own
            continue
        if given is None or not PATH_PARAM_VALUE.fullmatch(given):
            raise Refusal("invalid_param")
        values[name] = given
    unknown = set(params) - set(op.params)
    if unknown:
        raise Refusal("invalid_param")
    return TEMPLATE_PARAM.sub(lambda m: values[m.group(1)], op.template)


def check_body(op: Operation, data: Optional[bytes]) -> None:
    """A body only where the docs define one; unknown or missing top-level fields are refused."""
    if data is None:
        if op.body_required:
            raise Refusal("invalid_body")
        return
    if op.body_schema is None:
        raise Refusal("invalid_body")
    try:
        obj = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise Refusal("invalid_body") from None
    schema = op.body_schema
    if schema.get("type") == "object":
        if not isinstance(obj, dict):
            raise Refusal("invalid_body")
        props = schema.get("properties") or {}
        if schema.get("additionalProperties") is False and set(obj) - set(props):
            raise Refusal("invalid_body")
        for name in schema.get("required") or []:
            value = obj.get(name)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise Refusal("invalid_body")


def parse_query(pairs: List[str], allowed: Optional[frozenset] = None) -> List[tuple]:
    query = []
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not QUERY_KEY_PATTERN.fullmatch(key) or key.lower() in FORBIDDEN_QUERY_KEYS:
            raise Refusal("invalid_query")
        if allowed is not None and key not in allowed:
            raise Refusal("invalid_query")
        query.append((key, value))
    return query


def parse_params(pairs: List[str]) -> Dict[str, str]:
    params: Dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key or key in params:
            raise Refusal("invalid_param")
        params[key] = value
    return params


def store_url(path: str, creds: Credentials, hosts: Mapping[str, str]) -> str:
    """Store admin catalog read, always scoped to the configured project."""
    check_raw_path(path)
    match = STORE_PATH_PATTERN.fullmatch(path)
    if match is None:
        raise Refusal("target_not_allowed")
    project = match.group(1)
    if project != "{project_id}" and project != creds.project_id:
        raise Refusal("scope_mismatch")
    suffix = f"/sku/{match.group(2)}" if match.group(2) else ""
    return f"{hosts['store']}/api/v2/project/{creds.project_id}/admin/items/virtual_items{suffix}"


def prepare(op: Operation, params: Mapping[str, str], query: List[tuple], body: Optional[bytes],
            creds: Credentials, hosts: Mapping[str, str]) -> str:
    """Check a documented call and return its URL. Nothing is sent."""
    check_body(op, body)
    url = hosts["quests"] + build_path(op, params, creds)
    if query:
        url += "?" + urllib.parse.urlencode(query)
    return url


def load_body(path_text: str) -> bytes:
    path = Path(path_text)
    try:
        if not path.is_file() or path.stat().st_size > MAX_BODY_FILE_BYTES:
            raise Refusal("invalid_body")
        data = path.read_bytes()
        json.loads(data.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise Refusal("invalid_body") from None
    require_https_images(json.loads(data.decode("utf-8")))
    return data


def require_https_images(node: Any) -> None:
    """Quest public_view.image_url and block image overrides must be https. Nothing is sent otherwise."""
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str) and "image" in str(key).lower() \
                    and value.strip().lower().startswith("http://"):
                raise Refusal("https only: image URLs must start with https://")
            require_https_images(value)
    elif isinstance(node, list):
        for item in node:
            require_https_images(item)


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
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        response = opener.open(request, timeout=TIMEOUT_SECONDS)
        try:
            status = int(response.status)
            raw = response.read(MAX_RESPONSE_BYTES)
        finally:
            response.close()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        try:
            raw = exc.read(MAX_RESPONSE_BYTES)
        except (OSError, http.client.HTTPException):
            raw = b""
        finally:
            exc.close()
    except (OSError, ValueError, http.client.HTTPException) as exc:
        return {"ok": False, "error": "network", "detail": _network_detail(exc, creds)}

    result: Dict[str, Any] = {
        "ok": 200 <= status < 300,
        "status": status,
        "body": _parse_body(raw, creds),
    }
    if status in (401, 403):
        result["error"] = "access_denied"
    return result


def _operation_list(ops: Mapping[str, Operation]) -> List[Dict[str, str]]:
    return [{"id": op.op_id, "method": op.method, "path": op.template, "summary": op.summary}
            for op in sorted(ops.values(), key=lambda o: (o.template, o.method))]


def main(argv: Optional[List[str]] = None, environ: Optional[Mapping[str, str]] = None,
         cwd: Optional[str] = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    env: Mapping[str, str] = os.environ if environ is None else environ
    folder = Path(cwd) if cwd is not None else Path.cwd()
    try:
        if args_list == ["whoami"]:
            hosts = configured_hosts(env, folder)
            creds = resolve_credentials(env, folder)
            _emit({"ok": True, "merchant_id": creds.merchant_id, "project_id": creds.project_id,
                   "environment": qp_config.environment(env, folder), "source": creds.source})
            return 0
        if args_list == ["ops"]:
            ops = load_operations(env, folder)
            _emit({"ok": True, "environment": qp_config.environment(env, folder),
                   "operations": _operation_list(ops)})
            return 0

        if args_list and args_list[0] in ("catalog-list", "catalog-item"):
            hosts = configured_hosts(env, folder)
            if args_list[0] == "catalog-item":
                if len(args_list) != 2 or not SKU_PATTERN.fullmatch(args_list[1]):
                    raise Refusal("usage")
                path, query = CATALOG_ITEM.replace("{sku}", args_list[1]), []
            else:
                rest = args_list[1:]
                if len(rest) % 2 or any(flag != "--query" for flag in rest[::2]):
                    raise Refusal("usage")
                path, query = CATALOG_LIST, parse_query(rest[1::2], CATALOG_QUERY_KEYS)
            creds = resolve_credentials(env, folder)
            url = store_url(path, creds, hosts)
            if query:
                url += "?" + urllib.parse.urlencode(query)
            result = send("GET", url, creds, None)
            _emit(result)
            return 0 if result["ok"] else 1

        parser = _ArgParser(prog="qp_request.py", add_help=True)
        parser.add_argument("target")
        parser.add_argument("path", nargs="?")
        parser.add_argument("--param", action="append", default=[], metavar="K=V")
        parser.add_argument("--body-file", default=None)
        parser.add_argument("--query", action="append", default=[], metavar="K=V")
        parser.add_argument("--store", action="store_true")
        args = parser.parse_args(args_list)

        hosts = configured_hosts(env, folder)
        if args.store:
            if args.target.upper() != "GET" or args.path is None or args.body_file or args.param:
                raise Refusal("target_not_allowed")
            query = parse_query(args.query)
            creds = resolve_credentials(env, folder)
            url = store_url(args.path, creds, hosts)
            if query:
                url += "?" + urllib.parse.urlencode(query)
            body = None
            method = "GET"
        else:
            # The body is checked first: a refused image never depends on the target.
            body = load_body(args.body_file) if args.body_file is not None else None
            ops = load_operations(env, folder)
            if args.target == "call":
                if args.path not in ops:
                    raise Refusal("unknown_operation")
                op, params = ops[args.path], parse_params(args.param)
            else:
                method_name = args.target.upper()
                if method_name not in METHODS or args.path is None or args.param:
                    raise Refusal("target_not_allowed")
                op, params = find_operation(method_name, args.path, ops)
            method = op.method
            if body is not None and method in ("GET", "DELETE"):
                raise Refusal("invalid_body")
            query = parse_query(args.query, op.query_keys)
            creds = resolve_credentials(env, folder)
            url = prepare(op, params, query, body, creds, hosts)
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

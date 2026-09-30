#!/usr/bin/env python3
"""Initialize a Shop Builder portal template or add a block-set template to it."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Mapping

API_BASE_URL = "https://sitebuilder.xsolla.com/api"
SESSION_URL = "https://api.xsolla.com/merchant/xsolla_login/session"
PUBLISHER_URL = "https://publisher.xsolla.com"
SESSION_ENV = "XSOLLA_SHOPBUILDER_SESSION"
SESSION_COOKIES = ("pa-v4-token", "ps2[user_session]")
LANDING_TYPES = ("sellingpage", "gplay", "steam", "store", "topup", "rfppage")
TEMPLATES = ("home", "store", "news")
STATUS_BY_HTTP = {401: "needs_access", 403: "needs_access", 404: "needs_human"}
TIMEOUT_SECONDS = 30


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("portal", "template"):
        command = commands.add_parser(name)
        command.add_argument("--merchant-id", required=True, type=positive_int)
        command.add_argument("--project-id", required=True, type=positive_int)
        command.add_argument("--domain", required=True)
        command.add_argument("--dry-run", action="store_true")
    layout = commands.choices["portal"].add_mutually_exclusive_group(required=True)
    layout.add_argument("--single-page", dest="single_page", action="store_true")
    layout.add_argument("--hub", dest="single_page", action="store_false")
    template = commands.choices["template"]
    template.add_argument("--template", required=True, choices=TEMPLATES)
    template.add_argument("--type", default="steam", choices=LANDING_TYPES)
    return parser.parse_args(argv)


def build_request(args: argparse.Namespace) -> tuple[str, dict]:
    domain = urllib.parse.quote(args.domain, safe="")
    url = (
        f"{API_BASE_URL}/merchant/{args.merchant_id}/project/{args.project_id}"
        f"/landing/{domain}/{args.command}"
    )
    if args.command == "portal":
        return url, {"isSinglePage": args.single_page}
    return url, {"type": args.type, "template": args.template}


def cookie_header(cookies: Mapping[str, str], merchant_id: int, project_id: int) -> str:
    merged = {name: value for name, value in cookies.items() if name and value}
    merged["pa-merchant-id"] = str(merchant_id)
    merged["sb-pa-merchant-id"] = str(merchant_id)
    merged["sb-pa-project-id"] = str(project_id)
    return "; ".join(f"{name}={merged[name]}" for name in sorted(merged))


def publisher_token() -> str:
    result = subprocess.run(
        ["xsolla", "auth", "get-token"], capture_output=True, text=True, check=False
    )
    token = result.stdout.strip()
    if result.returncode != 0 or not token:
        raise RuntimeError("no Publisher login: run `xsolla auth login` and rerun")
    return token


def bootstrap_cookies(token: str) -> dict[str, str]:
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    query = urllib.parse.urlencode({"token": token, "remember_me": "true"})
    try:
        with opener.open(f"{SESSION_URL}?{query}", timeout=TIMEOUT_SECONDS) as response:
            final_url = response.geturl()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"publisher session bootstrap failed (HTTP {exc.code})") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"publisher session bootstrap failed: {exc.reason}") from None
    if "error=" in final_url:
        raise RuntimeError("publisher session bootstrap was rejected")
    cookies = {cookie.name: cookie.value for cookie in jar if cookie.value}
    if not any(name in cookies for name in SESSION_COOKIES):
        raise RuntimeError(
            "publisher session bootstrap did not yield a session cookie: "
            "run `xsolla auth login` and rerun"
        )
    return cookies


def session_header(
    merchant_id: int,
    project_id: int,
    env: Mapping[str, str] = os.environ,
    get_token: Callable[[], str] = publisher_token,
    get_cookies: Callable[[str], dict[str, str]] = bootstrap_cookies,
) -> str:
    configured = env.get(SESSION_ENV, "").strip()
    if configured:
        return configured
    return cookie_header(get_cookies(get_token()), merchant_id, project_id)


def send(
    url: str,
    body: dict,
    cookie: str,
    merchant_id: int,
    project_id: int,
    urlopen: Callable = urllib.request.urlopen,
) -> tuple[int, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": cookie,
            "Origin": PUBLISHER_URL,
            "Referer": f"{PUBLISHER_URL}/{merchant_id}/projects/{project_id}/site-builder",
        },
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, parse_body(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, parse_body(exc.read())


def parse_body(raw: bytes) -> object:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def outcome(command: str, http_status: int, response: object) -> dict:
    if 200 <= http_status < 300:
        return {"ok": True, "status": "applied", "http_status": http_status, "response": response}
    if command == "portal" and http_status == 409:
        return {
            "ok": True,
            "status": "already_initialized",
            "http_status": http_status,
            "next_action": "read the structure and resume; do not recreate the portal",
        }
    return {
        "ok": False,
        "status": STATUS_BY_HTTP.get(http_status, "failed"),
        "http_status": http_status,
        "response": response,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    url, body = build_request(args)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "method": "POST", "url": url, "body": body}))
        return 0
    try:
        cookie = session_header(args.merchant_id, args.project_id)
        http_status, response = send(url, body, cookie, args.merchant_id, args.project_id)
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    result = outcome(args.command, http_status, response)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

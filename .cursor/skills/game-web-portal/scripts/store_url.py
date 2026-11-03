#!/usr/bin/env python3
"""Check a partner's store URL: Steam, App Store or Google Play, by exact host only.

Prints the store, the app ID and the platform as JSON. Any other host, a look-alike, a
URL with user info or a port, or one without an app ID exits 1 with the reason: that is
`needs_input`, never a guess.
"""

from __future__ import annotations

import json
import re
import sys
from urllib.parse import parse_qs, urlsplit

# Exact hosts. A subdomain, a look-alike or a lookalike suffix such as
# `apps.apple.com.example.net` doesn't match.
STORES = {
    "store.steampowered.com": ("steam", "pc"),
    "apps.apple.com": ("app_store", "mobile"),
    "play.google.com": ("google_play", "mobile"),
}
STEAM_PATH = re.compile(r"/app/(\d+)(?:/.*)?")
APP_STORE_PATH = re.compile(r"/(?:[a-z]{2}/)?app/(?:[^/]+/)?id(\d+)/?")
PLAY_PATH = "/store/apps/details"
PLAY_PACKAGE = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+")


def classify(url: object) -> dict:
    """Return {"store", "platform", "app_id"} or {"needs_input": reason}."""
    if not isinstance(url, str) or not url.strip():
        return {"needs_input": "no store URL"}
    parts = urlsplit(url.strip())
    if parts.scheme != "https":
        return {"needs_input": "the store URL must start with https://"}
    if parts.username is not None or parts.password is not None or "@" in parts.netloc:
        return {"needs_input": "the store URL must not carry user info"}
    try:
        port = parts.port
    except ValueError:
        return {"needs_input": "the store URL has an invalid port"}
    if port is not None:
        return {"needs_input": "the store URL must not name a port"}
    host = (parts.hostname or "").lower()
    if host not in STORES:
        return {
            "needs_input": f"{host or 'the URL'} isn't Steam, the App Store or Google Play; "
            "send the game's own store page"
        }
    store, platform = STORES[host]
    app_id = None
    if store == "steam":
        match = STEAM_PATH.fullmatch(parts.path)
        app_id = match.group(1) if match else None
    elif store == "app_store":
        match = APP_STORE_PATH.fullmatch(parts.path)
        app_id = match.group(1) if match else None
    elif parts.path.rstrip("/") == PLAY_PATH:
        ids = parse_qs(parts.query).get("id", [])
        if len(ids) == 1 and PLAY_PACKAGE.fullmatch(ids[0]):
            app_id = ids[0]
    if app_id is None:
        return {"needs_input": f"the {host} URL doesn't name one app"}
    return {"store": store, "platform": platform, "app_id": app_id}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: store_url.py <store URL>", file=sys.stderr)
        return 2
    result = classify(args[0])
    print(json.dumps(result))
    return 1 if "needs_input" in result else 0


if __name__ == "__main__":
    raise SystemExit(main())

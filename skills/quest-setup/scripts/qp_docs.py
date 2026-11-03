#!/usr/bin/env python3
"""Stub for the live docs fetcher. Contract only, no logic yet (step 06 stub)."""
from __future__ import annotations

DEFAULT_BASE_URL = "https://xsolla--e401f7.preview.redocly.app"
TTL_SECONDS = 0
CACHE_DIR_NAME = "quest-setup-docs"


def fetch_docs(base_url=DEFAULT_BASE_URL, home=None, ttl=TTL_SECONDS, transport=None, now=None):
    return {"status": "error", "cache_path": "", "host": "", "pages": [], "error": "not implemented"}


def main(argv=None, transport=None, home=None):
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

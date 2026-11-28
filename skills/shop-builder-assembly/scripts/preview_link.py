#!/usr/bin/env python3
"""Switch on the public preview of an unpublished Shop Builder site and print its link.

`xsolla shopbuilder enable-preview` answers with a token, and no CLI command gives the
link (Xsolla CLI 1.10.0 removed `preview-link`). The link is the preview host, the site's
slug and that token. Anyone with the link can open the draft, signed in or not, until the
token expires or the preview is switched off
(`xsolla shopbuilder disable-preview --slug <slug>`).

A preview that is already on is reused, so a link handed over earlier keeps working.
`--new` asks for a new token.

Never publishes. A published site is refused before any write, like every other write
of this skill.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

sys.dont_write_bytecode = True  # keep the installed skill folder clean

# `python3 -I` (isolated mode) does not put the script's own folder on sys.path, so
# the sibling imports below would fail. Add it explicitly.
SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import cli_environment
from preflight import data, run_json

# Where Publisher Account's own "public preview" switch sends people.
PREVIEW_HOST = "https://preview.xsollasitebuilder.com"
# A token closer to its end than this is replaced: the link would die mid-review.
MIN_LIFETIME_SECONDS = 15 * 60
PUBLISHED_SITE = (
    "the site is published, and assembly writes only to an unpublished site. Nothing was "
    "changed. Its live address shows it as players see it"
)
BROWSER_WAY = (
    ". This is a known CLI gap: open the preview in the browser signed in to Publisher "
    "Account (the site's editor, then Preview) and use that link"
)


def token_expiry(token: str) -> float | None:
    """The end of a preview token's life, in seconds since the epoch, or None when the
    token doesn't say. The service's tokens are JWTs: the claims are the middle part."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        claims = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
    except (ValueError, binascii.Error):
        return None
    expires = claims.get("exp") if isinstance(claims, dict) else None
    if isinstance(expires, bool) or not isinstance(expires, (int, float)):
        return None
    return float(expires)


def preview_state(value: object) -> tuple[bool, str]:
    """Return (preview is on, its token) from get-structure's site or from the answer of
    enable-preview, which is the preview itself or the whole site."""
    if isinstance(value, dict) and isinstance(value.get("publicPreview"), dict):
        value = value["publicPreview"]
    if not isinstance(value, dict):
        return False, ""
    token = value.get("lastToken")
    return value.get("enabled") is True, token.strip() if isinstance(token, str) else ""


def preview_url(slug: str, token: str) -> str:
    return f"{PREVIEW_HOST}/{quote(slug, safe='')}?publicToken={quote(token, safe='')}"


def load_plan(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    target = value.get("target") if isinstance(value, dict) else None
    if not isinstance(target, dict):
        raise ValueError("the plan has no target")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--plan", type=Path, help="the approved plan; its target is the site")
    source.add_argument("--slug", help="the site's slug, in the CLI's current project")
    parser.add_argument(
        "--new", action="store_true", help="ask for a new token even if the preview is on"
    )
    args = parser.parse_args()
    try:
        if args.plan is not None:
            expected = load_plan(args.plan)
            slug = expected.get("slug")
        else:
            slug = args.slug
        if not isinstance(slug, str) or not slug.strip():
            raise ValueError("no site slug")
        slug = slug.strip()
        if args.plan is None:
            config = cli_environment.config_data(run_json("config", "list"))
            expected = {
                "merchant_id": config.get("merchant_id"),
                "project_id": config.get("project_id"),
            }
        # Shop Builder has no sandbox: the calls below use a sandbox-off environment.
        cli_environment.select(expected, run_json)

        site = data(run_json("shopbuilder", "get-structure", "--slug", slug))
        if not isinstance(site, dict):
            raise RuntimeError("get-structure returned an unexpected shape")
        if site.get("published") not in (None, False):
            raise RuntimeError(PUBLISHED_SITE)

        enabled, token = preview_state(site)
        expires = token_expiry(token) if token else None
        reused = (
            enabled
            and bool(token)
            and not args.new
            and (expires is None or expires - time.time() > MIN_LIFETIME_SECONDS)
        )
        if not reused:
            answer = data(run_json("shopbuilder", "enable-preview", "--slug", slug))
            _, token = preview_state(answer)
            if not token:
                raise RuntimeError("enable-preview returned no preview token")
            expires = token_expiry(token)
    except (RuntimeError, ValueError, OSError) as exc:
        message = str(exc)
        if "admin_privileges" in message:
            message += BROWSER_WAY
        print(f"Preview link failed: {message}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "slug": slug,
                "preview_url": preview_url(slug, token),
                "reused": reused,
                "expires": (
                    datetime.fromtimestamp(expires, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    if expires is not None
                    else None
                ),
                "access": "anyone with the link",
                "switch_off": f"xsolla shopbuilder disable-preview --slug {slug}",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

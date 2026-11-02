#!/usr/bin/env python3
"""Read confirmed onboarding intake without changing the ledger or calling Xsolla."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


INTAKE_KEYS = (
    "game_name", "platforms", "description", "store_url", "brand_assets",
    "domain", "primary_locale", "locales",
)


def read_onboarding(project_root: Path) -> dict:
    """Return intake from the ledger. Do not read a build path from .env."""
    path = project_root / ".xsolla" / "onboarding.json"
    if not path.exists():
        return {"status": "absent", "site_kind": "shop", "intake": {}}
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("Cannot parse .xsolla/onboarding.json; repair it before intake.") from exc
    if not isinstance(ledger, dict) or type(ledger.get("version")) is not int or ledger["version"] != 1:
        raise ValueError("Expected a version 1 onboarding object; do not discard existing answers.")
    if ledger.get("path") == "headless":
        raise ValueError("This onboarding ledger is for a shop the user codes. Open shop-setup.")
    site_kind = ledger.get("site_kind", "") or "shop"
    if site_kind not in ("shop", "portal"):
        raise ValueError("Invalid site_kind in .xsolla/onboarding.json. It must be shop or portal.")
    intake = ledger.get("intake", {})
    if not isinstance(intake, dict):
        raise ValueError("Onboarding intake must be an object; repair it before intake.")
    return {
        "status": "loaded",
        "site_kind": site_kind,
        "intake": {key: intake[key] for key in INTAKE_KEYS if key in intake},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = read_onboarding(args.project_root)
    except (OSError, ValueError) as exc:
        # Do not echo file contents: .env may contain credentials.
        print(str(exc) if isinstance(exc, ValueError) else "Cannot read onboarding files; check access.", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

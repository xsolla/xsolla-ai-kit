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
    """Check the recorded route and return only intake, not step history or secrets."""
    env_path = project_root / ".env"
    decisions = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key in ("XSOLLA_BUILD_PATH", "XSOLLA_SITE_KIND"):
                decisions[key] = value
    build_path = decisions.get("XSOLLA_BUILD_PATH", "")
    if not build_path:
        raise ValueError("No build path recorded. Run shop-plan before intake.")
    if build_path not in ("headless", "shopbuilder"):
        raise ValueError("Invalid XSOLLA_BUILD_PATH in .env. Resolve it with shop-plan.")
    if build_path == "headless":
        raise ValueError("The recorded path is headless. Return to shop-setup; do not collect SB intake.")
    site_kind = decisions.get("XSOLLA_SITE_KIND", "") or "shop"
    if site_kind not in ("shop", "portal"):
        raise ValueError("Invalid XSOLLA_SITE_KIND in .env. Resolve it with shop-plan.")

    path = project_root / ".xsolla" / "onboarding.json"
    result = {"status": "absent", "site_kind": site_kind, "intake": {}}
    if not path.exists():
        return result
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("Cannot parse .xsolla/onboarding.json; repair it before intake.") from exc
    if not isinstance(ledger, dict) or type(ledger.get("version")) is not int or ledger["version"] != 1:
        raise ValueError("Expected a version 1 onboarding object; do not discard existing answers.")
    if ledger.get("path") != build_path or ledger.get("site_kind") != site_kind:
        raise ValueError("Onboarding path/site_kind conflicts with .env. Rerun shop-plan; do not choose one.")
    intake = ledger.get("intake", {})
    if not isinstance(intake, dict):
        raise ValueError("Onboarding intake must be an object; repair it before intake.")
    result.update(status="loaded", intake={key: intake[key] for key in INTAKE_KEYS if key in intake})
    return result


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

#!/usr/bin/env python3
"""Export read-only Shop Builder state before an assembly write."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from preflight import approved_test_project, first_landing
from validate_shop_brief import load_brief, validate

ENVIRONMENTS = ("sandbox", "test")
SESSION_BOOTSTRAP_RETRY_DELAYS = (5, 10, 20)
LOGIN_SETTLE_SECONDS = 2
LOGIN_TIMEOUT_SECONDS = 45
LOGIN_RETRY_DELAY_SECONDS = 5


def refresh_supported_login() -> None:
    """Refresh the supported CLI login without handling or copying PA tokens."""
    for attempt in range(2):
        try:
            result = subprocess.run(
                ["xsolla", "auth", "login"],
                check=False,
                timeout=LOGIN_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            if attempt == 0:
                time.sleep(LOGIN_RETRY_DELAY_SECONDS)
                continue
            raise RuntimeError("supported Publisher login refresh timed out") from None
        if result.returncode == 0:
            time.sleep(LOGIN_SETTLE_SECONDS)
            return
        if attempt == 0:
            time.sleep(LOGIN_RETRY_DELAY_SECONDS)
    raise RuntimeError("supported Publisher login refresh failed")


def run_json(*args: str) -> object:
    command = ["xsolla", *args, "--json"]
    if args and args[0] == "shopbuilder":
        refresh_supported_login()
    rate_limit_attempt = 0
    refreshed_login = False
    while True:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            break
        detail = result.stderr.strip() or result.stdout.strip()
        retryable_bootstrap_limit = (
            "publisher session bootstrap" in detail and "HTTP 429" in detail
        )
        if retryable_bootstrap_limit and rate_limit_attempt < len(
            SESSION_BOOTSTRAP_RETRY_DELAYS
        ):
            time.sleep(SESSION_BOOTSTRAP_RETRY_DELAYS[rate_limit_attempt])
            rate_limit_attempt += 1
            continue
        missing_bootstrap_cookie = (
            "publisher session bootstrap did not yield" in detail
        )
        if missing_bootstrap_cookie and not refreshed_login:
            refresh_supported_login()
            refreshed_login = True
            continue
        if "publisher session bootstrap" in detail:
            detail += (
                "; refresh the supported Publisher login with `xsolla auth login` "
                "and rerun—never copy a browser PA token"
            )
        raise RuntimeError(f"{' '.join(args)} failed: {detail}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{' '.join(args)} returned invalid JSON") from exc


def data(value: object) -> object:
    if isinstance(value, dict) and value.get("ok") is True and "data" in value:
        return value["data"]
    return value


def landing_id(structure: object) -> str:
    value = data(structure)
    if not isinstance(value, dict) or not isinstance(value.get("_id"), str):
        raise RuntimeError("get-structure did not return a landing _id")
    return value["_id"]


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def target_project(args: argparse.Namespace) -> dict:
    """The project to back up: from the shop brief, or by identity for an update or resume."""
    identity = (args.merchant_id, args.project_id, args.environment)
    if args.brief is not None:
        if any(value is not None for value in identity):
            raise RuntimeError(
                "pass either --brief or --merchant-id, --project-id and --environment, not both"
            )
        brief = load_brief(args.brief)
        errors = validate(brief)
        if errors:
            raise RuntimeError("invalid shop brief: " + "; ".join(errors))
        return brief["project"]
    if any(value is None for value in identity):
        raise RuntimeError("pass --brief, or all of --merchant-id, --project-id and --environment")
    if args.merchant_id <= 0 or args.project_id <= 0:
        raise RuntimeError("--merchant-id and --project-id must be positive integers")
    expected = {
        "merchant_id": args.merchant_id,
        "project_id": args.project_id,
        "environment": args.environment,
    }
    approved_test_project(args.approved_test_projects, expected)
    return expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", type=Path)
    parser.add_argument("--merchant-id", type=int)
    parser.add_argument("--project-id", type=int)
    parser.add_argument("--environment", choices=ENVIRONMENTS)
    parser.add_argument("--approved-test-projects", type=Path)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    if shutil.which("xsolla") is None:
        print("xsolla CLI is not installed", file=sys.stderr)
        return 1
    if args.output_dir.exists():
        if not args.output_dir.is_dir() or any(args.output_dir.iterdir()):
            print("output directory must be absent or empty", file=sys.stderr)
            return 1

    try:
        expected = target_project(args)
        source = "the shop brief" if args.brief is not None else "the target"
        config = run_json("config", "list")
        config_data = data(config)
        if not isinstance(config_data, dict):
            raise RuntimeError("xsolla config list returned an unexpected shape")
        if config_data.get("merchant_id") != expected["merchant_id"]:
            raise RuntimeError(f"CLI merchant_id does not match {source}")
        if config_data.get("project_id") != expected["project_id"]:
            raise RuntimeError(f"CLI project_id does not match {source}")
        expected_sandbox = expected["environment"] == "sandbox"
        sandbox_enabled = config_data.get("sandbox") is True
        if sandbox_enabled != expected_sandbox:
            raise RuntimeError(f"CLI sandbox setting does not match the environment of {source}")

        websites = run_json("shopbuilder", "list-websites")
        if args.brief is None and first_landing(websites, args.slug) is None:
            raise RuntimeError(
                f"{args.slug} does not exist: a backup by merchant, project and environment "
                "is for updating or resuming an existing site"
            )
        landing = run_json("shopbuilder", "get-landing", "--slug", args.slug)
        structure = run_json("shopbuilder", "get-structure", "--slug", args.slug)
        localization = run_json("shopbuilder", "get-localization", "--slug", args.slug)
        assets = run_json(
            "shopbuilder", "list-assets", "--landing-id", landing_id(structure)
        )
        versions = run_json("shopbuilder", "list-versions", "--slug", args.slug)

        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_json(args.output_dir / "config.json", config)
        write_json(args.output_dir / "websites.json", websites)
        write_json(args.output_dir / "landing.json", landing)
        write_json(args.output_dir / "structure.json", structure)
        write_json(args.output_dir / "localization.json", localization)
        write_json(args.output_dir / "assets.json", assets)
        write_json(args.output_dir / "versions.json", versions)
        files = [
            "config.json",
            "websites.json",
            "landing.json",
            "structure.json",
            "localization.json",
            "assets.json",
            "versions.json",
        ]
        write_json(
            args.output_dir / "manifest.json",
            {
                "slug": args.slug,
                "merchant_id": expected["merchant_id"],
                "project_id": expected["project_id"],
                "environment": expected["environment"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "read_only": True,
                "files": files,
                "sha256": {name: checksum(args.output_dir / name) for name in files},
            },
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(args.output_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

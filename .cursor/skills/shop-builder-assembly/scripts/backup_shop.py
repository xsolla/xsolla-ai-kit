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

from validate_shop_brief import load_brief, validate

SESSION_BOOTSTRAP_RETRY_DELAYS = (5, 10, 20)
LOGIN_SETTLE_SECONDS = 2
LOGIN_TIMEOUT_SECONDS = 45
LOGIN_RETRY_DELAY_SECONDS = 5
# `xsolla` exits with 10 when the API answers HTTP 401 or 403.
CLI_EXIT_AUTH = 10
AUTH_FAILURE_MARKERS = (
    "authentication required",
    "publisher session bootstrap did not yield",
    "auto-bootstrapping publisher session",
)
# A run logs in at most once, and only after the CLI reports an auth failure.
# `context` is the merchant, project and sandbox setting that main() verified;
# `xsolla auth login` can write token claims into the CLI config, so it is
# re-checked after the login.
RUN_AUTH: dict = {"logged_in": False, "context": None}


def refresh_supported_login() -> None:
    """Refresh the supported CLI login without handling or copying PA tokens."""
    for attempt in range(2):
        try:
            # Login messages go to stderr so stdout stays the script's result.
            result = subprocess.run(
                ["xsolla", "auth", "login"],
                check=False,
                stdout=sys.stderr,
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


def auth_failure(returncode: int, detail: str) -> bool:
    """Return whether a CLI failure is one that a fresh supported login can fix."""
    if "HTTP 429" in detail:
        return False
    return returncode == CLI_EXIT_AUTH or any(
        marker in detail for marker in AUTH_FAILURE_MARKERS
    )


def cli_context(config: object) -> dict:
    value = data(config)
    if not isinstance(value, dict):
        raise RuntimeError("xsolla config list returned an unexpected shape")
    return {
        "merchant_id": value.get("merchant_id"),
        "project_id": value.get("project_id"),
        "sandbox": value.get("sandbox") is True,
    }


def login_once(detail: str) -> None:
    if RUN_AUTH["logged_in"]:
        raise RuntimeError(
            "authentication still fails after this run's one `xsolla auth login`. "
            "The failed command made no change, so it is safe to rerun. CLI error: "
            + detail
        )
    approved = RUN_AUTH["context"]
    if approved is None:
        raise RuntimeError(
            "authentication failed before the CLI context was verified: " + detail
        )
    RUN_AUTH["logged_in"] = True
    refresh_supported_login()
    current = cli_context(run_json("config", "list"))
    changed = [
        f"{key} {approved[key]!r} -> {current[key]!r}"
        for key in approved
        if current[key] != approved[key]
    ]
    if changed:
        raise RuntimeError(
            "CLI context changed after `xsolla auth login` ("
            + ", ".join(changed)
            + "). The command was not retried and made no change, so it is safe to "
            "rerun: check .xsolla.json in the working directory, then run preflight "
            "again"
        )


def run_json(*args: str) -> object:
    if any(arg == "--force" or arg.startswith("--force=") for arg in args):
        raise RuntimeError("--force is prohibited in Shop Builder assembly")
    command = ["xsolla", *args, "--json"]
    rate_limit_attempt = 0
    while True:
        # The CLI writes UTF-8; without an explicit encoding Windows decodes with
        # the ANSI code page and loses the output.
        result = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", check=False
        )
        if result.returncode == 0:
            break
        detail = (
            (result.stderr or "").strip()
            or (result.stdout or "").strip()
            or f"exit code {result.returncode}"
        )
        retryable_bootstrap_limit = (
            "publisher session bootstrap" in detail and "HTTP 429" in detail
        )
        if retryable_bootstrap_limit and rate_limit_attempt < len(
            SESSION_BOOTSTRAP_RETRY_DELAYS
        ):
            time.sleep(SESSION_BOOTSTRAP_RETRY_DELAYS[rate_limit_attempt])
            rate_limit_attempt += 1
            continue
        if auth_failure(result.returncode, detail):
            login_once(detail)
            continue
        if "publisher session bootstrap" in detail:
            detail += (
                "; refresh the supported Publisher login with `xsolla auth login` "
                "and rerun—never copy a browser PA token"
            )
        raise RuntimeError(f"{' '.join(args)} failed: {detail}")
    stdout = result.stdout or ""
    stderr = (result.stderr or "").strip() or "no stderr output"
    if not stdout.strip():
        raise RuntimeError(f"{' '.join(args)} returned no output: {stderr}")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{' '.join(args)} returned invalid JSON: {stderr}") from exc


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", required=True, type=Path)
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
        brief = load_brief(args.brief)
        errors = validate(brief)
        if errors:
            raise RuntimeError("invalid shop brief: " + "; ".join(errors))
        expected = brief["project"]
        config = run_json("config", "list")
        config_data = data(config)
        if not isinstance(config_data, dict):
            raise RuntimeError("xsolla config list returned an unexpected shape")
        if config_data.get("merchant_id") != expected["merchant_id"]:
            raise RuntimeError("CLI merchant_id does not match the shop brief")
        if config_data.get("project_id") != expected["project_id"]:
            raise RuntimeError("CLI project_id does not match the shop brief")
        if config_data.get("sandbox") is True:
            raise RuntimeError("CLI sandbox must be disabled for Shop Builder")
        RUN_AUTH["context"] = cli_context(config_data)

        websites = run_json("shopbuilder", "list-websites")
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

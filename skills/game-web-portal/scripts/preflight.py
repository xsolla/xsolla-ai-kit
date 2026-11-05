#!/usr/bin/env python3
"""Refuse a portal write unless the CLI targets the intended project, with sandbox mode off."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def cli_config() -> dict:
    # The CLI writes UTF-8; without an explicit encoding Windows decodes with the
    # ANSI code page and loses the output.
    result = subprocess.run(
        ["xsolla", "config", "list", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    try:
        value = json.loads(result.stdout or "")
    except json.JSONDecodeError:
        raise RuntimeError(
            "no Xsolla CLI project context: run `xsolla config init` for the project"
        ) from None
    if isinstance(value, dict) and value.get("ok") is False:
        raise RuntimeError(f"xsolla config list failed: {value.get('error', value)}")
    if isinstance(value, dict) and value.get("ok") is True and "data" in value:
        value = value["data"]
    if not isinstance(value, dict):
        raise RuntimeError("xsolla config list returned an unexpected shape")
    return value


def check_project(merchant_id: int, project_id: int, config: dict | None = None) -> None:
    """Raise unless the CLI targets this merchant and project with sandbox mode off."""
    config = cli_config() if config is None else config
    if config.get("merchant_id") != merchant_id or config.get("project_id") != project_id:
        raise RuntimeError("the CLI's configured merchant/project does not match the target")
    if config.get("sandbox") is True:
        raise RuntimeError(
            "the CLI's sandbox mode is on (a new CLI config starts with it on). Shop Builder "
            "has no sandbox: ask the partner before running `xsolla config set sandbox false`, "
            "then run this preflight again"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--merchant-id", required=True, type=positive_int)
    parser.add_argument("--project-id", required=True, type=positive_int)
    args = parser.parse_args(argv)
    try:
        check_project(args.merchant_id, args.project_id)
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps({
        "ok": True,
        "merchant_id": args.merchant_id,
        "project_id": args.project_id,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

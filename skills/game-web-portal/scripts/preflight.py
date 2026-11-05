#!/usr/bin/env python3
"""Refuse a portal write unless the CLI targets a listed test project, with sandbox mode off."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


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
            "no Xsolla CLI project context: run `xsolla config init` for the test project"
        ) from None
    if isinstance(value, dict) and value.get("ok") is False:
        raise RuntimeError(f"xsolla config list failed: {value.get('error', value)}")
    if isinstance(value, dict) and value.get("ok") is True and "data" in value:
        value = value["data"]
    if not isinstance(value, dict):
        raise RuntimeError("xsolla config list returned an unexpected shape")
    return value


def listed_test_project(path: Path, merchant_id: int, project_id: int) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read the test-project list: {exc}") from exc
    if not isinstance(value, dict) or value.get("version") != 1:
        raise RuntimeError("the test-project list must be a version 1 object")
    projects = value.get("projects")
    if not isinstance(projects, list):
        raise RuntimeError("the test-project list must contain a projects list")
    for index, project in enumerate(projects):
        if not isinstance(project, dict):
            raise RuntimeError(f"test-project list entry {index} must be an object")
        ids = (project.get("merchant_id"), project.get("project_id"))
        if any(isinstance(i, bool) or not isinstance(i, int) for i in ids):
            raise RuntimeError(f"test-project list entry {index} must contain integer IDs")
        if ids == (merchant_id, project_id):
            return project
    raise RuntimeError("merchant_id/project_id is not on the test-project list")


def check_project(
    merchant_id: int, project_id: int, allowlist: Path, config: dict | None = None
) -> dict:
    """Raise unless the target is safe to write; return its test-project list entry."""
    config = cli_config() if config is None else config
    if config.get("merchant_id") != merchant_id or config.get("project_id") != project_id:
        raise RuntimeError("the CLI's configured merchant/project does not match the target")
    if config.get("sandbox") is True:
        raise RuntimeError(
            "the CLI's sandbox mode is on (a new CLI config starts with it on). Shop Builder "
            "has no sandbox: ask the partner before running `xsolla config set sandbox false`, "
            "then run this preflight again"
        )
    return listed_test_project(allowlist, merchant_id, project_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--merchant-id", required=True, type=positive_int)
    parser.add_argument("--project-id", required=True, type=positive_int)
    parser.add_argument("--approved-test-projects", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        entry = check_project(args.merchant_id, args.project_id, args.approved_test_projects)
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps({
        "ok": True,
        "merchant_id": args.merchant_id,
        "project_id": args.project_id,
        "test_project": entry,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

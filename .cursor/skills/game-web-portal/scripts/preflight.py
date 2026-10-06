#!/usr/bin/env python3
"""Refuse a portal write unless the CLI targets an approved test project."""

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
    result = subprocess.run(
        ["xsolla", "config", "list", "--json"], capture_output=True, text=True, check=False
    )
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(
            "no Xsolla CLI project context: run `xsolla config init` for the test project"
        ) from None
    if isinstance(value, dict) and value.get("ok") is True and "data" in value:
        value = value["data"]
    if not isinstance(value, dict):
        raise RuntimeError("xsolla config list returned an unexpected shape")
    return value


def approved_test_project(path: Path, merchant_id: int, project_id: int) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read approved test projects: {exc}") from exc
    if not isinstance(value, dict) or value.get("version") != 1:
        raise RuntimeError("approved test projects must be a version 1 object")
    projects = value.get("projects")
    if not isinstance(projects, list):
        raise RuntimeError("approved test projects must contain a projects list")
    for index, project in enumerate(projects):
        if not isinstance(project, dict):
            raise RuntimeError(f"approved test projects[{index}] must be an object")
        ids = (project.get("merchant_id"), project.get("project_id"))
        if any(isinstance(i, bool) or not isinstance(i, int) for i in ids):
            raise RuntimeError(f"approved test projects[{index}] must contain integer IDs")
        for field in ("approved_by", "approval_reference"):
            if not isinstance(project.get(field), str) or not project[field].strip():
                raise RuntimeError(f"approved test projects[{index}].{field} is required")
        if ids == (merchant_id, project_id):
            return project
    raise RuntimeError("merchant_id/project_id is not in the approved test-project allowlist")


def check_project(
    merchant_id: int, project_id: int, allowlist: Path, config: dict | None = None
) -> dict:
    """Raise unless the target is safe to write; return its approval record."""
    config = cli_config() if config is None else config
    if config.get("merchant_id") != merchant_id or config.get("project_id") != project_id:
        raise RuntimeError("the CLI's configured merchant/project does not match the target")
    return approved_test_project(allowlist, merchant_id, project_id)


def add_target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--merchant-id", required=True, type=positive_int)
    parser.add_argument("--project-id", required=True, type=positive_int)
    parser.add_argument("--approved-test-projects", required=True, type=Path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_target_arguments(parser)
    args = parser.parse_args(argv)
    try:
        approval = check_project(args.merchant_id, args.project_id, args.approved_test_projects)
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps({
        "ok": True,
        "merchant_id": args.merchant_id,
        "project_id": args.project_id,
        "approval": approval,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Verify CLI auth, safe project context, target site, and catalog references."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from validate_shop_brief import load_brief, validate


def run_json(*args: str) -> object:
    result = subprocess.run(
        ["xsolla", *args, "--json"], capture_output=True, text=True, check=False
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{' '.join(args)} failed: {detail}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{' '.join(args)} returned invalid JSON") from exc


def data(value: object) -> object:
    if isinstance(value, dict) and value.get("ok") is True and "data" in value:
        return value["data"]
    return value


def objects(value: object):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)


def first_landing(value: object, slug: str) -> dict | None:
    for item in objects(data(value)):
        if item.get("domain") == slug or item.get("slug") == slug:
            return item
    return None


def active_publisher_account(value: object) -> bool:
    payload = data(value)
    if not isinstance(payload, dict):
        return False
    accounts = payload.get("accounts")
    return isinstance(accounts, list) and any(
        isinstance(account, dict)
        and account.get("context") == "publisher"
        and account.get("active") is True
        and account.get("expired") is False
        for account in accounts
    )


def group_external_ids(value: object) -> set[str]:
    """Return group IDs from the storefront response.

    ``catalog list-item-groups`` does not return an item ``type`` for a group.
    The requested type remains part of the Shop Builder section mapping, while
    preflight can only verify that its referenced group ID exists.
    """

    return {
        item["external_id"]
        for item in objects(data(value))
        if isinstance(item.get("external_id"), str)
    }


def approved_test_project(path: Path | None, expected: dict) -> dict | None:
    """Return the separate approval record for a dedicated test project."""
    if expected["environment"] != "test":
        return None
    if path is None:
        raise RuntimeError(
            "--approved-test-projects is required for a dedicated test project"
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read approved test projects: {exc}") from exc
    if not isinstance(value, dict) or value.get("version") != 1:
        raise RuntimeError("approved test projects must be a version 1 object")
    projects = value.get("projects")
    if not isinstance(projects, list):
        raise RuntimeError("approved test projects must contain a projects list")

    target = (expected["merchant_id"], expected["project_id"])
    for index, project in enumerate(projects):
        if not isinstance(project, dict):
            raise RuntimeError(f"approved test projects[{index}] must be an object")
        merchant_id = project.get("merchant_id")
        project_id = project.get("project_id")
        if (
            isinstance(merchant_id, bool)
            or not isinstance(merchant_id, int)
            or isinstance(project_id, bool)
            or not isinstance(project_id, int)
        ):
            raise RuntimeError(
                f"approved test projects[{index}] must contain integer IDs"
            )
        if not isinstance(project.get("approved_by"), str) or not project[
            "approved_by"
        ].strip():
            raise RuntimeError(
                f"approved test projects[{index}].approved_by is required"
            )
        if not isinstance(project.get("approval_reference"), str) or not project[
            "approval_reference"
        ].strip():
            raise RuntimeError(
                f"approved test projects[{index}].approval_reference is required"
            )
        if (merchant_id, project_id) == target:
            return project
    raise RuntimeError(
        "configured merchant_id/project_id is not in the approved test-project allowlist"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("brief", type=Path)
    parser.add_argument("--approved-test-projects", type=Path)
    args = parser.parse_args()

    if shutil.which("xsolla") is None:
        print("xsolla CLI is not installed", file=sys.stderr)
        return 1
    try:
        brief = load_brief(args.brief)
        errors = validate(brief)
        if errors:
            raise RuntimeError("invalid shop brief: " + "; ".join(errors))

        config = data(run_json("config", "list"))
        if not isinstance(config, dict):
            raise RuntimeError("xsolla config list returned an unexpected shape")
        expected = brief["project"]
        test_project_approval = approved_test_project(
            args.approved_test_projects, expected
        )
        expected_sandbox = expected["environment"] == "sandbox"
        sandbox_enabled = config.get("sandbox") is True
        if sandbox_enabled != expected_sandbox:
            raise RuntimeError(
                "CLI sandbox setting does not match the shop brief environment"
            )
        if config.get("merchant_id") != expected["merchant_id"]:
            raise RuntimeError("CLI merchant_id does not match the shop brief")
        if config.get("project_id") != expected["project_id"]:
            raise RuntimeError("CLI project_id does not match the shop brief")

        accounts = run_json("auth", "list-account")
        if not active_publisher_account(accounts):
            raise RuntimeError("no active, unexpired Publisher login is available")

        websites = run_json("shopbuilder", "list-websites")
        landing = first_landing(websites, brief["site"]["slug"])

        groups = run_json(
            "catalog",
            "list-item-groups",
            "--project-id",
            str(expected["project_id"]),
        )
        available_group_ids = group_external_ids(groups)
        requested_groups = {
            (group["external_id"], group["type"])
            for group in brief["catalog"]["groups"]
            if group["external_id"] != "__all__"
        }
        missing_groups = sorted(
            (external_id, group_type)
            for external_id, group_type in requested_groups
            if external_id not in available_group_ids
        )
        if missing_groups:
            raise RuntimeError(
                "catalog groups do not exist in the configured project: "
                + ", ".join(
                    f"{group_type}:{external_id}"
                    for external_id, group_type in missing_groups
                )
            )

        result = {
            "ok": True,
            "context": {
                "merchant_id": expected["merchant_id"],
                "project_id": expected["project_id"],
                "environment": expected["environment"],
                "sandbox": sandbox_enabled,
                "test_project_acknowledged": expected.get(
                    "test_project_acknowledged", False
                ),
                "test_project_allowlisted": test_project_approval is not None,
                "approval_reference": (
                    test_project_approval["approval_reference"]
                    if test_project_approval
                    else None
                ),
            },
            "auth": {"publisher_account_active": True},
            "target": {
                "slug": brief["site"]["slug"],
                "exists": landing is not None,
                "landing_id": landing.get("_id") if landing else None,
                "type": landing.get("type") if landing else None,
            },
            "catalog": {
                "verified_groups": [
                    {"external_id": external_id, "type": group_type}
                    for external_id, group_type in sorted(requested_groups)
                ]
            },
        }
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Preflight failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

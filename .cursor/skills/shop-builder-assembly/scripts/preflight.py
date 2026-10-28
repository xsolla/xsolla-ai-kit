#!/usr/bin/env python3
"""Verify CLI auth, safe project context, target site, and catalog references."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from render_plan import common_layout_id
from validate_shop_brief import load_brief, validate

LAYOUT_SKIPPED = (
    "the common layout needs a newer Xsolla CLI; the site is built without it. A site "
    "without the common layout won't open in the Editor, Publish or private preview"
)


def run_json(*args: str) -> object:
    if any(arg == "--force" or arg.startswith("--force=") for arg in args):
        raise RuntimeError("--force is prohibited in Shop Builder assembly")
    # The CLI writes UTF-8; without an explicit encoding Windows decodes with the
    # ANSI code page and loses the output.
    result = subprocess.run(
        ["xsolla", *args, "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode:
        detail = (
            (result.stderr or "").strip()
            or (result.stdout or "").strip()
            or f"exit code {result.returncode}"
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


def cli_has_command(*command: str) -> bool:
    """Return whether the installed CLI has the command.

    For an unknown subcommand the CLI prints its parent's help and exits 0, so only
    the usage line tells: it names the command when the command exists.
    """

    try:
        result = subprocess.run(
            ["xsolla", *command, "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError:
        return False
    usage = " ".join(["xsolla", *command])
    return any(
        line.strip() == usage or line.strip().startswith(usage + " ")
        for line in (result.stdout or "").splitlines()
    )


def site_block_module(slug: str, block_id: str) -> object:
    block = data(
        run_json("shopbuilder", "get-block", "--slug", slug, "--block-id", block_id)
    )
    return block.get("module") if isinstance(block, dict) else None


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


def approved_test_project(path: Path | None, expected: dict) -> dict:
    """Return the separate approval record for a dedicated test project."""
    if expected["environment"] != "test":
        raise RuntimeError("Shop Builder assembly requires a dedicated test project")
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
        if config.get("sandbox") is True:
            raise RuntimeError("CLI sandbox must be disabled for Shop Builder")
        if config.get("merchant_id") != expected["merchant_id"]:
            raise RuntimeError("CLI merchant_id does not match the shop brief")
        if config.get("project_id") != expected["project_id"]:
            raise RuntimeError("CLI project_id does not match the shop brief")

        accounts = run_json("auth", "list-account")
        if not active_publisher_account(accounts):
            raise RuntimeError("no active, unexpired Publisher login is available")

        slug = brief["site"]["slug"]
        websites = run_json("shopbuilder", "list-websites")
        landing = first_landing(websites, slug)

        # Assembly adds the common layout after its page writes. A CLI without
        # create-block cannot add it, so assembly skips that step.
        layout_id = None
        if landing is not None:
            site = data(run_json("shopbuilder", "get-structure", "--slug", slug))
            if not isinstance(site, dict):
                raise RuntimeError("get-structure returned an unexpected shape")
            layout_id = common_layout_id(
                site, lambda block_id: site_block_module(slug, block_id)
            )
        if layout_id is not None:
            layout_step = "present"
        elif cli_has_command("shopbuilder", "create-block"):
            layout_step = "create"
        else:
            layout_step = "skip"
            print(LAYOUT_SKIPPED, file=sys.stderr)

        groups = run_json(
            "catalog",
            "list-item-groups",
            "--project-id",
            str(expected["project_id"]),
        )
        available_group_ids = group_external_ids(groups)
        requested_groups = {
            (group["external_id"], group["type"])
            for group in brief.get("catalog", {}).get("groups", [])
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
                "sandbox": False,
                "test_project_acknowledged": expected.get(
                    "test_project_acknowledged", False
                ),
                "test_project_allowlisted": True,
                "approval_reference": test_project_approval["approval_reference"],
            },
            "auth": {"publisher_account_active": True},
            "target": {
                "slug": slug,
                "exists": landing is not None,
                "landing_id": landing.get("_id") if landing else None,
                "type": landing.get("type") if landing else None,
                "common_layout_id": layout_id,
                "layout_step": layout_step,
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

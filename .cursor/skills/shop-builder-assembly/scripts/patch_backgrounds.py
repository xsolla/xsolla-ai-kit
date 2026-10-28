#!/usr/bin/env python3
"""Apply the background fixes after the visual review, under the plan's yes.

The developer's yes to the plan covers only `values.background` leaves on blocks that
this assembly created, as its run reports record them. Site and page themes, wording,
and blocks that existed before the run need a new yes, so this script refuses them. An
image must be one uploaded to this site, and a gradient must have the shape of one
already on the site.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from apply_plan import (
    backup_structure,
    check_cli_context,
    run_json,
    run_preflight,
    structure,
    verified_backup,
)
from render_plan import (
    canonical_hash,
    created_block_ids,
    load_approved_plan,
    load_run_report,
    structure_hash,
)
from validate_shop_brief import load_brief, validate

# The leaves of `values.background` observed with CLI 1.9.4 (visual-style.md). The
# shape of a gradient value isn't recorded, so it may be a string or an object.
BACKGROUND_LEAVES = {
    "enable": (bool,),
    "type": (str,),
    "color": (str,),
    "gradient": (str, dict),
    "img": (str,),
    "position": (str,),
    "size": (str,),
}


def load_fixes(path: Path) -> list[dict]:
    fixes = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(fixes, list) or not fixes:
        raise ValueError("the fixes file must hold a non-empty list")
    for index, fix in enumerate(fixes):
        if not isinstance(fix, dict) or set(fix) != {"block_id", "leaf", "value"}:
            raise ValueError(f"fixes[{index}] must have block_id, leaf and value only")
        if fix["leaf"] not in BACKGROUND_LEAVES:
            raise ValueError(
                f"fixes[{index}].leaf must be one of: {', '.join(BACKGROUND_LEAVES)}; "
                "anything else needs a new yes"
            )
        if not isinstance(fix["value"], BACKGROUND_LEAVES[fix["leaf"]]) or (
            fix["leaf"] != "enable" and isinstance(fix["value"], bool)
        ):
            raise ValueError(f"fixes[{index}].value has the wrong type for {fix['leaf']}")
    return fixes


def page_blocks(value: dict) -> dict[str, dict]:
    return {
        block["_id"]: block
        for page in value.get("pages", [])
        for block in page.get("blocks", [])
        if isinstance(block, dict) and isinstance(block.get("_id"), str)
    }


def asset_urls(backup_dir: Path) -> set[str]:
    """Return the URLs in the backup's asset list, where `upload-asset` adds each upload."""
    urls: set[str] = set()
    pending = [json.loads((backup_dir / "assets.json").read_text(encoding="utf-8"))]
    while pending:
        node = pending.pop()
        if isinstance(node, dict):
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)
        elif isinstance(node, str) and node.startswith("https://"):
            urls.add(node)
    return urls


def gradient_shape(value: object) -> object:
    """Return a gradient's shape: its type, and for an object its keys."""
    return tuple(sorted(value)) if isinstance(value, dict) else type(value).__name__


def site_gradient_shapes(blocks: dict[str, dict]) -> set:
    shapes = set()
    for block in blocks.values():
        background = (block.get("values") or {}).get("background")
        gradient = background.get("gradient") if isinstance(background, dict) else None
        if gradient:
            shapes.add(gradient_shape(gradient))
    return shapes


def refused_fixes(
    fixes: list[dict], blocks: dict[str, dict], created: frozenset, assets: set[str]
) -> list[str]:
    errors = []
    gradients = site_gradient_shapes(blocks)
    for fix in fixes:
        block_id = fix["block_id"]
        values = blocks.get(block_id, {}).get("values")
        if block_id not in created:
            errors.append(f"{block_id} existed before this assembly; changing it needs a new yes")
        elif block_id not in blocks:
            errors.append(f"{block_id} is not on the site")
        elif not isinstance(values, dict) or not isinstance(values.get("background"), dict):
            errors.append(f"{block_id} has no values.background to patch")
        elif fix["leaf"] == "img" and fix["value"] and fix["value"] not in assets:
            errors.append(
                f"{block_id} img is not an asset of this site; upload it with upload-asset "
                "and back up again"
            )
        elif fix["leaf"] == "gradient" and gradient_shape(fix["value"]) not in gradients:
            errors.append(
                f"{block_id} gradient doesn't match the shape of a gradient on the site; "
                "leave gradients to the Site Builder editor"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("brief", type=Path)
    parser.add_argument("--approved-plan", type=Path, required=True)
    parser.add_argument("--run-report", type=Path, action="append", required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--fixes", type=Path, required=True)
    parser.add_argument("--approved-test-projects", type=Path)
    args = parser.parse_args()
    try:
        brief = load_brief(args.brief)
        errors = validate(brief)
        if errors:
            raise RuntimeError("invalid shop brief: " + "; ".join(errors))
        approved = load_approved_plan(args.approved_plan)
        if approved.get("brief_sha256") != canonical_hash(brief):
            raise RuntimeError("the shop brief changed after the plan was approved")
        reports = [load_run_report(path) for path in args.run_report]
        slug = brief["site"]["slug"]
        for path, report in zip(args.run_report, reports):
            if (
                report.get("approved_confirmation_id") != approved["confirmation_id"]
                or report.get("slug") != slug
            ):
                raise RuntimeError(f"{path} is not a run under the approved plan")
        fixes = load_fixes(args.fixes)
        run_preflight(args.brief, args.approved_test_projects)
        check_cli_context(brief["project"])

        if not verified_backup(args.backup_dir, brief["project"], slug):
            raise RuntimeError("a complete verified backup taken before the fixes is required")
        current = structure(slug)
        if structure_hash(current) != structure_hash(backup_structure(args.backup_dir)):
            raise RuntimeError("the site changed after the backup; back up again")
        landing_id = current.get("_id")
        if not isinstance(landing_id, str) or any(
            report.get("landing_id") != landing_id for report in reports
        ):
            raise RuntimeError("the site isn't the one the run reports describe")

        created = frozenset().union(*(created_block_ids(report) for report in reports))
        blocks = page_blocks(current)
        refused = refused_fixes(fixes, blocks, created, asset_urls(args.backup_dir))
        if refused:
            raise RuntimeError("; ".join(refused) + ". Nothing was written")

        patches_by_block: dict[str, list[dict]] = {}
        for fix in fixes:
            background = blocks[fix["block_id"]]["values"]["background"]
            patches_by_block.setdefault(fix["block_id"], []).append(
                {
                    "op": "replace" if fix["leaf"] in background else "add",
                    "path": ["values", "background", fix["leaf"]],
                    "value": fix["value"],
                }
            )
        for block_id, patches in patches_by_block.items():
            run_json(
                "shopbuilder",
                "update-block",
                "--landing-id",
                landing_id,
                "--data",
                json.dumps(
                    {"background": {"type": "block", "id": block_id, "patches": patches}},
                    separators=(",", ":"),
                ),
            )

        saved = page_blocks(structure(slug))
        missing = [
            f"{fix['block_id']} {fix['leaf']}"
            for fix in fixes
            if saved.get(fix["block_id"], {}).get("values", {}).get("background", {}).get(
                fix["leaf"]
            )
            != fix["value"]
        ]
        if missing:
            raise RuntimeError("background fixes did not persist: " + ", ".join(missing))
        print(
            json.dumps(
                {
                    "operation_succeeded": True,
                    "slug": slug,
                    "patched": [
                        {"block_id": fix["block_id"], "leaf": fix["leaf"]} for fix in fixes
                    ],
                    "published": False,
                },
                indent=2,
            )
        )
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Background fixes failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

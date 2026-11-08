#!/usr/bin/env python3
"""Render one plan for a batch: every page that appears or changes, its blocks, versions,
bindings, row content, SEO and page look. Writes nothing.

The plan is rendered from the backup's structure. Its confirmation_id binds the user's yes to
exactly this plan; apply refuses an edited plan, a different backup, or a changed site.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import backup  # noqa: E402
import cli_gate  # noqa: E402
import plan_checks  # noqa: E402
import plan_model  # noqa: E402
import verify_pages  # noqa: E402
import xla_common as common  # noqa: E402


def create_ops(expected: dict) -> list[dict]:
    route = expected["route"]
    paths = next((c for c in expected["connections"] if c["kind"] == "path"), None)
    ops = [{
        "op": "create_page",
        "route": route,
        "name": expected["name"],
        "kind": expected["kind"],
        "paths": {"provider": paths["provider"], "input": paths["input"]} if paths else None,
    }]
    for conn in expected["connections"]:
        if conn["kind"] == "value" and not conn["linked"]:
            ops.append({
                "op": "add_data_connection", "route": route, "key": conn["key"],
                "provider": conn["provider"], "kind": conn["kind"], "input": conn["input"],
            })
    for index, block in enumerate(expected["blocks"]):
        ops.append({
            "op": "add_block", "route": route, "key": block["key"],
            "package": block["package"], "version": block["version"], "index": index,
        })
        for field, value in block["fields"].items():
            ops.append({"op": "set_block_field", "route": route, "key": block["key"], "field": field, "value": value})
        for field, bind in block["bindings"].items():
            ops.append({"op": "bind_field", "route": route, "key": block["key"], "field": field, **bind})
    for field, value in expected["seo"].items():
        ops.append({"op": "set_page_seo", "route": route, "field": field, **value})
    for key, value in expected["look"].items():
        ops.append({"op": "set_page_look", "route": route, "key": key, "value": value})
    return ops


def update_ops(expected: dict, page: dict, localization: dict, locale: str) -> list[dict]:
    """Only what an update may change: row content, settings, hiding an empty optional block,
    adding a missing unbound block, static SEO text and the page look. Bindings stay as they are."""
    route = expected["route"]
    ops = []
    current = {}
    for block in page.get("blocks") or []:
        package = common.block_identity(block)[0]
        if package and package not in current:
            current[package] = block
    order = [common.block_identity(b)[0] for b in page.get("blocks") or []]
    for want in expected["blocks"]:
        block = current.get(want["package"])
        if block is None:
            if want["bindings"] or want["hidden"]:
                continue
            before = [b["package"] for b in expected["blocks"][: expected["blocks"].index(want)]]
            index = max((order.index(p) + 1 for p in before if p in order), default=0)
            order.insert(index, want["package"])
            ops.append({
                "op": "add_block", "route": route, "key": want["key"],
                "package": want["package"], "version": want["version"], "index": index,
            })
            for field, value in want["fields"].items():
                ops.append({"op": "set_block_field", "route": route, "key": want["key"], "field": field, "value": value})
            continue
        fields = common.block_fields(block)
        for field, value in want["fields"].items():
            if fields.get(field) != value:
                ops.append({"op": "set_block_field", "route": route, "key": want["key"], "field": field, "value": value})
        if want["hidden"] and block.get("hidden") is not True:
            ops.append({"op": "hide_block", "route": route, "key": want["key"]})
    seo = common.page_seo(page, localization, locale)
    for field, value in expected["seo"].items():
        if "value" in value and seo.get(field) != {"value": value["value"]}:
            ops.append({"op": "set_page_seo", "route": route, "field": field, **value})
    for key, value in expected["look"].items():
        if page.get(key) != value:
            ops.append({"op": "set_page_look", "route": route, "key": key, "value": value})
    return ops


def plan_page(manifest: dict, config: dict, structure: dict, localization: dict, type_name: str,
              row: dict | None) -> tuple[dict, list[str], list[str]]:
    route = common.route_for(manifest, type_name, row.get("provider") if row else None)
    existing = common.find_page(structure, route)
    expected, errors, notes = plan_model.desired_page(manifest, config, structure, type_name, row, existing)
    if existing is None:
        ops, action, now = create_ops(expected), "create", []
    else:
        locale = common.site_locale(manifest)
        ops = update_ops(expected, existing, localization, locale)
        action = "update" if ops else "unchanged"
        now = verify_pages.compare_page(expected, existing, structure, localization, locale)[0]
    return {
        "page_type": type_name,
        "route": route,
        "provider": expected["provider"],
        "action": action,
        "page_id": existing.get("_id") if existing else None,
        "expected": expected,
        "ops": ops,
        "differences_now": now,
    }, errors, notes


def build_plan(manifest: dict, config: dict, structure: dict, batch: dict,
               localization: dict) -> tuple[dict, list[str]]:
    structure, localization = common.data(structure), common.data(localization)
    rows, errors = plan_model.batch_rows(batch)
    try:
        common.check_target(structure, config)
    except common.CliError as exc:
        errors.append(str(exc))
    if common.site_connections(structure) is None:
        errors.append(
            "get-structure returned no valuesSystem.dataProviderConnections, so the pages' data "
            "connections can't be read (references/cli-gaps.md, read-back)"
        )
    pages, notes = [], []
    work = [("game", None)] + [
        (type_name, row) for row in rows if isinstance(row, dict) for type_name in ("payment_provider", "combined")
    ]
    if not errors:
        for type_name, row in work:
            page, page_errors, page_notes = plan_page(manifest, config, structure, localization, type_name, row)
            pages.append(page)
            errors += [f"{page['route']}: {e}" for e in page_errors if f"{page['route']}: {e}" not in errors]
            notes += [n for n in page_notes if n not in notes]
    plan = {
        "version": 1,
        "skill": "xla-pages",
        "target": {
            "merchant_id": config["merchant_id"],
            "project_id": config["project_id"],
            "site_slug": config["site_slug"],
            "landing_id": structure.get("_id"),
            "published": common.is_published(structure),
        },
        "manifest_sha256": common.canonical_hash(manifest),
        "structure_sha256": common.structure_hash(structure),
        "localization_sha256": common.canonical_hash(localization),
        "rows": rows,
        "pages": pages,
        "notes": notes,
        "never": ["publish", "write to the catalog or LiveOps", "write to the XLA Pages API"],
    }
    plan["capabilities"] = cli_gate.needed(plan)
    if not errors:
        errors += [e["message"] for e in plan_checks.validate(plan, manifest, config, structure)]
    plan["confirmation_id"] = common.confirmation_id(plan)
    return plan, errors


def summary(plan: dict) -> list[str]:
    lines = []
    for page in plan["pages"]:
        blocks = ", ".join(f"{b['package']}@{b['version']}" for b in page["expected"]["blocks"])
        lines.append(f"{page['action']} {page['route']} ({page['page_type']}, {len(page['ops'])} writes): {blocks}")
        lines += [f"  now: {d}" for d in page["differences_now"]]
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True, type=Path)
    parser.add_argument("--backup-dir", required=True, type=Path, help="the folder backup.py wrote")
    parser.add_argument("--config", type=Path, default=common.DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, help="write the plan here instead of stdout")
    args = parser.parse_args(argv)
    try:
        config = common.load_config(args.config)
        manifest = common.load_manifest()
        structure = backup.load(args.backup_dir, config)
        localization = backup.load_localization(args.backup_dir, config)
        plan, errors = build_plan(manifest, config, structure, common.load_json(args.batch, "batch"), localization)
    except (OSError, ValueError) as exc:
        print(f"Plan failed: {exc}", file=sys.stderr)
        return 1
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2, ensure_ascii=False))
        return 1
    if args.output:
        common.write_json(args.output, plan)
    else:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
    print("\n".join(summary(plan)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

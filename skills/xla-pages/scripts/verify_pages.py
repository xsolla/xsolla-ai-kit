#!/usr/bin/env python3
"""Read the pages back and compare them with the plan's manifest pages, one report per page.

For each page: pass, or the exact difference (blocks, order, versions, hidden flags, fields,
bindings, data connections, SEO, page look). For a page that existed before the run, the set
of data bindings must be identical before and after. Also computes the manifest's acceptance
numbers. Reads the Site Builder shapes xla_common describes: site-level data connections,
"#VC:" bound values and SEO texts in the localization.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import plan_checks  # noqa: E402
import xla_common as common  # noqa: E402


def connection_identity(conn: dict) -> tuple:
    return (conn.get("provider"), common.canonical_hash(conn.get("input")))


def describe_connection(conn: dict | None) -> str:
    if not conn:
        return "an unknown connection"
    return f"{conn.get('provider')} {json.dumps(conn.get('input'), sort_keys=True)}"


def binding_set(page: dict | None, structure: dict, localization: dict, locale: str) -> list[tuple]:
    """Every data binding on the page, by block package, field, connection and output."""
    if not page:
        return []
    by_id = common.all_connections(structure)
    found = []
    for block in page.get("blocks") or []:
        package = common.block_identity(block)[0] or common.block_label(block)
        for field, binding in sorted(common.block_bindings(block).items()):
            found.append((package, field, describe_connection(by_id.get(binding["connection"])), binding["output"]))
    for field, value in sorted(common.page_seo(page, localization, locale).items()):
        if "connection" in value:
            found.append(("seo", field, describe_connection(by_id.get(value["connection"])), value["output"]))
    return sorted(found)


def compare_page(expected: dict, page: dict | None, structure: dict, localization: dict,
                 locale: str) -> tuple[list[str], dict]:
    counts = {"outside": 0, "custom": 0, "hand_typed": 0}
    if page is None:
        return [f"the page {expected['route']} is missing"], counts
    if common.site_connections(structure) is None:
        return ["get-structure returned no valuesSystem, so data connections can't be read"], counts
    diffs: list[str] = []
    by_id = common.all_connections(structure)
    connections = common.page_connections(structure, page)
    wanted = {conn["key"]: conn for conn in expected["connections"]}
    actual_ids = [connection_identity(c) for c in connections]
    for key, conn in wanted.items():
        if connection_identity(conn) not in actual_ids:
            diffs.append(f"missing data connection {key} ({describe_connection(conn)})")
    wanted_ids = [connection_identity(c) for c in wanted.values()]
    for conn in connections:
        if connection_identity(conn) not in wanted_ids:
            diffs.append(f"extra data connection {describe_connection(conn)}")

    def bound_right(actual: dict | None, want: dict) -> bool:
        conn = by_id.get(actual.get("connection")) if isinstance(actual, dict) else None
        want_conn = wanted.get(want["source"])
        return (
            conn is not None
            and want_conn is not None
            and connection_identity(conn) == connection_identity(want_conn)
            and actual.get("output") == want["output"]
        )

    expected_packages = [block["package"] for block in expected["blocks"]]
    seen: dict[str, dict] = {}
    order: list[str] = []
    for index, block in enumerate(page.get("blocks") or []):
        package = common.block_identity(block)[0]
        if common.has_custom_code(block):
            counts["custom"] += 1
            diffs.append(f"block {index + 1} ({common.block_label(block)}) is custom code")
        if package not in expected_packages or package in seen:
            counts["outside"] += 1
            diffs.append(f"block {index + 1} ({common.block_label(block)}) is outside the manifest")
            continue
        seen[package] = block
        order.append(package)

    for want in expected["blocks"]:
        package = want["package"]
        block = seen.get(package)
        if block is None:
            diffs.append(f"missing block {package}@{want['version']}")
            continue
        version = common.block_identity(block)[1]
        if version != want["version"]:
            diffs.append(f"{package}: expected version {want['version']}, got {version}")
        hidden = block.get("hidden") is True
        if hidden != want["hidden"]:
            diffs.append(
                f"{package}: expected {'hidden' if want['hidden'] else 'visible'}, "
                f"got {'hidden' if hidden else 'visible'}"
            )
        fields = common.block_fields(block)
        for field, value in want["fields"].items():
            if fields.get(field) != value:
                diffs.append(f"{package} field {field}: expected {value!r}, got {fields.get(field)!r}")
        bindings = common.block_bindings(block)
        for field, bind in want["bindings"].items():
            actual = bindings.get(field)
            label = f"{bind['source']}.{bind['output']}"
            if actual is None:
                diffs.append(f"{package} field {field}: expected binding {label}, got none")
                if fields.get(field) not in (None, "", [], {}):
                    counts["hand_typed"] += 1
                    diffs.append(f"{package} field {field}: holds a typed value instead of {label}")
            elif not bound_right(actual, bind):
                diffs.append(
                    f"{package} field {field}: expected binding {label}, got "
                    f"{describe_connection(by_id.get(actual['connection']))}.{actual['output']}"
                )
            elif common.block_usage(block.get("_id")) not in by_id[actual["connection"]]["usedBy"]:
                diffs.append(f"{package} field {field}: its connection doesn't list the block in usedBy")
        for field in sorted(set(bindings) - set(want["bindings"])):
            diffs.append(f"{package} field {field}: bound, but the manifest lists no binding for it")

    expected_order = [package for package in expected_packages if package in seen]
    if order != expected_order:
        diffs.append(f"block order differs: expected {expected_order}, got {order}")

    seo = common.page_seo(page, localization, locale)
    for field, want in expected["seo"].items():
        actual = seo.get(field)
        if "value" in want:
            got = actual.get("value") if isinstance(actual, dict) else None
            if got != want["value"]:
                diffs.append(f"seo {field}: expected {want['value']!r}, got {got!r}")
        elif not bound_right(actual, want):
            diffs.append(f"seo {field}: expected binding {want['source']}.{want['output']}, got {actual!r}")
    for key, value in expected["look"].items():
        if page.get(key) != value:
            diffs.append(f"page {key} differs from the reference page")
    return diffs, counts


def verify(plan: dict, structure: dict, before: dict, manifest: dict, config: dict,
           localization: dict, before_localization: dict) -> dict:
    structure, before = common.data(structure), common.data(before)
    localization, before_localization = common.data(localization), common.data(before_localization)
    locale = common.site_locale(manifest)
    style = sum(1 for e in plan_checks.validate(plan, manifest, config, before) if e["category"] == "style")
    pages, totals = [], {"outside": 0, "custom": 0, "hand_typed": 0}
    for planned in plan.get("pages") or []:
        page = common.find_page(structure, planned["route"])
        diffs, counts = compare_page(planned["expected"], page, structure, localization, locale)
        if planned.get("action") != "create":
            old = binding_set(common.find_page(before, planned["route"]), before, before_localization, locale)
            new = binding_set(page, structure, localization, locale)
            if old != new:
                removed = [b for b in old if b not in new]
                added = [b for b in new if b not in old]
                diffs.append(f"the page's data bindings changed: removed {removed}, added {added}")
        for key in totals:
            totals[key] += counts[key]
        pages.append({
            "route": planned["route"],
            "page_type": planned["page_type"],
            "action": planned.get("action"),
            "ok": not diffs,
            "differences": diffs,
        })
    matching = sum(1 for page in pages if page["ok"])
    percent = round(100 * matching / len(pages)) if pages else 100
    acceptance = {
        "blocks_outside_manifest": totals["outside"],
        "theme_or_style_patches": style,
        "custom_code_items": totals["custom"],
        "hand_typed_game_data_fields": totals["hand_typed"],
        "pages_matching_manifest": f"{percent}%",
    }
    ok = matching == len(pages) and style == 0 and not any(totals.values())
    return {
        "ok": ok,
        "confirmation_id": plan.get("confirmation_id"),
        "published": common.is_published(structure),
        "pages": pages,
        "acceptance": acceptance,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--structure", required=True, type=Path, help="get-structure after the writes")
    parser.add_argument("--localization", required=True, type=Path, help="get-localization after the writes")
    parser.add_argument("--backup-dir", required=True, type=Path, help="the backup taken before the writes")
    parser.add_argument("--config", type=Path, default=common.DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    try:
        import backup  # noqa: PLC0415

        config = common.load_config(args.config)
        result = verify(
            common.load_json(args.plan, "plan"),
            common.load_json(args.structure, "structure"),
            backup.load(args.backup_dir, config),
            common.load_manifest(),
            config,
            common.load_json(args.localization, "localization"),
            backup.load_localization(args.backup_dir, config),
        )
    except (OSError, ValueError, KeyError) as exc:
        print(f"Verification failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

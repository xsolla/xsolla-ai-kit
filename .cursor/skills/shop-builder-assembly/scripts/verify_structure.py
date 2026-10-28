#!/usr/bin/env python3
"""Compare a confirmed assembly plan with a read-only Shop Builder structure.

get-structure lists site-level blocks by ID only, so the command line reads the
module of each site layout with read-only `xsolla shopbuilder get-block`.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from block_ops import (
    QUESTS_DEV_NAME,
    QUESTS_MODULE,
    QUESTS_VERSION,
    card_text_ref,
)
import cli_environment
from preflight import LAYOUT_SKIPPED, cli_has_command, run_json, site_block_module
from render_plan import (
    canonical_hash,
    common_layout_id,
    effective_module,
    page_path,
    stable_structure,
    structure_data,
)


def load_object(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read valid {label} JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def same_identifier(actual: object, expected: object) -> bool:
    if isinstance(actual, (str, int)) and not isinstance(actual, bool):
        if isinstance(expected, (str, int)) and not isinstance(expected, bool):
            return str(actual) == str(expected)
    return False


_MISSING = object()


def _read(root: object, path: list) -> object:
    node = root
    for segment in path:
        if isinstance(node, dict) and segment in node:
            node = node[segment]
        else:
            return _MISSING
    return node


def _page_blocks(current: dict) -> dict[str, tuple[str, int, dict]]:
    found = {}
    for page in current.get("pages") or []:
        if not isinstance(page, dict):
            continue
        for index, block in enumerate(page.get("blocks") or []):
            if isinstance(block, dict) and isinstance(block.get("_id"), str):
                found[block["_id"]] = (page.get("_id"), index, block)
    return found


def _localized_text(localization: dict, text_id: str, locale: str) -> object:
    namespaces = [(localization.get("common") or {})]
    namespaces += list((localization.get("pages") or {}).values())
    for namespace in namespaces:
        entry = (namespace.get("texts") or {}).get(text_id)
        if isinstance(entry, dict):
            return (entry.get("translations") or {}).get(locale, _MISSING)
    return _MISSING


def _text_id(block: dict, key: str) -> str | None:
    values = block.get("values") or {}
    short = ((values.get("internalBlockValues") or {}).get("translations") or {}).get(key)
    texts = (((values.get("resources") or {}).get("localizedValues") or {}).get(short) or {}).get(
        "texts"
    )
    text_id = texts.get("id") if isinstance(texts, dict) else None
    return text_id if isinstance(text_id, str) else None


def verify_block_operations(
    plan: dict, structure: object, localization: object, refs: dict | None = None
) -> list[str]:
    """Return what differs between a block-operations plan and the live site.

    Checks that every planned leaf reads back equal, the final block order on each
    touched page matches the plan, and every block
    the plan does not target is unchanged from the backup (the plan carries a digest
    of each page block). ``refs`` maps the plan's
    ``op:N`` / ``dup:N`` names to the ids of blocks the run created; without it a new
    block is resolved only when it is the single unplanned block on its page.
    """
    errors: list[str] = []
    current = structure_data(structure)
    loc = structure_data(localization) if localization is not None else {}
    refs = dict(refs or {})
    state = plan.get("current_state") or {}
    digests = state.get("block_sha256") or {}
    order = state.get("block_order") or {}
    items = plan.get("block_operations") or []
    blocks = _page_blocks(current)

    placeholders = {item["block_ref"] for item in items if item["type"] == "block_add"}
    placeholders |= {f"dup:{item['op_index']}" for item in items if item["type"] == "block_duplicate"}

    def resolve(name: str, page_id: object) -> str | None:
        if refs.get(name) in blocks:
            return refs[name]
        taken = set(refs.values())
        candidates = [
            block_id
            for block_id, (owner, _, _) in blocks.items()
            if owner == page_id and block_id not in digests and block_id not in taken
        ]
        return candidates[0] if len(candidates) == 1 else None

    def target(item: dict) -> str | None:
        if item.get("block_id"):
            return item["block_id"]
        return resolve(item["block_ref"], item.get("page_id") or _ref_page(item))

    def _ref_page(item: dict) -> object:
        for other in items:
            if other.get("block_ref") == item.get("block_ref") and other.get("page_id"):
                return other["page_id"]
        return None

    simulated = {page_id: list(ids) for page_id, ids in order.items()}
    touched: set = set()
    targets: set = set()
    hidden: dict[str, bool] = {}
    for item in items:
        kind = item["type"]
        page_id = item.get("page_id")
        if kind == "block_add":
            simulated.setdefault(page_id, []).insert(item["index"], item["block_ref"])
            touched.add(page_id)
        elif kind == "block_duplicate":
            simulated.setdefault(page_id, []).insert(item["index"], f"dup:{item['op_index']}")
            touched.add(page_id)
        elif kind == "block_move":
            ids = simulated.setdefault(page_id, [])
            if item["block_id"] in ids:
                ids.remove(item["block_id"])
                ids.insert(item["index"], item["block_id"])
            touched.add(page_id)
        elif kind == "block_visibility":
            hidden[item["block_id"]] = item["hidden"]
        if kind != "block_duplicate":
            block_id = target(item)
            if block_id:
                targets.add(block_id)

    for page_id in sorted(touched, key=str):
        page = next((p for p in current.get("pages") or [] if p.get("_id") == page_id), None)
        if page is None:
            errors.append(f"page {page_id} is missing")
            continue
        actual = [b.get("_id") for b in page.get("blocks") or []]
        expected = simulated.get(page_id, [])
        if len(actual) != len(expected):
            errors.append(
                f"page {page_id} has {len(actual)} blocks, expected {len(expected)}"
            )
            continue
        for position, (want, got) in enumerate(zip(expected, actual)):
            if want in placeholders:
                ok = refs[want] == got if want in refs else got not in digests
            else:
                ok = want == got
            if not ok:
                errors.append(f"block order differs at {page_id}[{position}]: got {got}")

    for item in items:
        kind = item["type"]
        block_id = target(item)
        if block_id is None or block_id not in blocks:
            errors.append(f"{kind} op {item['op_index']}: the block cannot be found")
            continue
        block = blocks[block_id][2]
        values = block.get("values") or {}
        if kind == "block_add":
            if values.get("blockId") != QUESTS_MODULE or values.get("version") != item.get(
                "version", QUESTS_VERSION
            ):
                errors.append(f"new block {block_id} is not a Quests block at the planned version")
            if values.get("useAsNativeBlock") is not False:
                errors.append(f"new block {block_id} has useAsNativeBlock set")
            if block.get("devName") != QUESTS_DEV_NAME:
                errors.append(f"new block {block_id} has devName {block.get('devName')!r}")
        elif kind == "block_values":
            for patch in item["patches"]:
                got = _read(block, patch["path"])
                if got != patch["value"]:
                    errors.append(
                        f"{block_id} {patch['key']} reads back {got!r}, expected {patch['value']!r}"
                    )
        elif kind == "block_reset":
            for patch in item["patches"]:
                if _read(block, patch["path"]) is not _MISSING:
                    errors.append(f"{block_id} {patch['key']} is still set after reset")
        elif kind == "block_visibility":
            if hidden.get(block_id) is not None and block.get("hidden") is not hidden[block_id]:
                errors.append(f"{block_id} hidden is {block.get('hidden')!r}, expected {hidden[block_id]!r}")
        elif kind == "block_card_text":
            for entry in item["texts"]:
                _, text_id = card_text_ref(block, entry["quest_id"], entry["field"])
                for locale in item["locales"]:
                    got = _localized_text(loc, text_id, locale) if text_id else _MISSING
                    if got != entry["text"]:
                        errors.append(
                            f"{block_id} {entry['ref_key']} editor text ({locale}) reads "
                            f"back {got!r}, expected {entry['text']!r}"
                        )
        elif kind == "block_localization":
            for locale, texts in item["translations"].items():
                for key, text in texts.items():
                    text_id = _text_id(block, key)
                    got = _localized_text(loc, text_id, locale) if text_id else _MISSING
                    if got != text:
                        errors.append(
                            f"{block_id} {key} ({locale}) reads back {got!r}, expected {text!r}"
                        )

    for block_id, digest in sorted(digests.items()):
        if block_id in targets:
            continue
        if block_id not in blocks:
            errors.append(f"non-target block {block_id} is missing")
        elif canonical_hash(stable_structure(blocks[block_id][2])) != digest:
            errors.append(f"non-target block {block_id} changed since the backup")
    return errors


def verify(
    plan: dict,
    structure: object,
    module_of: Callable[[str], object] | None = None,
    layout_required: bool = True,
    localization: object = None,
) -> dict:
    """``layout_required`` is False when the CLI has no create-block, so assembly
    skipped the layout step. ``localization`` is the get-localization output a
    block-operations plan reads heading texts back from."""
    if plan.get("mode") == "block_operations":
        errors = verify_block_operations(plan, structure, localization)
        current = structure_data(structure)
        return {
            "ok": not errors,
            "confirmation_id": plan.get("confirmation_id"),
            "slug": (plan.get("target") or {}).get("slug"),
            "errors": errors,
            "warnings": [],
            "published": current.get("published") not in (None, False),
        }
    errors: list[str] = []
    warnings: list[str] = []
    current = structure_data(structure)
    target = plan.get("target")
    pages = plan.get("pages")
    if not isinstance(target, dict) or not isinstance(pages, list):
        raise ValueError("plan must contain target and pages")

    if not same_identifier(current.get("merchantId"), target.get("merchant_id")):
        errors.append("merchant ID does not match the confirmed plan")
    if not same_identifier(current.get("projectId"), target.get("project_id")):
        errors.append("project ID does not match the confirmed plan")
    if current.get("domain") != target.get("slug"):
        errors.append("site slug does not match the confirmed plan")
    if current.get("type") != "store":
        errors.append("landing type is not store")
    if current.get("published") not in (None, False):
        errors.append("test landing is published")

    if plan.get("site_layout"):
        try:
            if common_layout_id(current, module_of) is None:
                if layout_required:
                    errors.append("site-level common layout is missing")
                else:
                    warnings.append(LAYOUT_SKIPPED)
        except ValueError as exc:
            errors.append(f"site-level common layout is inconsistent: {exc}")

    current_pages = current.get("pages")
    if not isinstance(current_pages, list):
        raise ValueError("structure.pages must be a list")
    by_path = {
        page_path(page): page
        for page in current_pages
        if page_path(page) is not None
    }
    if any(
        not isinstance(page, dict) or not isinstance(page.get("path"), str)
        for page in pages
    ):
        raise ValueError("plan pages must have string paths")
    desired_paths = [page["path"] for page in pages]
    expected_navigation_ids = [
        target.get("page_id") for target in plan.get("navigation", [])
    ]
    if set(by_path) != set(desired_paths):
        errors.append(
            "page paths differ: expected "
            f"{sorted(desired_paths)}, got {sorted(by_path)}"
        )

    page_results: list[dict] = []
    for page_plan in pages:
        path = page_plan.get("path")
        page = by_path.get(path)
        if not isinstance(page, dict):
            page_results.append({"path": path, "ok": False, "error": "missing page"})
            continue
        blocks = page.get("blocks")
        if not isinstance(blocks, list) or any(
            not isinstance(block, dict) for block in blocks
        ):
            raise ValueError(f"structure page {path} has an invalid blocks list")
        actual_modules = [effective_module(block) for block in blocks]
        expected_modules = page_plan.get("blocks")
        page_ok = actual_modules == expected_modules
        if not page_ok:
            errors.append(
                f"block order differs on {path}: expected {expected_modules}, "
                f"got {actual_modules}"
            )
        actual_by_id = {
            block.get("_id"): effective_module(block)
            for block in blocks
            if isinstance(block.get("_id"), str)
        }
        for preserved in page_plan.get("preserved_blocks", []):
            if actual_by_id.get(preserved.get("block_id")) != preserved.get("module"):
                errors.append(
                    f"preserved block {preserved.get('block_id')} is missing on {path}"
                )
        for removal in page_plan.get("removals", []):
            if removal.get("block_id") in actual_by_id:
                errors.append(
                    f"confirmed removal {removal.get('block_id')} still exists on {path}"
                )
        expected_sections = [
            (
                section.get("external_id"),
                section.get("type"),
                section.get("layout"),
                True,
            )
            for section in plan.get("catalog_sections", [])
        ]
        for block in blocks:
            if effective_module(block) != "newStore" or not expected_sections:
                continue
            actual_sections = []
            for component in block.get("components", []):
                section = component.get("section", {})
                item = section.get("item", {})
                card = component.get("card", {})
                actual_sections.append(
                    (
                        item.get("group"),
                        item.get("type"),
                        card.get("selectedLayoutType"),
                        component.get("enable"),
                    )
                )
            if actual_sections != expected_sections:
                errors.append(
                    f"catalog sections differ on {path}: expected {expected_sections}, "
                    f"got {actual_sections}"
                )
        header = next(
            (block for block in blocks if effective_module(block) == "header"), None
        )
        if isinstance(header, dict) and expected_navigation_ids:
            values = header.get("values", {})
            components = values.get("components", {})
            right = values.get("rightComponents", [])
            actual_navigation_ids = [
                components[component_id]
                .get("button", {})
                .get("action", {})
                .get("pageId")
                for component_id in right
                if isinstance(components.get(component_id), dict)
                and components[component_id].get("type") == "button"
                and components[component_id]
                .get("button", {})
                .get("action", {})
                .get("action")
                == "page"
            ]
            if actual_navigation_ids != expected_navigation_ids:
                errors.append(
                    f"navigation differs on {path}: expected {expected_navigation_ids}, "
                    f"got {actual_navigation_ids}"
                )
        page_results.append(
            {"path": path, "ok": page_ok, "blocks": actual_modules}
        )

    languages = current.get("languages")
    requested_locales = plan.get("locales")
    if (
        not isinstance(languages, list)
        or any(not isinstance(locale, str) for locale in languages)
        or not isinstance(requested_locales, list)
        or any(not isinstance(locale, str) for locale in requested_locales)
    ):
        errors.append("structure or plan has an invalid locale list")
    else:
        missing_locales = sorted(set(requested_locales) - set(languages))
        if missing_locales:
            errors.append("missing requested locales: " + ", ".join(missing_locales))

    return {
        "ok": not errors,
        "confirmation_id": plan.get("confirmation_id"),
        "slug": target.get("slug"),
        "pages": page_results,
        "requested_locales": requested_locales,
        "errors": errors,
        "warnings": warnings,
        "published": current.get("published") not in (None, False),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--structure", required=True, type=Path)
    parser.add_argument(
        "--localization",
        type=Path,
        help="get-localization output; read back heading texts of block operations",
    )
    args = parser.parse_args()
    try:
        plan = load_object(args.plan, "plan")
        target = plan.get("target") or {}
        slug = target.get("slug")
        # The CLI reads below use the sandbox-off environment preflight settled.
        cli_environment.select(target, run_json, switch=False)
        result = verify(
            plan,
            load_object(args.structure, "structure"),
            lambda block_id: site_block_module(slug, block_id),
            layout_required=cli_has_command("shopbuilder", "create-block"),
            localization=(
                load_object(args.localization, "localization") if args.localization else None
            ),
        )
    except (RuntimeError, ValueError) as exc:
        print(f"Structure verification failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

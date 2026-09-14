#!/usr/bin/env python3
"""Render a deterministic, non-mutating assembly plan from a shop brief."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

from validate_shop_brief import load_brief, validate

PRESET_PAGES = {
    "mobile-single-page": [
        {
            "name": "Home",
            "path": "/",
            "blocks": ["header", "leadGameSales", "newStore", "faq", "footer"],
        }
    ],
    "pc-multi-page": [
        {
            "name": "Home",
            "path": "/",
            "blocks": ["header", "leadGameSales", "description", "gallery", "footer"],
        },
        {
            "name": "Store",
            "path": "/store",
            "blocks": ["header", "newStore", "faq", "footer"],
        },
        {
            "name": "About",
            "path": "/about",
            "blocks": ["header", "description", "requirements", "faq", "footer"],
        },
    ],
    "live-service-events": [
        {
            "name": "Home",
            "path": "/",
            "blocks": [
                "header",
                "leadGameSales",
                "newStore",
                "gallery",
                "faq",
                "footer",
            ],
        },
        {
            "name": "Store",
            "path": "/store",
            "blocks": ["header", "newStore", "faq", "footer"],
        },
        {
            "name": "Events",
            "path": "/events",
            "blocks": ["header", "leadGameSales", "newStore", "description", "footer"],
        },
    ],
}


def choose_preset(brief: dict) -> str:
    requested = brief["site"]["preset"]
    if requested != "auto":
        return requested
    game = brief["game"]
    if game["lifecycle"] == "live-service" or brief.get("content", {}).get("events"):
        return "live-service-events"
    if set(game["platforms"]) & {"pc", "console"}:
        return "pc-multi-page"
    return "mobile-single-page"


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def stable_structure(value: object) -> object:
    """Remove only API-generated component IDs from a structure fingerprint.

    Shop Builder regenerates the ``_id`` of entries inside ``components`` arrays on
    every read. Those IDs cannot be used for optimistic concurrency because two
    consecutive reads of an unchanged site differ. Page and block IDs remain in the
    fingerprint, as do every component value and localization reference.
    """

    if isinstance(value, list):
        return [stable_structure(item) for item in value]
    if not isinstance(value, dict):
        return value

    normalized = {}
    for key, item in value.items():
        if key == "components" and isinstance(item, list):
            normalized[key] = [
                stable_structure(
                    {child_key: child_value for child_key, child_value in component.items() if child_key != "_id"}
                )
                if isinstance(component, dict)
                else stable_structure(component)
                for component in item
            ]
        else:
            normalized[key] = stable_structure(item)
    return normalized


def structure_hash(value: object) -> str:
    return canonical_hash(stable_structure(value))


def structure_data(value: object) -> dict:
    if isinstance(value, dict) and value.get("ok") is True and "data" in value:
        value = value["data"]
    if not isinstance(value, dict):
        raise ValueError("structure must contain an object")
    return value


def effective_module(block: dict) -> object:
    module = block.get("module")
    values = block.get("values")
    if module == "federated" and isinstance(values, dict):
        block_id = values.get("blockId")
        if isinstance(block_id, str) and block_id:
            return block_id
    return module


def selected_pages(brief: dict, preset: str) -> list[dict]:
    overrides = brief.get("content", {}).get("page_overrides")
    return copy.deepcopy(overrides if overrides is not None else PRESET_PAGES[preset])


def missing_data_reason(module: str, brief: dict) -> str | None:
    content = brief.get("content", {})
    catalog = brief["catalog"]
    if module == "newStore" and not catalog["groups"]:
        return "no catalog groups supplied"
    if module == "gallery" and not (content.get("gallery") or content.get("media")):
        return "no approved gallery media supplied"
    if module == "requirements" and not content.get("requirements"):
        return "no approved platform requirements supplied"
    if module == "faq" and not content.get("faq"):
        return "no approved FAQ supplied"
    if module == "description" and not (
        content.get("description") or content.get("events")
    ):
        return "no approved descriptive or event copy supplied"
    if module == "bento-grid" and not content.get("features"):
        return "no approved feature cards supplied"
    if module == "packs" and not (catalog["groups"] or catalog.get("featured_skus")):
        return "no catalog groups or featured SKUs supplied"
    return None


def catalog_sections(brief: dict, preset: str) -> list[dict]:
    """Return render-safe store sections with deterministic card layouts."""
    sections = []
    for group in brief["catalog"]["groups"]:
        placement = group["placement"]
        if placement == "featured":
            layout = "featured"
        elif placement == "secondary":
            layout = "horizontal"
        elif preset == "pc-multi-page" and group["type"] == "bundle":
            layout = "large"
        elif preset == "live-service-events" and group["type"] == "virtual_currency":
            layout = "horizontal"
        else:
            layout = "vertical"
        sections.append({**group, "layout": layout, "title_enabled": False})
    return sections


def omit_unwritable_blocks(
    pages: list[dict], brief: dict
) -> tuple[list[dict], list[dict]]:
    omissions: list[dict] = []
    for page in pages:
        page["requested_blocks"] = list(page["blocks"])
        kept: list[str] = []
        for module in page["blocks"]:
            reason = missing_data_reason(module, brief)
            if reason is None:
                kept.append(module)
            else:
                omissions.append(
                    {
                        "path": page["path"],
                        "module": module,
                        "reason": reason,
                        "action": "omit",
                    }
                )
        page["blocks"] = kept
    return pages, omissions


def bind_current_state(
    pages: list[dict], omissions: list[dict], structure: object | None
) -> dict:
    if structure is None:
        for page in pages:
            page["page_id"] = None
            page["current_blocks"] = []
            page["preserved_blocks"] = []
            page["removals"] = []
        return {
            "status": "not-supplied",
            "application_mode": "bootstrap-only",
            "structure_sha256": None,
            "extra_pages": [],
        }

    current = structure_data(structure)
    current_pages = current.get("pages")
    if not isinstance(current_pages, list):
        raise ValueError("structure.pages must be a list")
    planned_paths = {page["path"] for page in pages}
    extra_pages = []
    by_path = {}
    for page in current_pages:
        if not isinstance(page, dict) or not isinstance(page.get("path"), str):
            raise ValueError("every current page must be an object with a path")
        if page["path"] in by_path:
            raise ValueError(
                f"current structure contains duplicate path {page['path']}"
            )
        by_path[page["path"]] = page
        if page["path"] not in planned_paths:
            extra_pages.append(
                {
                    "page_id": page.get("_id"),
                    "name": page.get("name"),
                    "path": page["path"],
                }
            )

    for page_plan in pages:
        page_plan["page_id"] = None
        page_plan["current_blocks"] = []
        page_plan["preserved_blocks"] = []
        page_plan["removals"] = []
        current_page = by_path.get(page_plan["path"])
        if current_page is None:
            continue
        page_plan["page_id"] = current_page.get("_id")
        blocks = current_page.get("blocks", [])
        if not isinstance(blocks, list) or any(
            not isinstance(block, dict) for block in blocks
        ):
            raise ValueError(
                "current pages[].blocks must contain full block objects from get-structure"
            )
        omitted_on_page = {
            omission["module"]: omission
            for omission in omissions
            if omission["path"] == page_plan["path"]
        }
        current_modules = {
            effective_module(block)
            for block in blocks
            if isinstance(effective_module(block), str)
        }
        preserved_modules = set(omitted_on_page) & current_modules
        if preserved_modules:
            page_plan["blocks"] = [
                module
                for module in page_plan["requested_blocks"]
                if module in page_plan["blocks"] or module in preserved_modules
            ]
        kept: set[str] = set()
        desired = page_plan["blocks"]
        for block in blocks:
            block_id = block.get("_id")
            module = effective_module(block)
            if not isinstance(block_id, str) or not isinstance(module, str):
                raise ValueError(
                    "every current block must have string _id and module fields"
                )
            page_plan["current_blocks"].append({"block_id": block_id, "module": module})
            if module in preserved_modules and module not in kept:
                page_plan["preserved_blocks"].append(
                    {
                        "block_id": block_id,
                        "module": module,
                        "reason": omitted_on_page[module]["reason"],
                    }
                )
                omitted_on_page[module]["action"] = "preserve-existing"
                omitted_on_page[module]["block_id"] = block_id
            if module in desired and module not in kept:
                kept.add(module)
            else:
                reason = (
                    "duplicate module"
                    if module in kept
                    else "not in confirmed page plan"
                )
                page_plan["removals"].append(
                    {"block_id": block_id, "module": module, "reason": reason}
                )

    return {
        "status": "captured",
        "application_mode": "reconcile",
        "landing_id": current.get("_id"),
        "structure_sha256": canonical_hash(current),
        "extra_pages": extra_pages,
    }


def build_plan(brief: dict, current_structure: object | None = None) -> dict:
    preset = choose_preset(brief)
    catalog_groups = catalog_sections(brief, preset)
    pages, omissions = omit_unwritable_blocks(selected_pages(brief, preset), brief)
    current_state = bind_current_state(pages, omissions, current_structure)
    warnings = []
    brand = brief.get("brand", {})
    if not brand.get("logo"):
        warnings.append(
            "No logo supplied; keep the template text identity until approved."
        )
    if preset == "live-service-events" and not brief.get("content", {}).get("events"):
        warnings.append(
            "No event data supplied; omit event-specific copy and scarcity claims."
        )
    plan = {
        "version": 1,
        "target": {
            "merchant_id": brief["project"]["merchant_id"],
            "project_id": brief["project"]["project_id"],
            "environment": brief["project"]["environment"],
            "test_project_acknowledged": brief["project"].get(
                "test_project_acknowledged", False
            ),
            "site_name": brief["site"]["name"],
            "slug": brief["site"]["slug"],
        },
        "preset": preset,
        "requires_confirmation": True,
        "publication": "forbidden",
        "order": [
            "backup",
            "theme",
            "pages",
            "navigation",
            "blocks",
            "copy_assets",
            "catalog_links",
            "verify",
            "preview",
        ],
        "pages": pages,
        "navigation": [
            {"name": page["name"], "path": page["path"], "page_id": page["page_id"]}
            for page in pages
        ],
        "locales": brief["site"]["locales"],
        "primary_locale": brief["site"]["primary_locale"],
        "catalog_sections": catalog_groups,
        "featured_skus": brief["catalog"].get("featured_skus", []),
        "brand": brand,
        "content": brief.get("content", {}),
        "sources": brief["sources"],
        "omissions": omissions,
        "current_state": current_state,
        "brief_sha256": canonical_hash(brief),
        "implemented_phases": [
            "pages",
            "navigation",
            "blocks",
            "locales",
            "catalog_links",
        ],
        "unsupported_phases": [
            "theme",
            "copy_assets",
            "verify",
            "preview",
        ],
        "warnings": warnings,
    }
    plan["confirmation_id"] = "sha256:" + canonical_hash(plan)[:12]
    return plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("brief", type=Path)
    parser.add_argument(
        "--structure",
        type=Path,
        help="get-structure JSON from the verified backup of an existing target",
    )
    args = parser.parse_args()
    try:
        brief = load_brief(args.brief)
        structure = None
        if args.structure is not None:
            structure = json.loads(args.structure.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    errors = validate(brief)
    if errors:
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    try:
        plan = build_plan(brief, structure)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

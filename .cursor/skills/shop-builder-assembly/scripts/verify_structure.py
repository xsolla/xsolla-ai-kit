#!/usr/bin/env python3
"""Compare a confirmed assembly plan with a read-only Shop Builder structure."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from render_plan import effective_module, structure_data


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


def verify(plan: dict, structure: object) -> dict:
    errors: list[str] = []
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

    current_pages = current.get("pages")
    if not isinstance(current_pages, list):
        raise ValueError("structure.pages must be a list")
    by_path = {
        page.get("path"): page
        for page in current_pages
        if isinstance(page, dict) and isinstance(page.get("path"), str)
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
        "published": current.get("published") not in (None, False),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--structure", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = verify(
            load_object(args.plan, "plan"),
            load_object(args.structure, "structure"),
        )
    except ValueError as exc:
        print(f"Structure verification failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

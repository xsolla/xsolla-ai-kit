#!/usr/bin/env python3
"""Apply a confirmed Shop Builder plan without publishing the landing."""

from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

from render_plan import build_plan, effective_module, structure_data, structure_hash
from validate_shop_brief import VERIFIED_BLOCK_MODULES, load_brief, validate

BACKUP_FILE_NAMES = {
    "config.json",
    "websites.json",
    "landing.json",
    "structure.json",
    "localization.json",
    "assets.json",
    "versions.json",
}
SESSION_BOOTSTRAP_RETRY_DELAYS = (5, 10, 20)
LOGIN_SETTLE_SECONDS = 2
LOGIN_TIMEOUT_SECONDS = 45
LOGIN_RETRY_DELAY_SECONDS = 5


def refresh_supported_login() -> None:
    for attempt in range(2):
        try:
            result = subprocess.run(
                ["xsolla", "auth", "login"],
                check=False,
                timeout=LOGIN_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            if attempt == 0:
                time.sleep(LOGIN_RETRY_DELAY_SECONDS)
                continue
            raise RuntimeError("supported Publisher login refresh timed out") from None
        if result.returncode == 0:
            time.sleep(LOGIN_SETTLE_SECONDS)
            return
        if attempt == 0:
            time.sleep(LOGIN_RETRY_DELAY_SECONDS)
    raise RuntimeError("supported Publisher login refresh failed")


def run_json(*args: str) -> object:
    command = ["xsolla", *args, "--json"]
    if args and args[0] == "shopbuilder":
        refresh_supported_login()
    rate_limit_attempt = 0
    refreshed_login = False
    while True:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if not result.returncode:
            break
        detail = result.stderr.strip() or result.stdout.strip()
        retryable_bootstrap_limit = (
            "publisher session bootstrap" in detail and "HTTP 429" in detail
        )
        if retryable_bootstrap_limit and rate_limit_attempt < len(
            SESSION_BOOTSTRAP_RETRY_DELAYS
        ):
            time.sleep(SESSION_BOOTSTRAP_RETRY_DELAYS[rate_limit_attempt])
            rate_limit_attempt += 1
            continue
        missing_bootstrap_cookie = (
            "publisher session bootstrap did not yield" in detail
        )
        if missing_bootstrap_cookie and not refreshed_login:
            refresh_supported_login()
            refreshed_login = True
            continue
        if "publisher session bootstrap" in detail:
            detail += (
                "; refresh the supported Publisher login with `xsolla auth login` "
                "and rerun—never copy a browser PA token"
            )
        raise RuntimeError(f"{' '.join(args)} failed: {detail}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{' '.join(args)} returned invalid JSON") from exc


def data(value: object) -> object:
    if isinstance(value, dict) and value.get("ok") is True and "data" in value:
        return value["data"]
    return value


def website_exists(value: object, slug: str) -> bool:
    payload = data(value)
    if isinstance(payload, dict):
        payload = payload.get("items", payload.get("landings", payload))
    if isinstance(payload, list):
        return any(
            isinstance(item, dict)
            and (item.get("domain") == slug or item.get("slug") == slug)
            for item in payload
        )
    text = json.dumps(payload, sort_keys=True)
    return f'"{slug}"' in text


def structure(slug: str) -> dict:
    value = data(run_json("shopbuilder", "get-structure", "--slug", slug))
    if not isinstance(value, dict) or not isinstance(value.get("pages"), list):
        raise RuntimeError("get-structure returned an unexpected shape")
    return value


def page_for_path(value: dict, path: str) -> dict | None:
    for page in value["pages"]:
        if isinstance(page, dict) and page.get("path") == path:
            return page
    return None


def verified_backup(path: Path, expected: dict, slug: str) -> bool:
    manifest_path = path / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("slug") != slug
            or manifest.get("merchant_id") != expected["merchant_id"]
            or manifest.get("project_id") != expected["project_id"]
            or manifest.get("environment") != expected["environment"]
            or manifest.get("read_only") is not True
        ):
            return False
        files = manifest.get("files")
        digests = manifest.get("sha256")
        if (
            not isinstance(files, list)
            or not files
            or any(
                not isinstance(name, str) or Path(name).name != name for name in files
            )
            or len(files) != len(set(files))
            or set(files) != BACKUP_FILE_NAMES
            or not isinstance(digests, dict)
            or set(files) != set(digests)
        ):
            return False
        for name in files:
            digest = digests[name]
            if not isinstance(digest, str):
                return False
            file_path = path / name
            if hashlib.sha256(file_path.read_bytes()).hexdigest() != digest:
                return False
        return True
    except (OSError, TypeError, json.JSONDecodeError):
        return False


def backup_structure(path: Path) -> object:
    try:
        value = json.loads((path / "structure.json").read_text(encoding="utf-8"))
        return structure_data(value)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read backup structure: {exc}") from exc


def run_preflight(brief_path: Path, approved_test_projects: Path | None) -> None:
    command = [
        sys.executable,
        str(Path(__file__).with_name("preflight.py")),
        str(brief_path),
    ]
    if approved_test_projects is not None:
        command.extend(["--approved-test-projects", str(approved_test_projects)])
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            result.stderr.strip() or result.stdout.strip() or "preflight failed"
        )


def reconcile_page(slug: str, landing_id: str, page_plan: dict) -> dict:
    current = structure(slug)
    page = page_for_path(current, page_plan["path"])
    if page is None:
        raise RuntimeError(
            f"page {page_plan['path']} must be created in the page phase before reconciliation"
        )
    if not isinstance(page.get("_id"), str):
        raise RuntimeError(f"could not resolve page {page_plan['path']}")

    page_id = page["_id"]
    desired = page_plan["blocks"]
    unverified = sorted(set(desired) - VERIFIED_BLOCK_MODULES)
    if unverified:
        raise RuntimeError(
            "plan contains unverified block modules: " + ", ".join(unverified)
        )
    kept: set[str] = set()
    removals: list[dict] = []
    blocks = page.get("blocks", [])
    if not isinstance(blocks, list) or any(
        not isinstance(block, dict) for block in blocks
    ):
        raise RuntimeError("pages[].blocks must contain full block objects")
    for block in blocks:
        module = effective_module(block)
        if module in desired and module not in kept:
            kept.add(module)
        else:
            removals.append(block)
    approved_removals = {
        removal["block_id"]: removal["module"]
        for removal in page_plan.get("removals", [])
    }
    unapproved = [
        block
        for block in removals
        if approved_removals.get(block.get("_id")) != effective_module(block)
    ]
    if unapproved:
        details = ", ".join(
            f"{effective_module(block)}:{block.get('_id')}" for block in unapproved
        )
        raise RuntimeError(
            "current page requires unconfirmed block removals; back up, re-render, "
            f"and reconfirm the plan ({details})"
        )
    current_modules = [effective_module(block) for block in blocks]
    if not removals and current_modules == desired:
        return {
            "path": page_plan["path"],
            "page_id": page_id,
            "blocks": current_modules,
            "removed_blocks": 0,
        }
    if removals:
        removal_ids = {block["_id"] for block in removals}
        removal_indexes = sorted(
            (
                index
                for index, block in enumerate(blocks)
                if block.get("_id") in removal_ids
            ),
            reverse=True,
        )
        removal_payload = {
            "removeBlocks": {
                "type": "page",
                "id": page_id,
                "patches": [
                    {"op": "remove", "path": ["blocks", index]}
                    for index in removal_indexes
                ],
            }
        }
        run_json(
            "shopbuilder",
            "update-block",
            "--landing-id",
            landing_id,
            "--data",
            json.dumps(removal_payload, sort_keys=True, separators=(",", ":")),
        )

    page = page_for_path(structure(slug), page_plan["path"])
    if page is None:
        raise RuntimeError(
            f"page disappeared during reconciliation: {page_plan['path']}"
        )
    existing = [effective_module(block) for block in page.get("blocks", [])]
    for module in desired:
        if module not in existing:
            run_json(
                "shopbuilder",
                "add-block",
                "--landing-id",
                landing_id,
                "--page-id",
                page_id,
                "--block",
                module,
            )
            existing.append(module)

    for destination, module in enumerate(desired):
        page = page_for_path(structure(slug), page_plan["path"])
        if page is None:
            raise RuntimeError(f"page disappeared during ordering: {page_plan['path']}")
        modules = [effective_module(block) for block in page.get("blocks", [])]
        source = modules.index(module)
        if source != destination:
            run_json(
                "shopbuilder",
                "move-block",
                "--landing-id",
                landing_id,
                "--page-id",
                page_id,
                "--source",
                str(source),
                "--destination",
                str(destination),
            )

    final_page = page_for_path(structure(slug), page_plan["path"])
    if final_page is None:
        raise RuntimeError(f"could not read final page {page_plan['path']}")
    final_modules = [effective_module(block) for block in final_page.get("blocks", [])]
    if final_modules != desired:
        raise RuntimeError(
            f"block reconciliation failed for {page_plan['path']}: {final_modules}"
        )
    return {
        "path": page_plan["path"],
        "page_id": page_id,
        "blocks": final_modules,
        "removed_blocks": len(removals),
    }


def add_missing_pages(slug: str, page_plans: list[dict]) -> list[str]:
    created: list[str] = []
    current = structure(slug)
    for page_plan in page_plans:
        if page_for_path(current, page_plan["path"]) is not None:
            continue
        run_json(
            "shopbuilder",
            "add-page",
            "--slug",
            slug,
            "--name",
            page_plan["name"],
            "--path",
            page_plan["path"],
        )
        created.append(page_plan["path"])
        current = structure(slug)
        if page_for_path(current, page_plan["path"]) is None:
            raise RuntimeError(f"could not resolve created page {page_plan['path']}")
    return created


def ensure_locales(slug: str, desired: list[str]) -> dict:
    current = structure(slug)
    languages = current.get("languages")
    if not isinstance(languages, list) or any(
        not isinstance(language, str) for language in languages
    ):
        raise RuntimeError("get-structure returned an invalid languages list")
    added: list[str] = []
    for locale in desired:
        if locale in languages:
            continue
        run_json("shopbuilder", "add-language", "--slug", slug, "--language", locale)
        added.append(locale)
        languages.append(locale)
    if not added:
        return {
            "requested": desired,
            "added": [],
            "preserved_extra": sorted(set(languages) - set(desired)),
        }
    refreshed = structure(slug)
    final_languages = refreshed.get("languages")
    if (
        not isinstance(final_languages, list)
        or any(not isinstance(language, str) for language in final_languages)
        or any(locale not in final_languages for locale in desired)
    ):
        raise RuntimeError("locale reconciliation did not produce every requested locale")
    return {
        "requested": desired,
        "added": added,
        "preserved_extra": sorted(set(final_languages) - set(desired)),
    }


def stable_component_id(landing_id: str, page_id: str, target_path: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{landing_id}:{page_id}:{target_path}"))


def stable_localization_id(component_id: str) -> str:
    return "L:" + str(uuid.uuid5(uuid.NAMESPACE_URL, component_id + ":label"))


def header_navigation_patches(
    header: dict, landing_id: str, page_id: str, navigation: list[dict]
) -> tuple[list[dict], dict[str, str]]:
    values = header.get("values")
    if not isinstance(values, dict):
        raise RuntimeError("header values must be an object")
    components = values.get("components")
    if not isinstance(components, dict):
        raise RuntimeError("header values.components must be an object")

    existing_buttons = sorted(
        key
        for key, component in components.items()
        if isinstance(key, str)
        and isinstance(component, dict)
        and component.get("type") == "button"
    )
    button_ids: list[str] = []
    labels: dict[str, str] = {}
    patches: list[dict] = []
    for index, target in enumerate(navigation):
        target_page_id = target.get("page_id")
        if not isinstance(target_page_id, str):
            raise RuntimeError("navigation target page IDs require a target-bound plan")
        component_id = (
            existing_buttons[index]
            if index < len(existing_buttons)
            else stable_component_id(landing_id, page_id, target["path"])
        )
        button_ids.append(component_id)
        existing = components.get(component_id)
        action = (
            existing.get("button", {}).get("action", {})
            if isinstance(existing, dict)
            else {}
        )
        text = action.get("text") if isinstance(action, dict) else None
        localization_id = text.get("id") if isinstance(text, dict) else None
        if not isinstance(localization_id, str) or not localization_id.startswith("L:"):
            localization_id = stable_localization_id(component_id)
        labels[localization_id] = target["name"]
        new_action = {
            "__type": "action",
            "action": "page",
            "landingId": landing_id,
            "openNewTab": False,
            "pageId": target_page_id,
            "text": {"enable": True, "id": localization_id},
        }
        if existing is None:
            patches.append(
                {
                    "op": "add",
                    "path": ["values", "components", component_id],
                    "value": {
                        "id": component_id,
                        "type": "button",
                        "button": {
                            "action": new_action,
                            "variant": {"type": "extra", "value": "header-button"},
                        },
                    },
                }
            )
        else:
            patches.append(
                {
                    "op": "replace",
                    "path": ["values", "components", component_id, "button", "action"],
                    "value": new_action,
                }
            )

    for component_id in existing_buttons[len(navigation) :]:
        patches.append(
            {"op": "remove", "path": ["values", "components", component_id]}
        )

    for area in ("fixedComponents", "leftComponents", "rightComponents"):
        current = values.get(area)
        if not isinstance(current, list):
            raise RuntimeError(f"header values.{area} must be a list")
        retained = [item for item in current if item not in existing_buttons]
        if area == "rightComponents":
            retained.extend(button_ids)
        patches.append(
            {"op": "replace", "path": ["values", area], "value": retained}
        )
    return patches, labels


def update_localized_label_scopes(
    slug: str, labels_by_page: dict[str, dict[str, str]], locales: list[str]
) -> None:
    for locale in locales:
        per_scope = {
            page_id: {
                localization_id: {
                    "translation": f"<span>{html.escape(label)}</span>"
                }
                for localization_id, label in labels.items()
            }
            for page_id, labels in labels_by_page.items()
        }
        run_json(
            "shopbuilder",
            "update-many-localization",
            "--slug",
            slug,
            "--data",
            json.dumps(
                {"locale": locale, "perScopeValues": per_scope},
                separators=(",", ":"),
            ),
        )


def apply_navigation(slug: str, landing_id: str, plan: dict) -> list[dict]:
    current = structure(slug)
    results: list[dict] = []
    operations: list[dict] = []
    labels_by_page: dict[str, dict[str, str]] = {}
    expected_page_ids = [target["page_id"] for target in plan["navigation"]]
    for page_plan in plan["pages"]:
        page = page_for_path(current, page_plan["path"])
        if page is None or not isinstance(page.get("_id"), str):
            raise RuntimeError(f"missing page during navigation: {page_plan['path']}")
        header = next(
            (
                block
                for block in page.get("blocks", [])
                if effective_module(block) == "header"
            ),
            None,
        )
        if not isinstance(header, dict) or not isinstance(header.get("_id"), str):
            raise RuntimeError(f"page {page_plan['path']} has no header block")
        components = header.get("values", {}).get("components", {})
        right = header.get("values", {}).get("rightComponents", [])
        actual_page_ids = [
            components[component_id].get("button", {}).get("action", {}).get("pageId")
            for component_id in right
            if isinstance(components.get(component_id), dict)
            and components[component_id].get("type") == "button"
            and components[component_id]
            .get("button", {})
            .get("action", {})
            .get("action")
            == "page"
        ]
        results.append(
            {
                "path": page_plan["path"],
                "header_id": header["_id"],
                "target_page_ids": expected_page_ids,
            }
        )
        if actual_page_ids == expected_page_ids:
            continue
        patches, labels = header_navigation_patches(
            header, landing_id, page["_id"], plan["navigation"]
        )
        labels_by_page[page["_id"]] = labels
        operations.append(
            {"path": page_plan["path"], "header_id": header["_id"], "patches": patches}
        )

    if labels_by_page:
        update_localized_label_scopes(slug, labels_by_page, plan["locales"])
    for operation in operations:
        run_json(
            "shopbuilder",
            "update-block",
            "--landing-id",
            landing_id,
            "--data",
            json.dumps(
                {
                    "navigation": {
                        "type": "block",
                        "id": operation["header_id"],
                        "patches": operation["patches"],
                    }
                },
                separators=(",", ":"),
            ),
        )

    refreshed = structure(slug)
    for result in results:
        page = page_for_path(refreshed, result["path"])
        header = next(
            (
                block
                for block in page.get("blocks", [])
                if block.get("_id") == result["header_id"]
            ),
            None,
        ) if page else None
        if not isinstance(header, dict):
            raise RuntimeError("header disappeared during navigation verification")
        components = header.get("values", {}).get("components", {})
        right = header.get("values", {}).get("rightComponents", [])
        actual_page_ids = [
            components[component_id].get("button", {}).get("action", {}).get("pageId")
            for component_id in right
            if isinstance(components.get(component_id), dict)
            and components[component_id].get("type") == "button"
            and components[component_id]
            .get("button", {})
            .get("action", {})
            .get("action")
            == "page"
        ]
        if actual_page_ids != expected_page_ids:
            raise RuntimeError(
                f"navigation reconciliation failed on {result['path']}: {actual_page_ids}"
            )
    return results


def store_section_identity(component: object) -> tuple[object, object, object, object]:
    if not isinstance(component, dict):
        return (None, None, None, None)
    section = component.get("section")
    card = component.get("card")
    item = section.get("item") if isinstance(section, dict) else None
    return (
        item.get("group") if isinstance(item, dict) else None,
        item.get("type") if isinstance(item, dict) else None,
        card.get("selectedLayoutType") if isinstance(card, dict) else None,
        component.get("enable"),
    )


def catalog_patches(components: object, sections: list[dict]) -> list[dict]:
    """Create targeted Immer patches without replacing the components array."""
    if not isinstance(components, list) or not components:
        raise RuntimeError("newStore has no component template")
    if any(not isinstance(component, dict) for component in components):
        raise RuntimeError("newStore components must be objects")

    patches: list[dict] = []
    shared = min(len(components), len(sections))
    for index in range(shared):
        section = sections[index]
        patches.extend(
            [
                {
                    "op": "replace",
                    "path": ["components", index, "enable"],
                    "value": True,
                },
                {
                    "op": "replace",
                    "path": ["components", index, "section", "item", "autoSelected"],
                    "value": False,
                },
                {
                    "op": "replace",
                    "path": ["components", index, "section", "item", "group"],
                    "value": section["external_id"],
                },
                {
                    "op": "replace",
                    "path": ["components", index, "section", "item", "type"],
                    "value": section["type"],
                },
                {
                    "op": "replace",
                    "path": ["components", index, "card", "selectedLayoutType"],
                    "value": section["layout"],
                },
                {
                    "op": "replace",
                    "path": ["components", index, "section", "title", "enable"],
                    "value": section["title_enabled"],
                },
            ]
        )

    template = components[0]
    for index in range(shared, len(sections)):
        section = sections[index]
        component = copy.deepcopy(template)
        component.pop("_id", None)
        component["enable"] = True
        component.setdefault("section", {}).setdefault("item", {}).update(
            {
                "autoSelected": False,
                "group": section["external_id"],
                "type": section["type"],
            }
        )
        component.setdefault("section", {}).setdefault("title", {})[
            "enable"
        ] = section["title_enabled"]
        component.setdefault("card", {})["selectedLayoutType"] = section["layout"]
        patches.append(
            {"op": "add", "path": ["components", index], "value": component}
        )

    for index in range(len(components) - 1, len(sections) - 1, -1):
        patches.append({"op": "remove", "path": ["components", index]})
    return patches


def wire_catalog_sections(slug: str, landing_id: str, plan: dict) -> list[dict]:
    if not plan["catalog_sections"]:
        return []
    desired = [
        (
            section["external_id"],
            section["type"],
            section["layout"],
            True,
        )
        for section in plan["catalog_sections"]
    ]
    current = structure(slug)
    results: list[dict] = []
    for page_plan in plan["pages"]:
        page = page_for_path(current, page_plan["path"])
        if page is None:
            raise RuntimeError(f"missing page during catalog wiring: {page_plan['path']}")
        for block in page.get("blocks", []):
            if effective_module(block) != "newStore":
                continue
            block_id = block.get("_id")
            if not isinstance(block_id, str):
                raise RuntimeError("newStore block has no _id")
            patches = catalog_patches(block.get("components"), plan["catalog_sections"])
            actual = [
                store_section_identity(component)
                for component in block.get("components", [])
            ]
            if actual == desired:
                patches = []
            if patches:
                run_json(
                    "shopbuilder",
                    "update-block",
                    "--landing-id",
                    landing_id,
                    "--data",
                    json.dumps(
                        {
                            "catalog": {
                                "type": "block",
                                "id": block_id,
                                "patches": patches,
                            }
                        },
                        separators=(",", ":"),
                    ),
                )
            results.append(
                {"path": page_plan["path"], "block_id": block_id, "sections": desired}
            )

    refreshed = structure(slug)
    for result in results:
        page = page_for_path(refreshed, result["path"])
        block = next(
            (
                candidate
                for candidate in page.get("blocks", [])
                if candidate.get("_id") == result["block_id"]
            ),
            None,
        ) if page else None
        if block is None:
            raise RuntimeError("newStore block disappeared during catalog verification")
        actual = [
            store_section_identity(component) for component in block.get("components", [])
        ]
        if actual != desired:
            raise RuntimeError(
                f"catalog reconciliation failed on {result['path']}: {actual}"
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("brief", type=Path)
    parser.add_argument("--confirmation-id", required=True)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--approved-test-projects", type=Path)
    args = parser.parse_args()
    try:
        brief = load_brief(args.brief)
        errors = validate(brief)
        if errors:
            raise RuntimeError("invalid shop brief: " + "; ".join(errors))
        run_preflight(args.brief, args.approved_test_projects)

        expected = brief["project"]
        config = data(run_json("config", "list"))
        if not isinstance(config, dict):
            raise RuntimeError("xsolla config list returned an unexpected shape")
        if config.get("merchant_id") != expected["merchant_id"]:
            raise RuntimeError("CLI merchant_id does not match the shop brief")
        if config.get("project_id") != expected["project_id"]:
            raise RuntimeError("CLI project_id does not match the shop brief")
        if (config.get("sandbox") is True) != (expected["environment"] == "sandbox"):
            raise RuntimeError("CLI sandbox setting does not match the shop brief")

        slug = brief["site"]["slug"]
        existed = website_exists(run_json("shopbuilder", "list-websites"), slug)
        if existed:
            if args.backup_dir is None:
                raise RuntimeError("--backup-dir is required for an existing target")
            if not verified_backup(args.backup_dir, expected, slug):
                raise RuntimeError(
                    "a complete verified backup created before confirmation is required"
                )
            saved_structure = backup_structure(args.backup_dir)
            plan = build_plan(brief, saved_structure)
        else:
            plan = build_plan(brief)

        if args.confirmation_id != plan["confirmation_id"]:
            raise RuntimeError("confirmation ID does not match the current plan")

        if existed:
            current = structure(slug)
            if structure_hash(current) != structure_hash(saved_structure):
                raise RuntimeError(
                    "target structure changed after backup; back up, re-render, and reconfirm"
                )
            extra_pages = plan["current_state"]["extra_pages"]
            if extra_pages:
                paths = ", ".join(page["path"] for page in extra_pages)
                raise RuntimeError(
                    "target contains pages outside the confirmed plan and the CLI cannot "
                    f"delete pages safely: {paths}"
                )
        else:
            run_json(
                "shopbuilder",
                "create-website",
                "--name",
                brief["site"]["name"],
                "--slug",
                slug,
                "--type",
                "topup",
            )

        current = structure(slug)
        if current.get("type") is None:
            run_json(
                "shopbuilder", "set-landing-type", "--slug", slug, "--type", "store"
            )
            current = structure(slug)
        if current.get("type") != "store":
            raise RuntimeError(
                f"target landing type is {current.get('type')!r}, expected 'store'"
            )
        landing_id = current.get("_id")
        if not isinstance(landing_id, str):
            raise RuntimeError("landing has no _id")

        created_pages = add_missing_pages(slug, plan["pages"])
        locales = ensure_locales(slug, plan["locales"])
        if not existed:
            print(
                json.dumps(
                    {
                        "operation_succeeded": True,
                        "assembly_complete": False,
                        "status": "bootstrap-complete",
                        "confirmation_id": plan["confirmation_id"],
                        "slug": slug,
                        "landing_id": landing_id,
                        "created_pages": created_pages,
                        "locales": locales,
                        "next_action": (
                            "Back up the generated site, render a target-bound plan, "
                            "and explicitly confirm its exact removals before reconciliation."
                        ),
                        "published": False,
                    },
                    indent=2,
                )
            )
            return 0

        if created_pages:
            print(
                json.dumps(
                    {
                        "operation_succeeded": True,
                        "assembly_complete": False,
                        "status": "page-phase-complete",
                        "confirmation_id": plan["confirmation_id"],
                        "slug": slug,
                        "landing_id": landing_id,
                        "created_pages": created_pages,
                        "locales": locales,
                        "next_action": (
                            "Back up the changed site, re-render its generated block IDs, "
                            "and explicitly confirm before block reconciliation."
                        ),
                        "published": False,
                    },
                    indent=2,
                )
            )
            return 0

        pages = [reconcile_page(slug, landing_id, page) for page in plan["pages"]]
        navigation = apply_navigation(slug, landing_id, plan)
        catalog_links = wire_catalog_sections(slug, landing_id, plan)
        print(
            json.dumps(
                {
                    "operation_succeeded": True,
                    "assembly_complete": not plan["unsupported_phases"],
                    "status": "implemented-phases-applied",
                    "confirmation_id": plan["confirmation_id"],
                    "slug": slug,
                    "landing_id": landing_id,
                    "site_existed": existed,
                    "pages": pages,
                    "navigation": navigation,
                    "catalog_links": catalog_links,
                    "locales": locales,
                    "completed_phases": plan["implemented_phases"],
                    "pending_phases": plan["unsupported_phases"],
                    "published": False,
                },
                indent=2,
            )
        )
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Apply failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

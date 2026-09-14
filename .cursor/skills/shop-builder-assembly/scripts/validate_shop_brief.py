#!/usr/bin/env python3
"""Validate the stable, non-secret inputs for Shop Builder assembly."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PRESETS = {"auto", "mobile-single-page", "pc-multi-page", "live-service-events"}
PLATFORMS = {"mobile", "pc", "console", "web"}
LIFECYCLES = {"launch", "evergreen", "live-service"}
GROUP_TYPES = {"virtual_good", "bundle", "virtual_currency"}
PLACEMENTS = {"primary", "featured", "secondary"}
VERIFIED_BLOCK_MODULES = {
    "header",
    "leadGameSales",
    "hero",
    "fast-login",
    "description",
    "packs",
    "bento-grid",
    "gallery",
    "requirements",
    "news",
    "promoSlider",
    "promocodes",
    "rewards",
    "sb-offer-chain",
    "embed",
    "html",
    "social-quests",
    "faq",
    "footer",
    "newStore",
}
SECRET_KEY_SUFFIXES = (
    "apikey",
    "password",
    "token",
    "secret",
    "cookie",
    "session",
    "credential",
)
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LOCALE_RE = re.compile(r"^[a-z]{2}-[A-Z]{2}$")
PATH_RE = re.compile(r"^/(?:[a-z0-9]+(?:-[a-z0-9]+)*/?)*$")


def load_brief(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("top-level value must be an object")
    return value


def validate(brief: dict) -> list[str]:
    errors: list[str] = []

    def obj(name: str) -> dict:
        value = brief.get(name)
        if not isinstance(value, dict):
            errors.append(f"{name} must be an object")
            return {}
        return value

    version = brief.get("version")
    if isinstance(version, bool) or version != 1:
        errors.append("version must be 1")

    def find_secrets(value: object, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else key
                normalized_key = re.sub(r"[^a-z0-9]", "", key.lower())
                if normalized_key.endswith(SECRET_KEY_SUFFIXES):
                    errors.append(f"{child_path} must not contain credentials")
                find_secrets(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                find_secrets(child, f"{path}[{index}]")

    find_secrets(brief)
    project, game, site, catalog = (
        obj("project"),
        obj("game"),
        obj("site"),
        obj("catalog"),
    )
    brand_value = brief.get("brand", {})
    content_value = brief.get("content", {})
    if not isinstance(brand_value, dict):
        errors.append("brand must be an object")
    if not isinstance(content_value, dict):
        errors.append("content must be an object")
        content: dict = {}
    else:
        content = content_value

    for field in ("merchant_id", "project_id"):
        value = project.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            errors.append(f"project.{field} must be a positive integer")
    environment = project.get("environment")
    if not isinstance(environment, str) or environment not in {"sandbox", "test"}:
        errors.append("project.environment must be sandbox or test")
    if environment == "test" and project.get("test_project_acknowledged") is not True:
        errors.append(
            "project.test_project_acknowledged must be true for a dedicated test project"
        )

    if not isinstance(game.get("name"), str) or not game["name"].strip():
        errors.append("game.name is required")
    platforms = game.get("platforms")
    if (
        not isinstance(platforms, list)
        or not platforms
        or any(not isinstance(platform, str) for platform in platforms)
        or not set(platforms) <= PLATFORMS
    ):
        errors.append(f"game.platforms must use: {', '.join(sorted(PLATFORMS))}")
    lifecycle = game.get("lifecycle")
    if not isinstance(lifecycle, str) or lifecycle not in LIFECYCLES:
        errors.append(f"game.lifecycle must use: {', '.join(sorted(LIFECYCLES))}")

    if not isinstance(site.get("name"), str) or not site["name"].strip():
        errors.append("site.name is required")
    if not isinstance(site.get("slug"), str) or not SLUG_RE.fullmatch(site["slug"]):
        errors.append("site.slug must be lowercase kebab-case")
    preset = site.get("preset")
    if not isinstance(preset, str) or preset not in PRESETS:
        errors.append(f"site.preset must use: {', '.join(sorted(PRESETS))}")
    locales = site.get("locales")
    if (
        not isinstance(locales, list)
        or not locales
        or any(not isinstance(x, str) or not LOCALE_RE.fullmatch(x) for x in locales)
    ):
        errors.append("site.locales must be a non-empty list of full locale codes")
    valid_locales = locales if isinstance(locales, list) else []
    if site.get("primary_locale") not in valid_locales:
        errors.append("site.primary_locale must be included in site.locales")

    groups = catalog.get("groups")
    if not isinstance(groups, list):
        errors.append("catalog.groups must be a list")
    else:
        seen: set[tuple[str, str]] = set()
        for index, group in enumerate(groups):
            if not isinstance(group, dict):
                errors.append(f"catalog.groups[{index}] must be an object")
                continue
            external_id = group.get("external_id")
            if not isinstance(external_id, str) or not external_id.strip():
                errors.append(f"catalog.groups[{index}].external_id is required")
            group_type = group.get("type")
            if not isinstance(group_type, str) or group_type not in GROUP_TYPES:
                errors.append(
                    f"catalog.groups[{index}].type must use: {', '.join(sorted(GROUP_TYPES))}"
                )
            elif isinstance(external_id, str) and external_id.strip():
                identity = (group_type, external_id)
                if identity in seen:
                    errors.append(
                        f"catalog.groups[{index}] duplicates the same type and external_id"
                    )
                else:
                    seen.add(identity)
            placement = group.get("placement")
            if not isinstance(placement, str) or placement not in PLACEMENTS:
                errors.append(
                    f"catalog.groups[{index}].placement must use: "
                    + ", ".join(sorted(PLACEMENTS))
                )

    featured_skus = catalog.get("featured_skus", [])
    if not isinstance(featured_skus, list) or any(
        not isinstance(sku, str) or not sku.strip() for sku in featured_skus
    ):
        errors.append("catalog.featured_skus must be a list of non-empty strings")

    page_overrides = content.get("page_overrides")
    if page_overrides is not None:
        if not isinstance(page_overrides, list) or not page_overrides:
            errors.append("content.page_overrides must be a non-empty list")
        else:
            seen_paths: set[str] = set()
            for index, page in enumerate(page_overrides):
                prefix = f"content.page_overrides[{index}]"
                if not isinstance(page, dict):
                    errors.append(f"{prefix} must be an object")
                    continue
                if not isinstance(page.get("name"), str) or not page["name"].strip():
                    errors.append(f"{prefix}.name is required")
                path = page.get("path")
                if not isinstance(path, str) or not PATH_RE.fullmatch(path):
                    errors.append(
                        f"{prefix}.path must be a root-relative kebab-case path"
                    )
                elif path in seen_paths:
                    errors.append(f"{prefix}.path duplicates {path}")
                else:
                    seen_paths.add(path)
                blocks = page.get("blocks")
                if not isinstance(blocks, list) or not blocks:
                    errors.append(f"{prefix}.blocks must be a non-empty list")
                elif any(not isinstance(module, str) for module in blocks):
                    errors.append(f"{prefix}.blocks must contain module names")
                else:
                    if len(blocks) != len(set(blocks)):
                        errors.append(f"{prefix}.blocks must not contain duplicates")
                    unverified = sorted(set(blocks) - VERIFIED_BLOCK_MODULES)
                    if unverified:
                        errors.append(
                            f"{prefix}.blocks contains unverified modules: "
                            + ", ".join(unverified)
                        )

    sources = brief.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("sources must be a non-empty list")
    else:
        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                errors.append(f"sources[{index}] must be an object")
            elif not isinstance(source.get("kind"), str) or not source["kind"].strip():
                errors.append(f"sources[{index}].kind is required")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("brief", type=Path)
    args = parser.parse_args()
    try:
        brief = load_brief(args.brief)
        errors = validate(brief)
    except ValueError as exc:
        errors = [str(exc)]
    if errors:
        print("Shop brief is invalid:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Shop brief is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate the stable, non-secret inputs for Shop Builder assembly."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # keep the installed skill folder clean

from block_ops import OPS_BLOCK_MODULES, validate_block_operations

PRESETS = {"auto", "mobile-single-page", "pc-multi-page", "live-service-events"}
PLATFORMS = {"mobile", "pc", "console", "web"}
LIFECYCLES = {"launch", "evergreen", "live-service"}
GROUP_TYPES = {"virtual_good", "bundle", "virtual_currency"}
PLACEMENTS = {"primary", "featured", "secondary"}
LIVEOPS_FEATURES = {"promo_codes", "reward_chain", "offer_chain"}
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
# The site theme's colors, by their Shop Builder names (`theme.input` on the site).
THEME_COLORS = ("bg", "overlay", "border", "primary", "secondary", "text")
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}")


def theme_errors(theme: object) -> list[str]:
    """Check `brand.theme`: the site palette, as `#rrggbb` colors and `isDark`."""
    if not isinstance(theme, dict) or not theme:
        return ["brand.theme must be a non-empty object"]
    errors = []
    unknown = sorted(set(theme) - set(THEME_COLORS) - {"isDark"})
    if unknown:
        errors.append(
            "brand.theme has unknown keys: "
            + ", ".join(unknown)
            + f"; use {', '.join(THEME_COLORS)} and isDark"
        )
    for key in THEME_COLORS:
        value = theme.get(key)
        if key in theme and (not isinstance(value, str) or not HEX_COLOR.fullmatch(value)):
            errors.append(f"brand.theme.{key} must be a #rrggbb color")
    if "isDark" in theme and not isinstance(theme["isDark"], bool):
        errors.append("brand.theme.isDark must be true or false")
    return errors


# Where an image goes on a block: the block's background, or its logo.
IMAGE_SLOTS = {"background": ("values", "background", "img"), "logo": ("values", "logo", "img")}
# The image types `upload-asset --type image` accepts.
IMAGE_EXTENSIONS = {
    ".gif", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".ico", ".tif", ".tiff", ".svg"
}


def image_errors(images: object) -> list[str]:
    """Check `brand.images`: local image files, each placed on a block module's slot."""
    if not isinstance(images, list) or not images:
        return ["brand.images must be a non-empty list"]
    errors = []
    for index, image in enumerate(images):
        prefix = f"brand.images[{index}]"
        if not isinstance(image, dict):
            errors.append(f"{prefix} must be an object")
            continue
        unknown = sorted(set(image) - {"file", "module", "slot", "page"})
        if unknown:
            errors.append(f"{prefix} has unknown keys: " + ", ".join(unknown))
        file = image.get("file")
        if not isinstance(file, str) or not file.strip():
            errors.append(f"{prefix}.file is required")
        elif "://" in file:
            errors.append(f"{prefix}.file must be a local file; download it first")
        elif Path(file).suffix.lower() not in IMAGE_EXTENSIONS:
            errors.append(
                f"{prefix}.file must be one of: " + ", ".join(sorted(IMAGE_EXTENSIONS))
            )
        if image.get("module") not in VERIFIED_BLOCK_MODULES:
            errors.append(f"{prefix}.module must be a verified block module")
        if image.get("slot") not in IMAGE_SLOTS:
            errors.append(f"{prefix}.slot must be one of: " + ", ".join(IMAGE_SLOTS))
        page = image.get("page")
        if page is not None and (not isinstance(page, str) or not page.startswith("/")):
            errors.append(f"{prefix}.page must be a page path such as /")
    return errors + overlap_errors(images, "brand.images", "slot")


# Block text fields the copy step writes: `values.<field>.id` holds the string's `L:` id.
COPY_FIELDS = ("title", "subtitle", "description")


# Copy never carries code: no script or embedding tags, event handlers or script URLs.
UNSAFE_HTML = re.compile(
    r"<\s*(script|img|iframe|object|embed|style|link|meta)\b|\son[a-z]+\s*=|javascript\s*:",
    re.IGNORECASE,
)


def overlap_errors(
    items: list, kind: str, slot_key: str, slot_label: str = "{}"
) -> list[str]:
    """Two entries for the same module and slot whose pages overlap (no page means every
    page) would write over each other on every run."""
    errors, seen = [], []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        key = (item.get("module"), item.get(slot_key))
        page = item.get("page")
        for other_index, other_key, other_page in seen:
            if key == other_key and (page is None or other_page is None or page == other_page):
                errors.append(
                    f"{kind}[{index}] and {kind}[{other_index}] both set the "
                    f"{slot_label.format(key[1])} of "
                    f"{key[0]} on the same page; keep one, or give each its own page"
                )
        seen.append((index, key, page))
    return errors


def html_errors(value: object, label: str) -> list[str]:
    """Copy is HTML. A title doesn't render `<img>`, and code never goes in copy."""
    if not isinstance(value, str) or not value.strip():
        return [f"{label} must be non-empty HTML"]
    if UNSAFE_HTML.search(value):
        return [
            f"{label} must not contain <script>, <img>, <iframe>, other embedding tags, "
            "event handlers or javascript: links"
        ]
    if "<" not in value:
        return [f"{label} must be HTML, such as <p>…</p>: a bare string renders unstyled"]
    return []


def copy_errors(copy_value: object) -> list[str]:
    """Check `content.copy`: approved HTML for a text field of a planned block module."""
    if not isinstance(copy_value, list) or not copy_value:
        return ["content.copy must be a non-empty list"]
    errors = []
    for index, item in enumerate(copy_value):
        prefix = f"content.copy[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        unknown = sorted(set(item) - {"module", "field", "html", "page"})
        if unknown:
            errors.append(f"{prefix} has unknown keys: " + ", ".join(unknown))
        if item.get("module") not in VERIFIED_BLOCK_MODULES:
            errors.append(f"{prefix}.module must be a verified block module")
        if item.get("field") not in COPY_FIELDS:
            errors.append(f"{prefix}.field must be one of: " + ", ".join(COPY_FIELDS))
        errors.extend(html_errors(item.get("html"), f"{prefix}.html"))
        page = item.get("page")
        if page is not None and (not isinstance(page, str) or not page.startswith("/")):
            errors.append(f"{prefix}.page must be a page path such as /")
    return errors + overlap_errors(copy_value, "content.copy", "field")


def faq_errors(faq: object) -> list[str]:
    """Check `content.faq`: the approved questions and answers, in order."""
    if not isinstance(faq, list) or not faq:
        return ["content.faq must be a non-empty list"]
    errors = []
    for index, item in enumerate(faq):
        prefix = f"content.faq[{index}]"
        if not isinstance(item, dict) or set(item) != {"question", "answer"}:
            errors.append(f"{prefix} must have question and answer only")
            continue
        errors.extend(html_errors(item["question"], f"{prefix}.question"))
        errors.extend(html_errors(item["answer"], f"{prefix}.answer"))
        if isinstance(item["question"], str) and "<h4" not in item["question"].lower():
            errors.append(f"{prefix}.question must be an <h4>: the FAQ block needs it")
    return errors


# Blocks whose buttons hold their labels in `values.buttons[].button.action.text`.
BUTTON_MODULES = ("leadGameSales",)
BUTTON_LABEL_LIMIT = 40


def button_errors(buttons: object) -> list[str]:
    """Check `content.buttons`: a plain-text label for a hero button, by its position."""
    if not isinstance(buttons, list) or not buttons:
        return ["content.buttons must be a non-empty list"]
    errors = []
    for index, item in enumerate(buttons):
        prefix = f"content.buttons[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        unknown = sorted(set(item) - {"module", "position", "label", "page"})
        if unknown:
            errors.append(f"{prefix} has unknown keys: " + ", ".join(unknown))
        if item.get("module") not in BUTTON_MODULES:
            errors.append(f"{prefix}.module must be one of: " + ", ".join(BUTTON_MODULES))
        position = item.get("position")
        if isinstance(position, bool) or not isinstance(position, int) or position < 1:
            errors.append(f"{prefix}.position must be 1 for the first button, 2 for the next")
        label = item.get("label")
        if not isinstance(label, str) or not label.strip():
            errors.append(f"{prefix}.label must be non-empty text")
        elif "<" in label or ">" in label:
            errors.append(f"{prefix}.label is plain text, not HTML: buttons don't render tags")
        elif len(label) > BUTTON_LABEL_LIMIT:
            errors.append(f"{prefix}.label must be at most {BUTTON_LABEL_LIMIT} characters")
        page = item.get("page")
        if page is not None and (not isinstance(page, str) or not page.startswith("/")):
            errors.append(f"{prefix}.page must be a page path such as /")
    return errors + overlap_errors(buttons, "content.buttons", "position", "label of button {}")


# Search engines cut longer titles and descriptions short.
SEO_LIMITS = {"title": 70, "description": 200}


def seo_errors(seo: object) -> list[str]:
    """Check `content.seo`: per page, a plain-text title and description, and a local
    share image (og:image)."""
    if not isinstance(seo, list) or not seo:
        return ["content.seo must be a non-empty list"]
    errors, pages = [], set()
    for index, item in enumerate(seo):
        prefix = f"content.seo[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        unknown = sorted(set(item) - {"page", "title", "description", "image"})
        if unknown:
            errors.append(f"{prefix} has unknown keys: " + ", ".join(unknown))
        page = item.get("page")
        if not isinstance(page, str) or not page.startswith("/"):
            errors.append(f"{prefix}.page must be a page path such as /")
        elif page in pages:
            errors.append(f"{prefix}.page {page} is listed twice")
        else:
            pages.add(page)
        if not any(item.get(key) for key in ("title", "description", "image")):
            errors.append(f"{prefix} needs a title, a description or an image")
        for key, limit in SEO_LIMITS.items():
            value = item.get(key)
            if value is None:
                continue
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}.{key} must be non-empty text")
            elif "<" in value or ">" in value:
                errors.append(f"{prefix}.{key} is plain text, not HTML")
            elif len(value) > limit:
                errors.append(f"{prefix}.{key} must be at most {limit} characters")
        image = item.get("image")
        if image is not None:
            if not isinstance(image, str) or not image.strip():
                errors.append(f"{prefix}.image must be a local file")
            elif "://" in image:
                errors.append(f"{prefix}.image must be a local file; download it first")
            elif Path(image).suffix.lower() not in IMAGE_EXTENSIONS:
                errors.append(
                    f"{prefix}.image must be one of: " + ", ".join(sorted(IMAGE_EXTENSIONS))
                )
    return errors




# OPS_BLOCK_MODULES (Quests) lives in block_ops and is imported above. Those modules
# have exported contracts but are outside the reviewed presets, so they stay out of
# VERIFIED_BLOCK_MODULES: the reconcile flow and page_overrides reject them, and only
# block_operations accepts them.
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
    if "block_operations" in brief:
        return errors + validate_ops_mode(brief)
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

    liveops = catalog.get("liveops", [])
    if (
        not isinstance(liveops, list)
        or any(not isinstance(feature, str) for feature in liveops)
        or not set(liveops) <= LIVEOPS_FEATURES
    ):
        errors.append(f"catalog.liveops must use: {', '.join(sorted(LIVEOPS_FEATURES))}")
    elif len(liveops) != len(set(liveops)):
        errors.append("catalog.liveops must not contain duplicates")

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

    if isinstance(brand_value, dict) and "theme" in brand_value:
        errors.extend(theme_errors(brand_value["theme"]))
    if isinstance(brand_value, dict) and "images" in brand_value:
        errors.extend(image_errors(brand_value["images"]))
    if "copy" in content:
        errors.extend(copy_errors(content["copy"]))
    if "faq" in content:
        errors.extend(faq_errors(content["faq"]))
    if "seo" in content:
        errors.extend(seo_errors(content["seo"]))
    if "buttons" in content:
        errors.extend(button_errors(content["buttons"]))

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


# An operations brief carries only these keys. Anything else (catalog, site.pages,
# content, game) would be silently ignored by the plan, so it is rejected instead.
OPS_TOP_LEVEL_KEYS = {"version", "project", "site", "block_operations"}
OPS_PROJECT_KEYS = {"merchant_id", "project_id"}
OPS_SITE_KEYS = {"slug"}


def validate_ops_mode(brief: dict) -> list[str]:
    """Validate a block-operations brief; site-wide fields are not allowed."""
    errors: list[str] = []
    project = brief.get("project")
    site = brief.get("site")
    for key in sorted(set(brief) - OPS_TOP_LEVEL_KEYS):
        errors.append(
            f"{key} is not allowed with block_operations; an operations brief has only "
            + ", ".join(sorted(OPS_TOP_LEVEL_KEYS))
        )
    if not isinstance(project, dict):
        errors.append("project must be an object")
        project = {}
    if not isinstance(site, dict):
        errors.append("site must be an object")
        site = {}
    for key in sorted(set(project) - OPS_PROJECT_KEYS):
        errors.append(f"project.{key} is not allowed with block_operations")
    for key in sorted(set(site) - OPS_SITE_KEYS):
        errors.append(f"site.{key} is not allowed with block_operations; only site.slug is")
    for field in ("merchant_id", "project_id"):
        value = project.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            errors.append(f"project.{field} must be a positive integer")
    if not isinstance(site.get("slug"), str) or not SLUG_RE.fullmatch(site["slug"]):
        errors.append("site.slug must be lowercase kebab-case")
    return errors + validate_block_operations(brief)


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

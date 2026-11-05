#!/usr/bin/env python3
"""Render a deterministic, non-mutating assembly plan from a shop brief."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections.abc import Callable
from pathlib import Path

# `python3 -I` (isolated mode) does not put the script's own folder on sys.path, so
# the sibling imports below would fail. Add it explicitly.
SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from validate_shop_brief import load_brief, validate

PRESET_PAGES = {
    "mobile-single-page": [
        {
            "name": "Home",
            "path": "/",
            "blocks": [
                "header",
                "leadGameSales",
                "sb-offer-chain",
                "newStore",
                "rewards",
                "promocodes",
                "faq",
                "footer",
            ],
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
            "blocks": [
                "header",
                "sb-offer-chain",
                "newStore",
                "rewards",
                "promocodes",
                "faq",
                "footer",
            ],
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
                "sb-offer-chain",
                "newStore",
                "gallery",
                "faq",
                "footer",
            ],
        },
        {
            "name": "Store",
            "path": "/store",
            "blocks": ["header", "newStore", "rewards", "promocodes", "faq", "footer"],
        },
        {
            "name": "Events",
            "path": "/events",
            "blocks": ["header", "leadGameSales", "newStore", "description", "footer"],
        },
    ],
}
CUSTOM_CODE_WARNING = (
    "The Custom code block is added empty and hidden; paste your code and make the "
    "block visible in the Site Builder editor."
)
LIVEOPS_BLOCKS = {
    "promocodes": ("promo_codes", "no promo code promotion configured in the project"),
    "rewards": ("reward_chain", "no reward chain configured in the project"),
    "sb-offer-chain": ("offer_chain", "no offer chain configured in the project"),
}
COMMON_LAYOUT = "common-layout"
# The presets' hero is `leadGameSales`; a template page carries its own hero as `lead`.
# `hero` is the Call-to-action block, not a stand-in for either.
TEMPLATE_HERO = {"leadGameSales": "lead"}
# The blocks `add-page` puts on a new store page with CLI 1.9.4 (test-findings.md).
NEW_PAGE_TEMPLATE = [
    "header",
    "leadGameSales",
    "description",
    "packs",
    "bento-grid",
    "gallery",
    "requirements",
    "faq",
    "footer",
]
PREVIEW = {"when": "after assembly, for the visual review", "access": "anyone with the link"}
# What the developer's yes to a plan covers. A later plan for the same assembly, such as
# a new site's second run, must keep these unchanged to reuse that yes.
APPROVAL_SCOPE = (
    ("target", "the target site or project"),
    ("preset", "the preset"),
    ("locales", "the locales"),
    ("primary_locale", "the primary locale"),
    ("catalog_sections", "the catalog sections"),
    ("featured_skus", "the featured products"),
    ("brand", "the brand"),
    ("content", "the content"),
    ("sources", "the sources"),
    ("preview", "the preview"),
    ("brief_sha256", "the shop brief"),
)
NO_OWN_HEADER = (
    "Page {path} has no header block of its own, and the site has no common layout "
    "that could hold one. Nothing was written."
)


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


def page_path(page: object) -> str | None:
    """Return the URL path of a page from get-structure.

    Shop Builder returns a page ``path`` either as a string (``"/"``) or as an object
    (``{"pathSegment": "/", "type": "static"}``), depending on the landing.
    """

    if not isinstance(page, dict):
        return None
    path = page.get("path")
    if isinstance(path, str):
        return path
    if isinstance(path, dict) and isinstance(path.get("pathSegment"), str):
        return path["pathSegment"]
    return None


def site_block_ids(blocks: object) -> set:
    if not isinstance(blocks, list):
        return set()
    return {
        block if isinstance(block, str) else block.get("_id")
        for block in blocks
        if isinstance(block, (str, dict))
    }


def common_layout_id(
    structure: dict, module_of: Callable[[str], object] | None = None
) -> str | None:
    """Return the ID of the site's ``common-layout`` block, or None if it has none.

    Other layouts may sit next to it: a site with a sidebar lists its side-by-side
    layout first. get-structure lists site-level blocks by ID only, so ``module_of``
    reads a layout's module (get-block on a live site) when ``blocks`` does not inline it.
    """

    layouts = structure.get("layouts")
    if not isinstance(layouts, list):
        raise ValueError("get-structure returned no layouts list")
    if not all(isinstance(layout_id, str) for layout_id in layouts):
        raise ValueError("get-structure returned invalid layout IDs")
    blocks = structure.get("blocks")
    inlined = {
        block.get("_id"): effective_module(block)
        for block in (blocks if isinstance(blocks, list) else [])
        if isinstance(block, dict)
    }
    for layout_id in layouts:
        if layout_id in inlined:
            module = inlined[layout_id]
        elif module_of is not None:
            module = module_of(layout_id)
        else:
            raise ValueError(f"cannot read the module of site layout {layout_id}")
        if module == COMMON_LAYOUT:
            if layout_id not in site_block_ids(blocks):
                raise ValueError("existing common layout is missing from site blocks")
            return layout_id
    return None


def has_own_header(page: dict, created_block_ids: frozenset = frozenset()) -> bool:
    """Whether the page has a header block of its own. A header this assembly created,
    with a page it added, doesn't count: on a template site that page uses the shared one."""
    blocks = page.get("blocks")
    return any(
        isinstance(block, dict)
        and effective_module(block) == "header"
        and block.get("_id") not in created_block_ids
        for block in (blocks if isinstance(blocks, list) else [])
    )


def shared_site_blocks(current: dict) -> set:
    """Site-level blocks that are on no page and aren't a layout: on a template site,
    the shared header and footer. A layout `create-block` added is not one."""
    page_blocks = {
        block.get("_id") if isinstance(block, dict) else block
        for page in current.get("pages") or []
        if isinstance(page, dict)
        for block in page.get("blocks") or []
    }
    layouts = current.get("layouts")
    return site_block_ids(current.get("blocks")) - page_blocks - site_block_ids(
        layouts if isinstance(layouts, list) else []
    )


def is_template_site(current: dict, pages: list[dict]) -> bool:
    """A site made from a Publisher Account template: it has a site layout and shared
    site-level blocks next to it, and a planned page on it has no header block at all,
    because the header and footer sit in that layout. A site this assembly built has
    only the layout at site level, even when a page lost its header."""
    layouts = current.get("layouts")
    if not (isinstance(layouts, list) and layouts) or not shared_site_blocks(current):
        return False
    by_path = {page_path(page): page for page in current.get("pages") or []}
    return any(
        not has_own_header(by_path[page["path"]]) for page in pages if page["path"] in by_path
    )


def require_header_source(pages: list[dict], structure: object) -> None:
    """Stop when a planned page already on the site has no header it can use.

    A site created from a Publisher Account template keeps its header and footer as
    site-level blocks next to the common layout, and its pages have none of their own;
    pages the plan adds there drop the header and footer `add-page` gives them. A page
    with no header on a site with no layout is broken, and stops. Pages the plan creates
    pass.
    """

    current = structure_data(structure)
    current_pages = current.get("pages")
    if not isinstance(current_pages, list):
        raise ValueError("structure.pages must be a list")
    layouts = current.get("layouts")
    has_layout = isinstance(layouts, list) and bool(layouts)
    by_path = {page_path(page): page for page in current_pages}
    for page_plan in pages:
        current_page = by_path.get(page_plan["path"])
        if current_page is None or has_own_header(current_page):
            continue
        if not has_layout:
            raise ValueError(NO_OWN_HEADER.format(path=page_plan["path"]))


def adapt_to_template_page(modules: list[str], on_page: set) -> list[str]:
    """Fit a preset's module list to a page made from a Publisher Account template.

    The header and footer stay in the site layout; the template's ``lead`` hero stands
    in for ``leadGameSales``; the template's daily rewards block is kept, because the
    kit can't add one back.
    """
    result = [
        module
        for module in modules
        if module != "header" and (module != "footer" or "footer" in on_page)
    ]
    if "leadGameSales" in result and "leadGameSales" not in on_page and "lead" in on_page:
        result[result.index("leadGameSales")] = "lead"
    # The template's LiveOps blocks stay as configured, like on any page that has them:
    # the daily rewards block, which the kit can't add back, then the offer chain, reward
    # system and promo codes blocks, after the hero.
    hero = next(
        (index for index, module in enumerate(result) if module in ("lead", "leadGameSales")),
        -1,
    )
    for module in ("sb-daily-reward", "sb-offer-chain", "rewards", "promocodes"):
        if module in on_page and module not in result:
            hero += 1
            result.insert(hero, module)
    return result


def custom_code_warnings(pages: list[dict]) -> list[str]:
    """Warn when the plan adds a Custom code block.

    The skill never writes custom HTML, CSS, or JS, so the user must add it. A block
    already on the page is left as the user set it, so it gets no warning.
    """
    for page in pages:
        current = {block.get("module") for block in page.get("current_blocks", [])}
        if "html" in page.get("blocks", []) and "html" not in current:
            return [CUSTOM_CODE_WARNING]
    return []


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
    if module in LIVEOPS_BLOCKS:
        feature, reason = LIVEOPS_BLOCKS[module]
        if feature not in catalog.get("liveops", []):
            return reason
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


def template_removals(page: dict) -> list[str]:
    """Return the template blocks a page created by this plan comes with but won't keep."""
    return [module for module in NEW_PAGE_TEMPLATE if module not in page["blocks"]]


def bind_current_state(
    pages: list[dict],
    omissions: list[dict],
    structure: object | None,
    created_block_ids: frozenset = frozenset(),
) -> dict:
    """Bind the plan to the current site.

    Blocks in ``created_block_ids`` were created by this assembly's earlier run, so they
    hold template content, not the publisher's configuration, and are never preserved.
    """
    if structure is None:
        for page in pages:
            page["page_id"] = None
            page["current_blocks"] = []
            page["preserved_blocks"] = []
            page["removals"] = []
            page["template_removals"] = template_removals(page)
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
        path = page_path(page)
        if path is None:
            raise ValueError("every current page must be an object with a path")
        if path in by_path:
            raise ValueError(f"current structure contains duplicate path {path}")
        by_path[path] = page
        if path not in planned_paths:
            extra_pages.append(
                {
                    "page_id": page.get("_id"),
                    "name": page.get("name"),
                    "path": path,
                }
            )

    template_site = is_template_site(current, pages)
    for page_plan in pages:
        page_plan["page_id"] = None
        page_plan["current_blocks"] = []
        page_plan["preserved_blocks"] = []
        page_plan["removals"] = []
        page_plan["template_removals"] = []
        current_page = by_path.get(page_plan["path"])
        if current_page is None:
            if template_site:
                # The page `add-page` makes comes with its own header and footer; on a
                # template site they would sit next to the shared ones, so they go.
                page_plan["site_header"] = "layout"
                for key in ("blocks", "requested_blocks"):
                    page_plan[key] = adapt_to_template_page(page_plan[key], set())
            page_plan["template_removals"] = template_removals(page_plan)
            continue
        page_plan["page_id"] = current_page.get("_id")
        blocks = current_page.get("blocks", [])
        if not isinstance(blocks, list) or any(
            not isinstance(block, dict) for block in blocks
        ):
            raise ValueError(
                "current pages[].blocks must contain full block objects from get-structure"
            )
        if template_site and not has_own_header(current_page, created_block_ids):
            page_plan["site_header"] = "layout"
            # Blocks this assembly created are template blocks, not the template's own.
            on_page = {
                effective_module(block)
                for block in blocks
                if block.get("_id") not in created_block_ids
            }
            for key in ("blocks", "requested_blocks"):
                page_plan[key] = adapt_to_template_page(page_plan[key], on_page)
        omitted_on_page = {
            omission["module"]: omission
            for omission in omissions
            if omission["path"] == page_plan["path"]
        }
        current_modules = {
            effective_module(block)
            for block in blocks
            if isinstance(effective_module(block), str)
            and block.get("_id") not in created_block_ids
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
            if (
                module in preserved_modules
                and module not in kept
                and block_id not in created_block_ids
            ):
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
                if module in kept:
                    reason = "duplicate module"
                elif block_id in created_block_ids:
                    reason = "template block on a page this assembly created"
                else:
                    reason = "not in confirmed page plan"
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


def uses_own_theme(page: object) -> bool:
    """Whether a page renders from its own copy of the theme ("Use global theme" off)."""
    theme = page.get("theme") if isinstance(page, dict) else None
    return isinstance(theme, dict) and theme.get("enabled") is True


def theme_plan(brief: dict, pages: list[dict], structure: object | None) -> dict:
    """The site colors `apply_style.py` sets, and the existing planned pages it switches
    to the site theme. A page on its own theme ignores the site colors."""
    site = brief.get("brand", {}).get("theme")
    if not site:
        return {"site": None, "pages_to_site_theme": []}
    switch = []
    if structure is not None:
        planned = {page["path"] for page in pages}
        switch = sorted(
            path
            for page in structure_data(structure).get("pages", [])
            if (path := page_path(page)) in planned and uses_own_theme(page)
        )
    return {"site": site, "pages_to_site_theme": switch}


def file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def placement(
    module: str, page_filter: str | None, pages: list[dict], created_block_ids: frozenset
) -> dict:
    """The planned pages a module's block is on, and the blocks there that existed before
    this assembly and stay: the yes covers changing those only because the plan lists them.
    A `leadGameSales` item goes on a template page's own hero (`lead`)."""
    page_modules = {}
    for page in pages:
        if page_filter not in (None, page["path"]):
            continue
        on_page = module
        if on_page not in page["blocks"] and TEMPLATE_HERO.get(on_page) in page["blocks"]:
            on_page = TEMPLATE_HERO[on_page]
        if on_page in page["blocks"]:
            page_modules[page["path"]] = on_page
    existing = []
    for page in pages:
        if page["path"] not in page_modules:
            continue
        removed = {removal["block_id"] for removal in page.get("removals", [])}
        existing.extend(
            block["block_id"]
            for block in page.get("current_blocks", [])
            if block["module"] == page_modules[page["path"]]
            and block["block_id"] not in removed
            and block["block_id"] not in created_block_ids
        )
    return {
        "pages": list(page_modules),
        "page_modules": page_modules,
        "existing_block_ids": existing,
    }


def not_placed(label: str, module: str, page: str | None) -> str:
    return (
        f"{label} has no {module} block to go on"
        + (f" on {page}" if page else "")
        + "; it isn't placed."
    )


def images_plan(
    brief: dict,
    pages: list[dict],
    created_block_ids: frozenset,
    base_dir: Path | None,
) -> tuple[list[dict], list[str]]:
    """Where each image in `brand.images` goes, for `apply_style.py`.

    ``sha256`` binds the yes to the file's content; it is None without ``base_dir`` or
    when the file is missing.
    """
    images, warnings = [], []
    for image in brief.get("brand", {}).get("images", []):
        where = placement(image["module"], image.get("page"), pages, created_block_ids)
        if not where["pages"]:
            warnings.append(
                not_placed(f"Image {image['file']}", image["module"], image.get("page"))
            )
        sha256 = None
        if base_dir is not None:
            path = Path(image["file"])
            sha256 = file_sha256(path if path.is_absolute() else base_dir / path)
            if sha256 is None:
                warnings.append(f"Image {image['file']} was not found next to the brief.")
        images.append(
            {
                "file": image["file"],
                "sha256": sha256,
                "module": image["module"],
                "slot": image["slot"],
                **where,
            }
        )
    return images, warnings


def copy_plan(
    brief: dict, pages: list[dict], created_block_ids: frozenset, base_dir: Path | None
) -> tuple[dict, list[str]]:
    """The approved text `apply_style.py` writes in the primary locale: block text fields
    from `content.copy`, hero button labels from `content.buttons`, the FAQ items from
    `content.faq`, and each page's SEO title,
    description and share image from `content.seo`. Other locales are
    `shopbuilder-translate`'s."""
    content = brief.get("content", {})
    texts, warnings = [], []
    for item in content.get("copy", []):
        where = placement(item["module"], item.get("page"), pages, created_block_ids)
        if not where["pages"]:
            warnings.append(
                not_placed(f"The {item['field']} text", item["module"], item.get("page"))
            )
        texts.append(
            {"module": item["module"], "field": item["field"], "html": item["html"], **where}
        )
    buttons = []
    for item in content.get("buttons", []):
        where = placement(item["module"], item.get("page"), pages, created_block_ids)
        if not where["pages"]:
            warnings.append(
                not_placed(f"Button {item['position']}'s label", item["module"], item.get("page"))
            )
        buttons.append(
            {
                "module": item["module"],
                "position": item["position"],
                "label": item["label"],
                **where,
            }
        )
    faq = None
    if content.get("faq"):
        faq = {"items": content["faq"], **placement("faq", None, pages, created_block_ids)}
    planned = {page["path"] for page in pages}
    seo = []
    for item in content.get("seo", []):
        if item["page"] not in planned:
            warnings.append(f"SEO for {item['page']} has no planned page; it isn't written.")
            continue
        entry = {
            "page": item["page"],
            "title": item.get("title"),
            "description": item.get("description"),
            "file": item.get("image"),
            "sha256": None,
        }
        if entry["file"] and base_dir is not None:
            path = Path(entry["file"])
            entry["sha256"] = file_sha256(path if path.is_absolute() else base_dir / path)
            if entry["sha256"] is None:
                warnings.append(f"Image {entry['file']} was not found next to the brief.")
        seo.append(entry)
    return {
        "locale": brief["site"]["primary_locale"],
        "texts": texts,
        "buttons": buttons,
        "faq": faq,
        "seo": seo,
    }, warnings


def drop_pages_without_content(
    pages: list[dict], structure: object | None
) -> tuple[list[dict], list[str]]:
    """Leave out a page the plan would add with nothing on it but a header and footer.

    Its sections were omitted for missing content, so it would be an empty page. A page
    already on the site, and the home page, stay.
    """
    existing = set()
    if structure is not None:
        current_pages = structure_data(structure).get("pages")
        if not isinstance(current_pages, list):
            raise ValueError("structure.pages must be a list")
        existing = {page_path(page) for page in current_pages}
    kept, warnings = [], []
    for page in pages:
        if (
            page["path"] != "/"
            and page["path"] not in existing
            and not set(page["blocks"]) - {"header", "footer"}
        ):
            warnings.append(
                f"Page {page['path']} would have no sections: the content they need isn't "
                "in the brief (see omissions). It isn't created."
            )
            continue
        kept.append(page)
    return kept, warnings


def build_plan(
    brief: dict,
    current_structure: object | None = None,
    created_block_ids: frozenset = frozenset(),
    base_dir: Path | None = None,
) -> dict:
    """``base_dir`` is the brief's folder, where `brand.images` files are read from."""
    preset = choose_preset(brief)
    catalog_groups = catalog_sections(brief, preset)
    pages, omissions = omit_unwritable_blocks(selected_pages(brief, preset), brief)
    pages, empty_warnings = drop_pages_without_content(pages, current_structure)
    current_state = bind_current_state(
        pages, omissions, current_structure, created_block_ids
    )
    images, warnings = images_plan(brief, pages, created_block_ids, base_dir)
    warnings[:0] = empty_warnings
    copy_section, copy_warnings = copy_plan(brief, pages, created_block_ids, base_dir)
    warnings.extend(copy_warnings)
    brand = brief.get("brand", {})
    if not brand.get("logo") and not any(
        image.get("slot") == "logo" for image in brand.get("images", [])
    ):
        warnings.append(
            "No logo supplied; keep the template text identity until approved."
        )
    if preset == "live-service-events" and not brief.get("content", {}).get("events"):
        warnings.append(
            "No event data supplied; omit event-specific copy and scarcity claims."
        )
    warnings.extend(custom_code_warnings(pages))
    plan = {
        "version": 2,
        "target": {
            "merchant_id": brief["project"]["merchant_id"],
            "project_id": brief["project"]["project_id"],
            "site_name": brief["site"]["name"],
            "slug": brief["site"]["slug"],
        },
        "preset": preset,
        "requires_confirmation": True,
        "publication": "forbidden",
        # Matches SKILL.md "Assembly order": apply_plan.py runs pages through catalog
        # links, apply_style.py the theme, images and copy after the last apply run.
        "order": [
            "backup",
            "pages",
            "site_layout",
            "navigation",
            "blocks",
            "catalog_links",
            "theme",
            "images",
            "copy",
            "verify",
            "preview",
        ],
        "pages": pages,
        "site_layout": {
            "module": COMMON_LAYOUT,
            "when": "after-pages",
            "if_missing": True,
        },
        "navigation": [
            {"name": page["name"], "path": page["path"], "page_id": page["page_id"]}
            for page in pages
        ],
        "locales": brief["site"]["locales"],
        "primary_locale": brief["site"]["primary_locale"],
        "catalog_sections": catalog_groups,
        "featured_skus": brief["catalog"].get("featured_skus", []),
        "brand": brand,
        "theme": theme_plan(brief, pages, current_structure),
        "images": images,
        "copy": copy_section,
        "content": brief.get("content", {}),
        "sources": brief["sources"],
        "omissions": omissions,
        "preview": PREVIEW,
        "current_state": current_state,
        "brief_sha256": canonical_hash(brief),
        "implemented_phases": [
            "pages",
            "site_layout",
            "navigation",
            "blocks",
            "locales",
            "catalog_links",
        ],
        # Applied by apply_style.py after the last apply_plan.py run.
        "style_phases": ["theme", "images", "copy"],
        "unsupported_phases": [
            "verify",
            "preview",
        ],
        "warnings": warnings,
    }
    plan["confirmation_id"] = "sha256:" + canonical_hash(plan)[:12]
    return plan


def load_approved_plan(path: Path) -> dict:
    """Load the rendered plan the developer approved, refusing an edited copy."""
    plan = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(plan, dict) or not isinstance(plan.get("confirmation_id"), str):
        raise ValueError("the approved plan has no confirmation_id")
    rendered = {key: value for key, value in plan.items() if key != "confirmation_id"}
    if plan["confirmation_id"] != "sha256:" + canonical_hash(rendered)[:12]:
        raise ValueError("the approved plan file was changed after it was rendered")
    return plan


STOPPED_PARTWAY = "stopped-partway"


def load_run_report(path: Path) -> dict:
    """Load an earlier apply_plan.py run's report: a finished run, or one that stopped
    partway after its writes began."""
    report = json.loads(path.read_text(encoding="utf-8"))
    finished = isinstance(report, dict) and report.get("operation_succeeded") is True
    stopped = (
        isinstance(report, dict)
        and report.get("operation_succeeded") is False
        and report.get("status") == STOPPED_PARTWAY
    )
    if not (finished or stopped):
        raise ValueError(f"{path} is not the report of an apply_plan.py run")
    return report


def created_block_ids(report: dict) -> frozenset:
    """Return the IDs of the blocks an apply run created, from its report."""
    ids: set = set()
    carried = report.get("created_block_ids")
    if isinstance(carried, list):
        ids.update(block_id for block_id in carried if isinstance(block_id, str))
    created = report.get("created_blocks")
    for block_ids in created.values() if isinstance(created, dict) else []:
        if isinstance(block_ids, list):
            ids.update(block_id for block_id in block_ids if isinstance(block_id, str))
    for page in report.get("pages", []):
        if isinstance(page, dict) and isinstance(page.get("added_block_ids"), list):
            ids.update(
                block_id for block_id in page["added_block_ids"] if isinstance(block_id, str)
            )
    return frozenset(ids)


def page_outline(plan: dict) -> list:
    return [(page["name"], page["path"], page["blocks"]) for page in plan.get("pages", [])]


def approval_changes(approved: dict, plan: dict, run_report: dict) -> list[str]:
    """Return what the developer's yes to ``approved`` doesn't cover in ``plan``.

    ``run_report`` is the report of the earlier run under that yes, such as a new
    site's bootstrap. The yes covers ``plan`` only when it keeps the approved pages,
    sections, catalog, locales, brand and content, and removes only blocks that the
    earlier run created or that the approved plan listed by ID.
    """
    changes = []
    if run_report.get("approved_confirmation_id") != approved.get("confirmation_id"):
        changes.append("the run report belongs to another approval")
    if run_report.get("slug") != plan["target"]["slug"] or run_report.get(
        "landing_id"
    ) != plan["current_state"].get("landing_id"):
        changes.append("the site isn't the one the earlier run built")
    for key, label in APPROVAL_SCOPE:
        if approved.get(key) != plan.get(key):
            changes.append(f"{label} changed")
    if page_outline(approved) != page_outline(plan):
        changes.append("the pages or their sections changed")
    extra_pages = plan["current_state"].get("extra_pages", [])
    if extra_pages:
        changes.append(
            "the site has pages outside the plan: "
            + ", ".join(page["path"] for page in extra_pages)
        )
    created = created_block_ids(run_report)
    approved_removals = {
        (page["path"], removal.get("block_id"))
        for page in approved.get("pages", [])
        for removal in page.get("removals", [])
    }
    for page in plan["pages"]:
        for removal in page["removals"]:
            if (
                removal["block_id"] not in created
                and (page["path"], removal["block_id"]) not in approved_removals
            ):
                changes.append(
                    f"it removes the {removal['module']} block {removal['block_id']} "
                    f"on {page['path']}, which the approved plan didn't show"
                )
    return changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("brief", type=Path)
    parser.add_argument(
        "--structure",
        type=Path,
        help="get-structure JSON from the verified backup of an existing target",
    )
    parser.add_argument(
        "--approved-plan",
        type=Path,
        help="the plan the developer approved; says whether that yes covers this plan",
    )
    parser.add_argument(
        "--run-report",
        type=Path,
        help="report of the earlier apply run under the same yes, such as the bootstrap",
    )
    args = parser.parse_args()
    try:
        brief = load_brief(args.brief)
        structure = None
        if args.structure is not None:
            structure = json.loads(args.structure.read_text(encoding="utf-8"))
        approved = (
            load_approved_plan(args.approved_plan) if args.approved_plan else None
        )
        report = load_run_report(args.run_report) if args.run_report else None
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    errors = validate(brief)
    if errors:
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    try:
        plan = build_plan(
            brief,
            structure,
            created_block_ids(report) if report else frozenset(),
            args.brief.resolve().parent,
        )
        if structure is not None:
            require_header_source(plan["pages"], structure)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(plan, indent=2))
    if approved is not None:
        if report is not None and report.get("approved_confirmation_id") != approved.get(
            "confirmation_id"
        ):
            changes = ["the run report belongs to another approval"]
        elif plan["confirmation_id"] == approved["confirmation_id"]:
            changes = []
        elif report is None:
            changes = ["this isn't the approved plan, and no earlier run report was given"]
        else:
            changes = approval_changes(approved, plan, report)
        print(
            "Covered by the approved plan."
            if not changes
            else "Needs a new yes: " + "; ".join(changes),
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

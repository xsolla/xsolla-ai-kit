#!/usr/bin/env python3
"""Apply the approved theme, images and copy after the last apply_plan.py run, under the yes.

Theme: sets the site theme's colors (`theme.input`) to the palette in the approved plan's
brand, and switches the planned pages to the site theme. Only keys the site theme already
has are patched, each in the format its current value has.

Images: uploads each approved file once (an asset cache keeps the URL across runs) and
puts its CDN URL in the block slot the plan named.

Copy: writes the approved text in the primary locale through `update-many-localization`,
never through block patches, and makes the FAQ block's items match the approved list.

A page or block that existed before this assembly changes only when the approved plan
listed it. Never publishes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

# `python3 -I` (isolated mode) does not put the script's own folder on sys.path, so
# the sibling imports below would fail. Add it explicitly.
SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from apply_plan import (
    backup_structure,
    check_cli_context,
    data,
    page_for_path,
    run_json,
    run_preflight,
    structure,
    verified_backup,
)
from patch_backgrounds import asset_urls, is_opaque
from render_plan import (
    canonical_hash,
    created_block_ids,
    effective_module,
    file_sha256,
    load_approved_plan,
    load_run_report,
    structure_hash,
    uses_own_theme,
)
from validate_shop_brief import IMAGE_SLOTS, load_brief, validate

# `upload-asset` takes files up to 10 MB.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

RECALCULATE_IN_EDITOR = (
    "Recalculate the theme in the Site Builder editor: the CLI saved the colors but "
    "didn't recalculate the theme the pages render from. Open a page, change one color "
    "in the Theme panel by one step and back, click Save as global theme, then turn Use "
    "global theme back on. With Use global theme off, Save as global theme saves that "
    "page's own copy over the site theme, so check the colors in the panel first: {colors}"
)
OWN_THEME_IN_EDITOR = (
    "Page {path} existed before this assembly and uses its own theme, so it ignores the "
    "site colors. Turn on Use global theme for it in the Site Builder editor if it "
    "should match the site."
)

COLOR = re.compile(
    r"#(?P<hex>[0-9a-fA-F]{3,8})"
    r"|rgba?\((?P<args>[^)]*)\)"
)


def parse_color(value: object) -> tuple[int, int, int, float] | None:
    """Return a color's red, green, blue and alpha, or None for a format not handled."""
    if not isinstance(value, str):
        return None
    match = COLOR.fullmatch(value.strip())
    if match is None:
        return None
    if match["hex"] is not None:
        digits = match["hex"]
        if len(digits) in (3, 4):
            digits = "".join(digit * 2 for digit in digits)
        if len(digits) not in (6, 8):
            return None
        alpha = int(digits[6:8], 16) / 255 if len(digits) == 8 else 1.0
        return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16), alpha)
    parts = [part.strip() for part in match["args"].split(",")]
    if len(parts) not in (3, 4):
        return None
    try:
        red, green, blue = (int(part) for part in parts[:3])
        alpha = float(parts[3]) if len(parts) == 4 else 1.0
    except ValueError:
        return None
    if not all(0 <= channel <= 255 for channel in (red, green, blue)) or not 0 <= alpha <= 1:
        return None
    return (red, green, blue, alpha)


def same_color(left: object, right: object) -> bool:
    first, second = parse_color(left), parse_color(right)
    return (
        first is not None
        and second is not None
        and first[:3] == second[:3]
        and abs(first[3] - second[3]) < 0.01
    )


def in_format_of(color: str, current: str) -> str:
    """Write the brief's `#rrggbb` color in the format of the value it replaces."""
    red, green, blue, _ = parse_color(color)  # type: ignore[misc]
    text = current.strip()
    if text.startswith("#"):
        hex_value = f"{red:02x}{green:02x}{blue:02x}"
        if len(text) in (5, 9):
            hex_value += "ff"
        if any(char.isupper() for char in text[1:]):
            hex_value = hex_value.upper()
        return "#" + hex_value
    separator = ", " if ", " in text else ","
    channels = separator.join(str(channel) for channel in (red, green, blue))
    if text.startswith("rgba"):
        return f"rgba({channels}{separator}1)"
    return f"rgb({channels})"


def site_theme_changes(site_theme: object, palette: dict) -> tuple[list[dict], dict, list]:
    """Return the patches that set ``palette`` on the site theme, the values they write,
    and the keys left alone with the reason."""
    inputs = site_theme.get("input") if isinstance(site_theme, dict) else None
    if not isinstance(inputs, dict):
        reason = "the site theme has no input colors"
        if isinstance(site_theme, dict) and isinstance(site_theme.get("mainColors"), dict):
            reason = (
                "the site theme still has the older mainColors shape, which Site Builder "
                "migrates to theme.input; set the colors in the editor's Theme panel"
            )
        return [], {}, [{"key": key, "reason": reason} for key in palette]
    patches, written, skipped = [], {}, []
    for key, value in palette.items():
        if key not in inputs:
            skipped.append({"key": key, "reason": "the site theme has no such key"})
            continue
        current = inputs[key]
        if key == "isDark":
            if not isinstance(current, bool):
                skipped.append({"key": key, "reason": "its value isn't true or false"})
            elif current != value:
                written[key] = value
        elif parse_color(current) is None:
            skipped.append(
                {"key": key, "reason": f"its value {current!r} isn't a format this writes"}
            )
        elif not same_color(current, value):
            written[key] = in_format_of(value, current)
    for key, value in written.items():
        patches.append({"op": "replace", "path": ["theme", "input", key], "value": value})
    return patches, written, skipped


def check_reports(reports: list[dict], paths: list[Path], approved: dict, slug: str) -> None:
    for path, report in zip(paths, reports):
        if (
            report.get("approved_confirmation_id") != approved["confirmation_id"]
            or report.get("slug") != slug
        ):
            raise RuntimeError(f"{path} is not a run under the approved plan")


def localization(slug: str) -> object:
    return data(run_json("shopbuilder", "get-localization", "--slug", slug))


def write_changes(slug: str, landing_id: str, changes: dict, what: str) -> dict:
    """Send one `update-block` batch, then return the saved structure. Stops if the
    site's text changed: a patch that hits a string deletes it."""
    text_before = localization(slug)
    run_json(
        "shopbuilder",
        "update-block",
        "--landing-id",
        landing_id,
        "--data",
        json.dumps(changes, separators=(",", ":")),
    )
    saved = structure(slug)
    if localization(slug) != text_before:
        raise RuntimeError(
            f"the site's text changed during the {what} patch; stop and compare "
            "get-localization with the backup"
        )
    return saved


def theme_phase(
    slug: str, landing_id: str, current: dict, approved: dict, created_pages: set
) -> tuple[dict, list[str], dict]:
    """Set the approved palette and put the planned pages on the site theme."""
    palette = approved.get("brand", {}).get("theme")
    if not palette:
        return {"status": "kept: no palette in the approved plan"}, [], current
    site_patches, written, skipped = site_theme_changes(current.get("theme"), palette)
    listed = set(approved.get("theme", {}).get("pages_to_site_theme", []))
    changes: dict[str, dict] = {}
    if site_patches:
        changes["site"] = {"type": "site", "id": landing_id, "patches": site_patches}
    switched, needs_human = [], []
    for index, page_plan in enumerate(approved.get("pages", [])):
        page = page_for_path(current, page_plan["path"])
        if page is None or not isinstance(page.get("_id"), str):
            raise RuntimeError(f"page {page_plan['path']} is missing; finish apply_plan.py first")
        if not uses_own_theme(page):
            continue
        if page_plan["path"] in listed or page_plan["path"] in created_pages:
            changes[f"page{index}"] = {
                "type": "page",
                "id": page["_id"],
                "patches": [{"op": "replace", "path": ["theme", "enabled"], "value": False}],
            }
            switched.append(page_plan["path"])
        else:
            needs_human.append(OWN_THEME_IN_EDITOR.format(path=page_plan["path"]))

    recalculated = None
    if changes:
        calculated_before = (current.get("theme") or {}).get("calculatedTheme")
        current = write_changes(slug, landing_id, changes, "theme")
        saved_inputs = (current.get("theme") or {}).get("input") or {}
        missing = [
            key
            for key, value in written.items()
            if not (
                saved_inputs.get(key) == value
                if key == "isDark"
                else same_color(saved_inputs.get(key), value)
            )
        ]
        missing += [path for path in switched if uses_own_theme(page_for_path(current, path))]
        if missing:
            raise RuntimeError("the theme change did not persist: " + ", ".join(missing))
        if site_patches:
            recalculated = (current.get("theme") or {}).get("calculatedTheme") != calculated_before
            if not recalculated:
                colors = ", ".join(
                    f"{key} {value}" for key, value in palette.items() if key != "isDark"
                )
                needs_human.insert(0, RECALCULATE_IN_EDITOR.format(colors=colors))
    result = {
        "patched": sorted(written),
        "unchanged": sorted(set(palette) - set(written) - {item["key"] for item in skipped}),
        "skipped": skipped,
        "pages_to_site_theme": switched,
        "recalculated": recalculated,
    }
    return result, needs_human, current


def image_path(base_dir: Path, image: dict) -> Path:
    path = Path(image["file"])
    return path if path.is_absolute() else base_dir / path


def check_image_files(base_dir: Path, images: list[dict]) -> None:
    """Stop before any upload unless every file is there, small enough, and the one the
    plan showed."""
    for image in images:
        path = image_path(base_dir, image)
        if image.get("sha256") is None:
            raise RuntimeError(
                f"{image['file']} wasn't next to the brief when the plan was rendered; add "
                "it, render the plan again and show it"
            )
        if not path.is_file():
            raise RuntimeError(f"{image['file']} is missing")
        if path.stat().st_size > MAX_UPLOAD_BYTES:
            raise RuntimeError(f"{image['file']} is over the 10 MB upload limit")
        if file_sha256(path) != image["sha256"]:
            raise RuntimeError(
                f"{image['file']} changed after the plan was approved; showing the new "
                "image needs a new yes"
            )


def slot_problem(block: dict, slot: str) -> str | None:
    """Why the block's slot can't take an image, or None when it can."""
    values = block.get("values")
    if not isinstance(values, dict) or isinstance(values.get("blockId"), str):
        return "it is a federated block, whose wrapper isn't patched"
    if not isinstance(values.get(IMAGE_SLOTS[slot][1]), dict):
        return f"it has no {slot} to put an image in"
    return None


def image_patch(block: dict, slot: str, url: str) -> dict | None:
    """The patch that puts ``url`` in the block's slot, or None when it is already there.
    Call it only when ``slot_problem`` found none."""
    path = IMAGE_SLOTS[slot]
    parent = block["values"][path[1]]
    if parent.get("img") == url:
        return None
    return {"op": "replace" if "img" in parent else "add", "path": list(path), "value": url}


def load_cache(path: Path, landing_id: str) -> dict[str, str]:
    """Uploads an earlier run made for this site: file sha256 -> CDN URL."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read the asset cache {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("landing_id") != landing_id:
        return {}
    uploads = value.get("uploads")
    return {
        key: url
        for key, url in (uploads.items() if isinstance(uploads, dict) else [])
        if isinstance(key, str) and isinstance(url, str)
    }


def save_cache(path: Path, landing_id: str, uploads: dict[str, str]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps({"landing_id": landing_id, "uploads": uploads}, indent=2), encoding="utf-8"
    )
    temporary.replace(path)


def upload(landing_id: str, path: Path) -> str:
    result = data(
        run_json(
            "shopbuilder",
            "upload-asset",
            "--landing-id",
            landing_id,
            "--file",
            str(path),
            "--type",
            "image",
        )
    )
    url = result.get("url") if isinstance(result, dict) else None
    if not isinstance(url, str) or not url.startswith("https://"):
        raise RuntimeError(f"upload-asset returned no URL for {path.name}")
    return url


def images_phase(
    slug: str,
    landing_id: str,
    current: dict,
    approved: dict,
    created: frozenset,
    base_dir: Path,
    site_assets: set[str],
    cache_path: Path,
) -> tuple[list[dict], list[str]]:
    """Upload the approved images once each and put them on their blocks."""
    images = approved.get("images", [])
    if not images:
        return [], []
    check_image_files(base_dir, images)
    needs_human: list[str] = []
    targets: list[tuple[dict, dict]] = []
    for image in images:
        allowed = set(image.get("existing_block_ids", [])) | created
        for path in image["pages"]:
            module = image.get("page_modules", {}).get(path, image["module"])
            page = page_for_path(current, path) or {}
            for block in page.get("blocks", []):
                if effective_module(block) != module:
                    continue
                if block.get("_id") in allowed:
                    targets.append((image, block))
                else:
                    needs_human.append(
                        f"The {module} block on {path} existed before this "
                        f"assembly and the plan didn't list it; set its image to "
                        f"{image['file']} in the editor if it should have it."
                    )

    cache = load_cache(cache_path, landing_id)
    urls: dict[str, str] = {}
    results: list[dict] = []
    changes: dict[str, dict] = {}
    written: list[tuple[str, tuple, str]] = []
    for image, block in targets:
        module = effective_module(block)
        entry = {
            "file": image["file"],
            "block_id": block["_id"],
            "module": module,
            "slot": image["slot"],
        }
        problem = slot_problem(block, image["slot"])
        if problem is not None:
            # Nothing to put it on, so nothing is uploaded for it.
            results.append({**entry, "status": "skipped", "reason": problem})
            needs_human.append(
                f"{image['file']} wasn't put on the {module} block: {problem}."
            )
            continue
        sha = image["sha256"]
        if sha not in urls:
            cached = cache.get(sha)
            if cached in site_assets:
                urls[sha] = cached
            else:
                urls[sha] = upload(landing_id, image_path(base_dir, image))
                cache[sha] = urls[sha]
                save_cache(cache_path, landing_id, cache)
        patch = image_patch(block, image["slot"], urls[sha])
        entry["url"] = urls[sha]
        if patch is not None:
            changes.setdefault(
                block["_id"], {"type": "block", "id": block["_id"], "patches": []}
            )["patches"].append(patch)
            written.append((block["_id"], IMAGE_SLOTS[image["slot"]], urls[sha]))
            entry["status"] = "set"
            background = block["values"].get("background")
            color = background.get("color") if isinstance(background, dict) else None
            if image["slot"] == "background" and isinstance(color, str) and is_opaque(color):
                needs_human.append(
                    f"The {module} block's background color {color} is opaque "
                    "and hides its image; set a color with alpha below 1 with "
                    "patch_backgrounds.py."
                )
        else:
            entry["status"] = "unchanged"
        results.append(entry)

    if changes:
        saved = write_changes(slug, landing_id, changes, "image")
        blocks = {
            block.get("_id"): block
            for page in saved.get("pages", [])
            for block in page.get("blocks", [])
            if isinstance(block, dict)
        }
        missing = []
        for block_id, path, url in written:
            node: object = blocks.get(block_id, {})
            for key in path:
                node = node.get(key) if isinstance(node, dict) else None
            if node != url:
                missing.append(f"{block_id} {path[1]}")
        if missing:
            raise RuntimeError("the images did not persist: " + ", ".join(missing))
    return results, needs_human


def translation(entry: object, locale: str) -> object:
    """A string's text in ``locale``; a read may key it by the short code, such as `en`."""
    translations = entry.get("translations") if isinstance(entry, dict) else None
    translations = translations if isinstance(translations, dict) else {}
    return translations.get(locale, translations.get(locale.split("-")[0]))


def text_slot(loc: object, page_id: str, lid: str, locale: str) -> tuple[str, str, object]:
    """Where an `L:` string lives (its page's scope or `common`), its description, and its
    current text in ``locale``."""
    loc = loc if isinstance(loc, dict) else {}
    page = ((loc.get("pages") or {}).get(page_id) or {}).get("texts") or {}
    for scope, texts in ((page_id, page), ("common", loc.get("common") or {})):
        entry = texts.get(lid) if isinstance(texts, dict) else None
        if isinstance(entry, dict):
            description = entry.get("description")
            return (
                scope,
                description if isinstance(description, str) else "",
                translation(entry, locale),
            )
    return page_id, "", None


def flat_texts(loc: object) -> dict[tuple[str, str], object]:
    """Every string in a `get-localization` result, by (scope, `L:` id)."""
    loc = loc if isinstance(loc, dict) else {}
    flat: dict[tuple[str, str], object] = {}
    for page_id, page in (loc.get("pages") or {}).items():
        for lid, entry in ((page or {}).get("texts") or {}).items():
            flat[(page_id, lid)] = entry
    for lid, entry in (loc.get("common") or {}).items():
        flat[("common", lid)] = entry
    return flat


def faq_item_ids(landing_id: str, block_id: str, index: int) -> tuple[str, str, str]:
    """Stable IDs for an FAQ item this script adds, so a rerun finds it again."""
    component = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{landing_id}:{block_id}:faq:{index}"))
    return (
        component,
        "L:" + str(uuid.uuid5(uuid.NAMESPACE_URL, component + ":question")),
        "L:" + str(uuid.uuid5(uuid.NAMESPACE_URL, component + ":answer")),
    )


def copy_phase(
    slug: str, landing_id: str, current: dict, approved: dict, created: frozenset
) -> tuple[list[dict], list[str], dict]:
    """Write the approved text in the primary locale: block text fields, then the FAQ
    items, adding or removing items to match the approved list."""
    copy_plan = approved.get("copy") or {}
    texts, faq = copy_plan.get("texts", []), copy_plan.get("faq")
    if not texts and not faq:
        return [], [], current
    locale = copy_plan["locale"]
    before = localization(slug)
    writes: dict[str, dict[str, dict]] = {}
    expected: dict[tuple[str, str], str] = {}
    structural: dict[str, dict] = {}
    added: dict[str, list[str]] = {}
    results: list[dict] = []
    needs_human: list[str] = []

    def write(page_id: str, lid: str, html_text: str) -> str:
        scope, description, now = text_slot(before, page_id, lid, locale)
        expected[(scope, lid)] = html_text
        if isinstance(now, str) and now.strip() == html_text.strip():
            return "unchanged"
        writes.setdefault(scope, {})[lid] = {
            "description": description,
            "translation": html_text,
        }
        return "set"

    def planned_blocks(item: dict):
        allowed = set(item.get("existing_block_ids", [])) | created
        for path in item["pages"]:
            module = item["page_modules"][path]
            page = page_for_path(current, path) or {}
            for block in page.get("blocks", []):
                if effective_module(block) != module:
                    continue
                if block.get("_id") in allowed:
                    yield page, block
                else:
                    needs_human.append(
                        f"The {module} block on {path} existed before this assembly and the "
                        "plan didn't list it; its text wasn't changed."
                    )

    for item in texts:
        for page, block in planned_blocks(item):
            field = (block.get("values") or {}).get(item["field"])
            lid = field.get("id") if isinstance(field, dict) else None
            entry = {
                "block_id": block["_id"],
                "module": effective_module(block),
                "field": item["field"],
            }
            if isinstance(lid, str) and lid.startswith("L:"):
                entry["status"] = write(page["_id"], lid, item["html"])
            else:
                entry.update(status="skipped", reason=f"it has no {item['field']} text")
                needs_human.append(
                    f"The {entry['module']} block has no {item['field']} text to write; set "
                    "it in the editor if it should have one."
                )
            results.append(entry)

    for page, block in planned_blocks(faq) if faq else []:
        components = block.get("components")
        components = components if isinstance(components, list) else []
        questions = [
            index
            for index, component in enumerate(components)
            if isinstance(component, dict) and component.get("type") == "questionV2"
        ]
        statuses, patches = [], []
        for index, item in enumerate(faq["items"]):
            if index < len(questions):
                component = components[questions[index]]
                question_id = (component.get("question") or {}).get("id")
                answer_id = (component.get("answer") or {}).get("id")
                if not all(
                    isinstance(lid, str) and lid.startswith("L:")
                    for lid in (question_id, answer_id)
                ):
                    raise RuntimeError(
                        f"FAQ item {index + 1} of block {block['_id']} has no question or "
                        "answer text ID; nothing of the copy was written"
                    )
            else:
                component_id, question_id, answer_id = faq_item_ids(
                    landing_id, block["_id"], index
                )
                patches.append(
                    {
                        "op": "add",
                        "path": ["components", len(components) + len(patches)],
                        "value": {
                            "_id": component_id,
                            "type": "questionV2",
                            "enable": True,
                            "question": {"id": question_id},
                            "answer": {"id": answer_id},
                        },
                    }
                )
                added.setdefault(block["_id"], []).append(component_id)
            statuses.append(write(page["_id"], question_id, item["question"]))
            statuses.append(write(page["_id"], answer_id, item["answer"]))
        extra = questions[len(faq["items"]):]
        # `enable: false` is ignored for FAQ questions: extra items are removed.
        patches.extend(
            {"op": "remove", "path": ["components", index]} for index in reversed(extra)
        )
        if patches:
            structural[block["_id"]] = {"type": "block", "id": block["_id"], "patches": patches}
        results.append(
            {
                "block_id": block["_id"],
                "module": "faq",
                "field": "items",
                "status": "set" if patches or "set" in statuses else "unchanged",
                "added": len(added.get(block["_id"], [])),
                "removed": len(extra),
            }
        )

    if writes:
        # The text goes in first: a block that points at a missing string breaks the page.
        run_json(
            "shopbuilder",
            "update-many-localization",
            "--slug",
            slug,
            "--data",
            json.dumps({"locale": locale, "perScopeValues": writes}, separators=(",", ":")),
        )
    if structural:
        current = write_changes(slug, landing_id, structural, "FAQ")
    if writes or structural:
        after = flat_texts(localization(slug))
        old = flat_texts(before)
        written = {(scope, lid) for scope, ids in writes.items() for lid in ids}
        outside = sorted(
            key[1]
            for key in set(old) | set(after)
            if key not in written and old.get(key) != after.get(key)
        )
        if outside:
            raise RuntimeError("text outside the plan changed: " + ", ".join(outside))
        missing = []
        for key, html_text in expected.items():
            now = translation(after.get(key), locale)
            if not isinstance(now, str) or now.strip() != html_text.strip():
                missing.append(key[1])
        saved_ids = {
            component.get("_id")
            for page in current.get("pages", [])
            for block in page.get("blocks", [])
            for component in (block.get("components") or [])
            if isinstance(component, dict)
        }
        missing += [cid for ids in added.values() for cid in ids if cid not in saved_ids]
        if missing:
            raise RuntimeError("the copy did not persist: " + ", ".join(missing))
    return results, needs_human, current


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("brief", type=Path)
    parser.add_argument("--approved-plan", type=Path, required=True)
    parser.add_argument("--run-report", type=Path, action="append", required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument(
        "--asset-cache",
        type=Path,
        help="uploads earlier runs made; default: asset-cache.json next to the approved plan",
    )
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
        slug = brief["site"]["slug"]
        reports = [load_run_report(path) for path in args.run_report]
        check_reports(reports, args.run_report, approved, slug)
        base_dir = args.brief.resolve().parent
        copy_plan = approved.get("copy") or {}
        if not (
            approved.get("brand", {}).get("theme")
            or approved.get("images")
            or copy_plan.get("texts")
            or copy_plan.get("faq")
        ):
            print(
                json.dumps(
                    {
                        "operation_succeeded": True,
                        "status": "nothing-to-apply",
                        "slug": slug,
                        "theme": "no palette in the approved plan; the site keeps its theme",
                        "images": [],
                        "copy": [],
                        "published": False,
                    },
                    indent=2,
                )
            )
            return 0
        check_image_files(base_dir, approved.get("images", []))

        run_preflight(args.brief, args.approved_test_projects)
        check_cli_context(brief["project"])
        if not verified_backup(args.backup_dir, brief["project"], slug):
            raise RuntimeError(
                "a complete verified backup taken after the last apply run is required"
            )
        current = structure(slug)
        if structure_hash(current) != structure_hash(backup_structure(args.backup_dir)):
            raise RuntimeError("the site changed after the backup; back up again")
        landing_id = current.get("_id")
        if not isinstance(landing_id, str) or any(
            report.get("landing_id") != landing_id for report in reports
        ):
            raise RuntimeError("the site isn't the one the run reports describe")

        created_pages = {
            path
            for report in reports
            for path in report.get("created_pages", [])
            if isinstance(path, str)
        }
        theme, theme_needs, current = theme_phase(
            slug, landing_id, current, approved, created_pages
        )
        created = frozenset().union(*(created_block_ids(report) for report in reports))
        images, image_needs = images_phase(
            slug,
            landing_id,
            current,
            approved,
            created,
            base_dir,
            asset_urls(args.backup_dir) if approved.get("images") else set(),
            args.asset_cache or args.approved_plan.resolve().parent / "asset-cache.json",
        )
        copy_results, copy_needs, current = copy_phase(
            slug, landing_id, structure(slug), approved, created
        )
        print(
            json.dumps(
                {
                    "operation_succeeded": True,
                    "status": "style-applied",
                    "approved_confirmation_id": approved["confirmation_id"],
                    "slug": slug,
                    "landing_id": landing_id,
                    "theme": theme,
                    "images": images,
                    "copy": copy_results,
                    "needs_human": theme_needs + image_needs + copy_needs,
                    "pending_phases": approved.get("unsupported_phases", []),
                    "published": False,
                },
                indent=2,
            )
        )
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Style failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

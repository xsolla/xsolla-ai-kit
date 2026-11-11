#!/usr/bin/env python3
"""What each XLA page must look like: the manifest, pinned to its reference page, for one batch row.

Render, the pre-write validation and the post-write check all derive a page from here, so the
three can't disagree about what the manifest asks for.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import xla_common as common  # noqa: E402

# Batch row field -> block field. The manifest names row fields only; these block field names
# are UNVERIFIED. A plan refuses any field the reference page's block doesn't have.
ROW_FIELDS = {
    "hero_title": "title",
    "hero_description": "description",
    "hero_image": "image",
    "partner_name": "partnerName",
    "partner_logo_url": "partnerLogoUrl",
    "offers": "offersJson",
}
ROW_LIMITS = {"hero_title": 60, "hero_description": 150}
ROW_REQUIRED = ("provider", "partner_name", "hero_title", "hero_description", "hero_image", "faq")
ROW_KEYS = set(ROW_REQUIRED) | {"partner_logo_url", "offers", "seo_title", "seo_description"}
JSON_OF_ROW = re.compile(r"^JSON string of row\.([a-z_]+)$")
SEO_FIELDS = ("title", "description", "image", "canonical")


def row_errors(row: object, index: int) -> list[str]:
    prefix = f"providers[{index}]"
    if not isinstance(row, dict):
        return [f"{prefix} must be an object"]
    errors = []
    unknown = sorted(set(row) - ROW_KEYS)
    if unknown:
        errors.append(f"{prefix} has unknown keys: {', '.join(unknown)}")
    for key in ROW_REQUIRED:
        if key not in row:
            errors.append(f"{prefix}.{key} is required")
    provider = row.get("provider")
    if "provider" in row and (not isinstance(provider, str) or not common.SITE_SLUG_RE.fullmatch(provider)):
        errors.append(f"{prefix}.provider must be the lowercase URL segment, such as klarna")
    for key in ("partner_name", "hero_title", "hero_description", "seo_title", "seo_description"):
        if key in row and (not isinstance(row[key], str) or not row[key].strip()):
            errors.append(f"{prefix}.{key} must be non-empty text")
    for key, limit in ROW_LIMITS.items():
        if isinstance(row.get(key), str) and len(row[key]) > limit:
            errors.append(f"{prefix}.{key} is {len(row[key])} characters (max {limit})")
    for key in ("hero_image", "partner_logo_url"):
        if key in row:
            value = row[key]
            if not isinstance(value, str) or urlsplit(value).scheme != "https" or not urlsplit(value).netloc:
                errors.append(f"{prefix}.{key} must be an https URL")
    faq = row.get("faq")
    if "faq" in row and (
        not isinstance(faq, list)
        or not faq
        or any(
            not isinstance(item, dict)
            or set(item) != {"question", "answer"}
            or not all(isinstance(item[k], str) and item[k].strip() for k in ("question", "answer"))
            for item in faq
        )
    ):
        errors.append(f"{prefix}.faq must be a non-empty list of {{question, answer}}")
    if "offers" in row and not isinstance(row["offers"], list):
        errors.append(f"{prefix}.offers must be a list")
    return errors


def batch_rows(batch: object) -> tuple[list[dict], list[str]]:
    rows = batch.get("providers") if isinstance(batch, dict) else None
    if not isinstance(rows, list):
        return [], ["the batch must hold a providers list"]
    errors = [e for i, row in enumerate(rows) for e in row_errors(row, i)]
    providers = [row.get("provider") for row in rows if isinstance(row, dict)]
    duplicates = sorted({p for p in providers if providers.count(p) > 1})
    if duplicates:
        errors.append("providers listed twice: " + ", ".join(map(str, duplicates)))
    return rows, errors


def json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def reference_pins(manifest: dict, structure: dict, type_name: str) -> tuple[dict, list[str], dict | None]:
    """{block key: {package, version, fields}} from the type's reference page."""
    route = common.reference_route(manifest, type_name)
    page = common.find_page(structure, route)
    if page is None:
        return {}, [f"the reference page {route} for {type_name} pages is not on the site"], None
    packages = common.key_of_package(manifest)
    pins, errors = {}, []
    for index, block in enumerate(page.get("blocks") or []):
        package, version = common.block_identity(block)
        if package is None:
            if block.get("module") == "federated":
                errors.append(
                    f"reference {route} block {index + 1} ({common.block_label(block)}) has no readable "
                    "package: the CLI must return it in values.blockId"
                )
            continue
        key = packages.get(package)
        if key is None:
            continue
        if not version:
            errors.append(f"reference {route} block {package} has no readable version")
            continue
        if key in pins:
            errors.append(f"reference {route} has {package} twice")
            continue
        pins[key] = {"package": package, "version": version, "fields": sorted(common.block_fields(block))}
    return pins, errors, page


def entry_bindings(manifest: dict, type_name: str, entry: dict, key: str) -> tuple[dict, str | None]:
    bind = entry.get("bind")
    if bind is None:
        bind = entry.get("bind_" + key.replace("-", "_"))
    if bind is None and type_name != "game" and len(common.block_keys(entry)) > 1:
        # "same variant as the game page": the combined page's about-game entry lists no
        # bindings, so it takes the game page's for the same variant.
        for game_entry in common.page_type(manifest, "game")["blocks"]:
            if key in common.block_keys(game_entry):
                bind = game_entry.get("bind_" + key.replace("-", "_"))
                if bind:
                    return dict(bind), (
                        f"{type_name} {key} takes the game page's bindings for the same variant; "
                        "the manifest lists none for it"
                    )
    return dict(bind or {}), None


def row_value(row: dict, name: str) -> object:
    value = row.get(name)
    return json_text(value) if isinstance(value, (list, dict)) else value


def block_content(entry: dict, row: dict | None) -> tuple[dict, bool]:
    """(field -> value from settings and the row, whether the row has content for it)."""
    fields: dict = {}
    for field, value in (entry.get("settings") or {}).items():
        if isinstance(value, str) and value.startswith("row."):
            value = (row or {}).get(value[4:])
        fields[field] = value
    content = entry.get("content_from_row")
    has_content = content is None
    if isinstance(content, list):
        for name in content:
            if row and row.get(name) not in (None, "", []):
                fields[ROW_FIELDS.get(name, name)] = row_value(row, name)
                has_content = True
    elif isinstance(content, dict):
        for field, spec in content.items():
            match = JSON_OF_ROW.fullmatch(str(spec))
            name = match.group(1) if match else str(spec).removeprefix("row.")
            if row and row.get(name) not in (None, "", []):
                fields[field] = json_text(row[name]) if match else row[name]
                has_content = True
    return fields, has_content


def seo_model(manifest: dict, spec: dict, row: dict | None, provider: str | None) -> dict:
    seo = {}
    for field in SEO_FIELDS:
        value = (spec.get("seo") or {}).get(field)
        if not isinstance(value, str):
            continue
        if value == "from row":
            name = {"title": "seo_title", "description": "seo_description"}.get(field)
            fallback = {"title": "hero_title", "description": "hero_description"}.get(field)
            if row and name:
                seo[field] = {"value": row.get(name) or row.get(fallback)}
        elif value.startswith("https://"):
            text = value.replace("{provider}", provider or "{provider}")
            if field == "canonical":
                # The manifest writes a route param as {slug}; Site Builder fills :slug in a dynamic
                # page's canonical URL with the page's value when it renders. Only the page's own
                # route params are rewritten: any other {name} stays as written.
                for param in re.findall(r":([A-Za-z0-9_]+)", str(spec.get("route") or "")):
                    text = text.replace("{" + param + "}", ":" + param)
            seo[field] = {"value": text}
        else:
            source, output = common.split_source(value)
            seo[field] = {"source": source, "output": output}
    return seo


def desired_page(manifest: dict, config: dict, structure: dict, type_name: str,
                 row: dict | None = None, existing: dict | None = None) -> tuple[dict, list[str], list[str]]:
    """The manifest's page for one row, pinned to the reference page. Returns (page, errors, notes)."""
    spec = common.page_type(manifest, type_name)
    provider = row.get("provider") if row else None
    route = common.route_for(manifest, type_name, provider)
    pins, errors, reference = reference_pins(manifest, structure, type_name)
    notes: list[str] = []
    existing_packages = {
        common.block_identity(block)[0] for block in (existing or {}).get("blocks") or []
    }
    blocks = []
    for entry in spec.get("blocks") or []:
        keys = common.block_keys(entry)
        present = [key for key in keys if key in pins]
        fields_needed = entry.get("content_from_row") is not None and row is not None
        if len(present) > 1:
            errors.append(f"the reference page has more than one of {', '.join(present)}")
            continue
        if not present:
            if entry.get("required"):
                errors.append(f"the reference page for {type_name} has no {' or '.join(keys)} block to pin")
            elif fields_needed and block_content(entry, row)[1]:
                errors.append(
                    f"{provider}: the row has content for {keys[0]}, but the reference page has no "
                    f"{keys[0]} block to pin its version"
                )
            continue
        key = present[0]
        pin = pins[key]
        bindings, note = entry_bindings(manifest, type_name, entry, key)
        if note and note not in notes:
            notes.append(note)
        fields, has_content = block_content(entry, row)
        hidden = False
        if not entry.get("required") and not has_content:
            if pin["package"] not in existing_packages:
                continue
            hidden = True
        for field in fields:
            if field not in pin["fields"]:
                errors.append(
                    f"{pin['package']}@{pin['version']} on the reference page has no field {field!r}; "
                    "the manifest's block field names are unverified"
                )
        for field in fields:
            if field in bindings:
                errors.append(f"{key}.{field} is both bound and typed in the manifest")
        blocks.append({
            "key": key,
            "package": pin["package"],
            "version": pin["version"],
            "required": bool(entry.get("required")),
            "hidden": hidden,
            "bindings": {
                field: dict(zip(("source", "output"), common.split_source(ref)))
                for field, ref in bindings.items()
            },
            "fields": fields,
        })
    connections: dict[str, dict] = {}
    if spec.get("kind") == "dynamic":
        paths = common.provider_spec(manifest, spec["paths"], config)
        connections[paths["key"]] = {**paths, "linked": False}
    seo = seo_model(manifest, spec, row, provider)
    sources = {b["source"] for block in blocks for b in block["bindings"].values()}
    sources |= {s["source"] for s in seo.values() if "source" in s}
    for source in sorted(sources):
        conn = common.provider_spec(manifest, source, config)
        linked = spec.get("kind") == "dynamic" and source == spec.get("data")
        connections[source] = {**conn, "linked": linked}
    look = {key: reference[key] for key in common.PAGE_LOOK_KEYS if reference and key in reference}
    name = {
        "payment_provider": f"Payment: {(row or {}).get('partner_name', provider)}",
        "combined": f"Payment: {(row or {}).get('partner_name', provider)} games",
    }.get(type_name, (existing or {}).get("name") or type_name)
    page = {
        "page_type": type_name,
        "route": route,
        "provider": provider,
        "kind": spec.get("kind"),
        "name": name,
        "reference_route": common.reference_route(manifest, type_name),
        "connections": [connections[key] for key in sorted(connections)],
        "blocks": blocks,
        "seo": seo,
        "look": look,
    }
    return page, errors, notes

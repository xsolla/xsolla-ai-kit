"""The ordered write plan: what would change, before anything does.

The Definition of Done asks that the extracted-to-shop mapping be shown before
writing.  For the Steam path that cannot come from the API: the parsing
endpoint returns ``{developer, icon, title}`` and nothing else (verified live,
merchant 936601, 2026-09-14), so three of eleven target fields are previewable
server-side.  This module builds the rest of the preview from the agent's own
extraction, which is why the extraction step is required even on the one source
where the backend can do the import itself.

Order is not cosmetic.  It follows the sequence the CLI's own reference records
as working, and two of the steps are ordered by hard constraints:

1. Read the structure.  Also the backup -- keep the response.
2. Upload assets.  Remote URLs cannot be patched in: ``upload-asset`` takes a
   local file, so every image is fetch-then-upload, and only the returned CDN
   url is safe to write.  A Steam URL written straight into a block hotlinks
   another storefront from the partner's page.
3. Write localization **before** the image patches.  A block that references an
   ``L:`` id with no string behind it renders as a 500, so the string has to
   exist before anything makes the block visible.
4. Patch images and backgrounds.
5. Read back.  Every patch, not a sample: Shop Builder answers ``ok: true`` to a
   patch at a path that does not exist and changes nothing, so an unread write
   is an unverified one.

What this module misses: it plans, it does not execute, and it does not diff
against current values -- an operation that would write what is already there
still appears.  It also cannot see whether an ``L:`` id exists, because the
localization store is a separate fetch; ``--localization`` is accepted and the
check is skipped without it, reported as unverified rather than assumed.
"""

from __future__ import annotations

from html import escape

from . import catalog as catalog_plan
from . import fields as field_model
from . import mapping
from . import overflow
from . import sanitize
from .bbcode import to_html as bbcode_to_html
from .errors import finding
from .listing_schema import long_description


def index_blocks(structure):
    """Map module name -> list of ``(page_id, block_id)``, in page order."""
    found = {}
    for page in (structure or {}).get("pages") or []:
        page_id = page.get("_id")
        for block in page.get("blocks") or []:
            if isinstance(block, dict) and block.get("module"):
                found.setdefault(block["module"], []).append((page_id, block["_id"]))
    return found


def _asset_ops(field, urls, target, block_id, page_id):
    """One fetch-then-upload-then-patch triple per image."""
    ops = []
    for index, url in enumerate(urls):
        path = list(target.path)
        if field == "screenshots":
            path = path + [index, "image", "img"]
        ops.append({
            "kind": "asset",
            "field": field,
            "module": target.module,
            "block_id": block_id,
            "page_id": page_id,
            "path": path,
            "source_url": url,
            "confidence": target.confidence,
            "note": ("Fetch to a local file, upload-asset, then patch the returned "
                     "CDN url. Never patch the source URL directly."),
        })
    return ops


def build(document, structure, localization=None):
    """Build the plan.  Returns ``(plan, blockers)``.

    ``blockers`` are conditions that must clear before any write. A non-empty
    ``blockers`` means the plan is a preview only and must not be executed.
    """
    blockers = []
    document = document or {}
    values = document.get("fields") or {}
    source = document.get("source")

    if document.get("rights_confirmed") is not True:
        blockers.append(finding(
            "rights_confirmed",
            "true before any write -- the partner confirms they hold the rights to "
            "this listing's copy and artwork",
            "not confirmed",
        ))

    agrees = mapping.source_matches_url(source, document.get("source_url"))
    if agrees is False:
        blockers.append(finding(
            "source", "a source matching source_url's host",
            "%s, which source_url contradicts" % source,
        ))

    blocks = index_blocks(structure)
    if not blocks:
        blockers.append(finding(
            "structure", "a landing with at least one page of blocks",
            "no blocks -- a freshly created landing is empty, and import-listing "
            "silently no-ops on a landing that already has a structure",
        ))

    localization_ops = []
    asset_ops = []
    unresolved = []
    manual = []

    for name in field_model.dod_fields() + ("developer",):
        target = mapping.target_for(name)
        if target is None:
            continue
        present = (values.get(name)
                   or (name == "long_description" and long_description(document)[0]))
        if not present:
            continue

        if target.action in (mapping.OVERFLOW, mapping.CATALOG):
            # Aggregated below: three overflow fields share one component, and
            # the in-app items are one batch of catalog commands.
            continue

        if target.action == mapping.MANUAL:
            manual.append({
                "field": name,
                "action": target.action,
                "note": target.note,
                "value": values.get(name),
            })
            continue

        placements = blocks.get(target.module) or []
        if not placements:
            unresolved.append({
                "field": name,
                "module": target.module,
                "reason": "no %s block on this landing" % target.module,
                "note": target.note,
            })
            continue
        page_id, block_id = placements[0]

        if target.action == mapping.ASSET:
            raw = values.get(name)
            # A string here would otherwise be iterated character by character,
            # emitting one bogus operation per letter.  The CLI validates before
            # calling, but this is a public entry point.
            urls = raw if isinstance(raw, list) else [raw]
            asset_ops.extend(_asset_ops(name, [u for u in urls
                                               if isinstance(u, str) and u.strip()],
                                        target, block_id, page_id))
            if name == "key_art":
                for path, value in mapping.KEY_ART_COMPANIONS:
                    asset_ops.append({
                        "kind": "patch",
                        "field": name,
                        "module": target.module,
                        "block_id": block_id,
                        "page_id": page_id,
                        "path": list(path),
                        "value": value,
                        "confidence": mapping.CONFIRMED,
                        "note": "Companion to the key-art write; without it the "
                                "background stays hidden.",
                    })
            continue

        if name == "long_description":
            raw, form = long_description(document)
            if form == "bbcode":
                text, dropped = bbcode_to_html(raw)
            elif form == "html":
                # Steam and Play both serve rendered HTML, so this is the common
                # path, not the exception.  It has to be sanitised before it goes
                # anywhere near a localization write.
                text, dropped = sanitize.to_html(raw)
            else:
                text, dropped = escape(raw or "", quote=False), []
        else:
            text, dropped = values.get(name), []

        localization_ops.append({
            "kind": "localization",
            "field": name,
            "module": target.module,
            "block_id": block_id,
            "page_id": page_id,
            "path": list(target.path),
            "value": text,
            "dropped": dropped,
            "confidence": target.confidence,
            "note": target.note,
        })

    # Overflow: genres, tags and age rating as one block of copy, because no
    # module has a structured field for any of them.
    overflow_ops = []
    overflow_html, overflow_carried = overflow.render(values)
    if overflow_html:
        target = mapping.target_for("genres")
        placements = blocks.get(target.module) or []
        if placements:
            page_id, block_id = placements[0]
            overflow_ops.append({
                "kind": "overflow",
                "field": "+".join(overflow_carried),
                "module": target.module,
                "block_id": block_id,
                "page_id": page_id,
                "path": list(target.path),
                "value": overflow_html,
                "dropped": [],
                "confidence": target.confidence,
                "note": "One appended TEXT component carrying %s. Needs a "
                        "generated component id; read the block first."
                        % ", ".join(overflow_carried),
            })
        else:
            for name in overflow_carried:
                unresolved.append({
                    "field": name,
                    "module": target.module,
                    "reason": "no %s block to carry the copy" % target.module,
                    "note": target.note,
                })

    # Catalog: in-app items become priced virtual items.
    catalog_ops, catalog_warnings = [], []
    if values.get("iap_items"):
        catalog_ops, catalog_warnings = catalog_plan.build_operations(
            values["iap_items"], source)

    unverified = []
    if localization is None:
        unverified.append(
            "L: reference existence -- pass --localization (from "
            "`xsolla shopbuilder get-localization`) to check that every id a "
            "localization write targets already exists"
        )
    schema_only = sorted({op["field"] for op in localization_ops + asset_ops
                          if op["confidence"] == mapping.SCHEMA})
    if schema_only:
        unverified.append(
            "patch paths not confirmed against the live API, so a write may "
            "silently no-op: " + ", ".join(schema_only)
        )

    plan = {
        "source": source,
        "source_label": field_model.SOURCE_LABELS.get(source, str(source)),
        "source_url": document.get("source_url"),
        "operations": localization_ops + overflow_ops + asset_ops,
        "catalog_operations": catalog_ops,
        "catalog_warnings": catalog_warnings,
        "manual_follow_up": manual,
        "unresolved": unresolved,
        "unverified": unverified,
        "counts": {
            "localization": len(localization_ops),
            "overflow": len(overflow_ops),
            "asset": len([o for o in asset_ops if o["kind"] == "asset"]),
            "patch": len([o for o in asset_ops if o["kind"] == "patch"]),
            "catalog": len(catalog_ops),
            "manual": len(manual),
            "unresolved": len(unresolved),
        },
    }
    for step, op in enumerate(plan["operations"], start=1):
        op["step"] = step
    return plan, blockers

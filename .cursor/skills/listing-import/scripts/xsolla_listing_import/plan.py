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
from . import packs as packs_plan
from . import sanitize
from .bbcode import to_html as bbcode_to_html
from .errors import finding
from .listing_schema import long_description


def resolve_localized_id(block, path):
    """The ``L:`` id a localized field already carries, or ``None``.

    A localized field is stored as ``{"enable": true, "id": "L:<uuid>"}`` -- the
    string itself lives in the separate localization store.  So a write to
    ``values.title`` is really a write to that id, and the runner needs the id,
    not the path.

    Resolved here rather than in the runner because this module already has the
    block in hand.  ``None`` means the field is absent or carries no id, and the
    caller must not invent one: a localization write against an id the block
    does not reference changes a string nothing renders.
    """
    cursor = block
    for segment in path:
        if not isinstance(cursor, dict) or segment not in cursor:
            return None
        cursor = cursor[segment]
    if isinstance(cursor, dict):
        found = cursor.get("id")
        return found if isinstance(found, str) and found.startswith("L:") else None
    if isinstance(cursor, str) and cursor.startswith("L:"):
        return cursor
    return None


def resolve_component_path(block, component_type, field):
    """The path to ``field`` on the first component of ``component_type``.

    The header's logo is not a ``values`` field.  It is a component of
    ``type: "logo"`` inside ``values.components``, keyed by a UUID the editor
    generated -- so no static path can reach it, which is how the first live
    run found ``values.logo.img`` to be wrong: the patch was accepted and
    changed nothing, and the read-back caught it.

    Returns ``None`` when no such component exists.  The caller must not fall
    back to a guessed path: that is the failure this function exists to stop.
    """
    components = ((block or {}).get("values") or {}).get("components")
    if isinstance(components, dict):
        pairs = sorted(components.items())
    elif isinstance(components, list):
        pairs = list(enumerate(components))
    else:
        return None
    for key, component in pairs:
        if isinstance(component, dict) and component.get("type") == component_type:
            return ["values", "components", key, field]
    return None


def index_blocks(structure):
    """Map module name -> list of ``(page_id, block_id)``, in page order."""
    found = {}
    for page in (structure or {}).get("pages") or []:
        page_id = page.get("_id")
        for block in page.get("blocks") or []:
            if isinstance(block, dict) and block.get("module"):
                found.setdefault(block["module"], []).append(
                    (page_id, block["_id"], block))
    return found


def _asset_ops(field, urls, target, block_id, page_id, path_override=None):
    """One fetch-then-upload-then-patch triple per image."""
    ops = []
    for index, url in enumerate(urls):
        path = list(path_override if path_override is not None else target.path)
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
        if field == "screenshots":
            # The slide's colour layer sits over the image, and the template
            # ships it 85% opaque. Without these the screenshot is uploaded,
            # patched, read back as correct -- and invisible.
            for key, value in mapping.SLIDE_COMPANIONS:
                ops.append({
                    "kind": "patch",
                    "field": field,
                    "module": target.module,
                    "block_id": block_id,
                    "page_id": page_id,
                    "path": path[:-1] + [key],
                    "value": value,
                    "confidence": mapping.CONFIRMED,
                    "note": "Companion to the slide image; the template's dark "
                            "overlay hides it otherwise.",
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

        if target.action in (mapping.OVERFLOW, mapping.CATALOG,
                             mapping.REQUIREMENTS):
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
        page_id, block_id, block_doc = placements[0]

        if target.action == mapping.ASSET:
            resolved_path = target.path
            if target.component_type:
                resolved_path = resolve_component_path(
                    block_doc, target.component_type, target.path[-1])
                if resolved_path is None:
                    unresolved.append({
                        "field": name,
                        "module": target.module,
                        "reason": "no %s component on the %s block to carry it"
                                  % (target.component_type, target.module),
                        "note": target.note,
                    })
                    continue
            raw = values.get(name)
            # A string here would otherwise be iterated character by character,
            # emitting one bogus operation per letter.  The CLI validates before
            # calling, but this is a public entry point.
            urls = raw if isinstance(raw, list) else [raw]
            usable = [u for u in urls if isinstance(u, str) and u.strip()]

            # A gallery's `slides` array is finite and pre-existing: a patch to
            # slides[3] on a three-slide block is accepted and changes nothing.
            # Found live -- Steam's imported gallery has ten slides and took all
            # ten screenshots, while the default template has three and silently
            # dropped screenshots four upward. Cap at what the block has and
            # report the surplus rather than writing into nothing.
            if name == "screenshots":
                slots = len(((block_doc.get("values") or {}).get("slides")) or [])
                if len(usable) > slots:
                    unresolved.append({
                        "field": "screenshots",
                        "module": target.module,
                        "reason": "the %s block has %d slide(s); %d screenshot(s) "
                                  "were extracted, so %d cannot be placed"
                                  % (target.module, slots, len(usable),
                                     len(usable) - slots),
                        "note": "Add slides in Site Builder, or accept the first "
                                "%d." % slots,
                    })
                usable = usable[:slots]

            asset_ops.extend(_asset_ops(name, usable, target, block_id, page_id,
                                        path_override=resolved_path))
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

        localized = resolve_localized_id(block_doc, target.path)
        if name == "long_description" and localized is None:
            # The description block keeps its text on a TEXT component's
            # `label`, one level below `values.components`. The original path
            # stopped at the components dict, found no id, and the runner
            # correctly refused -- leaving "About the game" as template copy.
            component = resolve_component_path(block_doc, "text", "label")
            if component is not None:
                localized = resolve_localized_id(block_doc, component)
                if localized is not None:
                    target_path = component
                else:
                    target_path = list(target.path)
            else:
                target_path = list(target.path)
        else:
            target_path = list(target.path)

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
            "path": target_path,
            "localized_id": localized,
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
            page_id, block_id, _doc = placements[0]
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

    # Catalog first: in-app items become priced virtual items, and a pack
    # card's buy button points at the SKU, which is where its price comes from.
    catalog_ops, catalog_warnings = [], []
    editions = values.get("iap_items") or []
    if editions:
        catalog_ops, catalog_warnings = catalog_plan.build_operations(
            editions, source)

    # Editions onto the "Game editions" cards.
    pack_ops = []
    pack_blocks = set()
    if editions:
        slots = packs_plan.all_slots(blocks.get("packs") or [])
        if not slots:
            unresolved.append({
                "field": "iap_items",
                "module": "packs",
                "reason": "no packs block with a card to show the editions on",
                "note": "They still become catalog items.",
            })
        else:
            pack_ops, unplaced, pack_blocks = packs_plan.plan_writes(
                slots, editions, skus=[op["sku"] for op in catalog_ops])
            if unplaced:
                unresolved.append({
                    "field": "iap_items",
                    "module": "packs",
                    "reason": "%d card(s) across the packs blocks, %d edition(s) "
                              "extracted, so %d cannot be shown"
                              % (len(slots), len(editions), len(unplaced)),
                    "note": "Unshown editions still become catalog items: %s"
                            % ", ".join(e.get("name", "?") for e in unplaced),
                })

    # System requirements onto the requirements block.
    requirement_ops = []
    requirement_blocks = set()
    platforms = values.get("requirements") or []
    if platforms:
        placements = blocks.get("requirements") or []
        if not placements:
            unresolved.append({
                "field": "requirements",
                "module": "requirements",
                "reason": "no requirements block on this landing",
                "note": "The listing publishes them; the page has nowhere to "
                        "show them.",
            })
        else:
            page_id, block_id, block_doc_req = placements[0]
            requirement_ops, unplaced_req = packs_plan.requirement_writes(
                block_doc_req, block_id, page_id, platforms)
            if requirement_ops:
                requirement_blocks.add(block_id)
            if unplaced_req:
                unresolved.append({
                    "field": "requirements",
                    "module": "requirements",
                    "reason": "%d requirement row(s) had no row on the block"
                              % len(unplaced_req),
                    "note": "Unplaced: %s" % ", ".join(unplaced_req[:6]),
                })

    # A block nothing was written to has nothing from this listing to show.
    written_blocks = {op["block_id"] for op in
                      (localization_ops + overflow_ops + asset_ops + pack_ops
                       + requirement_ops)
                      if op.get("block_id")} | set(pack_blocks) \
        | set(requirement_blocks)
    # A previous run may have hidden a block this one fills.
    unhide_ops = packs_plan.unhide_operations(structure, written_blocks)
    prune_ops = packs_plan.prune_operations(structure, written_blocks)

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
        # Deletes last: a block is only removed once everything that had
        # something to write has written it.
        # Unhide first: a block hidden by an earlier run must be visible
        # before anything written into it counts for anything. Deletes last.
        "operations": (unhide_ops + localization_ops + overflow_ops + pack_ops
                       + requirement_ops + asset_ops + prune_ops),
        "catalog_operations": catalog_ops,
        "catalog_warnings": catalog_warnings,
        "manual_follow_up": manual,
        "unresolved": unresolved,
        "unverified": unverified,
        "counts": {
            "localization": len(localization_ops) + len(requirement_ops),
            "overflow": len(overflow_ops),
            "editions_on_page": len([o for o in pack_ops
                                     if o["field"].startswith("edition.")
                                     and o["kind"] != "patch"]),
            "requirements": len(requirement_ops),
            "unhidden": len(unhide_ops),
            "pruned_unsupported": len(prune_ops),
            "asset": len([o for o in asset_ops if o["kind"] == "asset"]),
            "patch": len([o for o in (asset_ops + pack_ops + unhide_ops)
                          if o["kind"] == "patch"]),
            "delete": len(prune_ops),
            "catalog": len(catalog_ops),
            "manual": len(manual),
            "unresolved": len(unresolved),
        },
    }
    for step, op in enumerate(plan["operations"], start=1):
        op["step"] = step
    return plan, blockers

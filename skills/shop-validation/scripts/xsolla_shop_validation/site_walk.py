"""The whole-site walk -- ``validate-shop``.

This is a composition, not a port.  Site Builder's own tooling validates one
block payload before one write; it has no whole-site validator.  The per-block
rules underneath are real checks carried across faithfully; the enumeration and
aggregation around them is this script's own construction.

Two enumeration passes, and neither is optional.  ``pages[].blocks[]`` holds
full block documents; the site-level ``blocks[]`` holds *ids only*, and every id
there that no page carries is an off-page block that has to be fetched
separately.  On one live landing that second pass was the difference between
seeing 5 blocks and seeing all 14.

Field-level module schemas are deliberately NOT applied here.  They are a
create-payload contract: checking a stored block against its own schema failed
on all 36 live blocks tested, every failure a false alarm.
"""

from __future__ import annotations

from .component_checks import (
    ValidationContext,
    scan_localized_reference_ids,
    validate_actions_anywhere,
    validate_block_components,
    validate_footer_v2,
    validate_gallery_v2,
)
from .errors import MISSING
from .federated import (
    is_custom_block_id,
    resolve_federated_localized_id,
)
from .module_checks import (
    check_lead_v2,
    check_sidebar,
    is_daily_reward,
    is_offer_chain,
    validate_daily_reward,
    validate_lead_game_sales,
    validate_new_store_block,
    validate_offer_chain,
    validate_rewards_block,
    validate_subscriptions_block,
)
from .federated import validate_federated
from .native import (
    FEDERATED_MODULE,
    LAYOUT_MODULES,
    NATIVE_MODULES,
    REMOTE_BLOCK_IDS,
    validate_envelope,
)

def _tag(errors, category):
    """Stamp a category on errors so a report can separate the kinds.

    Conflating them is what gets a gate switched off: a malformed payload will
    be rejected, while an unconfigured template placeholder is the state every
    fresh landing starts in.  Both are worth reporting; they are not the same
    news.
    """
    for f in errors:
        f.setdefault("category", category)
    return errors


CATEGORY_SHAPE = "shape"
CATEGORY_CONTENT = "content"
CATEGORY_REFERENCE = "reference"
CATEGORY_SITE = "site"

# The module-specific visitors the editor's block walker registers. Keyed by
# module so routing is a lookup rather than a chain of ifs -- and so a reader
# can see the whole set at once.
MODULE_VISITORS = {
    "subscriptions-packs": validate_subscriptions_block,
    "rewards": validate_rewards_block,
    "leadGameSales": validate_lead_game_sales,
    "newStore": validate_new_store_block,
    "lead": check_lead_v2,
    "sidebar": check_sidebar,
}

FAMILY_NATIVE = "native"
FAMILY_FEDERATED = "federated"
FAMILY_CUSTOM = "custom"
FAMILY_LAYOUT = "layout"
FAMILY_UNKNOWN = "unknown"


def route_block(block):
    """Classify by ``module``, then split federated on the ``ai_`` prefix.

    A federated block's ``module`` is the literal string ``federated`` -- not
    the remote block's name -- and a custom block is stored as ``federated``
    too.  Route on ``values.blockId`` and every federated block falls through to
    the native rules and fails on every field; treat the four remote ids as a
    closed set and every custom block on the site becomes a finding.
    """
    if not isinstance(block, dict):
        return FAMILY_UNKNOWN
    module = block.get("module")
    if module in LAYOUT_MODULES:
        return FAMILY_LAYOUT
    if module == FEDERATED_MODULE:
        values = block.get("values") or {}
        block_id = values.get("blockId") if isinstance(values, dict) else None
        if is_custom_block_id(block_id):
            return FAMILY_CUSTOM
        return FAMILY_FEDERATED
    if module in NATIVE_MODULES:
        return FAMILY_NATIVE
    return FAMILY_UNKNOWN


def enumerate_blocks(structure, off_page_blocks=None):
    """Both passes.  Returns ``(records, dangling_ids)``.

    A record is ``{id, module, blockVersion, parent, page_id, block, source}``
    where ``source`` is ``page`` or ``off-page``.  Ids in the site-level list
    that neither a page carries nor ``off_page_blocks`` supplies come back as
    dangling: the site document references blocks that no longer exist, and
    nothing else in the walk sees that.
    """
    off_page_blocks = off_page_blocks or {}
    records = []
    seen = set()

    for page in structure.get("pages") or []:
        if not isinstance(page, dict):
            continue
        page_id = page.get("_id")
        for block in page.get("blocks") or []:
            if not isinstance(block, dict):
                continue
            block_id = block.get("_id")
            seen.add(block_id)
            records.append(_record(block, page_id, "page"))

    dangling = []
    # ``layouts[]`` repeats ids that ``blocks[]`` already lists, so dedupe while
    # keeping document order: an id listed twice is one block, not two, and
    # reporting it twice would double-count a dangling reference.
    site_ids = []
    for source in ("blocks", "layouts"):
        for block_id in structure.get(source) or []:
            if isinstance(block_id, str) and block_id not in site_ids:
                site_ids.append(block_id)
    for block_id in site_ids:
        if block_id in seen:
            continue
        block = off_page_blocks.get(block_id)
        if block is None:
            dangling.append(block_id)
            continue
        seen.add(block_id)
        records.append(_record(block, None, "off-page"))

    return records, dangling


def _record(block, page_id, source):
    return {
        "id": block.get("_id"),
        "module": block.get("module"),
        "blockVersion": block.get("blockVersion", None),
        "parent": block.get("parent"),
        "page_id": page_id,
        "source": source,
        "block": block,
    }


def _localization_ids(localization):
    """Every ``L:`` id the landing's store actually defines.

    Both namespaces count: ``common`` and ``pages.<pageId>.texts``.
    """
    ids = set()
    if not isinstance(localization, dict):
        return ids
    common = localization.get("common")
    if isinstance(common, dict):
        ids.update(k for k in common if isinstance(k, str))
    pages = localization.get("pages")
    if isinstance(pages, dict):
        for page in pages.values():
            texts = page.get("texts") if isinstance(page, dict) else None
            if isinstance(texts, dict):
                ids.update(k for k in texts if isinstance(k, str))
    return ids


def check_block(record, context=None, unverified=None):
    """Per-block checks for a *stored* block, in the order the checklist sets.

    Stops at the first level that fails, so one bad payload does not cascade.
    """
    context = context or ValidationContext()
    unverified = unverified if unverified is not None else []
    block = record["block"]
    family = route_block(block)
    errors = []

    if family in (FAMILY_NATIVE, FAMILY_LAYOUT, FAMILY_UNKNOWN):
        errors.extend(_tag(validate_envelope(block), CATEGORY_SHAPE))
        if errors:
            return family, errors
        if isinstance(block.get("components"), list):
            errors.extend(
                _tag(
                    validate_block_components(block["components"], context=context, unverified=unverified),
                    CATEGORY_CONTENT,
                )
            )
        errors.extend(_tag(validate_actions_anywhere(block, [], context, unverified), CATEGORY_CONTENT))
        # Gated on the module, not on blockVersion 2: an enabled social item
        # with an empty url renders a dead icon at every footer version, and the
        # editor's own check happens to be written against v2 only.
        if block.get("module") in ("footer", "common-layout"):
            errors.extend(_tag(validate_footer_v2(block), CATEGORY_CONTENT))
        if block.get("module") == "gallery" and block.get("blockVersion") == 2:
            errors.extend(_tag(validate_gallery_v2(block), CATEGORY_CONTENT))
        module_check = MODULE_VISITORS.get(block.get("module"))
        if module_check is not None:
            errors.extend(_tag(module_check(block), CATEGORY_CONTENT))
        if family == FAMILY_UNKNOWN and block.get("module"):
            unverified.append(
                "block %s: module %r -- no schema available, structure not checked"
                % (record["id"], block.get("module"))
            )
        return family, errors

    values = block.get("values") or {}
    internal = values.get("internalBlockValues", MISSING) if isinstance(values, dict) else MISSING
    defaults = values.get("defaultData", MISSING) if isinstance(values, dict) else MISSING
    result = validate_federated(internal, defaults)
    errors.extend(_tag(result["errors"], CATEGORY_SHAPE))
    if not result["walked"]:
        unverified.append(
            "block %s: federated walk skipped -- %s"
            % (
                record["id"],
                "no internalBlockValues" if internal is MISSING or internal is None else "no defaultData",
            )
        )

    if family == FAMILY_FEDERATED:
        if is_daily_reward(block):
            errors.extend(_tag(validate_daily_reward(block), CATEGORY_CONTENT))
        elif is_offer_chain(block):
            errors.extend(_tag(validate_offer_chain(block), CATEGORY_CONTENT))

        block_id = values.get("blockId") if isinstance(values, dict) else None
        if block_id not in REMOTE_BLOCK_IDS:
            unverified.append(
                "block %s: values.blockId %r is not one of the four known remote blocks -- "
                "unrecognised, not necessarily wrong" % (record["id"], block_id)
            )

    return family, errors


def check_localized_ids(records, localization, unverified=None):
    """The highest-value site-level check, and the easiest to get wrong.

    A native block's ``<field>.id`` uuid must be in the landing's localization
    store.  A federated block's short ids must **not** be looked up there: they
    resolve through the block's own ``values.resources.localizedValues`` first.
    Applying the native route to federated blocks produced 43 false errors on
    one known-good site.
    """
    unverified = unverified if unverified is not None else []
    store_ids = _localization_ids(localization)
    errors = []
    checked = 0

    for record in records:
        block = record["block"]
        family = route_block(block)
        if family in (FAMILY_FEDERATED, FAMILY_CUSTOM):
            values = block.get("values") or {}
            resources = values.get("resources") if isinstance(values, dict) else None
            # Only the block's own data carries short ids.  Scanning
            # ``values.resources`` too would pick up the resolved uuids it maps
            # to and then try to resolve those as short ids -- a false finding
            # per localized field on every federated block.
            scanned = [
                values.get("defaultData"),
                values.get("internalBlockValues"),
            ] if isinstance(values, dict) else []
            short_ids = set()
            for subtree in scanned:
                short_ids.update(scan_localized_reference_ids(subtree))
            for short_id in sorted(short_ids):
                resolved = resolve_federated_localized_id(short_id, resources)
                checked += 1
                if resolved is None:
                    errors.append(
                        {
                            "category": CATEGORY_REFERENCE,
                            "block_id": record["id"],
                            "path": "values.resources.localizedValues.%s" % short_id,
                            "expected": "an entry mapping the block-local id to an L: uuid",
                            "got": "missing",
                            "value": short_id,
                        }
                    )
                elif store_ids and resolved not in store_ids:
                    errors.append(
                        {
                            "category": CATEGORY_REFERENCE,
                            "block_id": record["id"],
                            "path": "localization.%s" % resolved,
                            "expected": "an entry in the landing's localization store",
                            "got": "missing",
                            "value": resolved,
                        }
                    )
            continue

        for reference in set(scan_localized_reference_ids(block)):
            checked += 1
            if store_ids and reference not in store_ids:
                errors.append(
                    {
                        "category": CATEGORY_REFERENCE,
                        "block_id": record["id"],
                        "path": "localization.%s" % reference,
                        "expected": "an entry in the landing's localization store",
                        "got": "missing",
                        "value": reference,
                    }
                )

    if not store_ids:
        unverified.append("localization store not supplied -- L: ids collected but not resolved")

    return errors, checked


def check_duplicate_layouts(records, unverified=None):
    """A second ``header`` or ``common-layout`` is the fingerprint of a create
    that should have been a patch.  A fresh landing has neither, which is not a
    finding -- it means no page has been added yet.
    """
    errors = []
    per_page = {}
    for record in records:
        if record["module"] not in ("header", "common-layout"):
            continue
        key = (record["module"], record["page_id"])
        per_page.setdefault(key, []).append(record["id"])
    for (module, page_id), ids in sorted(per_page.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        if len(ids) > 1:
            errors.append(
                {
                    "category": CATEGORY_SITE,
                    "block_id": ids[1],
                    "path": "module",
                    "expected": "exactly one %s%s" % (module, " per page" if page_id else ""),
                    "got": "%d" % len(ids),
                    "value": ids,
                }
            )
    return errors


def check_store_wiring(records, unverified=None):
    """A store block with an empty catalog reference is a valid payload and an
    empty shop, so it cannot be judged from the block alone.
    """
    unverified = unverified if unverified is not None else []
    store_modules = ("newStore", "packs", "subscriptions-packs")
    for record in records:
        if record["module"] in store_modules:
            unverified.append(
                "block %s (%s): confirm it points at a catalog with items in it -- not checkable "
                "from the site structure" % (record["id"], record["module"])
            )
    return []


def check_page_reachability(structure, unverified=None):
    """A page with no navigation entry pointing at it is published-but-invisible."""
    unverified = unverified if unverified is not None else []
    pages = [p for p in (structure.get("pages") or []) if isinstance(p, dict)]
    if len(pages) <= 1:
        return []
    navigation = str(structure.get("navigation") or structure.get("menu") or "")
    errors = []
    for page in pages:
        page_id = page.get("_id")
        path = page.get("path") or page.get("url")
        if not navigation:
            unverified.append(
                "page %s (%s): navigation not present in the structure -- reachability not checked"
                % (page_id, path)
            )
            continue
        if page_id and page_id not in navigation and (not path or str(path) not in navigation):
            errors.append(
                {
                    "category": CATEGORY_SITE,
                    "block_id": None,
                    "path": "pages.%s" % page_id,
                    "expected": "a navigation entry pointing at the page",
                    "got": "none",
                    "value": path,
                }
            )
    return errors


def walk_site(structure, localization=None, off_page_blocks=None, context=None, assets=None):
    """Run the whole gate and return one report.

    The report says what it did not check, on purpose: a gate that hides its own
    blind spots is worse than no gate.
    """
    context = context or ValidationContext(site=structure)
    unverified = []
    errors = []

    records, dangling = enumerate_blocks(structure, off_page_blocks)

    families = {}
    for record in records:
        family, block_errors = check_block(record, context, unverified)
        record["family"] = family
        families[family] = families.get(family, 0) + 1
        for f in block_errors:
            entry = dict(f)
            entry["block_id"] = record["id"]
            entry["module"] = record["module"]
            entry["family"] = family
            errors.append(entry)

    for block_id in dangling:
        errors.append(
            {
                "category": CATEGORY_SITE,
                "block_id": block_id,
                "module": None,
                "family": None,
                "path": "blocks",
                "expected": "an id that resolves to a block",
                "got": "block_not_found",
                "value": block_id,
            }
        )

    localized_errors, ids_checked = check_localized_ids(records, localization, unverified)
    errors.extend(localized_errors)
    errors.extend(check_duplicate_layouts(records, unverified))
    check_store_wiring(records, unverified)
    errors.extend(check_page_reachability(structure, unverified))

    image_ids = set()
    for record in records:
        for value in _scan_image_ids(record["block"]):
            image_ids.add(value)
    if image_ids:
        unverified.append(
            "%d I: image id(s) collected but not verified -- the landing asset list covers "
            "uploads only, and federated blocks' images ship with the remote block, so a "
            "missing entry is not evidence of a broken image" % len(image_ids)
        )

    return {
        "scope": {
            "site": structure.get("domain") or structure.get("name") or structure.get("_id"),
            "landing_id": structure.get("_id"),
            "pages": len([p for p in (structure.get("pages") or []) if isinstance(p, dict)]),
            "blocks": len(records),
            "families": families,
            "off_page_blocks": len([r for r in records if r["source"] == "off-page"]),
            "dangling_ids": len(dangling),
            "localized_ids_checked": ids_checked,
            "image_ids_collected": len(image_ids),
            "errors_by_category": _counts(errors),
        },
        "errors": errors,
        "unverified": unverified,
        "ok": not errors,
        "verdict": "clean"
        if not errors
        else "%d error(s) across %d block(s)"
        % (len(errors), len({f.get("block_id") for f in errors})),
    }


def _counts(errors):
    out = {}
    for f in errors:
        key = f.get("category") or "uncategorised"
        out[key] = out.get(key, 0) + 1
    return out


def _scan_image_ids(node):
    out = []
    if isinstance(node, str):
        if node.startswith("I:"):
            out.append(node)
    elif isinstance(node, list):
        for item in node:
            out.extend(_scan_image_ids(item))
    elif isinstance(node, dict):
        for item in node.values():
            out.extend(_scan_image_ids(item))
    return out

"""Editions onto the "Game editions" cards, and the cards nobody filled.

Two problems this module exists for, both found by looking at a shop in the
editor rather than at a coverage number:

**The editions were going to the catalog and nowhere else.**  A Steam listing's
editions became priced catalog items -- correct, a landing holds no prices --
but the page's three "Game editions" cards kept showing
``Edition name / Provide your players with detailed…``.  A reader of the shop
saw placeholder text where the whole point was that they would not have to
type it.

**Every block the import did not touch kept its template content.**  Nine of
thirteen blocks, in every shop: three ``packs``, two or three ``bento-grid``,
``requirements``, ``faq``, ``footer``.  Field coverage read 90% and the page
looked a third finished, because coverage counts the target field list and not
whether the page has placeholder copy left on it.

A pack card is not a flat object.  Its text lives in ``content`` rows, each
with its own ``L:`` reference:

    values.packs[i].image.img                       the card's artwork
    values.packs[i].content[j] type=label           a ribbon
    values.packs[i].content[j] type=title           the edition name
    values.packs[i].content[j] type=description     the edition's own copy
    values.packs[i].content[j] type=advantages      a bullet list
    values.packs[i].content[j] type=button          the buy action

What this module misses:

* **It does not verify the SKU exists.**  The button's ``action.sku`` is set to
  the SKU the edition will become, and the catalog create is ordered first, but
  nothing here reads the catalog back to confirm it landed.  A button pointing
  at a SKU that failed to create renders without a price.
* **It disables ``advantages`` rather than filling it.**  No storefront
  publishes a per-edition bullet list, and five placeholder bullets read worse
  than none.
* **It hides, it does not delete.**  ``delete-block`` is deliberately absent
  from the runner's allowlist, and ``hidden: true`` has the same visible result
  while staying reversible from the editor.
"""

from __future__ import annotations

# Content rows this module writes, and the field each takes its text from.
TITLE_ROW = "title"
DESCRIPTION_ROW = "description"
# Rows with no source data.  Left enabled they render template copy.
EMPTY_ROWS = ("label", "advantages")
BUTTON_ROW = "button"


def _rows(card):
    content = card.get("content")
    return content if isinstance(content, list) else []


def _row_ref(card, row_type):
    """``(index, L: id)`` for one content row, or ``None`` if it has no ref."""
    for index, row in enumerate(_rows(card)):
        if not isinstance(row, dict) or row.get("type") != row_type:
            continue
        text = row.get("text")
        if isinstance(text, dict) and str(text.get("id", "")).startswith("L:"):
            return index, text["id"]
        return None
    return None


def _button_row(card):
    """The index of the card's button row, or ``None``."""
    for index, row in enumerate(_rows(card)):
        if isinstance(row, dict) and row.get("type") == BUTTON_ROW:
            return index
    return None


def cards(block):
    """The pack cards on a ``packs`` block, in render order."""
    found = ((block or {}).get("values") or {}).get("packs")
    return found if isinstance(found, list) else []


def all_slots(placements):
    """Every pack card across every ``packs`` block, in page order.

    An earlier version used only the widest block, on the grounds that a
    one-card row beside a three-card row reads oddly.  That hid editions the
    listing genuinely publishes -- Steam's five became three -- and a missing
    edition is worse than an uneven row.  A landing's three blocks hold one,
    three and one card: exactly five slots.

    Returns ``(page_id, block_id, block, card_index)`` tuples.
    """
    slots = []
    for page_id, block_id, block in placements or []:
        for index in range(len(cards(block))):
            slots.append((page_id, block_id, block, index))
    return slots


def plan_writes(slots, editions, skus=None):
    """Operations to put ``editions`` on the available pack cards.

    ``slots`` comes from ``all_slots``; ``skus`` is the catalog SKU each edition
    became, positionally, so a card's buy button can point at it.

    Returns ``(operations, unplaced, used_blocks)``.  ``unplaced`` names
    editions that had no card at all -- silently dropping one is how a shop
    ends up wrong in a way nobody notices.
    """
    operations = []
    used_blocks = set()
    placed = editions[:len(slots)]
    unplaced = editions[len(slots):]
    skus = skus or []

    for position, edition in enumerate(placed):
        page_id, block_id, block, index = slots[position]
        card = cards(block)[index]
        used_blocks.add(block_id)
        base = ["values", "packs", index]

        title = _row_ref(card, TITLE_ROW)
        if title:
            row, ref = title
            operations.append({
                "kind": "localization", "field": "edition.title",
                "module": "packs", "block_id": block_id, "page_id": page_id,
                "path": base + ["content", row, "text"],
                "localized_id": ref, "value": edition["name"], "dropped": [],
                "confidence": "schema",
                "note": "The edition name, on card %d." % index,
            })

        # A cleaned description is preferred when the agent supplied one: a
        # storefront's own copy is written to sell on that storefront, and it
        # arrives with marketing furniture, platform references and length that
        # a card cannot hold. See SKILL.md -- the cleaning is the agent's, not
        # this module's, because it is a judgement rather than a transform.
        copy = (edition.get("description_clean")
                or edition.get("description")
                or _price_line(edition))
        description = _row_ref(card, DESCRIPTION_ROW)
        if description and copy:
            row, ref = description
            operations.append({
                "kind": "localization", "field": "edition.description",
                "module": "packs", "block_id": block_id, "page_id": page_id,
                "path": base + ["content", row, "text"],
                "localized_id": ref, "value": copy, "dropped": [],
                "confidence": "schema",
                "note": "The edition's own copy, or its price when it has none.",
            })

        if edition.get("image"):
            operations.append({
                "kind": "asset", "field": "edition.image",
                "module": "packs", "block_id": block_id, "page_id": page_id,
                "path": base + ["image", "img"],
                "source_url": edition["image"], "confidence": "schema",
                "note": "The edition's own artwork, not the game's.",
            })

        # The buy button carries an empty sku out of the template. Pointed at
        # the catalog item this edition became, Shop Builder renders that item's
        # price on the button -- which is where a price belongs, since a landing
        # holds none of its own.
        sku = skus[position] if position < len(skus) else None
        button = _button_row(card)
        if button is not None and sku:
            row = button
            operations.append({
                "kind": "patch", "field": "edition.button",
                "module": "packs", "block_id": block_id, "page_id": page_id,
                "path": base + ["content", row, "button", "action", "sku"],
                "value": sku, "confidence": "schema",
                "note": "The buy action's sku. The price on the button comes "
                        "from the catalog item, so this must be created first.",
            })

        for row_type in EMPTY_ROWS:
            for row, existing in enumerate(_rows(card)):
                if isinstance(existing, dict) and existing.get("type") == row_type:
                    operations.append({
                        "kind": "patch", "field": "edition.%s" % row_type,
                        "module": "packs", "block_id": block_id,
                        "page_id": page_id,
                        "path": base + ["content", row, "enable"],
                        "value": False, "confidence": "schema",
                        "note": "No source data for this row; left enabled it "
                                "renders template copy.",
                    })

    # Cards beyond the editions keep their placeholders, so they go too.
    for page_id, block_id, _block, index in slots[len(placed):]:
        operations.append({
            "kind": "patch", "field": "edition.unused",
            "module": "packs", "block_id": block_id, "page_id": page_id,
            "path": ["values", "packs", index, "hidden"],
            "value": True, "confidence": "schema",
            "note": "Card %d has no edition; hidden so it does not show "
                    "placeholder copy." % index,
        })

    return operations, unplaced, used_blocks


def _price_line(edition):
    price = edition.get("price") or {}
    if price.get("amount") is None or not price.get("currency"):
        return None
    return "%.2f %s" % (price["amount"], price["currency"])


def unhide_operations(structure, keep_block_ids):
    """Make every block that receives content visible.

    The planner cannot assume a block starts visible.  An earlier run of this
    skill hid blocks it could not fill; a later run then wrote editions into two
    of those same ``packs`` blocks and never cleared the flag, so the Lara Croft
    and Summer Esports cards were written correctly into blocks nobody could
    see.  Found by looking at the shop, not at the run's output, which reported
    both writes as applied -- and they were.
    """
    operations = []
    for page in (structure or {}).get("pages") or []:
        for block in page.get("blocks") or []:
            if not isinstance(block, dict):
                continue
            if block.get("_id") not in keep_block_ids:
                continue
            if block.get("hidden") is not True:
                continue
            operations.append({
                "kind": "patch",
                "field": "visible.%s" % block.get("module"),
                "module": block.get("module"),
                "block_id": block["_id"],
                "page_id": page.get("_id"),
                "path": ["hidden"],
                "value": False,
                "confidence": "confirmed",
                "note": "A previous run hid this block; it has content now, so "
                        "the flag has to be cleared or the content is invisible.",
            })
    return operations


def prune_operations(structure, keep_block_ids):
    """Delete every block the listing does not support.

    Content-first, arrived at the long way.  The first version hid unfilled
    blocks, which left a Play shop carrying three invisible "Game editions"
    sections.  The obvious alternative -- tear the template down and add back
    only what the listing supports -- turned out to be worse, and the reason is
    worth recording because it is not guessable:

    A freshly added block does not arrive the way the template's does.
    Verified on a throwaway landing, 2026-09-17:

    ======================  ====================================
    ``add-block gallery``   3 slides, real ``L:`` refs -- usable
    ``add-block packs``     **0 cards** -- nothing to put an edition on
    ``add-block description``  **componentsIds: []** -- no text component
    ``add-block faq``       1 component
    ======================  ====================================

    So rebuilding would break exactly the two blocks that carry the most
    content.  The template's ``packs`` blocks are the only source of usable
    cards, and the template's ``description`` is the only one with somewhere to
    put the description.

    Pruning gets the same result the rebuild was for -- a block the listing
    cannot fill is *absent*, not hidden -- without losing the structure that
    only the template provides.

    Layout blocks are never pruned: deleting a ``header`` or ``footer`` removes
    navigation rather than placeholder copy.

    What this misses: it prunes by "was anything written to it", so a block that
    a *future* field would fill is deleted today and has to be re-added by hand.
    And a delete is not reversible from here -- the pre-write backup is the only
    way back, which is why ``apply.py`` takes one before the first write.
    """
    never_prune = {"header", "footer", "common-layout", "side-by-side-layout"}
    operations = []
    for page in (structure or {}).get("pages") or []:
        for block in page.get("blocks") or []:
            if not isinstance(block, dict):
                continue
            module = block.get("module")
            if not module or module in never_prune:
                continue
            if block.get("_id") in keep_block_ids:
                continue
            operations.append({
                "kind": "delete",
                "field": "unsupported.%s" % module,
                "module": module,
                "block_id": block["_id"],
                "page_id": page.get("_id"),
                "path": None,
                "confidence": "confirmed",
                "note": "The listing publishes nothing this block can show, so "
                        "it is removed rather than left holding the template's "
                        "copy. Recoverable only from the pre-write backup.",
            })
    return operations


def requirement_writes(block, block_id, page_id, platforms):
    """Write extracted system requirements onto a ``requirements`` block.

    The block's shape, read off a live landing rather than guessed: each
    platform is a ``platform_req_v2`` component, and each of its
    ``requirementList`` rows carries a ``name`` and a ``minimum``, both as their
    own ``L:`` references.  So a requirement is two localization writes, not a
    patch.

    Returns ``(operations, unplaced)``.  ``unplaced`` names requirement rows
    with no row to write to -- the component ships a fixed number, the same way
    a gallery ships a fixed number of slides.
    """
    operations = []
    unplaced = []
    components = block.get("components") or (block.get("values") or {}).get(
        "components") or []
    items = components if isinstance(components, list) else list(
        components.values())
    usable = [(index, c) for index, c in enumerate(items)
              if isinstance(c, dict) and c.get("type") == "platform_req_v2"]

    for position, platform in enumerate(platforms or []):
        if position >= len(usable):
            unplaced.append(platform.get("platform", "?"))
            continue
        comp_index, component = usable[position]
        rows = ((component.get("value") or {}).get("requirementList")) or []
        for row_index, requirement in enumerate(platform.get("rows") or []):
            if row_index >= len(rows):
                unplaced.append("%s/%s" % (platform.get("platform"),
                                           requirement.get("name")))
                continue
            row = rows[row_index]
            for key, text in (("name", requirement.get("name")),
                              ("minimum", requirement.get("value"))):
                ref = row.get(key)
                target = ref.get("id") if isinstance(ref, dict) else None
                if not (isinstance(target, str) and target.startswith("L:")):
                    continue
                operations.append({
                    "kind": "localization",
                    "field": "requirement.%s" % key,
                    "module": "requirements",
                    "block_id": block_id,
                    "page_id": page_id,
                    "path": ["components", comp_index, "value",
                             "requirementList", row_index, key],
                    "localized_id": target,
                    "value": text,
                    "dropped": [],
                    "confidence": "schema",
                    "note": "%s, %s row %d." % (platform.get("platform"),
                                                key, row_index),
                })
    return operations, unplaced


def bento_leaves(block):
    """The ``bento-grid`` leaf nodes that can hold content, in a stable order.

    A bento grid is two maps: ``values.grid`` of nodes, and
    ``values.gridComponents`` of the text components those nodes reference by
    ``contentIds``.  Only ``leaf`` nodes carry content -- ``group`` nodes are
    layout and have no ``contentIds`` -- so a card is a leaf.

    Sorted by key rather than left in dict order, because the order a JSON
    object comes back in is not a promise and a review landing on a different
    card between runs would look like a bug.

    Returns ``[(node_id, [component_id, ...])]``.
    """
    values = (block or {}).get("values") or {}
    grid = values.get("grid") or {}
    components = values.get("gridComponents") or {}
    leaves = []
    for node_id in sorted(grid):
        node = grid[node_id]
        if not isinstance(node, dict) or node.get("type") != "leaf":
            continue
        ids = [c for c in (node.get("contentIds") or [])
               if (components.get(c) or {}).get("type") == "text"]
        if ids:
            leaves.append((node_id, ids))
    return leaves


def review_writes(block, block_id, page_id, quotes):
    """Write chosen player reviews onto a ``bento-grid``'s cards.

    Each leaf gets one review.  A leaf with two text components takes the quote
    in the first and the attribution in the second; a leaf with one takes both
    in that one, because a quote with nobody behind it is worth less than an
    uneven card.

    Returns ``(operations, unplaced)``.
    """
    operations = []
    values = (block or {}).get("values") or {}
    components = values.get("gridComponents") or {}
    leaves = bento_leaves(block)
    placed = quotes[:len(leaves)]
    unplaced = quotes[len(leaves):]

    for position, quote in enumerate(placed):
        _node_id, component_ids = leaves[position]
        text = quote.get("quote") or ""
        who = quote.get("attribution") or ""
        parts = [text, who] if len(component_ids) > 1 else \
            ["%s — %s" % (text, who) if who else text]
        for offset, body in enumerate(parts):
            if offset >= len(component_ids):
                break
            component = components.get(component_ids[offset]) or {}
            ref = component.get("text")
            target = ref.get("id") if isinstance(ref, dict) else None
            if not (isinstance(target, str) and target.startswith("L:")):
                continue
            operations.append({
                "kind": "localization",
                "field": "review.quote" if offset == 0 else "review.attribution",
                "module": "bento-grid",
                "block_id": block_id,
                "page_id": page_id,
                "path": ["values", "gridComponents", component_ids[offset],
                         "text"],
                "localized_id": target,
                "value": body,
                "dropped": [],
                "confidence": "schema",
                "note": "Player review %d, on a bento-grid card." % (position + 1),
            })
    return operations, unplaced

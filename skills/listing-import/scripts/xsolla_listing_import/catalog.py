"""In-app items, turned into catalog entities.

A landing holds no prices, so extracted in-app items are catalog work.  Two
decisions are baked in here and both are worth arguing with before they are
changed:

*Everything becomes a virtual item priced in real money.*  Not a currency
package, not a bundle.  Those two require a ``content`` array of
``{sku, quantity}``, and **no storefront publishes the quantity**: the App
Store says "Pocketful of Gems", never "1200 gems".  A virtual item is the only
catalog entity whose whole body can be filled from a public listing -- sku,
name, description, prices, group, image.  Creating a currency package with a
guessed quantity would be worse than not creating one, because it looks
finished.

*Everything lands in one group, flagged for review.*  A partner has to
reclassify these by hand; grouping them makes that one pass rather than a hunt.

What this module misses: it emits commands, it does not run them.  It does not
check whether a SKU already exists, so a re-run produces the same SKUs and the
create calls will conflict -- by design, since silently updating a live priced
item is worse than a visible error.  It also cannot tell a subscription from a
consumable: "Gold Pass" is a season pass and belongs in the subscriptions
product, not here, and nothing in a listing marks it as one.
"""

from __future__ import annotations

import re

DEFAULT_GROUP = "imported_listing"

SOURCE_PREFIX = {
    "steam": "steam",
    "google_play": "gp",
    "app_store": "ios",
}

_NON_SKU = re.compile(r"[^a-z0-9]+")
SKU_MAX = 48


def slugify(name):
    """A catalog-safe SKU fragment: lowercase, alphanumeric, underscores."""
    slug = _NON_SKU.sub("_", (name or "").lower()).strip("_")
    return slug[:SKU_MAX].rstrip("_")


def _price_fragment(price):
    """A short, SKU-safe rendering of a price, for breaking name collisions."""
    amount = price.get("amount")
    if amount is None:
        return None
    text = ("%.2f" % float(amount)).replace(".", "_")
    return "%s_%s" % (text, str(price.get("currency", "")).lower())


def build_skus(items, source):
    """Assign a unique SKU to each item.

    Names collide in real data -- the App Store listing for Clash of Clans has
    ``Gold Pass`` twice, at $4.99 and $6.99.  A collision is broken by the
    price first, since that is what actually distinguishes them, and only then
    by an index, so a stable input gives a stable SKU.
    """
    prefix = SOURCE_PREFIX.get(source, "ext")
    taken = {}
    out = []
    for index, item in enumerate(items):
        base = "%s_%s" % (prefix, slugify(item.get("name")) or "item")
        candidate = base
        if candidate in taken:
            fragment = _price_fragment(item.get("price") or {})
            candidate = "%s_%s" % (base, fragment) if fragment else base
        while candidate in taken:
            candidate = "%s_%d" % (base, index)
            index += 1
        taken[candidate] = True
        out.append(candidate)
    return out


def build_operations(items, source, group=DEFAULT_GROUP, locale="en"):
    """One create-item operation per in-app item.

    Returns ``(operations, warnings)``.  Warnings name what a human has to
    settle: an item with no price, and the fact that a quantity was never
    available to begin with.
    """
    operations = []
    warnings = []
    skus = build_skus(items, source)

    priced = 0
    for item, sku in zip(items, skus):
        price = item.get("price") or {}
        amount = price.get("amount")
        currency = price.get("currency")
        prices = []
        if amount is not None and currency:
            priced += 1
            prices = [{
                "amount": amount,
                "currency": currency,
                "is_default": True,
                "is_enabled": True,
            }]
        else:
            warnings.append(
                "%s has no price in the listing; created disabled until one is set"
                % (item.get("name") or sku)
            )
        operations.append({
            "kind": "catalog",
            "entity": "virtual_item",
            "sku": sku,
            "name": {locale: item.get("name")},
            "description": {locale: "Imported from the %s listing. Review before "
                                    "selling." % source.replace("_", " ")},
            "prices": prices,
            "groups": [group],
            "is_enabled": bool(prices),
            "is_show_in_store": bool(prices),
            "needs_review": True,
            "review_reason": "type guessed as a virtual item; the listing does not "
                             "publish what the item contains",
        })

    if operations:
        warnings.append(
            "%d item(s) created as virtual items. None is a currency package or a "
            "bundle: those need a content array, and no storefront publishes the "
            "quantity behind an item name." % len(operations)
        )
    if operations and priced < len(operations):
        warnings.append(
            "%d of %d items had a usable price." % (priced, len(operations))
        )
    return operations, warnings


def render_commands(operations, group=DEFAULT_GROUP):
    """The CLI commands for a set of operations, in order, as strings.

    Rendered rather than run.  The group has to exist before the items, so it
    is emitted first.

    Every JSON argument goes through ``shlex.quote``.  Hand-wrapping them in
    single quotes produced commands that looked right and were not: the first
    real title through here was "Assassin's Creed Odyssey", whose apostrophe
    closed the quote and split the argument.  A game title is exactly the kind
    of string that contains one.
    """
    import json
    import shlex

    def arg(flag, value):
        text = value if isinstance(value, str) else json.dumps(value,
                                                               ensure_ascii=False)
        return "  %s %s" % (flag, shlex.quote(text))

    lines = [
        "xsolla catalog admin-create-group --merchant-id $M --project-id $P \\",
        "  --external-id %s --order 99 --is-enabled \\" % shlex.quote(group),
        arg("--name", {"en": "Imported from listing"}),
    ]
    for op in operations:
        lines.append("")
        lines.append("xsolla catalog create-items --merchant-id $M --project-id $P \\")
        parts = [arg("--sku", op["sku"]),
                 arg("--name", op["name"]),
                 arg("--description", op["description"])]
        if op["prices"]:
            parts.append(arg("--prices", op["prices"]))
        parts.append(arg("--groups", op["groups"]))
        if op["is_enabled"]:
            parts.append("  --is-enabled --is-show-in-store")
        lines.extend(part + " \\" for part in parts[:-1])
        lines.append(parts[-1])
    return "\n".join(lines)

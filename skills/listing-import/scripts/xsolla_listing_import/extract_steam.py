"""Steam listing extraction, from the public ``appdetails`` response.

Input is the JSON body of
``https://store.steampowered.com/api/appdetails?appids=<id>&l=english`` --
already fetched.  This module never makes a request: keeping the network out of
the library is what lets the tests run offline and what stops a rate limit from
looking like a parser bug.

Two things this gets from the API that the Shop Builder parsing endpoint does
not return at all: the screenshots and the age rating.

What it misses:

* ``tags`` -- Steam's user tags render on the store page and are **absent** from
  this response.  Declared in ``not_found`` rather than omitted, so coverage can
  tell "looked and it is not here" from "did not look".
* ``categories[]`` is deliberately not mapped to ``tags``.  It looks like tags
  and is not: it is Steam's own feature list (Single-player, Steam Achievements,
  Trading Cards), which means nothing on a partner's site.
* ``package_groups`` alone is not the edition list.  It holds the page's buy
  options; the "Content For This Game" table is ``dlc``, which is app **ids**
  only and needs one lookup each.  Pass those responses as ``dlc_details`` or
  the result under-reports -- for Brawlhalla, one entry instead of five.
* Steam publishes no in-game item list at all, so ``iap_items`` here is always
  editions and DLC, never consumables.
"""

from __future__ import annotations

from . import fields as field_model

# Rating bodies in preference order.  PEGI and ESRB first because they are the
# two a partner is most likely to recognise on their own store page.
RATING_BODIES = ("pegi", "esrb", "usk", "oflc", "dejus")


def unwrap(document):
    """Accept either the full ``{appid: {success, data}}`` body or the inner data."""
    if not isinstance(document, dict):
        return None
    if "name" in document or "steam_appid" in document:
        return document
    for value in document.values():
        if isinstance(value, dict) and value.get("success") and "data" in value:
            return value["data"]
    return None


def _age_rating(data):
    ratings = data.get("ratings") or {}
    for body in RATING_BODIES:
        entry = ratings.get(body) or {}
        rating = entry.get("rating")
        if rating:
            return "%s %s" % (body.upper(), str(rating).upper())
    return None


def _iap_items(data, dlc_details=None):
    """Everything Steam sells alongside the game.

    Two sources, and using only the first is why an earlier version found one
    edition where the store page shows five:

    ``package_groups``
        The buy options rendered at the top of the page -- for Brawlhalla, just
        "All Legends Pack". For a paid game, its editions.
    ``dlc``
        A list of **app ids only**. The "Content For This Game" table on the
        page is these, and their names and prices need one ``appdetails``
        lookup each. The caller fetches them and passes them in; this module
        does not make requests.

    An entry carries ``image`` where the source has one, so the edition can be
    given its own artwork rather than inheriting the game's.
    """
    # A free-to-play app has no `price_overview`, so its buy options carry cents
    # with no currency.  The DLC came from the same storefront in the same
    # round of requests, so its currency is the right one to borrow.
    currency = (data.get("price_overview") or {}).get("currency")
    if not currency:
        for dlc in dlc_details or []:
            found = (dlc or {}).get("price_overview", {}).get("currency")
            if found:
                currency = found
                break

    items = []
    for group in data.get("package_groups") or []:
        for sub in group.get("subs") or []:
            text = (sub.get("option_text") or "").strip()
            if not text:
                continue
            # Steam renders "Edition Name - 59,99€"; the price is a separate
            # field, so the trailing copy is noise in a catalog name.
            name = text.rsplit(" - ", 1)[0] if " - " in text else text
            entry = {"name": name}
            cents = sub.get("price_in_cents_with_discount")
            if cents and currency:
                entry["price"] = {"amount": round(cents / 100.0, 2),
                                  "currency": currency}
            items.append(entry)

    seen = {i["name"] for i in items}
    for dlc in dlc_details or []:
        if not isinstance(dlc, dict):
            continue
        name = (dlc.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        entry = {"name": name}
        price = dlc.get("price_overview") or {}
        if price.get("final") and price.get("currency"):
            entry["price"] = {"amount": round(price["final"] / 100.0, 2),
                              "currency": price["currency"]}
        if dlc.get("header_image"):
            entry["image"] = dlc["header_image"]
        if dlc.get("short_description"):
            entry["description"] = dlc["short_description"]
        items.append(entry)
    return items


def dlc_ids(document):
    """The DLC app ids a listing references, for the caller to fetch."""
    data = unwrap(document) or {}
    return [int(i) for i in (data.get("dlc") or []) if str(i).isdigit()]


def to_listing(document, source_url, dlc_details=None):
    """Build a listing document.  ``rights_confirmed`` is left false on purpose.

    Only the caller has asked the partner whether the game is theirs, so only
    the caller may set that flag.
    """
    data = unwrap(document)
    if data is None:
        raise ValueError("not a Steam appdetails response (no successful data)")

    values = {
        "title": data.get("name"),
        "developer": ", ".join(data.get("developers") or []) or None,
        "short_description": data.get("short_description"),
        "long_description_html": data.get("about_the_game"),
        "icon": data.get("capsule_image"),
        "key_art": data.get("header_image"),
        "screenshots": [s.get("path_full") for s in data.get("screenshots") or []
                        if s.get("path_full")],
        "genres": [g.get("description") for g in data.get("genres") or []
                   if g.get("description")],
        "platforms": [name for name, on in (data.get("platforms") or {}).items() if on],
        "age_rating": _age_rating(data),
        "iap_items": _iap_items(data, dlc_details),
    }
    not_found = ["tags"]
    for name, value in list(values.items()):
        if not value:
            values.pop(name)
            if name not in not_found:
                not_found.append(name)

    return {
        "source": field_model.STEAM,
        "source_url": source_url,
        "rights_confirmed": False,
        "fields": values,
        "not_found": not_found,
        "notes": "Steam user tags render on the store page but are absent from the "
                 "appdetails response; this extraction used the API. iap_items are "
                 "editions and DLC -- Steam publishes no in-game item list.",
    }

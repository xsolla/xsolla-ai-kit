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
* ``package_groups`` yields editions and DLC, not consumables.  Steam publishes
  no in-game item list, so ``iap_items`` from Steam is always editions.
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


def _iap_items(data):
    """Editions from ``package_groups``, priced from the discounted cents field."""
    items = []
    for group in data.get("package_groups") or []:
        for sub in group.get("subs") or []:
            text = (sub.get("option_text") or "").strip()
            if not text:
                continue
            # Steam renders "Edition Name - 59,99€"; the price is already a
            # separate field, so the trailing copy is noise in a catalog name.
            name = text.rsplit(" - ", 1)[0] if " - " in text else text
            entry = {"name": name}
            cents = sub.get("price_in_cents_with_discount")
            currency = data.get("price_overview", {}).get("currency")
            if cents and currency:
                entry["price"] = {"amount": round(cents / 100.0, 2),
                                  "currency": currency}
            items.append(entry)
    return items


def to_listing(document, source_url):
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
        "iap_items": _iap_items(data),
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

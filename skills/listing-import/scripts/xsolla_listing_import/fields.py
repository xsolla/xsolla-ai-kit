"""The target field set, and which of them each storefront actually publishes.

The field list is the epic's Definition of Done, turned into something a script
can count.  ``developer`` is here as well because the Shop Builder parsing
endpoint returns it, even though the DoD does not ask for it.

Why availability is per-source, and why the metric needs it: a source cannot be
marked down for a field it never publishes.  Steam has no content-rating block
on most pages and no consumable IAP list at all; the App Store publishes no
wide key art.  Scoring those as misses would report a mapping bug where the
real answer is "the page does not say".  So ``coverage.py`` reports two numbers
-- one against the fields the source publishes, which is the number to hold to
a target, and one against the whole DoD list, which is the number to quote
honestly when someone asks what a partner actually gets.

What this module misses: availability is recorded per storefront, not per page.
A given Steam page may carry a PEGI rating or may not, and this says only that
Steam sometimes does.  Treat ``PARTIAL`` as "ask the page, not the table".
"""

from __future__ import annotations

# Availability of a field on a source, as published on the public page.
ALWAYS = "always"
PARTIAL = "partial"
NEVER = "never"

STEAM = "steam"
GOOGLE_PLAY = "google_play"
APP_STORE = "app_store"

SOURCES = (STEAM, GOOGLE_PLAY, APP_STORE)

SOURCE_LABELS = {
    STEAM: "Steam",
    GOOGLE_PLAY: "Google Play",
    APP_STORE: "Apple App Store",
}

# Each entry: field -> (kind, in_dod, {source: availability})
#
# ``kind`` drives how the value is validated and how it is written:
#   text      a single localizable string
#   richtext  localizable HTML (the long description)
#   media     one remote image URL, which has to be fetched and re-uploaded
#   media[]   a list of remote image URLs
#   list      a list of plain strings (genres, tags, platforms)
#   items     the in-app purchase list, each with an optional price point
FIELDS = {
    "title": ("text", True, {STEAM: ALWAYS, GOOGLE_PLAY: ALWAYS, APP_STORE: ALWAYS}),
    "developer": ("text", False, {STEAM: ALWAYS, GOOGLE_PLAY: ALWAYS, APP_STORE: ALWAYS}),
    "short_description": (
        "text", True, {STEAM: ALWAYS, GOOGLE_PLAY: ALWAYS, APP_STORE: PARTIAL},
    ),
    "long_description": (
        "richtext", True, {STEAM: ALWAYS, GOOGLE_PLAY: ALWAYS, APP_STORE: ALWAYS},
    ),
    "icon": ("media", True, {STEAM: ALWAYS, GOOGLE_PLAY: ALWAYS, APP_STORE: ALWAYS}),
    # Play was first recorded as ALWAYS here, from the documented 1024x500
    # feature graphic.  Checked against the live page for
    # com.supercell.clashofclans on 2026-09-14: no image on it has that shape,
    # so Play appears to have stopped rendering it. Corrected to NEVER, which
    # keeps it out of Play's coverage denominator instead of scoring a field the
    # page does not publish as a miss.
    "key_art": ("media", True, {STEAM: ALWAYS, GOOGLE_PLAY: NEVER, APP_STORE: NEVER}),
    "screenshots": (
        "media[]", True, {STEAM: ALWAYS, GOOGLE_PLAY: ALWAYS, APP_STORE: ALWAYS},
    ),
    "genres": ("list", True, {STEAM: ALWAYS, GOOGLE_PLAY: ALWAYS, APP_STORE: ALWAYS}),
    # Steam user tags are rendered on the page but absent from the appdetails
    # response, so whether they are reachable depends on which the agent read.
    # PARTIAL rather than ALWAYS for that reason.
    "tags": ("list", True, {STEAM: PARTIAL, GOOGLE_PLAY: NEVER, APP_STORE: NEVER}),
    "platforms": ("list", True, {STEAM: ALWAYS, GOOGLE_PLAY: ALWAYS, APP_STORE: ALWAYS}),
    # Steam was first written down as PARTIAL here, on the assumption that only
    # some pages carry a rating.  Checked against app 812140 on 2026-09-14 the
    # listing exposes a full `ratings` block (pegi, esrb, usk, oflc, dejus and
    # more), so the rating is there to be read on any rated title.
    "age_rating": (
        "text", True, {STEAM: ALWAYS, GOOGLE_PLAY: ALWAYS, APP_STORE: ALWAYS},
    ),
    "iap_items": (
        "items", True, {STEAM: PARTIAL, GOOGLE_PLAY: PARTIAL, APP_STORE: PARTIAL},
    ),
    # Not in the DoD's field list, so it does not move the coverage numbers --
    # but all three storefronts publish it and a shop that omits it is leaving
    # the publisher's own social proof on the table. Steam gives a
    # recommendation count with no score; the other two give both.
    "reviews": (
        "text", False, {STEAM: PARTIAL, GOOGLE_PLAY: ALWAYS, APP_STORE: ALWAYS},
    ),
    # Steam publishes these as HTML per platform. Play states a minimum Android
    # version in prose on some listings and the App Store publishes none, so
    # the block is pruned on both rather than filled with a guess.
    "requirements": (
        "platforms", False, {STEAM: ALWAYS, GOOGLE_PLAY: NEVER, APP_STORE: NEVER},
    ),
    # Individual player reviews, as opposed to the aggregate score in
    # ``reviews``.  Steam and Apple both publish the text through a public
    # endpoint.  Play does not: its reviews section is rendered client-side and
    # the markup carries only the chrome, so a plain fetch finds nothing.
    "user_reviews": (
        "quotes", False, {STEAM: ALWAYS, GOOGLE_PLAY: NEVER, APP_STORE: ALWAYS},
    ),
}

# Fields the Shop Builder parsing endpoint (`xsolla shopbuilder get-listing`)
# returns.  Verified live against merchant 936601 on 2026-09-14: the response is
# `{developer, icon, title}` and nothing else, which is why the mapping preview
# cannot be built from that call alone.
GET_LISTING_FIELDS = ("title", "developer", "icon")


def dod_fields():
    """The fields the Definition of Done asks for, in declaration order."""
    return tuple(name for name, (_, in_dod, _a) in FIELDS.items() if in_dod)


def field_kind(name):
    """The ``kind`` of one field, or ``None`` if it is not a known field."""
    entry = FIELDS.get(name)
    return entry[0] if entry else None


def availability(name, source):
    """How reliably ``source`` publishes ``name``.  Unknown pairs read NEVER."""
    entry = FIELDS.get(name)
    if not entry:
        return NEVER
    return entry[2].get(source, NEVER)


def expected_fields(source):
    """DoD fields ``source`` publishes at all -- the coverage denominator.

    ``PARTIAL`` counts as expected.  A field the source sometimes publishes is a
    field worth trying for, and folding it into the denominator keeps the metric
    from flattering a run that simply did not look.
    """
    return tuple(
        name for name in dod_fields()
        if availability(name, source) in (ALWAYS, PARTIAL)
    )

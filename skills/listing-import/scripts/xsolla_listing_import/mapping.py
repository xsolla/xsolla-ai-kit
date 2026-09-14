"""Where each listing field lands in a Shop Builder page.

Every row carries a ``confidence``, and that column is the useful part:

``confirmed``
    The patch path was exercised against the live API and observed to take
    effect.  Source: the CLI's own ``external-store-to-shop`` reference, which
    records these as confirmed by contract.
``schema``
    The field exists in the Site Builder editor's own schema for that module,
    but this repo has not watched a write to it land.  Treat as a good guess.
    Shop Builder answers ``ok: true`` to a patch at a path that does not exist
    and changes nothing, so an unconfirmed path fails *silently* -- which is
    why ``plan.py`` pairs every write with a read-back.
``none``
    The listing publishes the field and no module has anywhere to put it.  Not
    a gap in this code; a gap in the block set.  Reported to the user as manual
    follow-up rather than dropped.

What this module misses: it maps a field to one destination, while several
modules could carry a title, and it assumes the block template a Steam import
produces (``header``, ``leadGameSales``, ``description``, ``packs``,
``bento-grid``, ``gallery``, ``requirements``, ``faq``, ``footer``).  A landing
built block-by-block may not have the module a row names, so ``plan.py``
resolves rows against the real structure and reports the misses.
"""

from __future__ import annotations

from . import fields as field_model

LOCALIZATION = "localization"
PATCH = "patch"
ASSET = "asset"
MANUAL = "manual"
EXTERNAL = "external"

CONFIRMED = "confirmed"
SCHEMA = "schema"
NONE = "none"


class Target(object):
    """One field's destination.  A plain object so it reads in a traceback."""

    __slots__ = ("field", "module", "action", "path", "confidence", "note")

    def __init__(self, field, module, action, path, confidence, note=""):
        self.field = field
        self.module = module
        self.action = action
        self.path = path
        self.confidence = confidence
        self.note = note

    def as_dict(self):
        return {
            "field": self.field,
            "module": self.module,
            "action": self.action,
            "path": list(self.path) if self.path else None,
            "confidence": self.confidence,
            "note": self.note,
        }

    def __repr__(self):
        return "Target(%s -> %s/%s)" % (self.field, self.module, self.action)


TARGETS = (
    Target("title", "leadGameSales", LOCALIZATION, ("values", "title"), SCHEMA,
           "h3 wrapper. The import fills this already; overwrite only on request."),
    Target("developer", "lead", LOCALIZATION, ("values", "developer"), SCHEMA,
           "Falls back to the footer description when no lead block exists."),
    Target("short_description", "leadGameSales", LOCALIZATION,
           ("values", "subtitle"), SCHEMA, "p wrapper."),
    Target("long_description", "description", LOCALIZATION,
           ("values", "components"), SCHEMA,
           "A keyed TEXT component, not a bare string. Read the block first: the "
           "component id is generated, and the L: ref has to already exist."),
    Target("icon", "header", ASSET, ("values", "logo", "img"), SCHEMA,
           "Upload first, then patch the returned CDN url."),
    Target("key_art", "leadGameSales", ASSET, ("values", "background", "img"),
           CONFIRMED,
           "Set background.enable true and background.size cover with it, and a "
           "gradient for text legibility over art."),
    Target("screenshots", "gallery", ASSET, ("values", "slides"), CONFIRMED,
           "One slide per screenshot: slides[i].image. Slide ids are generated "
           "when omitted."),
    Target("platforms", "sidebar", PATCH, ("values", "storeButtons"), SCHEMA,
           "platform is an enum (steam, app_store, google, playstation, xbox, "
           "...) plus a link. Where 'also available on' buttons belong."),
    Target("age_rating", "footer", MANUAL, ("values", "ageRatingIds"), NONE,
           "The footer takes rating *ids* it already holds, not free text. No "
           "command creates one, so this is a Publisher Account step."),
    Target("genres", None, MANUAL, None, NONE,
           "No module has a genre field. Carry into the description copy, or a "
           "bento-grid card, if the partner wants it visible."),
    Target("tags", None, MANUAL, None, NONE,
           "Steam user tags have no destination. Usually worth dropping: they "
           "are Steam's taxonomy, not the partner's."),
    Target("iap_items", None, EXTERNAL, None, NONE,
           "Catalog, not a landing. Route to catalog-admin; a store block then "
           "shows them via shopbuilder's wire-a-store flow."),
)

TARGETS_BY_FIELD = {target.field: target for target in TARGETS}

# Companion patches that have to accompany a key-art write for the result to be
# legible.  Confirmed paths, from the same reference as the background write.
KEY_ART_COMPANIONS = (
    (("values", "background", "enable"), True),
    (("values", "background", "size"), "cover"),
)


def target_for(field):
    """The destination for one field, or ``None`` if the field is unknown."""
    return TARGETS_BY_FIELD.get(field)


def unmapped_fields():
    """DoD fields with nowhere native to go -- the block-set gap, listed once."""
    return tuple(
        target.field for target in TARGETS
        if target.action in (MANUAL, EXTERNAL) and target.field in field_model.dod_fields()
    )


def source_matches_url(source, url):
    """Whether ``source`` is the storefront ``url`` points at.

    Returns ``None`` when the host is not one of the three, so a caller can tell
    "disagrees" from "cannot say".
    """
    if not url:
        return None
    host = url.split("//")[-1].split("/")[0].lower()
    if "steampowered.com" in host or "steamcommunity.com" in host:
        return source == field_model.STEAM
    if "play.google.com" in host:
        return source == field_model.GOOGLE_PLAY
    if "apps.apple.com" in host or "itunes.apple.com" in host:
        return source == field_model.APP_STORE
    return None

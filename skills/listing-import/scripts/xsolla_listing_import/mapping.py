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
OVERFLOW = "overflow"
CATALOG = "catalog"
REQUIREMENTS = "requirements"
REVIEWS = "reviews"
MANUAL = "manual"

# Actions that put the content somewhere the partner can see it.  OVERFLOW and
# CATALOG count: a genre rendered as a line of copy in the description block is
# copied, and an in-app item created as a catalog entity is copied.  Only MANUAL
# does not -- it means a human has to finish the job by hand.
DELIVERABLE = (LOCALIZATION, PATCH, ASSET, OVERFLOW, CATALOG, REQUIREMENTS,
               REVIEWS)

CONFIRMED = "confirmed"
SCHEMA = "schema"
NONE = "none"


class Target(object):
    """One field's destination.  A plain object so it reads in a traceback."""

    __slots__ = ("field", "module", "action", "path", "confidence", "note",
                 "component_type")

    def __init__(self, field, module, action, path, confidence, note="",
                 component_type=None):
        self.field = field
        self.module = module
        self.action = action
        self.path = path
        self.confidence = confidence
        self.note = note
        # When set, `path` is not literal: the last segment is a field on the
        # first component of this type, whose key the editor generated. The
        # planner resolves it from the block.
        self.component_type = component_type

    def as_dict(self):
        return {
            "field": self.field,
            "module": self.module,
            "action": self.action,
            "path": list(self.path) if self.path else None,
            "confidence": self.confidence,
            "note": self.note,
            "component_type": self.component_type,
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
    # `values.logo.img` was the first guess and it does not exist: the header's
    # logo is a component of type "logo" inside values.components, under a key
    # the editor generated. The first live run patched the guessed path, got
    # ok:true, changed nothing, and the read-back caught it.
    Target("icon", "header", ASSET, ("values", "components", "logo"), CONFIRMED,
           "Resolved against the block: the first component of type \"logo\". "
           "Upload the file first, then patch the returned CDN url.",
           component_type="logo"),
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
    # These four have no *structured* block field, which is not the same as
    # having nowhere to go.  Routed rather than dropped -- see overflow.py and
    # catalog.py.  The earlier version reported them as unmappable and put a
    # 7/11 ceiling on the whole skill; that ceiling was an artefact of only
    # counting native fields.
    Target("age_rating", "description", OVERFLOW, ("values", "components"), SCHEMA,
           "Rendered as a line of copy. The footer's ageRatingIds field takes "
           "rating *ids* the site already holds and no command creates one, so "
           "the badge itself stays a Publisher Account step."),
    Target("user_reviews", "bento-grid", REVIEWS, ("values", "gridComponents"),
           SCHEMA,
           "One chosen review per leaf card. A leaf with two text components "
           "takes the quote and the attribution separately. Gated on "
           "rights_reviews_confirmed: these are a player's words, not the "
           "publisher's."),
    Target("requirements", "requirements", REQUIREMENTS,
           ("components",), SCHEMA,
           "Each platform is a platform_req_v2 component whose requirementList "
           "rows carry their own L: references. Resolved against the block."),
    Target("reviews", "description", OVERFLOW, ("values", "components"), SCHEMA,
           "Rendered as a line of copy. No module has a reviews field, and the "
           "rating is a publisher's own social proof -- worth carrying over."),
    Target("genres", "description", OVERFLOW, ("values", "components"), SCHEMA,
           "Rendered as a line of copy in the description block. No module has a "
           "structured genre field."),
    Target("tags", "description", OVERFLOW, ("values", "components"), SCHEMA,
           "Rendered as a line of copy. Worth asking before carrying Steam user "
           "tags over: they are Steam's taxonomy of the game, not the "
           "publisher's positioning of it."),
    Target("iap_items", None, CATALOG, None, SCHEMA,
           "Created as catalog virtual items priced in real money. Not currency "
           "packages or bundles: those need a content array with quantities, and "
           "no storefront publishes the quantity behind a name like 'Pocketful "
           "of Gems'."),
)

TARGETS_BY_FIELD = {target.field: target for target in TARGETS}

# Companion patches that have to accompany a key-art write for the result to be
# legible.  Confirmed paths, from the same reference as the background write.
KEY_ART_COMPANIONS = (
    (("values", "background", "enable"), True),
    (("values", "background", "size"), "cover"),
)

# A gallery slide's media object carries a colour layer over the image.  The
# default block template ships it at ``rgba(23, 19, 32, 0.85)`` -- an 85%
# opaque dark wash, meant for artwork sitting behind text.  Write a screenshot
# underneath it and the slide looks empty, which is exactly how the Play and
# App Store shops came out: three uploaded images each, none of them visible.
# A landing built by `import-listing` has it transparent already, which is why
# Steam looked right and the other two did not.
SLIDE_COMPANIONS = (
    ("color", "transparent"),
    ("enable", True),
)


def target_for(field):
    """The destination for one field, or ``None`` if the field is unknown."""
    return TARGETS_BY_FIELD.get(field)


def unmapped_fields():
    """DoD fields with nowhere at all to go.  Empty since overflow routing."""
    return tuple(
        target.field for target in TARGETS
        if target.action == MANUAL and target.field in field_model.dod_fields()
    )


def overflow_fields():
    """Fields carried as copy because no structured block field exists."""
    return tuple(t.field for t in TARGETS if t.action == OVERFLOW)


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

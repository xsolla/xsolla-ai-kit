"""The federated structural walk: user data against the block's own defaults.

A federated block carries both sides of this comparison in one document --
``values.internalBlockValues`` is the user's data, ``values.defaultData`` the
shipped defaults that act as the reference shape.  Nothing else is fetched.

What the walk catches is type mismatches, and only those.  Required fields,
enums and array item shapes are not enforced, and nothing at all is enforced
where the defaults are empty.  That mirrors the tooling this is ported from,
which is itself a stopgap pending federated blocks exposing real schemas -- so
a clean federated run is not a full check and must not be reported as one.
"""

from __future__ import annotations

import re

from .errors import MISSING, finding, format_path, js_type

IMAGE_ID = re.compile(r"^I:[a-z0-9]+$")
LOCALIZED_ID = re.compile(r"^L:[a-z0-9-]+$", re.IGNORECASE)

# A field that takes either a CSS keyword or a pixel number.  A type-only
# comparison cannot express that, and without this list every block a user has
# resized reports a false finding -- which is how a gate gets switched off.
SIZING_KEYWORDS = frozenset(
    [
        "auto",
        "none",
        "normal",
        "inherit",
        "initial",
        "unset",
        "cover",
        "contain",
        "fit-content",
        "max-content",
        "min-content",
    ]
)


def is_custom_block_id(block_id):
    """Custom (AI) blocks share the ``federated`` module; the prefix is the test."""
    return isinstance(block_id, str) and block_id.startswith("ai_")


def is_remote_block_id(block_id, known):
    return isinstance(block_id, str) and block_id in known


def _is_reference_override(user, defaults):
    """A default that is an ``I:``/``L:`` id makes any user string acceptable.

    These are references, not content, so string-against-string is the only
    comparison available here.  Whether the reference *resolves* is a separate
    check -- and it is the one that matters.
    """
    if not isinstance(user, str) or not isinstance(defaults, str):
        return False
    return bool(IMAGE_ID.match(defaults) or LOCALIZED_ID.match(defaults))


def _is_sizing_union(user, defaults):
    keyword_then_number = (
        isinstance(defaults, str)
        and defaults in SIZING_KEYWORDS
        and isinstance(user, (int, float))
        and not isinstance(user, bool)
    )
    number_then_keyword = (
        isinstance(user, str)
        and user in SIZING_KEYWORDS
        and isinstance(defaults, (int, float))
        and not isinstance(defaults, bool)
    )
    return keyword_then_number or number_then_keyword


def _walk(user, defaults, path, out):
    # No reference shape here: the user may legitimately add fields the
    # defaults never mentioned, so the whole subtree is skipped.
    if defaults is MISSING or defaults is None:
        return

    if _is_reference_override(user, defaults) or _is_sizing_union(user, defaults):
        return

    user_type = js_type(user)
    default_type = js_type(defaults)
    if user_type != default_type:
        out.append(finding(format_path(path), default_type, user_type, user))
        # One finding per bad path: descending would report its children too.
        return

    if isinstance(user, list) and isinstance(defaults, list):
        # The defaults array's length means nothing; item 0 is the shape.
        reference = defaults[0] if defaults else MISSING
        for index, item in enumerate(user):
            _walk(item, reference, path + [index], out)
        return

    if isinstance(user, dict) and isinstance(defaults, dict):
        for key, value in user.items():
            _walk(value, defaults.get(key, MISSING), path + [key], out)


def validate_federated(internal_block_values, default_data):
    """Walk the user's values against the defaults.

    ``internalBlockValues`` absent entirely passes -- there is nothing to check.
    So does a block with no ``defaultData``, which is the normal state of a
    freshly created custom block.
    """
    if internal_block_values is MISSING or internal_block_values is None:
        return {"ok": True, "errors": [], "walked": False}

    if default_data is MISSING or default_data is None:
        return {"ok": True, "errors": [], "walked": False}

    out = []
    _walk(internal_block_values, default_data, [], out)
    return {"ok": not out, "errors": out, "walked": True}


def resolve_federated_localized_id(short_id, resources):
    """Federated ``L:`` ids take two hops, not one.

    The short ids inside a federated block are block-local.  They are not in the
    landing's localization store and looking for them there is wrong: doing that
    scored 43 false errors on one known-good site.  They resolve through the
    block's own ``values.resources.localizedValues`` first, and it is the uuid
    that comes back which belongs in the store.
    """
    if not isinstance(resources, dict):
        return None
    localized = resources.get("localizedValues")
    if not isinstance(localized, dict):
        return None
    entry = localized.get(short_id)
    if not isinstance(entry, dict):
        return None
    texts = entry.get("texts")
    if not isinstance(texts, dict):
        return None
    resolved = texts.get("id")
    return resolved if isinstance(resolved, str) else None

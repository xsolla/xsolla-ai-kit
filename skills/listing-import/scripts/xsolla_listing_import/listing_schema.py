"""Validation of the ``listing.json`` an agent produces from a store page.

This is the seam between the two halves of the skill.  The agent reads the
public page and writes this document; everything downstream is deterministic.
Validating it here means a mapping bug and an extraction bug fail in different
places, with different messages, instead of both surfacing as a broken block.

Two fields carry more weight than their size suggests:

``rights_confirmed``
    Checked for *type* here and for *truth* in ``plan.py``.  Has to be ``true``
    before anything is planned.  The Shop Builder parsing
    endpoint will read *any* public store page -- verified live on 2026-09-14
    against a Ubisoft listing on merchant 936601 -- so nothing upstream checks
    whether the game belongs to the partner running the import.  This flag is
    where that check lives, and ``plan.py`` refuses without it.

``not_found``
    What the agent looked for and could not find, as opposed to what it never
    looked for.  Without it an absent field is ambiguous, and coverage cannot
    tell a page that publishes no age rating from an extraction that skipped
    it.

What this module misses: it checks shape and type, not truth.  Nothing here can
tell that a ``title`` belongs to a different game than the ``screenshots``, or
that a URL 404s.  It also does not verify ``source`` against ``source_url``;
``mapping.py`` warns on a mismatch instead, because a deliberate override is
occasionally right.
"""

from __future__ import annotations

from . import fields as field_model
from .errors import MISSING, describe_got, finding, js_type

REQUIRED_TOP = ("source", "source_url", "rights_confirmed", "fields")
OPTIONAL_TOP = ("fetched_at", "not_found", "notes")

# Long description arrives in one of two forms; Steam ships BBCode, the other
# two ship something closer to HTML or plain text.
DESCRIPTION_KEYS = ("long_description_bbcode", "long_description_html",
                    "long_description_text")

_EXPECTED_KIND_TYPES = {
    "platforms": list,
    "text": str,
    "richtext": str,
    "media": str,
    "media[]": list,
    "list": list,
    "items": list,
}


IAP_KEYS = ("name", "price", "description", "description_clean", "image")


def _check_iap_items(items, errors):
    """Each IAP entry needs a name; everything else is optional.

    ``description`` is the storefront's own copy.  ``description_clean`` is that
    copy rewritten by the agent for a card -- preferred when present, because a
    storefront's description is written to sell on that storefront and arrives
    with marketing furniture and a length a card cannot hold.
    """
    for index, item in enumerate(items):
        path = "fields.iap_items.%d" % index
        if not isinstance(item, dict):
            errors.append(finding(path, "object", js_type(item)))
            continue
        unknown = set(item) - set(IAP_KEYS)
        for extra in sorted(unknown):
            errors.append(finding(path + "." + extra, "a known in-app item key",
                                  "unknown key"))
        for text_key in ("description", "description_clean", "image"):
            if text_key in item and not isinstance(item[text_key], str):
                errors.append(finding(path + "." + text_key, "string",
                                      js_type(item[text_key])))
        if not item.get("name"):
            errors.append(finding(path + ".name", "non-empty string",
                                  describe_got(item.get("name", MISSING))))
        price = item.get("price", MISSING)
        if price is MISSING or price is None:
            continue
        if not isinstance(price, dict):
            errors.append(finding(path + ".price", "object", js_type(price)))
            continue
        amount = price.get("amount", MISSING)
        if not isinstance(amount, (int, float)) or isinstance(amount, bool):
            errors.append(finding(path + ".price.amount", "number",
                                  describe_got(amount)))
        currency = price.get("currency", MISSING)
        if not isinstance(currency, str) or len(currency) != 3:
            errors.append(finding(path + ".price.currency", "3-letter ISO code",
                                  describe_got(currency)))


def validate(document):
    """Check a listing document.  Returns a list of errors; empty means valid."""
    errors = []
    if not isinstance(document, dict):
        return [finding("(root)", "object", js_type(document))]

    for key in REQUIRED_TOP:
        if key not in document:
            errors.append(finding(key, "present", "undefined"))

    source = document.get("source")
    if source is not None and source not in field_model.SOURCES:
        errors.append(finding("source", " | ".join(field_model.SOURCES),
                              describe_got(source)))

    # Shape only: that this is a boolean.  Whether it is *true* is a policy
    # question, not a malformed-document question, and it belongs to the thing
    # that stands in front of the write -- `plan.build`.  Checking it here as
    # well reported an unconfirmed-but-well-formed listing as invalid JSON,
    # which sends the reader to fix the file rather than to ask the partner.
    if "rights_confirmed" in document and not isinstance(
        document["rights_confirmed"], bool
    ):
        errors.append(finding("rights_confirmed", "boolean",
                              js_type(document["rights_confirmed"])))

    unknown = set(document) - set(REQUIRED_TOP) - set(OPTIONAL_TOP)
    for key in sorted(unknown):
        errors.append(finding(key, "a known top-level key", "unknown key"))

    values = document.get("fields")
    if values is None:
        return errors
    if not isinstance(values, dict):
        errors.append(finding("fields", "object", js_type(values)))
        return errors

    for name, value in sorted(values.items()):
        if name in DESCRIPTION_KEYS:
            if not isinstance(value, str):
                errors.append(finding("fields." + name, "string", js_type(value)))
            continue
        kind = field_model.field_kind(name)
        if kind is None:
            errors.append(finding("fields." + name, "a known field", "unknown field"))
            continue
        expected_type = _EXPECTED_KIND_TYPES[kind]
        if not isinstance(value, expected_type) or isinstance(value, bool):
            errors.append(finding("fields." + name,
                                  "array" if expected_type is list else "string",
                                  js_type(value)))
            continue
        if kind == "items":
            _check_iap_items(value, errors)
        elif kind in ("media[]", "list"):
            for index, entry in enumerate(value):
                if not isinstance(entry, str) or not entry.strip():
                    errors.append(finding("fields.%s.%d" % (name, index),
                                          "non-empty string", describe_got(entry)))

    present = [key for key in DESCRIPTION_KEYS if values.get(key)]
    if len(present) > 1:
        errors.append(finding("fields", "one long-description form",
                              "both " + " and ".join(present)))

    not_found = document.get("not_found", [])
    if not isinstance(not_found, list):
        errors.append(finding("not_found", "array", js_type(not_found)))
    else:
        for index, name in enumerate(not_found):
            if name in values and values[name]:
                errors.append(finding(
                    "not_found.%d" % index,
                    "a field that is absent from fields",
                    "%s, which fields also sets" % name,
                ))


    return errors


def long_description(document):
    """The long description and its format, as ``(text, form)``.

    ``form`` is ``bbcode``, ``html``, ``text`` or ``None``.  Steam's BBCode goes
    through ``bbcode.to_html``; the others are used as-is.
    """
    values = (document or {}).get("fields") or {}
    for key in DESCRIPTION_KEYS:
        if values.get(key):
            return values[key], key.rsplit("_", 1)[1]
    return None, None

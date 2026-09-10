"""Native block payload checks -- the envelope, then the field-level schemas.

Two independent sections, each checked only when present, each finding
re-rooted under the section it came from.  An absent section is not a finding:
it is a payload that does not touch that section.

The field-level schemas are a **create-payload** contract.  Checking a block you
read back against its own module schema fails every time (36 live blocks, 36
false alarms), so ``validate_native`` is for payloads on the way in.  Use the
structural checks and the site walk on the way out.
"""

from __future__ import annotations

import json
import os

from .errors import finding, prefix_errors
from .schema_subset import validate

# The 23 native modules' field schemas, generated from Site Builder's own
# schemas rather than transcribed.  Data, not code: regenerate it rather than
# hand-editing, and see INVENTORY.md for what it does and does not cover.
_SCHEMAS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "block-schemas.json",
)

# Verbatim, and never normalised: the API treats `newstore` and `newStore` as
# different keys.  Kept as a tuple so a caller cannot mutate the list.
NATIVE_MODULES = (
    "bento-grid",
    "description",
    "embed",
    "faq",
    "fast-login",
    "footer",
    "gallery",
    "hero",
    "html",
    "lead",
    "leadGameSales",
    "newStore",
    "news",
    "nft",
    "packs",
    "payment-methods",
    "promoSlider",
    "promocodes",
    "requirements",
    "retailers",
    "rewards",
    "sidebar",
    "subscriptions-packs",
)

LAYOUT_MODULES = ("header", "common-layout", "side-by-side-layout")

FEDERATED_MODULE = "federated"

REMOTE_BLOCK_IDS = (
    "sb-offer-chain",
    "sb-daily-reward",
    "social-quests",
    "offerwall-block",
)

# Verified against the live API on 2026-09-10: the shipped schemas mark
# ``quillWrapper`` as a required key on a localized descriptor, but a create
# that omits it is accepted and the text renders correctly (patched a faq
# title with no wrapper; the server stored the reference and returned the
# HTML unchanged).  Requiring it would block a write that works, so it is
# reported as advisory rather than as a finding.  Fold this back into the
# generator rather than growing the list.
ADVISORY_SUFFIXES = (".quillWrapper",)

_cache = {}


def load_schemas(path=None):
    """The shipped module schemas, read once per path."""
    resolved = os.path.normpath(path or _SCHEMAS_PATH)
    if resolved not in _cache:
        with open(resolved, "r") as handle:
            _cache[resolved] = json.load(handle)
    return _cache[resolved]


def module_schema(module, schemas=None):
    """One module's entry, or ``None`` when the module ships no schema."""
    return (schemas if schemas is not None else load_schemas()).get(module)


def max_version(module, schemas=None):
    """The version a create must pass, or ``None`` for an unversioned module."""
    entry = module_schema(module, schemas)
    return entry.get("maxVersion") if entry else None


def is_native_module(module):
    return module in NATIVE_MODULES


def validate_envelope(payload):
    """The shape every native payload has to have, before any field check.

    One finding and nothing else: reporting field paths inside a payload whose
    envelope is wrong points the reader at fields that do not exist.  ``values``
    arriving as a JSON *string* is the common form of this -- easy to produce
    from a shell, and it type-checks as "present" everywhere downstream.
    """
    if not isinstance(payload, dict):
        return [
            finding(
                "(root)",
                "object { values?, components? }",
                _envelope_got(payload),
                payload,
            )
        ]
    if "values" in payload and not isinstance(payload["values"], dict):
        return [
            finding(
                "values",
                "object",
                _envelope_got(payload["values"]),
                payload["values"],
            )
        ]
    if "components" in payload and not isinstance(payload["components"], list):
        return [
            finding(
                "components",
                "array",
                _envelope_got(payload["components"]),
                payload["components"],
            )
        ]
    return []


def _envelope_got(value):
    from .errors import js_type

    return js_type(value)


def validate_native(module, payload, partial=False, schemas=None):
    """Check one native block payload.

    ``partial=True`` for an update: a patch carries only the fields it changes,
    so a missing required field is not a finding.

    An unknown module key passes with ``schema_available: False``.  A skill or
    script that errors on an unrecognised module is stricter than the platform
    and blocks writes that would have succeeded -- but the caller has to say so
    in the report, which is why the flag is returned rather than swallowed.
    """
    envelope = validate_envelope(payload)
    if envelope:
        return {"ok": False, "errors": envelope, "advisories": [], "schema_available": False}

    entry = module_schema(module, schemas)
    if entry is None:
        return {"ok": True, "errors": [], "advisories": [], "schema_available": False}

    schema = entry.get("schema") or {}
    sections = schema.get("properties") or {}
    errors = []

    for section in ("values", "components"):
        section_schema = sections.get(section)
        if section_schema is None or section not in payload:
            continue
        section_errors = validate(
            payload[section],
            section_schema,
            partial=partial if section == "values" else False,
        )
        errors.extend(prefix_errors(section_errors, section))

    errors, advisories = _split_advisories(errors)

    return {
        "ok": not errors,
        "errors": errors,
        "advisories": advisories,
        "schema_available": True,
    }


def _split_advisories(errors):
    """Move the known over-strict schema requirements out of the errors list."""
    kept, advisory = [], []
    for f in errors:
        if f.get("got") == "undefined" and f["path"].endswith(ADVISORY_SUFFIXES):
            advisory.append(f)
        else:
            kept.append(f)
    return kept, advisory

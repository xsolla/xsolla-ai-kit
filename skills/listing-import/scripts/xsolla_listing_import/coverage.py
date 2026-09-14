"""The field-coverage metric, split into the two things it conflates.

The epic asks for one number -- "% of target fields filled from the source,
target >= 80%".  Measuring it turned up that a single number cannot be honest,
because two independent things can go wrong and they have different owners:

*extraction* coverage
    Of the DoD fields this source publishes, how many did the agent get?  A
    miss here is a bug in the extraction step, and it is the number worth
    holding to a target.

*mapping* coverage
    Of the fields extracted, how many have somewhere in a Shop Builder page to
    go?  A miss here is not fixable from this repo at all -- four DoD fields
    (``genres``, ``tags``, ``age_rating``, ``iap_items``) have no native block
    field, so landing-only mapping coverage is capped at 7/11 = 64%.  Reporting
    a blended number would read as an extraction failure and send someone to
    fix the wrong half.

*delivered* coverage, the product of the two, is what a partner actually sees
on the page.  Quote all three.  A run that extracts everything Steam publishes
and still delivers 64% is working correctly and hitting a ceiling in the block
set, and those two facts should not be summed into one disappointing figure.

What this module misses: it counts fields, not quality.  A ``long_description``
that converted badly counts the same as one that converted cleanly, and a
truncated title counts as present.  It also weights every field equally, which
a partner would not -- missing ``screenshots`` hurts more than missing ``tags``.
"""

from __future__ import annotations

from . import fields as field_model
from . import mapping
from .listing_schema import long_description


def _present(values, name):
    """Whether a field carries usable content.  Empty string/list is absent."""
    if name == "long_description":
        return bool(values.get("long_description_bbcode")
                    or values.get("long_description_html")
                    or values.get("long_description_text"))
    value = values.get(name)
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def measure(document):
    """Coverage of one listing document.

    Returns a report dict.  ``extraction``/``mapping``/``delivered`` each carry
    ``filled``, ``total`` and ``pct``; ``pct`` is ``None`` when ``total`` is 0
    rather than 0.0, so an empty denominator cannot read as a failure.
    """
    source = (document or {}).get("source")
    values = (document or {}).get("fields") or {}
    declared_missing = list((document or {}).get("not_found") or [])

    expected = field_model.expected_fields(source)
    extracted = [name for name in expected if _present(values, name)]
    missing = [name for name in expected if name not in extracted]

    deliverable = []
    manual = []
    for name in extracted:
        target = mapping.target_for(name)
        if target is not None and target.action in (
            mapping.LOCALIZATION, mapping.PATCH, mapping.ASSET
        ):
            deliverable.append(name)
        else:
            manual.append(name)

    # Fields this source does not publish at all -- excluded from the
    # denominator, and named so nobody reads their absence as a defect.
    not_published = [
        name for name in field_model.dod_fields()
        if field_model.availability(name, source) == field_model.NEVER
    ]

    _text, form = long_description(document)

    return {
        "source": source,
        "source_label": field_model.SOURCE_LABELS.get(source, str(source)),
        "extraction": _ratio(len(extracted), len(expected)),
        "mapping": _ratio(len(deliverable), len(extracted)),
        "delivered": _ratio(len(deliverable), len(field_model.dod_fields())),
        "extracted": extracted,
        "missing": missing,
        "declared_not_found": declared_missing,
        "undeclared_missing": [n for n in missing if n not in declared_missing],
        "manual_follow_up": manual,
        "not_published_by_source": not_published,
        "long_description_form": form,
        "mapping_ceiling": _ratio(
            len(field_model.dod_fields()) - len(mapping.unmapped_fields()),
            len(field_model.dod_fields()),
        ),
    }


def _ratio(filled, total):
    pct = None if not total else round(100.0 * filled / total, 1)
    return {"filled": filled, "total": total, "pct": pct}

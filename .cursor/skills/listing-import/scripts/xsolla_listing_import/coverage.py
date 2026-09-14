"""The field-coverage metric, split into the two things it conflates.

The epic asks for one number -- "% of target fields filled from the source,
target >= 80%".  Measuring it turned up that a single number cannot be honest,
because two independent things can go wrong and they have different owners:

*extraction* coverage
    Of the DoD fields this source publishes, how many did the agent get?  A
    miss here is a bug in the extraction step, and it is the number worth
    holding to a target.

*mapping* coverage
    Of the fields extracted, how many have somewhere to go?  This was capped at
    7/11 = 64% while only native block fields counted.  It no longer is:
    ``genres``, ``tags`` and ``age_rating`` are carried as copy in the
    description block and ``iap_items`` become catalog entities, so every target
    field has a destination and the ceiling is 11/11.  The 64% was an artefact
    of the measurement, not a limit of the product -- a genre rendered as a line
    of copy is on the page, and a reader cannot tell which kind of field
    delivered it.

    A miss here now means a *structural* one: the landing has no block of the
    kind a field needs, which ``unresolved`` names separately.

*delivered* coverage, the product of the two, is what a partner actually gets.
Quote all three: they fail for different reasons and have different owners.

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
        if target is not None and target.action in mapping.DELIVERABLE:
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

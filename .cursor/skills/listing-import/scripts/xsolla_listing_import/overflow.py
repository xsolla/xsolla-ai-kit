"""Fields with no structured block field, rendered as copy instead.

``genres``, ``tags`` and ``age_rating`` are published by the storefronts and no
Site Builder module has a field for any of them.  The first version of this
skill reported them as unmappable, which put a 7/11 ceiling on the whole
import.  That ceiling was an artefact of counting only native fields: a genre
list rendered as a line in the description block *is* copied onto the page, and
a partner reading the page cannot tell whether it arrived through a typed field
or a paragraph.

So these three are appended to the ``description`` block as one extra TEXT
component.  One component, not three, because three stacked one-line paragraphs
read like a debug dump.

What this module misses: it produces the HTML, not the component envelope --
``plan.py`` pairs it with a generated component id, because ids are the
block's, not this module's, to invent.  It also has no opinion on where in the
component order the line lands; appended last is the safe default but rarely
the prettiest.
"""

from __future__ import annotations

from html import escape

# The label each field is rendered under.  Wording is deliberately plain: this
# is a partner's own store page, not a data dump, so "Genres" beats
# "genres[]" and an age rating reads as a rating, not a field.
LABELS = {
    "genres": "Genres",
    "tags": "Tags",
    "age_rating": "Rating",
}

ORDER = ("genres", "tags", "age_rating")


def _render_value(value):
    """One field's value as escaped inline HTML."""
    if isinstance(value, (list, tuple)):
        parts = [escape(str(v).strip(), quote=False) for v in value if str(v).strip()]
        return ", ".join(parts)
    return escape(str(value).strip(), quote=False)


def render(values):
    """Build the overflow copy from a listing's ``fields``.

    Returns ``(html, carried)`` -- the component's HTML and the field names it
    actually carried, so the plan can report which ones this accounted for
    rather than leaving a reader to infer it.
    """
    lines = []
    carried = []
    for name in ORDER:
        value = values.get(name)
        if not value:
            continue
        rendered = _render_value(value)
        if not rendered:
            continue
        lines.append("<p><strong>%s:</strong> %s</p>" % (LABELS[name], rendered))
        carried.append(name)
    return "".join(lines), carried

"""The error shape this skill emits.

``{path, expected, got, value?}`` -- matching what the Site Builder tooling
already emits, which is why the key is ``got`` and not ``actual``.  Server-side
validation is moving to an ``actual`` envelope in a separate effort; until that
lands, emitting the key the existing tooling uses means two reports can be read
side by side without translating one of them.

Self-contained on purpose.  Nothing here imports from a sibling skill: skills
are distributed per-directory, so reaching across would make this one
unrunnable wherever it is installed alone.  The cost is that the shape is
pinned in more than one place across the kit; ``tests/test_errors.py`` asserts
the fields so a change here fails loudly rather than drifting quietly.
"""

from __future__ import annotations

MISSING = object()
"""Sentinel for "this key was absent", distinct from a JSON ``null``."""


def js_type(value):
    """The type name the Site Builder tooling reports, not Python's.

    ``bool`` before ``int``: in Python ``True`` is an ``int``, and reporting
    ``number`` for a boolean sends a reader after the wrong bug.
    """
    if value is MISSING:
        return "undefined"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def describe_got(value):
    """What to put in ``got``: a string's own content, otherwise its type."""
    if value is MISSING:
        return "undefined"
    if isinstance(value, str):
        return value
    return js_type(value)


def finding(path, expected, got, value=MISSING):
    """One error, in the shape the Site Builder tooling emits."""
    out = {"path": path if path else "(root)", "expected": expected, "got": got}
    if value is not MISSING:
        out["value"] = value
    return out

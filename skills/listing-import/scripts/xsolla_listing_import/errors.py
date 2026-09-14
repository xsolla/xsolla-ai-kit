"""The error shape this skill emits.

Deliberately the same ``{path, expected, got, value?}`` shape as
``shop-validation``'s ``errors.py``, and for the same reason its docstring
gives: the key is ``got``, not ``actual``.  Two skills that both stand in front
of a Shop Builder write should produce reports a reader -- or the CLI -- can
concatenate without translating one into the other.

It is a copy rather than an import on purpose.  Reaching across skill
directories would make ``listing-import`` unrunnable wherever only one of the
two is installed, and skills are distributed per-directory.  The cost is that
the shape is now pinned in two places; ``tests/test_errors.py`` asserts the
fields so a change here fails loudly rather than drifting quietly.
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
    """One error, in the shape ``shop-validation`` emits."""
    out = {"path": path if path else "(root)", "expected": expected, "got": got}
    if value is not MISSING:
        out["value"] = value
    return out

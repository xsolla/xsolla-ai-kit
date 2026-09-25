"""The two error shapes every validator emits.

Two shapes, deliberately different, because the two families of check produce
different kinds of information:

* payload errors -- ``{path, expected, got, value?}``, matching the shape the Site Builder
  MCP emits.  The key is ``got``, not ``actual``: server-side validation is moving to an
  ``actual`` envelope in a separate effort, and until that lands, matching the key the
  existing tooling emits means two reports can be compared without translating them.
* code violations -- ``{rule, message, suggestion}``, as the MCP's AI-block rules emit.
  A static-analysis hit has no path into a payload, and a rule id is what makes it
  actionable.
"""

from __future__ import annotations

MISSING = object()
"""Sentinel for "this key was absent", distinct from a JSON ``null``."""


def js_type(value):
    """The type name the Site Builder tooling reports, not Python's.

    ``bool`` is checked before ``int`` on purpose: in Python ``True`` is an
    ``int``, and reporting ``number`` for a boolean would send a reader looking
    for the wrong bug.
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
    """One payload error, in the MCP's shape.  ``value`` is omitted when useless."""
    out = {
        "path": path if path else "(root)",
        "expected": expected,
        "got": got,
    }
    if value is not MISSING:
        out["value"] = value
    return out


def violation(rule, message, suggestion):
    """One custom-block source violation."""
    return {"rule": rule, "message": message, "suggestion": suggestion}


def format_path(segments):
    """Dot-join a path.  Array indices are segments too: ``components.0.answer``."""
    if not segments:
        return "(root)"
    return ".".join(str(s) for s in segments)


def prefix_errors(errors, prefix):
    """Re-root errors under ``prefix`` -- ``values`` / ``components``.

    An error at the section root reports as the bare section name, not
    ``values.(root)``.
    """
    out = []
    for f in errors:
        f = dict(f)
        f["path"] = prefix if f["path"] == "(root)" else "%s.%s" % (prefix, f["path"])
        out.append(f)
    return out

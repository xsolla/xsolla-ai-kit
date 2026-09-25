"""A JSON Schema validator for exactly the subset ``block-schemas.json`` uses.

Deliberately not a general JSON Schema implementation and not a dependency.
The 23 shipped module schemas between them use thirteen keywords -- ``type``,
``properties``, ``required``, ``additionalProperties``, ``propertyNames``,
``const``, ``enum``, ``items``, ``anyOf``, ``oneOf``, ``allOf``, ``minimum``,
``maximum`` -- so that is what this supports.  Anything else in a schema is
ignored rather than guessed at, which is the safe direction: an unrecognised
keyword must never invent a finding.

Error phrasings match the five the skill documents, so two reports of the same
class of problem read the same:

* the plain type -- ``string``
* an allowed set -- ``one of: "sm", "lg"``
* a closed object -- ``no extra keys (got: titel)``
* an either/or field -- ``one of the union variants``
* a bound -- ``>= 0``
"""

from __future__ import annotations

import json

from .errors import MISSING, describe_got, finding, format_path, js_type

_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "null": lambda v: v is None,
}


def _quote(value):
    return json.dumps(value)


def _is_number(value):
    """A JSON number: an int or float, but never a bool."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _matches_type(value, type_kw):
    names = type_kw if isinstance(type_kw, list) else [type_kw]
    for name in names:
        check = _TYPE_CHECKS.get(name)
        if check is None:
            # Unknown type name: pass rather than fabricate a finding.
            return True
        if check(value):
            return True
    return False


def _expected_type(type_kw):
    if isinstance(type_kw, list):
        return " or ".join(type_kw)
    return type_kw


def validate(instance, schema, path=None, partial=False):
    """Validate ``instance`` against ``schema``; return a list of errors.

    ``partial`` drops ``required`` at the *top level only*, which is what an
    update means: a patch carries the fields it changes and no others.  It does
    not propagate into nested objects -- a nested object you do send must still
    be complete.
    """
    path = list(path or [])
    if not isinstance(schema, dict) or schema == {}:
        return []

    out = []

    if "const" in schema:
        if instance != schema["const"]:
            out.append(
                finding(
                    format_path(path),
                    "one of: %s" % _quote(schema["const"]),
                    describe_got(instance),
                    instance,
                )
            )
            return out

    if "enum" in schema:
        if instance not in schema["enum"]:
            out.append(
                finding(
                    format_path(path),
                    "one of: %s" % ", ".join(_quote(v) for v in schema["enum"]),
                    describe_got(instance),
                    instance,
                )
            )
            return out

    for key in ("anyOf", "oneOf"):
        if key in schema:
            branches = schema[key]
            if not any(not validate(instance, b, path) for b in branches):
                out.append(
                    finding(
                        format_path(path),
                        "one of the union variants",
                        describe_got(instance),
                        instance,
                    )
                )
                return out

    if "allOf" in schema:
        for branch in schema["allOf"]:
            out.extend(validate(instance, branch, path, partial=partial))

    if "type" in schema:
        if not _matches_type(instance, schema["type"]):
            out.append(
                finding(
                    format_path(path),
                    _expected_type(schema["type"]),
                    js_type(instance),
                    instance,
                )
            )
            # Wrong type at this node: its children are meaningless.
            return out

    if "minimum" in schema and _is_number(instance):
        if instance < schema["minimum"]:
            out.append(
                finding(
                    format_path(path),
                    ">= %s" % schema["minimum"],
                    describe_got(instance),
                    instance,
                )
            )
    if "maximum" in schema and _is_number(instance):
        if instance > schema["maximum"]:
            out.append(
                finding(
                    format_path(path),
                    "<= %s" % schema["maximum"],
                    describe_got(instance),
                    instance,
                )
            )

    if isinstance(instance, dict):
        out.extend(_validate_object(instance, schema, path, partial))
    elif isinstance(instance, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(instance):
                out.extend(validate(item, item_schema, path + [index]))

    return out


def _validate_object(instance, schema, path, partial):
    out = []
    properties = schema.get("properties") or {}

    if not partial:
        for name in schema.get("required") or []:
            if name not in instance:
                child = properties.get(name) or {}
                expected = _expected_type(child["type"]) if "type" in child else "required"
                out.append(finding(format_path(path + [name]), expected, "undefined"))

    additional = schema.get("additionalProperties", True)
    if additional is False:
        extras = [k for k in instance if k not in properties]
        if extras:
            out.append(
                finding(
                    format_path(path),
                    "no extra keys (got: %s)" % ", ".join(sorted(extras)),
                    ", ".join(sorted(extras)),
                )
            )

    names_schema = schema.get("propertyNames")
    if isinstance(names_schema, dict):
        for key in instance:
            for f in validate(key, names_schema, path + [key]):
                f["expected"] = "property name: %s" % f["expected"]
                out.append(f)

    for name, value in instance.items():
        if name in properties:
            out.extend(validate(value, properties[name], path + [name]))
        elif isinstance(additional, dict) and additional:
            out.extend(validate(value, additional, path + [name]))

    return out

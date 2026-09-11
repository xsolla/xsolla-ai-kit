"""The constraints that reject a write without being shape checks.

From the user's side the difference is invisible -- a rejected write is a
rejected write -- so these belong in the same gate as the payload rules.
"""

from __future__ import annotations

from .errors import MISSING, finding, js_type
from .native import LAYOUT_MODULES, max_version

PROTECTED_FIELDS = ("_id", "module", "blockVersion")


def check_create_version(module, version, schemas=None):
    """A create has to pass exactly the module's ``maxVersion``.

    Ten modules carry a versions list; every other module has none, and for
    those a create passes no version at all. That distinction comes from the
    block metadata, not from the shipped schemas — the schema tool reports
    ``maxVersion`` as "last version, or 1", which makes an unversioned module
    indistinguishable from a genuine version 1.
    """
    expected = max_version(module, schemas)
    if expected is None:
        return []
    if version is MISSING or version is None:
        return [finding("version", str(expected), "undefined")]
    if version != expected:
        return [finding("version", str(expected), str(version), version)]
    return []


def check_stored_version(module, block_version, schemas=None):
    """A stored block below ``maxVersion`` is normal, not a finding.

    Kept as its own function so an audit cannot accidentally call the create
    check.  An absent ``blockVersion`` on an unversioned module is correct, and
    so is an older version on an existing block.
    """
    return []


def check_not_layout_create(module):
    """Layout modules cannot be created, added or duplicated at all."""
    if module in LAYOUT_MODULES:
        return [
            finding(
                "module",
                "a creatable module (not %s)" % ", ".join(LAYOUT_MODULES),
                module,
                module,
            )
        ]
    return []


def check_protected_fields(patch):
    """``_id``, ``module`` and ``blockVersion`` cannot be patched.

    Worth planning around: a wrong ``blockVersion`` therefore cannot be fixed by
    an update.  The fix is to delete the block and recreate it at ``maxVersion``.
    """
    if not isinstance(patch, dict):
        return []
    out = []
    for field in PROTECTED_FIELDS:
        if field in patch:
            out.append(
                finding(
                    field,
                    "not present (protected field)",
                    js_type(patch[field]),
                    patch[field],
                )
            )
    return out


def expand_dotted_keys(payload):
    """Expand ``{"a.b.c": v}`` into nested objects before validating.

    Skip this and every dotted update reports a false finding, because the path
    checked is one top-level key with dots in its name rather than the field it
    addresses.  Expansion is per key and left-to-right; a segment that collides
    with a non-object value is replaced by an object, which is why a dotted key
    and its parent object must never be sent in the same payload.
    """
    if not isinstance(payload, dict):
        return payload

    out = {}
    for key, value in payload.items():
        expanded = expand_dotted_keys(value) if isinstance(value, dict) else value
        if not isinstance(key, str) or "." not in key:
            out[key] = expanded
            continue
        segments = key.split(".")
        cursor = out
        for segment in segments[:-1]:
            existing = cursor.get(segment)
            if not isinstance(existing, dict):
                existing = {}
                cursor[segment] = existing
            cursor = existing
        cursor[segments[-1]] = expanded
    return out


def check_batch_change_set(change_set):
    """The batch API's convention: patch paths are arrays of segments.

    A dotted string where a segment array belongs addresses a field literally
    named ``values.title``, which does not exist -- and depending on the
    endpoint that is a silent no-op rather than an error, which is worse.
    """
    out = []
    if not isinstance(change_set, dict):
        return [finding("(root)", "object { requestId: change }", js_type(change_set), change_set)]

    for request_id, change in change_set.items():
        base = str(request_id)
        if not isinstance(change, dict):
            out.append(finding(base, "object { type, id, patches }", js_type(change), change))
            continue
        if change.get("type") not in ("block", "page", "site"):
            out.append(
                finding(
                    "%s.type" % base,
                    'one of: "block", "page", "site"',
                    str(change.get("type")),
                    change.get("type"),
                )
            )
        if not isinstance(change.get("id"), str) or not change.get("id"):
            out.append(finding("%s.id" % base, "string", js_type(change.get("id", MISSING))))
        patches = change.get("patches")
        if not isinstance(patches, list):
            out.append(finding("%s.patches" % base, "array", js_type(patches if patches is not None else MISSING)))
            continue
        for index, patch in enumerate(patches):
            path = "%s.patches.%d" % (base, index)
            if not isinstance(patch, dict):
                out.append(finding(path, "object { op, path, value? }", js_type(patch), patch))
                continue
            if patch.get("op") not in ("add", "remove", "replace"):
                out.append(
                    finding(
                        "%s.op" % path,
                        'one of: "add", "remove", "replace"',
                        str(patch.get("op")),
                        patch.get("op"),
                    )
                )
            patch_path = patch.get("path")
            if isinstance(patch_path, str):
                out.append(
                    finding(
                        "%s.path" % path,
                        "array of path segments (e.g. [\"values\", \"title\"])",
                        "string",
                        patch_path,
                    )
                )
            elif not isinstance(patch_path, list) or not patch_path:
                out.append(
                    finding(
                        "%s.path" % path,
                        "array of path segments (e.g. [\"values\", \"title\"])",
                        js_type(patch_path if patch_path is not None else MISSING),
                        patch_path,
                    )
                )
    return out


def check_text_write_target(paths):
    """Patching a block path to change what the page *says* does nothing.

    A block's visible copy is an ``L:`` reference; the words live in the
    landing's localization store.  This is the single easiest way to believe a
    write succeeded when nothing changed, so it is a finding whatever shape the
    payload is in.
    """
    out = []
    for path in paths or []:
        out.append(
            finding(
                path,
                "a write against the localization store (page namespace + L: id + locale)",
                "a block values patch",
                path,
            )
        )
    return out

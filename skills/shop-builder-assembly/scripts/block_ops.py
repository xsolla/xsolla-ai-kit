#!/usr/bin/env python3
"""Validate and plan block operations (Quests block only).

Operation mode edits individual blocks on an existing site. The brief uses short
value keys (``questIds``, ``layout.cardAlign``); this module maps them to the full
CLI patch paths under ``["values", "internalBlockValues", ...]`` and reports which
parent objects must be created first, because the platform silently ignores a leaf
patch whose parent object is missing.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

# Contract recorded in references/block-operations.md ("Quests block contract").
QUESTS_MODULE = "_quest-platform_quests-block"
# Operations-only blocks: exported contracts exist, but they are outside the reviewed
# presets. validate_shop_brief re-exports this set; it is not part of
# VERIFIED_BLOCK_MODULES, so the reconcile flow and page_overrides never accept them.
OPS_BLOCK_MODULES = frozenset({QUESTS_MODULE})
# add-block --block federated, then one update-block retargeting the wrapper.
QUESTS_ADD_STRATEGY = "federated_patch"
# Package version the add strategy retargets to. 0.1.0-qp-3126.9 carries the reward
# override fields (`rewardText`, `rewardImageUrl`) in its bundle, and its default-data.json
# carries `layout` and `editorPreview`; its CDN files return 200 anonymously.
QUESTS_VERSION = "0.1.0-qp-3126.9"
QUESTS_CDN_ROOT = "https://cdn.xsolla.net/site-builder-modules/"
# Editor layer label that UI-added federated blocks carry (top-level `devName`).
QUESTS_DEV_NAME = "Quests"
BLOCK_VALUES_ROOT = ("values", "internalBlockValues")

LAYOUT_ENUMS = {
    "cardAlign": {"start", "center", "end"},
    "imageFit": {"cover", "contain"},
    "buttonStyle": {"primary", "secondary", "tertiary"},
    "blockBackground": {"transparent", "primary", "secondary"},
    "cardBackground": {"transparent", "primary", "secondary"},
}
LAYOUT_BOOLEANS = {"showHeading", "showDescription", "showImage"}
OVERRIDE_FIELDS = {
    "title",
    "description",
    "imageUrl",
    "imageRef",
    "rewardText",
    "rewardImageUrl",
}
EDITOR_PREVIEW = {
    "live",
    "anonymous",
    "not_started",
    "in_progress",
    "completed",
    "expired",
    "error",
}
# Short brief keys. ``overrides.<questId>.<field>`` is the only parametrised family.
QUESTS_PATCHABLE_LEAVES = frozenset(
    {"questIds", "maxQuests", "editorPreview"}
    | {f"layout.{name}" for name in (*LAYOUT_ENUMS, *LAYOUT_BOOLEANS)}
    | {f"overrides.<questId>.{name}" for name in OVERRIDE_FIELDS}
)
QUESTS_MAX_IDS = 24
# Quest Platform quest ids are UUIDs; a format check stops typos before any write.
QUEST_ID_RE = re.compile(r"[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")
TITLE_MAX = 120
REWARD_TEXT_MAX = 120
DESCRIPTION_MAX = 400
TRANSLATION_KEYS = {"heading"}
# Objects the pinned default-data.json already contains. A freshly added block has
# these; every other parent object must be created before its leaves are patched.
DEFAULT_PARENTS = {("overrides",)}

OPERATIONS = {
    "add": {"required": {"module", "page"}, "optional": {"index", "values", "translations"}},
    "update": {"required": {"block_id"}, "optional": {"values", "translations"}},
    "reset": {"required": {"block_id", "paths"}, "optional": set()},
    "move": {"required": {"block_id", "index"}, "optional": set()},
    "duplicate": {"required": {"block_id"}, "optional": {"index"}},
    "hide": {"required": {"block_id"}, "optional": set()},
    "show": {"required": {"block_id"}, "optional": set()},
    "delete": {"required": {"block_id"}, "optional": set()},
}
LOCALE_PARTS = 2


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_locale(value: object) -> bool:
    if not isinstance(value, str) or "-" not in value:
        return False
    language, _, region = value.partition("-")
    return (
        len(language) == LOCALE_PARTS
        and language.isalpha()
        and language.islower()
        and len(region) == LOCALE_PARTS
        and region.isalpha()
        and region.isupper()
    )


def split_key(key: str) -> tuple[str, ...] | None:
    """Split a short key into path segments, or None when it is not a patchable leaf."""
    if not isinstance(key, str):
        return None
    if key in ("questIds", "maxQuests", "editorPreview"):
        return (key,)
    head, _, rest = key.partition(".")
    if head == "layout" and rest in (*LAYOUT_ENUMS, *LAYOUT_BOOLEANS):
        return ("layout", rest)
    if head == "overrides":
        quest_id, _, field = rest.rpartition(".")
        if quest_id and field in OVERRIDE_FIELDS:
            return ("overrides", quest_id, field)
    return None


def full_path(key: str) -> list[str]:
    """Map a short brief key to the CLI patch path."""
    segments = split_key(key)
    if segments is None:
        raise ValueError(f"{key!r} is not a patchable leaf")
    return [*BLOCK_VALUES_ROOT, *segments]


def required_parents(keys: list[str]) -> list[tuple[str, ...]]:
    """Parent objects (relative to internalBlockValues) the leaves need, shallowest first."""
    parents: list[tuple[str, ...]] = []
    for key in keys:
        segments = split_key(key)
        if segments is None:
            continue
        for depth in range(1, len(segments)):
            parent = segments[:depth]
            if parent not in parents:
                parents.append(parent)
    return sorted(parents, key=lambda parent: (len(parent), parent))


def quests_host(version: str = QUESTS_VERSION) -> str:
    """CDN folder the federated wrapper's ``values.host`` points at."""
    return f"{QUESTS_CDN_ROOT}{QUESTS_MODULE}/{version}/"


def has_object(root: object, segments: tuple[str, ...]) -> bool:
    """Whether ``segments`` leads to an object inside ``root``."""
    return _has_path(root, segments)


def has_leaf(root: object, segments: tuple[str, ...]) -> bool:
    """Whether ``segments`` leads to any value (object or leaf) inside ``root``."""
    return _path_present(root, segments)


def block_fingerprints(structure: dict) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Return (digest per page block id, block id order per page id).

    Digests ignore only the component ``_id`` values Shop Builder regenerates on every
    read, so an untouched block hashes the same before and after the run.
    """
    from render_plan import canonical_hash, stable_structure

    digests: dict[str, str] = {}
    order: dict[str, list[str]] = {}
    for page in structure.get("pages") or []:
        if not isinstance(page, dict) or not isinstance(page.get("_id"), str):
            continue
        ids = []
        for block in page.get("blocks") or []:
            if isinstance(block, dict) and isinstance(block.get("_id"), str):
                ids.append(block["_id"])
                digests[block["_id"]] = canonical_hash(stable_structure(block))
        order[page["_id"]] = ids
    return digests, order


def _has_path(root: object, segments: tuple[str, ...]) -> bool:
    node = root
    for segment in segments:
        if not isinstance(node, dict) or segment not in node:
            return False
        node = node[segment]
    return isinstance(node, dict)


def plan_value_patches(
    values: dict, internal: dict | None, is_new_block: bool = False
) -> tuple[list[dict], list[dict]]:
    """Return (create_parents, patches) for a brief ``values`` mapping.

    ``internal`` is the block's current ``internalBlockValues`` from the backup
    structure. For a block that does not exist yet (``is_new_block``) only the
    parents named in DEFAULT_PARENTS are assumed present. Each create-parent entry
    is an ``add`` of an empty object; leaf patches are ``replace``.
    """
    keys = list(values)
    create_parents = []
    for parent in required_parents(keys):
        if is_new_block:
            present = parent in DEFAULT_PARENTS
        else:
            present = _has_path(internal, parent)
        if not present:
            create_parents.append(
                {
                    "op": "add",
                    "path": [*BLOCK_VALUES_ROOT, *parent],
                    "value": {},
                }
            )
    patches = [
        {"op": "replace", "key": key, "path": full_path(key), "value": values[key]}
        for key in keys
    ]
    return create_parents, patches


def is_quest_id(value: object) -> bool:
    return isinstance(value, str) and QUEST_ID_RE.fullmatch(value) is not None


def _validate_leaf_value(key: str, value: object) -> str | None:
    segments = split_key(key)
    if segments is None:
        return None
    if segments == ("questIds",):
        if (
            not isinstance(value, list)
            or any(not isinstance(item, str) or not item.strip() for item in value)
            or len(value) > QUESTS_MAX_IDS
            or len(set(value)) != len(value)
        ):
            return (
                f"questIds must be a list of at most {QUESTS_MAX_IDS} unique "
                "non-empty strings"
            )
        bad = [item for item in value if not is_quest_id(item)]
        if bad:
            return f"questIds entries must be quest UUIDs, got: {', '.join(map(repr, bad))}"
    elif segments == ("maxQuests",):
        if not _is_int(value) or not 1 <= value <= QUESTS_MAX_IDS:
            return f"maxQuests must be an integer from 1 to {QUESTS_MAX_IDS}"
    elif segments == ("editorPreview",):
        if value not in EDITOR_PREVIEW:
            return "editorPreview must use: " + ", ".join(sorted(EDITOR_PREVIEW))
    elif segments[0] == "layout":
        name = segments[1]
        if name in LAYOUT_BOOLEANS:
            if not isinstance(value, bool):
                return f"{key} must be a boolean"
        elif not isinstance(value, str) or value not in LAYOUT_ENUMS[name]:
            return f"{key} must use: " + ", ".join(sorted(LAYOUT_ENUMS[name]))
    else:
        if not is_quest_id(segments[1]):
            return f"{key}: the quest id {segments[1]!r} is not a quest UUID"
        field = segments[2]
        if field == "title":
            if not isinstance(value, str) or len(value) > TITLE_MAX:
                return f"{key} must be a string of at most {TITLE_MAX} characters"
        elif field == "description":
            if not isinstance(value, str) or len(value) > DESCRIPTION_MAX:
                return f"{key} must be a string of at most {DESCRIPTION_MAX} characters"
        elif field == "rewardText":
            if not isinstance(value, str) or len(value) > REWARD_TEXT_MAX:
                return f"{key} must be a string of at most {REWARD_TEXT_MAX} characters"
        elif field in ("imageUrl", "rewardImageUrl"):
            parsed = urlparse(value) if isinstance(value, str) else None
            if parsed is None or parsed.scheme != "https" or not parsed.netloc:
                return f"{key} must be an https URL"
        elif field == "imageRef":
            if not isinstance(value, (str, dict)) or not value:
                return f"{key} must be a non-empty string or object"
    return None


def _validate_values(values: object, prefix: str, errors: list[str]) -> None:
    if not isinstance(values, dict) or not values:
        errors.append(f"{prefix}.values must be a non-empty object")
        return
    for key, value in values.items():
        if split_key(key) is None:
            errors.append(
                f"{prefix}.values.{key} is not a patchable leaf; use: "
                + ", ".join(sorted(QUESTS_PATCHABLE_LEAVES))
            )
            continue
        problem = _validate_leaf_value(key, value)
        if problem:
            errors.append(f"{prefix}.values.{key}: {problem}")


def _validate_translations(translations: object, prefix: str, errors: list[str]) -> None:
    if not isinstance(translations, dict) or not translations:
        errors.append(f"{prefix}.translations must be a non-empty object")
        return
    for locale, texts in translations.items():
        if not _is_locale(locale):
            errors.append(f"{prefix}.translations key {locale!r} must be a full locale code")
        if not isinstance(texts, dict) or not texts:
            errors.append(f"{prefix}.translations.{locale} must be a non-empty object")
            continue
        for key, text in texts.items():
            if key not in TRANSLATION_KEYS:
                errors.append(
                    f"{prefix}.translations.{locale}.{key} is not editable; use: "
                    + ", ".join(sorted(TRANSLATION_KEYS))
                )
            elif not isinstance(text, str) or not text.strip():
                errors.append(f"{prefix}.translations.{locale}.{key} must be a non-empty string")


def _page_blocks(structure: dict) -> list[tuple[dict, dict]]:
    pairs = []
    for page in structure.get("pages") or []:
        if isinstance(page, dict):
            for block in page.get("blocks") or []:
                if isinstance(block, dict):
                    pairs.append((page, block))
    return pairs


def find_block(structure: dict, block_id: str) -> tuple[dict, int, dict] | None:
    """Return (page, index, block) for a block on a page of the structure."""
    for page in structure.get("pages") or []:
        if not isinstance(page, dict):
            continue
        for index, block in enumerate(page.get("blocks") or []):
            if isinstance(block, dict) and block.get("_id") == block_id:
                return page, index, block
    return None


def _structure(value: object) -> dict:
    from render_plan import structure_data

    return structure_data(value)


def _is_quests_block(block: dict) -> bool:
    from render_plan import effective_module

    return effective_module(block) == QUESTS_MODULE


def validate_block_operations(brief: dict, structure: dict | None = None) -> list[str]:
    """Return errors for ``brief["block_operations"]``.

    Structure-dependent rules (the block exists and is a Quests block) run only when
    the backup ``structure`` is supplied.
    """
    errors: list[str] = []
    operations = brief.get("block_operations")
    if not isinstance(operations, list) or not operations:
        return ["block_operations must be a non-empty list"]
    if brief.get("content", {}) and isinstance(brief.get("content"), dict):
        if "page_overrides" in brief["content"]:
            errors.append(
                "block_operations cannot be combined with content.page_overrides"
            )
    current = _structure(structure) if structure is not None else None

    for index, operation in enumerate(operations):
        prefix = f"block_operations[{index}]"
        if not isinstance(operation, dict):
            errors.append(f"{prefix} must be an object")
            continue
        op = operation.get("op")
        if not isinstance(op, str) or op not in OPERATIONS:
            errors.append(f"{prefix}.op must use: {', '.join(sorted(OPERATIONS))}")
            continue
        spec = OPERATIONS[op]
        allowed = {"op"} | spec["required"] | spec["optional"]
        for key in sorted(set(operation) - allowed):
            errors.append(f"{prefix}.{key} is not valid for op {op}")
        for key in sorted(spec["required"] - set(operation)):
            errors.append(f"{prefix}.{key} is required for op {op}")

        if op == "add" and "module" in operation:
            module = operation["module"]
            if module not in OPS_BLOCK_MODULES:
                errors.append(
                    f"{prefix}.module must be an operations block: "
                    + ", ".join(sorted(OPS_BLOCK_MODULES))
                )
        if "page" in operation:
            page = operation["page"]
            if not isinstance(page, str) or not page.startswith("/"):
                errors.append(f"{prefix}.page must be a root-relative path")
            elif current is not None and _find_page(current, page) is None:
                errors.append(f"{prefix}.page {page} is not in the backup structure")
        if "index" in operation and (
            not _is_int(operation["index"]) or operation["index"] < 0
        ):
            errors.append(f"{prefix}.index must be a non-negative integer")
        if "values" in operation:
            _validate_values(operation["values"], prefix, errors)
        if "translations" in operation:
            _validate_translations(operation["translations"], prefix, errors)
        if op == "update" and not ({"values", "translations"} & set(operation)):
            errors.append(f"{prefix} needs values or translations")
        if op == "reset":
            paths = operation.get("paths")
            if not isinstance(paths, list) or not paths:
                errors.append(f"{prefix}.paths must be a non-empty list")
            else:
                for path in paths:
                    segments = _reset_path(path)
                    if segments is None:
                        errors.append(
                            f"{prefix}.paths entry {path!r} is not a patchable leaf "
                            "or overrides.<questId>"
                        )
                    elif segments[0] == "overrides" and not is_quest_id(segments[1]):
                        errors.append(
                            f"{prefix}.paths entry {path!r}: the quest id "
                            f"{segments[1]!r} is not a quest UUID"
                        )
        if "block_id" in operation:
            block_id = operation["block_id"]
            if not isinstance(block_id, str) or not block_id:
                errors.append(f"{prefix}.block_id must be a non-empty string")
            elif current is not None:
                found = find_block(current, block_id)
                if found is None:
                    errors.append(f"{prefix}.block_id {block_id} is not in the backup structure")
                elif not _is_quests_block(found[2]):
                    errors.append(f"{prefix}.block_id {block_id} is not a Quests block")
    return errors


def _reset_path(path: object) -> tuple[str, ...] | None:
    if not isinstance(path, str):
        return None
    segments = split_key(path)
    if segments is not None:
        return segments
    head, _, quest_id = path.partition(".")
    if head == "overrides" and quest_id:
        return ("overrides", quest_id)
    return None


def _find_page(structure: dict, path: str) -> dict | None:
    from render_plan import page_path

    for page in structure.get("pages") or []:
        if page_path(page) == path:
            return page
    return None


def plan_block_operations(brief: dict, structure: dict) -> list[dict]:
    """Return plan items in brief order. Raises ValueError for an invalid brief."""
    errors = validate_block_operations(brief, structure)
    if errors:
        raise ValueError("invalid block_operations: " + "; ".join(errors))
    current = _structure(structure)
    items: list[dict] = []
    for index, operation in enumerate(brief["block_operations"]):
        op = operation["op"]
        ref = f"op:{index}"
        if op == "add":
            page = _find_page(current, operation["page"])
            count = len(page.get("blocks") or [])
            position = operation.get("index", 0)
            if position > count:
                raise ValueError(
                    f"block_operations[{index}].index {position} is past the end of "
                    f"{operation['page']} ({count} blocks)"
                )
            items.append(
                {
                    "type": "block_add",
                    "op_index": index,
                    "block_ref": ref,
                    "module": operation["module"],
                    "strategy": QUESTS_ADD_STRATEGY,
                    "version": QUESTS_VERSION,
                    "page": operation["page"],
                    "page_id": page.get("_id"),
                    "index": position,
                }
            )
            if operation.get("values"):
                create_parents, patches = plan_value_patches(
                    operation["values"], None, is_new_block=True
                )
                items.append(
                    _values_item(index, None, ref, page.get("_id"), create_parents, patches)
                )
            if operation.get("translations"):
                items.append(_localization_item(index, None, ref, operation["translations"]))
            continue

        page, position, block = find_block(current, operation["block_id"])
        block_id = operation["block_id"]
        page_id = page.get("_id")
        if op == "update":
            if operation.get("values"):
                internal = (block.get("values") or {}).get("internalBlockValues")
                create_parents, patches = plan_value_patches(operation["values"], internal)
                items.append(
                    _values_item(index, block_id, block_id, page_id, create_parents, patches)
                )
            if operation.get("translations"):
                items.append(
                    _localization_item(index, block_id, block_id, operation["translations"])
                )
        elif op == "reset":
            internal = (block.get("values") or {}).get("internalBlockValues")
            patches = []
            for path in operation["paths"]:
                segments = _reset_path(path)
                patches.append(
                    {
                        "op": "remove",
                        "key": path,
                        "path": [*BLOCK_VALUES_ROOT, *segments],
                        "present": _path_present(internal, segments),
                    }
                )
            items.append(
                {
                    "type": "block_reset",
                    "op_index": index,
                    "block_id": block_id,
                    "page_id": page_id,
                    "patches": patches,
                }
            )
        elif op == "move":
            blocks = page.get("blocks") or []
            if operation["index"] >= len(blocks):
                raise ValueError(
                    f"block_operations[{index}].index {operation['index']} is outside "
                    f"the page ({len(blocks)} blocks)"
                )
            items.append(
                {
                    "type": "block_move",
                    "op_index": index,
                    "block_id": block_id,
                    "page_id": page_id,
                    "source_index": position,
                    "index": operation["index"],
                }
            )
        elif op == "duplicate":
            items.append(
                {
                    "type": "block_duplicate",
                    "op_index": index,
                    "block_id": block_id,
                    "page_id": page_id,
                    "source_index": position,
                    "index": operation.get("index", position + 1),
                }
            )
        elif op in ("hide", "show"):
            items.append(
                {
                    "type": "block_visibility",
                    "op_index": index,
                    "block_id": block_id,
                    "page_id": page_id,
                    "hidden": op == "hide",
                }
            )
        else:
            items.append(
                {
                    "type": "block_delete",
                    "op_index": index,
                    "block_id": block_id,
                    "page_id": page_id,
                    "source_index": position,
                    "method": "delete-block --force while the block is on the page",
                }
            )
    return items


def _path_present(root: object, segments: tuple[str, ...]) -> bool:
    node = root
    for segment in segments:
        if not isinstance(node, dict) or segment not in node:
            return False
        node = node[segment]
    return True


def _values_item(
    index: int,
    block_id: str | None,
    ref: str,
    page_id: object,
    create_parents: list[dict],
    patches: list[dict],
) -> dict:
    return {
        "type": "block_values",
        "op_index": index,
        "block_id": block_id,
        "block_ref": ref,
        "page_id": page_id,
        "create_parents": create_parents,
        "patches": patches,
    }


def _localization_item(
    index: int, block_id: str | None, ref: str, translations: dict
) -> dict:
    return {
        "type": "block_localization",
        "op_index": index,
        "block_id": block_id,
        "block_ref": ref,
        "translations": translations,
    }


def removals(items: list[dict]) -> list[dict]:
    """Explicit delete ops only; ops mode never removes anything else."""
    return [
        {"block_id": item["block_id"], "page_id": item["page_id"], "reason": "explicit delete op"}
        for item in items
        if item["type"] == "block_delete"
    ]

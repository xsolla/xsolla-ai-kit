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
# Package version the add strategy retargets to: the latest released (non-prerelease)
# build on the CDN. 0.1.5 reads the editable override fields (`title`, `description`,
# `imageUrl`, `imageRef`) in its bundle; the reward text and reward image come from the
# quest definition and are read-only (READ_ONLY_OVERRIDE_FIELDS). Its default-data.json carries `overrides`, `layout` and `editorPreview`; its CDN files
# return 200 anonymously.
QUESTS_VERSION = "0.1.5"
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
}
# Product decision (PRD, 26 Oct 2026): the reward text and reward image come from the
# quest definition. No op may write or reset them.
# Card text the Site Builder editor seeds as a localized ref the first time it opens
# (`use-seed-card-texts.ts` in the block). A ref whose resource exists wins over the
# plain field, so an update writes the new text into the ref as well (latest change
# wins, PRD open question 14) and a reset removes the ref, as the block's own "Reset to
# quest content" does.
CARD_TEXT_REFS = {"title": "titleRef", "description": "descriptionRef"}
CARD_TEXT_NOTE = (
    "replaces the text set for this card in the Site Builder editor (all site locales)"
)
READ_ONLY_OVERRIDE_FIELDS = frozenset({"rewardText", "rewardImageUrl"})
READ_ONLY_REWARD_ERROR = (
    "the reward text and reward image come from the quest and can't be changed on "
    "the Quests block; change the reward in the quest itself (quest-setup)"
)
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
}
# No script deletes a block: `delete-block` asks for confirmation and the only way past
# the prompt without a terminal is `--force`, which the skill never passes.
DELETE_REFUSAL = (
    "op delete is not supported: no script deletes a block, because delete-block needs "
    "--force and the skill never passes it. Answer needs_human: the publisher deletes "
    "the block in the Site Builder editor. Offer op hide as the scripted alternative"
)
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


def is_read_only_key(key: object) -> bool:
    """Whether ``key`` targets a read-only reward leaf (``overrides.<questId>.rewardText``)."""
    if not isinstance(key, str):
        return False
    head, _, rest = key.partition(".")
    quest_id, _, field = rest.rpartition(".")
    return head == "overrides" and bool(quest_id) and field in READ_ONLY_OVERRIDE_FIELDS


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
        if not isinstance(value, str) or value not in EDITOR_PREVIEW:
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
        elif field == "imageUrl":
            parsed = urlparse(value) if isinstance(value, str) else None
            if parsed is None or parsed.scheme != "https" or not parsed.hostname:
                return f"{key} must be an https URL"
            if "@" in parsed.netloc:
                return f"{key} must not carry user credentials (user:password@host)"
        elif field == "imageRef":
            if not isinstance(value, (str, dict)) or not value:
                return f"{key} must be a non-empty string or object"
    return None


def _validate_values(values: object, prefix: str, errors: list[str]) -> None:
    if not isinstance(values, dict) or not values:
        errors.append(f"{prefix}.values must be a non-empty object")
        return
    for key, value in values.items():
        if is_read_only_key(key):
            errors.append(f"{prefix}.values.{key}: {READ_ONLY_REWARD_ERROR}")
            continue
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
        if op == "delete":
            errors.append(f"{prefix}.{DELETE_REFUSAL}")
            continue
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
                    if is_read_only_key(path):
                        errors.append(f"{prefix}.paths entry {path!r}: {READ_ONLY_REWARD_ERROR}")
                        continue
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
    if errors:
        return errors
    _check_conflicts(operations, errors)
    if current is not None:
        _check_locales(operations, current, errors)
        _check_card_refs(operations, current, errors)
        _check_indices(operations, current, errors)
    return errors


# Ops that change block order on a page; a duplicate's default index is stale after one.
ORDER_OPS = {"add", "move", "duplicate"}


def _op_page_id(operation: dict, current: dict) -> object:
    if operation["op"] == "add":
        return _find_page(current, operation["page"]).get("_id")
    return find_block(current, operation["block_id"])[0].get("_id")


def _check_locales(operations: list[dict], current: dict, errors: list[str]) -> None:
    """Translations may only target locales the site already has (apply re-checks)."""
    languages = current.get("languages") or []
    for index, operation in enumerate(operations):
        for locale in operation.get("translations") or {}:
            if locale not in languages:
                errors.append(
                    f"block_operations[{index}].translations locale {locale} is not "
                    "enabled on the site; enabled: " + (", ".join(languages) or "none")
                )


def card_text_ref(block: dict, quest_id: str, field: str) -> tuple[str | None, str | None]:
    """Return (ref, localization id) of a card's editor text ref for ``field``.

    ``(None, None)`` when the card has no ref or the ref is dangling (its resource was
    deleted, so the block ignores it). ``(ref, None)`` when the resource exists but
    Shop Builder has not assigned it a localization id yet.
    """
    values = block.get("values") or {}
    overrides = (values.get("internalBlockValues") or {}).get("overrides") or {}
    entry = overrides.get(quest_id) if isinstance(overrides, dict) else None
    ref = entry.get(CARD_TEXT_REFS[field]) if isinstance(entry, dict) else None
    if not isinstance(ref, str) or not ref.startswith("L:"):
        return None, None
    resources = (values.get("resources") or {}).get("localizedValues") or {}
    if not isinstance(resources, dict) or ref not in resources:
        return None, None
    texts = (resources.get(ref) or {}).get("texts")
    text_id = texts.get("id") if isinstance(texts, dict) else None
    if not isinstance(text_id, str) or not text_id.startswith("L:"):
        return ref, None
    return ref, text_id


def _card_text_updates(operation: dict) -> list[tuple[str, str, str, object]]:
    """(key, quest id, field, text) for every title/description an update sets."""
    found = []
    if operation.get("op") != "update":
        return found
    for key, value in (operation.get("values") or {}).items():
        segments = split_key(key)
        if segments and segments[0] == "overrides" and segments[2] in CARD_TEXT_REFS:
            found.append((key, segments[1], segments[2], value))
    return found


def _check_card_refs(operations: list[dict], current: dict, errors: list[str]) -> None:
    """An editor text ref must have a localization id before an update can write it."""
    for index, operation in enumerate(operations):
        updates = _card_text_updates(operation)
        if not updates:
            continue
        block = find_block(current, operation["block_id"])[2]
        for key, quest_id, field, _ in updates:
            ref, text_id = card_text_ref(block, quest_id, field)
            if ref is not None and text_id is None:
                errors.append(
                    f"block_operations[{index}].values.{key}: the card's editor text "
                    "is not saved on the site yet; ask the publisher to open the site in "
                    "the Site Builder editor once, then back up again"
                )
            elif ref is not None and not current.get("languages"):
                errors.append(
                    f"block_operations[{index}].values.{key}: the site lists no "
                    "languages, so the card's editor text cannot be rewritten"
                )


def _check_indices(operations: list[dict], current: dict, errors: list[str]) -> None:
    """Bound every index against the page as it is when the op runs.

    Apply re-reads the live page before each op, so an earlier add or duplicate on the
    same page counts. The final index of a new block (added or copied) may be the
    current block count (the end of the page); a move stays inside the page.
    """
    counts: dict[object, int] = {}
    order_ops: dict[object, list[int]] = {}
    for index, operation in enumerate(operations):
        page_id = _op_page_id(operation, current)
        if page_id not in counts:
            page = next(
                (p for p in current.get("pages") or [] if p.get("_id") == page_id), {}
            )
            counts[page_id] = len(page.get("blocks") or [])
        if operation["op"] in ORDER_OPS:
            order_ops.setdefault(page_id, []).append(index)
        count = counts[page_id]
        prefix = f"block_operations[{index}]"
        op = operation["op"]
        if op in ("add", "duplicate"):
            position = operation.get("index")
            if position is not None and position > count:
                errors.append(
                    f"{prefix}.index {position} is past the end of the page "
                    f"({count} blocks when this op runs; the new block can go at 0 to {count})"
                )
            counts[page_id] = count + 1
        elif op == "move" and operation["index"] >= count:
            errors.append(
                f"{prefix}.index {operation['index']} is outside the page "
                f"({count} blocks when this op runs; use 0 to {count - 1})"
            )
    for index, operation in enumerate(operations):
        if operation["op"] != "duplicate" or "index" in operation:
            continue
        page_id = _op_page_id(operation, current)
        if len(order_ops.get(page_id, [])) > 1:
            errors.append(
                f"block_operations[{index}] duplicate needs an explicit index: another "
                "add, move or duplicate on the same page shifts blocks, so the default "
                "(right after the source in the backup) can be stale"
            )


def _check_conflicts(operations: list[dict], errors: list[str]) -> None:
    """Reject two ops that set or reset the same leaf of one block differently.

    Verification reads every planned leaf back, so update-then-reset of one leaf, or two
    updates of it with different values, would apply and then fail verification.
    """
    sets: dict[tuple, tuple[int, object]] = {}
    resets: dict[tuple, int] = {}
    texts: dict[tuple, tuple[int, object]] = {}

    def clash(first: int, second: int, block_id: str, what: str) -> None:
        errors.append(
            f"block_operations[{first}] and block_operations[{second}] conflict on "
            f"{block_id} {what}; keep one of them"
        )

    def overlaps(a: tuple, b: tuple) -> bool:
        shorter = min(len(a), len(b))
        return a[:shorter] == b[:shorter]

    for index, operation in enumerate(operations):
        block_id = operation.get("block_id")
        if operation["op"] not in ("update", "reset") or not isinstance(block_id, str):
            continue
        for key, value in (operation.get("values") or {}).items():
            segments = split_key(key)
            if (block_id, segments) in sets:
                first, earlier = sets[(block_id, segments)]
                if earlier != value:
                    clash(first, index, block_id, f"{key} (two different values)")
            else:
                sets[(block_id, segments)] = (index, value)
            for (reset_block, reset_segments), first in resets.items():
                if reset_block == block_id and overlaps(segments, reset_segments):
                    clash(first, index, block_id, f"{key} (reset and update)")
        for path in operation.get("paths") or []:
            segments = _reset_path(path)
            for (set_block, set_segments), (first, _) in sets.items():
                if set_block == block_id and overlaps(segments, set_segments):
                    clash(first, index, block_id, f"{path} (update and reset)")
            resets.setdefault((block_id, segments), index)
        for locale, entries in (operation.get("translations") or {}).items():
            for key, text in entries.items():
                slot = (block_id, locale, key)
                if slot in texts and texts[slot][1] != text:
                    clash(texts[slot][0], index, block_id, f"{key} ({locale}, two different texts)")
                texts.setdefault(slot, (index, text))


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
            position = operation.get("index", 0)
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
                card_texts = _card_text_item(index, block, page_id, operation, current)
                if card_texts:
                    items.append(card_texts)
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
                # Like the block's "Reset to quest content": drop the editor text ref
                # too, or it keeps winning over the quest's own text.
                if len(segments) == 3 and segments[2] in CARD_TEXT_REFS:
                    ref_segments = (*segments[:2], CARD_TEXT_REFS[segments[2]])
                    if _path_present(internal, ref_segments):
                        patches.append(
                            {
                                "op": "remove",
                                "key": ".".join(ref_segments),
                                "path": [*BLOCK_VALUES_ROOT, *ref_segments],
                                "present": True,
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
        else:
            items.append(
                {
                    "type": "block_visibility",
                    "op_index": index,
                    "block_id": block_id,
                    "page_id": page_id,
                    "hidden": op == "hide",
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


def _card_text_item(
    index: int, block: dict, page_id: object, operation: dict, current: dict
) -> dict | None:
    """Plan the editor text refs an update must rewrite so the new text shows."""
    texts = []
    for key, quest_id, field, value in _card_text_updates(operation):
        ref, text_id = card_text_ref(block, quest_id, field)
        if ref is None:
            continue
        texts.append(
            {
                "key": key,
                "ref_key": f"overrides.{quest_id}.{CARD_TEXT_REFS[field]}",
                "quest_id": quest_id,
                "field": field,
                "ref": ref,
                "text_id": text_id,
                "text": value,
            }
        )
    if not texts:
        return None
    return {
        "type": "block_card_text",
        "op_index": index,
        "block_id": operation["block_id"],
        "page_id": page_id,
        "locales": list(current.get("languages") or []),
        "texts": texts,
        "note": CARD_TEXT_NOTE,
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


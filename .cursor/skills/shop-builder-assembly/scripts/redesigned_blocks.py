#!/usr/bin/env python3
"""Shop Builder's redesigned blocks: their names, and the store's catalog sections.

A redesigned block is a federated block whose ``values.blockId`` starts with
``_site-builder-classic_``. Each one stands for a native module but keeps its data in
another shape: settings in ``values.internalBlockValues``, content in
``values.resources``. A name from the table says which block it is; it never makes a
native patch fit. Shop Builder has no schema for these blocks and takes any patch, so
every write here first checks that the block looks as expected.
"""

from __future__ import annotations

PREFIX = "_site-builder-classic_"
# The name after the prefix, and the native module that block stands for. Both heroes
# stand for the presets' hero: the default page comes with `lead-gs`, a store page with
# `lead`.
NATIVE_MODULES = {
    "header": "header",
    "lead": "leadGameSales",
    "lead-gs": "leadGameSales",
    "store": "newStore",
    "promocode": "promocodes",
    "faq": "faq",
    "footer-v3": "footer",
    "game-packs": "packs",
    "description": "description",
    "card-grid": "bento-grid",
    "gallery": "gallery",
    "system-requirements": "requirements",
    "news": "news",
    "reward-chains": "rewards",
    "sidebar": "sidebar",
    "sb-offer-chain": "sb-offer-chain",
    "sb-daily-reward": "sb-daily-reward",
    "offerwall": "offerwall-block",
}
STORE = PREFIX + "store"
# A catalog group's type in the plan, and the item type a store section's group holds.
STORE_ITEM_TYPES = {
    "virtual_good": "virtual-item",
    "virtual_currency": "virtual-currency-pack",
    "bundle": "bundle",
}
STORE_SECTIONS = ["values", "internalBlockValues", "storeSections"]
STORE_GROUPS = ["values", "resources", "store-group"]
UNKNOWN_STORE = "its sections aren't stored the way assembly knows"


def is_redesigned(module: object) -> bool:
    return isinstance(module, str) and module.startswith(PREFIX)


def logical_name(module: object) -> object:
    """Return the native module a redesigned block stands for, and any other name as is.

    A name with the prefix that isn't in the table stays as it is: nothing is known
    about that block.
    """
    if is_redesigned(module):
        return NATIVE_MODULES.get(module[len(PREFIX) :], module)
    return module


def has_twin(module: str) -> bool:
    """Whether a redesigned block stands for this native module."""
    return module in NATIVE_MODULES.values()


def _store_parts(block: dict) -> tuple[list, dict, dict] | None:
    """The section IDs, the sections and the catalog groups of a store, if it has the
    shape this module writes to."""
    values = block.get("values")
    values = values if isinstance(values, dict) else {}
    internal, resources = values.get("internalBlockValues"), values.get("resources")
    sections = internal.get("storeSections") if isinstance(internal, dict) else None
    groups = resources.get("store-group") if isinstance(resources, dict) else None
    if not isinstance(sections, dict) or not isinstance(groups, dict):
        return None
    ids, entities = sections.get("ids"), sections.get("entities")
    if not isinstance(ids, list) or not isinstance(entities, dict):
        return None
    references = []
    for section_id in ids:
        section = entities.get(section_id) if isinstance(section_id, str) else None
        if not isinstance(section, dict) or not isinstance(section.get("layout"), str):
            return None
        group = groups.get(section.get("group"))
        if not isinstance(group, dict) or not all(
            isinstance(group.get(key), str) for key in ("groupExternalId", "type")
        ):
            return None
        references.append(section["group"])
    if len(set(references)) != len(references):
        return None  # two sections on one group: a patch to one would change both
    return ids, entities, groups


def store_section_count(block: dict) -> int:
    parts = _store_parts(block)
    return len(parts[0]) if parts else 0


def store_problem(block: dict, sections: list[dict]) -> str | None:
    """Why the plan's catalog sections can't be set on this store, or None."""
    parts = _store_parts(block)
    if parts is None:
        return UNKNOWN_STORE
    if len(sections) > len(parts[0]):
        return (
            f"it has {len(parts[0])} section(s) and the plan has {len(sections)}; "
            "assembly can't add a section to it"
        )
    unknown = sorted({s["type"] for s in sections} - set(STORE_ITEM_TYPES))
    if unknown:
        return "assembly doesn't know the item type for " + ", ".join(unknown)
    return None


def store_sections(block: dict) -> list[tuple]:
    """Each section as (group, plan type, layout), like the plan lists them. A store
    with another shape has none, and an item type the plan can't name stays as it is."""
    parts = _store_parts(block)
    if parts is None:
        return []
    ids, entities, groups = parts
    plan_types = {item: name for name, item in STORE_ITEM_TYPES.items()}
    result = []
    for section_id in ids:
        group = groups[entities[section_id]["group"]]
        result.append(
            (
                group["groupExternalId"],
                plan_types.get(group["type"], group["type"]),
                entities[section_id]["layout"],
            )
        )
    return result


def store_section_patches(block: dict, sections: list[dict]) -> list[dict]:
    """Patches that point the store's first sections at the plan's catalog groups and
    drop the rest. Call only when ``store_problem`` returns None."""
    ids, entities, groups = _store_parts(block)
    patches = []
    for section_id, section in zip(ids, sections):
        reference = entities[section_id]["group"]
        wanted = {
            "groupExternalId": section["external_id"],
            "type": STORE_ITEM_TYPES[section["type"]],
        }
        for key, value in wanted.items():
            if groups[reference][key] != value:
                patches.append(
                    {"op": "replace", "path": [*STORE_GROUPS, reference, key], "value": value}
                )
        if entities[section_id]["layout"] != section["layout"]:
            patches.append(
                {
                    "op": "replace",
                    "path": [*STORE_SECTIONS, "entities", section_id, "layout"],
                    "value": section["layout"],
                }
            )
    if len(ids) > len(sections):
        patches.append(
            {"op": "replace", "path": [*STORE_SECTIONS, "ids"], "value": ids[: len(sections)]}
        )
        patches.extend(
            {"op": "remove", "path": [*STORE_SECTIONS, "entities", section_id]}
            for section_id in ids[len(sections) :]
        )
    return patches

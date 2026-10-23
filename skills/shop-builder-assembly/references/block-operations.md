# Quests block operations

Use this for a `block_operations` brief: single Quests blocks on an existing Shop Builder
site. The gate in [SKILL.md](../SKILL.md) applies: preflight, backup, plan, the plan's
`confirmation_id`, then `scripts/apply_plan.py`, which verifies on exit and touches only
the listed blocks. Brief fields are in [shop brief](shop-brief.md).

## Apply behaviour

`apply_plan.py` runs a confirmed operations plan item by item. Every step re-reads
`get-structure` for ids and indices; the plan's positions are never trusted. Before the
first write it compares the live structure with the backup (volatile component IDs
ignored) and stops if they differ.

Verification runs automatically at the end of an apply and reads every planned leaf back.
Known gap: a deleted block's id can remain in the landing `blocks[]` (the apply report
warns). Track it as a CLI/API gap; do not patch `blocks[]` by hand.

## Operations

| Op | Commands | Notes |
|---|---|---|
| `add` | `add-block --block federated [--index N]`, then `get-structure` for the new id, one `update-block`, one `update-block` for `devName`, optional `move-block` | Created bare, then retargeted to the Quests module from the pinned version's defaults. Index 0 omits the flag. |
| `update` values | `update-block` with leaf `replace` patches under `["values","internalBlockValues", ...]` | A missing parent object (`layout`, `overrides.<questId>`) is created with `add` of `{}` first, only when it is absent now: a leaf patch under a missing parent answers 200 and is ignored, and an `add` over an existing object would wipe it. Whole `values` are never patched. |
| `reset` | `update-block` with leaf `remove` patches | Skips leaves already absent. |
| `update` heading | `update-many-localization --slug <slug> --data '{"locale":"en-US","perScopeValues":{"<pageId>":{"L:<id>":{"translation":"..."}}}}'` | The `L:` id is `values.resources.localizedValues[<translations.heading>].texts.id`; the scope is the namespace of `get-localization` that holds it. The value key must be `translation`. Any other key writes an empty string. |
| `move` | `move-block --source <live index> --destination <index>` | The source index is looked up from the block id. |
| `duplicate` | `duplicate-block --blockid <id> [--index N]` | The copy gets its own `L:` texts. The copy id is found by re-reading the page. |
| `hide` / `show` | `update-block`, `replace ["hidden"]` | Same helper (`set_block_hidden`) as the Custom code hiding. |
| `delete` | `delete-block --landing-id --page-id --blockid <id> --force` | Only for Quests blocks listed under `removals` in the confirmed plan, while the block is still on its page. Do not run a page-scoped `removeBlocks` patch first; it detaches the block but leaves it in the landing block list. |

## Quests block contract

- Wrapper: `federated`, `values.blockId` `_quest-platform_quests-block`
  (CDN-verified), `useAsNativeBlock: false`. The npm name `@quest-platform/quests-block`
  is stored with `@` and `/` replaced by `_`.
- Pinned build: the package version in `scripts/block_ops.py` (`QUESTS_VERSION`).
  Add strategy: `federated_patch`. `add-block --block federated` creates an empty wrapper
  at index 0 (omit `--index`), then one `update-block` sets `host`, `blockId`, `version`,
  `useAsNativeBlock` and `internalBlockValues` from the CDN `default-data.json`; the
  server mints the default `L:` texts. Adding by template name returns HTTP 500, so there
  is no palette template.
- Patchable leaves, all under `["values","internalBlockValues", ...]`: `questIds`,
  `maxQuests`, `overrides.<questId>.{title,description,imageUrl,imageRef,rewardText,rewardImageUrl}`,
  `layout.{showHeading,showDescription,showImage,cardAlign,imageFit,buttonStyle,blockBackground,cardBackground}`
  and `editorPreview`. The heading is the `L:` text at `translations.heading`; change it
  with localization commands.
- `rewardText` (string, at most 120 characters) and `rewardImageUrl` (absolute https URL,
  same check as `imageUrl`) are normal override fields. `reset` removes either one.
- Quest ids (in `questIds`, in `overrides.<questId>` keys and in reset paths) must be
  Quest Platform quest UUIDs. Preflight rejects any other string before a plan is made.
- A leaf patch into a missing parent (for example `layout`) returns 200 and is silently
  ignored, so create the parent object first.
- A page `removeBlocks` patch leaves the block orphaned in the landing; a real delete
  needs `delete-block --force` while the block is still on the page, for blocks named in
  the confirmed plan only.

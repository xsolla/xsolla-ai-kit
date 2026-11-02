# Quests block operations

Use this for a `block_operations` brief that targets Quests blocks on an existing Shop
Builder site. Run preflight and create a verified backup, then render with
`scripts/render_plan.py --structure <backup>/structure.json`. Save that plan as
`approved-plan.json` and apply it with both `--approved-plan approved-plan.json` and its
`--confirmation-id`. Do not pass `--run-report`; operations are a single confirmed run.
The current assembly entrypoint verifies the saved result and touches only the listed
blocks. If preflight recorded a sandbox switch, run
`scripts/restore_sandbox.py` when the run ends or stops. Brief fields are in
[shop brief](shop-brief.md).

## Apply behaviour

`apply_plan.py` runs a confirmed operations plan item by item. Every step re-reads
`get-structure` for ids and indices; the plan's positions are never trusted. Before the
first write it compares the live structure with the backup (volatile component IDs
ignored) and stops if they differ.

Block operations run on sites created from a Publisher Account template too (the header
lives in the common layout). They never touch the header, so the template-header stop
that guards a build does not apply. See Known limitations in [SKILL.md](../SKILL.md).

Verification runs automatically at the end of an apply and reads every planned leaf back.

No script passes `--force`, and no script deletes a block. `delete-block` asks for
confirmation and the only way past that prompt without a terminal is `--force`. A brief
with a `delete` op fails validation: answer `needs_human` (the publisher deletes the block
in the Site Builder editor) and offer `hide` as the scripted alternative.

## Planning checks

The plan runs against the backup structure and rejects these before confirmation:

- A `translations` locale the site does not have yet (`languages` in the backup). Apply
  re-checks it against the live site as a backstop. Add the locale first.
- An index outside the page as it is when the op runs. Earlier `add` and `duplicate`
  ops on the same page count. The final index of an added block or a copy may be 0 to
  the current block count (the end of the page). A `move` index is 0 to count - 1.
- A `duplicate` without `index` when another `add`, `move` or `duplicate` touches the
  same page. The default index (right after the source) comes from the backup and can be
  stale after one of those. Give the index explicitly.
- Two ops on one block that disagree about a leaf: an `update` and a `reset` of the
  same leaf (or of its `overrides.<questId>` parent), two `update`s of one leaf with
  different values, or two different headings for one locale. Verification reads every
  leaf back, so such a brief would apply and then fail. Keep one of the ops.
- `imageUrl` with user credentials in the URL (`user:pw@host`).
- Any `update` or `reset` of `overrides.<questId>.rewardText` or
  `overrides.<questId>.rewardImageUrl`. The reward comes from the quest and is read-only
  on the block.

## Operations

| Op | Commands | Notes |
|---|---|---|
| `add` | `add-block --block federated [--index N]`, then `get-structure` for the new id, one `update-block`, one `update-block` for `devName`, optional `move-block` | Created bare, then retargeted to the Quests module from the pinned version's defaults. Index 0 omits the flag. |
| `update` values | `update-block` with leaf `replace` patches under `["values","internalBlockValues", ...]` | A missing parent object (`layout`, `overrides.<questId>`) is created with `add` of `{}` first, only when it is absent now: a leaf patch under a missing parent answers 200 and is ignored, and an `add` over an existing object would wipe it. Whole `values` are never patched. |
| `update` card title/description over an editor ref | `update-block` for the plain field, then `update-many-localization` per site locale, `{"<scope>":{"L:<id>":{"translation":"..."}}}` | The `L:` id is `values.resources.localizedValues[<overrides.<questId>.titleRef>].texts.id` (or `descriptionRef`); the scope is found as for the heading. |
| `reset` | `update-block` with leaf `remove` patches | Skips leaves already absent. A title or description reset also removes its `titleRef` / `descriptionRef`. |
| `update` heading | `update-many-localization --slug <slug> --data '{"locale":"en-US","perScopeValues":{"<pageId>":{"L:<id>":{"translation":"..."}}}}'` | The `L:` id is `values.resources.localizedValues[<translations.heading>].texts.id`; the scope is the namespace of `get-localization` that holds it. The value key must be `translation`. Any other key writes an empty string. |
| `move` | `move-block --source <live index> --destination <index>` | The source index is looked up from the block id. |
| `duplicate` | `duplicate-block --blockid <id> [--index N]` | The copy gets its own `L:` texts. The copy id is found by re-reading the page. |
| `hide` / `show` | `update-block`, `replace ["hidden"]` | Same helper (`set_block_hidden`) as the Custom code hiding. |

## Quests block contract

- Wrapper: `federated`, `values.blockId` `_quest-platform_quests-block`
  (CDN-verified), `useAsNativeBlock: false`. The npm name `@quest-platform/quests-block`
  is stored with `@` and `/` replaced by `_`.
- Ordinary creation pin: the package version in `scripts/block_ops.py` (`QUESTS_VERSION`),
  currently stable `0.1.5`.
  Add strategy: `federated_patch`. `add-block --block federated` creates an empty wrapper
  at index 0 (omit `--index`), then one `update-block` sets `host`, `blockId`, `version`,
  `useAsNativeBlock` and `internalBlockValues` from the CDN `default-data.json`; the
  server mints the default `L:` texts. Adding by template name returns HTTP 500, so there
  is no palette template.
- Patchable leaves, all under `["values","internalBlockValues", ...]`: `questIds`,
  `maxQuests`, `overrides.<questId>.{title,description,imageUrl,imageRef}`,
  `layout.{showHeading,showDescription,showImage,cardAlign,imageFit,buttonStyle,blockBackground,cardBackground}`
  and `editorPreview`. The heading is the `L:` text at `translations.heading`; change it
  with localization commands.
- The reward text and reward image are read-only (product decision, 26 Oct 2026). They
  come from the quest definition, so `rewardText` and `rewardImageUrl` are not patchable
  leaves: preflight rejects any `update` or `reset` that names them with "the reward
  text and reward image come from the quest and can't be changed". To change a reward,
  edit the quest itself (`quest-setup`). Card title, description and image stay editable.
- The Site Builder editor stores card text as a localized ref
  (`overrides.<questId>.titleRef`, `descriptionRef`), seeded the first time it opens and
  changed by double-clicking a card. A ref whose resource exists wins over the plain
  `title` and `description`. The latest change wins (PRD open question 14): when the
  backup shows a ref for a card whose title or description an `update` sets, the plan
  adds a `block_card_text` item and a `warnings` line saying the text replaces the one
  set in the editor. Apply writes the plain field and the same text into the ref's
  localization for every site locale; verification reads both back. A dangling ref (no
  resource) is ignored, as the block ignores it. A ref with no localization id yet fails
  planning: the publisher opens the site in the editor once, then back up again.
- A `reset` of `overrides.<questId>.title` or `.description` also removes the matching
  ref, as the block's "Reset to quest content" does; the editor seeds it again from the
  quest text next time it opens.
- Quest ids (in `questIds`, in `overrides.<questId>` keys and in reset paths) must be
  Quest Platform quest UUIDs. Preflight rejects any other string before a plan is made.
- A leaf patch into a missing parent (for example `layout`) returns 200 and is silently
  ignored, so create the parent object first.

## Appearance and Backpack action capability

Ordinary `add` keeps using the stable creation pin `0.1.5`. An `add` operation may
select a different artifact only through its explicit `version` field. The only verified
candidate capability currently enabled is `0.2.4-qp-3256.0`; this is candidate-only
support, not a stable-version claim. Updates and resets that use these fields require the
target block's exact `values.version` to match that candidate. No other version is
accepted by inference.

The candidate artifact defaults `themeId` to `site-builder` and `backpackAction` to
`external`; `themeAppearance` is optional and stored as an open map. The operation paths
below it are therefore leaf patches under `values.internalBlockValues`.

On that candidate, the gate accepts the `themeId` values `site-builder`, `xsolla-pages`
and `custom`, the existing per-preset leaves under
`themeAppearance.site-builder.*` / `themeAppearance.xsolla-pages.*`, and Custom V1
leaves under `themeAppearance.custom`. Custom is an open saved map, but the gate allows
only these known leaf paths: `version`, `baseThemeId`, the palette colors, the typography
font/size/weight/line-height fields and the geometry fields. It never replaces the whole
map. A new Custom map needs `version: 1` and a `baseThemeId` (`site-builder` or
`xsolla-pages`) in the same operation before appearance leaves can be written. Existing
unknown fields and other theme entries survive leaf updates and resets. Reset removes
known palette/type/geometry override leaves only; it cannot remove `version`,
`baseThemeId`, `themeId`, a Custom parent or the whole appearance map.

Palette values must be literal `#RRGGBB` colors. Typography weights are 400, 500, 600 or
700; line heights are finite values from 1 to 2 and are rounded to two decimal places
using JavaScript rounding. Sizes and geometry use the adaptation contract's bounds.
Font choices are `host-body`, `host-heading`, `host-button`, or a `{"loadedFont": "..."}`
object containing a 1-64 character safe family name. This syntax check does not
prove that a font is loaded. Before proposing a `loadedFont`, inspect the target site's
actual loaded-font evidence; otherwise use a host font token or inherit the base. If both
`actionText` and `accent` are explicit, the pair must reach 4.5:1 contrast. Omitting
`actionText` leaves the block's safe derived-color behavior in control.

The candidate also supports the flat `backpackAction` leaf, `external` or `overlay`.
Omission and reset use the artifact default, `external`. The older nested
`backpackOverlay` shape and any host ID, loader, authentication, bootstrap or owner lease
field are not accepted. Selecting `overlay` only chooses the Quests action. Installation,
controller readiness and authentication belong to the independent owner procedure, not
this Quests mutation gate.

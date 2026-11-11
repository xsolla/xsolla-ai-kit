# Quests block operations

Use this for a `block_operations` brief that targets Quests blocks on an existing Shop
Builder site. Run preflight and create a verified backup, then render with
`scripts/render_plan.py --structure <backup>/structure.json`. Save that plan as
`approved-plan.json` and apply it with both `--approved-plan approved-plan.json` and its
`--confirmation-id`. Do not pass `--run-report`; operations are a single confirmed run.
The current assembly entrypoint verifies the saved result and touches only the listed
blocks. Brief fields are in [shop brief](shop-brief.md).

## Operation plan confirmation

For `block_operations`, show the rendered target site and each operation in plain words
(which quests and in what order, card limit, heading, card text, alignment, button,
background). Never show brief keys, leaf paths, quest IDs, created parents, `plan_notes`
or the confirmation ID: the agent passes `confirmation_id` from the saved plan to apply.
When quest-setup drives the gate, its reply-format rules apply.
Never fabricate or reuse another plan's ID. End the turn for a later yes to this exact
plan; earlier source requests or sandbox confirmation do not authorize apply.

## Apply behaviour

Apply binds to the verified backup and stops before writing if live structure changed
(volatile component IDs ignored). Positions/IDs are resolved from the current site.

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

| Op | Effect |
|---|---|
| `add` | Create a federated Quests wrapper from the pinned version's defaults. Shop Builder gives each default text an `L:` id but saves no text, so apply then writes every default text (heading, statuses, buttons, pagination) for each enabled locale the defaults have, and fails the run if any reads back empty. Needs at least one quest in `questIds`: a block with no cards renders nothing outside the editor. Default index is 0; explicit index chooses the position. |
| `seed_texts` | Write a block's empty default texts again, for a block whose add failed while saving them. Never adds a block and never overwrites a saved text; a text that was cleared on purpose gets its default back, and the plan says so. The default texts exist in en-US only, so the block's texts in other site languages stay empty; an `add` on a site without en-US is refused at plan time. |
| `update` values | Replace named leaves only. Create an absent parent object first, never overwrite an existing parent or whole values map. A leaf under a missing parent can return 200 while being ignored. |
| `update` title/description | Update the plain field and any valid editor localization ref for every site locale; warn that editor text is replaced. |
| `reset` | Remove selected leaves, skip absent ones; title/description reset also removes its matching ref. |
| `update` heading | Change the localized heading for the requested enabled locales. |
| `move` | Move the identified block to the requested current page index. |
| `duplicate` | Copy the block, with its own localized texts; read back the new copy/position. |
| `hide` / `show` | Set only the block's `hidden` state. |

Remaining operation forms (the add/update/reset examples are in [shop brief](shop-brief.md#operation-mode-block_operations-quests-block-only)):

```json
{"op":"move","block_id":"<id>","index":0}
{"op":"duplicate","block_id":"<id>","index":3}
{"op":"hide","block_id":"<id>"}
{"op":"show","block_id":"<id>"}
```

Localization payloads use `{"<scope>":{"L:<id>":{"translation":"..."}}}`. Heading form:
`{"locale":"en-US","perScopeValues":{"<pageId>":{"L:<id>":{"translation":"..."}}}}`.
Only `translation` writes text; another key writes an empty string. Resolve heading IDs
from `values.resources.localizedValues[<translations.heading>].texts.id`, and card IDs
from `values.resources.localizedValues[<overrides.<questId>.titleRef>].texts.id` (or
`descriptionRef`); the scope is the localization namespace holding that ID.

## Quests block contract

- Wrapper: `federated`, `values.blockId` `_quest-platform_quests-block`
  (CDN-verified), `useAsNativeBlock: false`. The npm name `@quest-platform/quests-block`
  is stored with `@` and `/` replaced by `_`.
- Creation uses `federated_patch` with CDN `default-data.json`, not a palette template
  (template-name add returns HTTP 500). The version is below. A block release
  requires changing `QUESTS_VERSION` and quest-setup `block-versions.md` together.
- Patchable leaves, all under `["values","internalBlockValues", ...]`: `questIds`,
  `maxQuests`, `overrides.<questId>.{title,description,imageUrl,imageRef}`,
  `layout.{showHeading,showDescription,showImage,cardAlign,imageFit,buttonStyle,blockBackground,cardBackground}`
  and `editorPreview`. The heading is the `L:` text at `translations.heading`; change it
  with localization commands.
- Reward text/image come from the quest and are read-only: `rewardText` and
  `rewardImageUrl` update/reset are rejected. Edit the quest to change rewards;
  card title/description/image remain editable.
- Editor card text refs (`overrides.<questId>.titleRef` / `descriptionRef`) are seeded
  on first editor open. An existing resource ref wins over plain text. Updating text
  updates both representations for every site locale, adds a `block_card_text` plan
  item and a replacement warning, and verifies both. Dangling refs are ignored; a ref
  with no localization ID fails planning, requiring one editor open then a fresh backup.
  Reset removes the matching ref; the editor next seeds it from quest content again.
- Quest ids (in `questIds`, in `overrides.<questId>` keys and in reset paths) must be
  Quest Platform quest UUIDs. Preflight rejects any other string before a plan is made.

## Appearance capability

The gate writes and accepts one Quests version, `QUESTS_VERSION` (`0.2.22`). Every add
uses it, with or without an explicit `version`. Appearance update/reset requires the
target's saved `values.version` to be that version; any other saved version is refused
for appearance. No operation changes an existing block's version; duplicate preserves it.
On an older block, offer only a new block with the same quests and hide the old one under
its own plan/yes. A new block gets `visibleGameSlugs: []` (the CDN default carries an
Xsolla demo game); never write `gameSlug` or `visibleGameSlugs` otherwise.

The verified artifacts default `themeId` to `site-builder` and use an
optional open `themeAppearance` map. The operation paths below it are leaf patches under
`values.internalBlockValues`.

On those pins, the gate accepts the `themeId` values `site-builder`, `xsolla-pages`
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

Older saved action-looking fields are opaque legacy data: never expose, interpret,
configure or delete them. Leaf updates and resets leave them untouched.

# Quests block brief

Brief keys, settings and operations for the `block_operations` brief that the
`shop-builder-assembly` gate validates. The agent never shows these keys to the publisher.
Appearance recommendations and fitting rules are in
[quests-block-appearance.md](quests-block-appearance.md). Appearance leaves are
supported only on block versions that
[block-versions.md](block-versions.md) lists as supporting them. Existing
block appearance updates and resets require an exact saved-version match.

## Block settings

Patch single leaves only, never a whole object. The plan maps each key to the
block's real path and creates a missing parent object (for example `layout`) first.

| Brief key | Allowed values | Default | What it does |
|---|---|---|---|
| `questIds` | list of unique quest UUIDs (the `id` from the quest list), at most 24 | empty | Which quests show, in display order. Changing the order is a `questIds` update. |
| `maxQuests` | whole number 1 to 24 | `6` | How many cards show at most. |
| `layout.showHeading` | `true` or `false` | `true` | Heading above the cards |
| `layout.showDescription` | `true` or `false` | `true` | Description on each card |
| `layout.showImage` | `true` or `false` | `true` | Image on each card |
| `layout.cardAlign` | `start`, `center`, `end` | `start` | Card alignment |
| `layout.imageFit` | `cover`, `contain` | `cover` | How the image fills its frame |
| `layout.buttonStyle` | `primary`, `secondary`, `tertiary` | `primary` | Card button style |
| `layout.blockBackground` | `transparent`, `primary`, `secondary` | `transparent` | Background behind the whole block |
| `layout.cardBackground` | `transparent`, `primary`, `secondary` | `secondary` | Background of each card |
| `themeId` | `site-builder`, `xsolla-pages`, `custom` | artifact default | Appearance preset for this Quests block only |
| `themeAppearance.site-builder.*` / `themeAppearance.xsolla-pages.*` | `cardAlign`, `blockBackground`, `cardBackground`, `buttonStyle` values listed in [appearance](quests-block-appearance.md) | inherited | Bounded appearance overrides for the selected preset |
| `themeAppearance.custom.*` | Custom V1 fields and bounds in [appearance](quests-block-appearance.md) | omitted values inherit | Measured, block-scoped appearance overrides |
| `overrides.<questId>.title` | text, at most 120 characters | none | Replaces that card's title |
| `overrides.<questId>.description` | text, at most 400 characters | none | Replaces that card's description |
| `overrides.<questId>.imageUrl` | absolute `https` URL | none | Replaces that card's image |
| `overrides.<questId>.imageRef` | image reference from the site's media library | none | Same, from the media picker |
| heading (`translations`) | text per locale, under the key `heading` | `Quests` in `en-US` | The block's heading, localized |

Notes:

- `<questId>` in every `overrides.<questId>` key is the quest UUID, the `id` from the
  quest list, the same value as in `questIds`.
- Overrides are plain strings, are not localized, and win over the quest's own view.
  Prefer fixing the quest's `public_view`. Overrides stay on the block when a quest
  is removed from `questIds`.
- The latest change wins. If the card's title or description was already set in the
  Site Builder editor (the editor also seeds it the first time it opens), an `update`
  of `overrides.<questId>.title` or `.description` replaces that text: the gate writes
  the new text there for every site locale and reads it back. The rendered plan's
  `warnings` say so. A `reset` of the title or description also clears the editor text,
  so the card shows the quest's own text again.
- The heading goes in `translations` of the operation, never in `values`. Only the
  key `heading` is accepted.
- The reward text and reward image on a card are not block settings. They come from
  the quest's reward and can't be changed on the block. To change them, change the
  quest's reward.
- Hiding the whole block is the `hide` operation. There is no other visibility
  toggle beyond the three `layout.show*` settings.

## Block contract (facts for every write)

Source: the block contract at commit 0b1586eb59. Version pins live only in
[block-versions.md](block-versions.md).

- `themeId` is `site-builder`, `xsolla-pages` or `custom`. `themeAppearance` leaves are keyed by preset (valid for that preset); `custom` is sent only when `themeId` is custom.
  The preset-keyed leaves under `site-builder` and `xsolla-pages` are listed in the table above.
- `questIds` absent means the block never had a selection and the editor fills it once, while `questIds` set to `[]` means the publisher cleared it and it is never refilled.
- `overrides` images are https only; reward overrides are ignored.
- Versions and event-field capabilities belong to [block-versions.md](block-versions.md).
  Never write `autoEvents` or `loginEventName`; match the trigger name exactly.
  Backpack Overlay is not supported yet (agent-only reason: upstream v2): decline it with
  the [overlay decline](reply-format.md#examples) and make no write.
- Custom-block creation 403: account lacks permission to create custom blocks;
  Xsolla support is next. Do not retry or create a file.

### Theme selector

Map the publisher's words to `themeId`: default or the site's own look maps to site-builder, Xsolla Pages maps to xsolla-pages, and a fully custom design maps to custom. For the first two, do not send the custom entry; only the preset-keyed leaves in [quests-block-appearance.md](quests-block-appearance.md) apply.

### Fully custom design

Use [the custom design workflow](quests-block-appearance.md#fully-custom-design) for
brand inputs, bounds, limitations and the publisher's choice before a write.

## Operations

Operations go in the brief's `block_operations` list and run in order. The brief
needs `version`, `project` (`merchant_id`, `project_id`, integers; numeric strings are
accepted and converted),
`site.slug` and `block_operations`. Nothing else is
allowed: the gate rejects any other top-level key (`game`, `catalog`, `content`,
`brand`, `sources`), any other `project` key and any `site` key but `slug`. Fill real
values from the conversation and the backup, never from memory. There is no
acknowledgement flag.

```json
{
  "version": 1,
  "project": {"merchant_id": 1, "project_id": 2},
  "site": {"slug": "<site-slug>"},
  "block_operations": [ ...operations below... ]
}
```

| Goal | Operation |
|---|---|
| Create a block | `add` |
| Edit settings, texts, heading, order or limit | `update` |
| Drop a card's text or image override | `reset` |
| Reposition the block on its page | `move` |
| Copy a block | `duplicate` |
| Hide or show a block | `hide`, `show` |
| Remove or delete a block | none: `needs_human`, offer `hide` (see below) |

Every new block, themed or not, is added with an explicit `version` equal to the one in
[block-versions.md](block-versions.md) (`0.2.22`).

Create a block with settings and a heading:

```json
{"op": "add", "module": "_quest-platform_quests-block", "page": "/", "index": 2,
 "version": "0.2.22",
 "values": {"questIds": ["<quest-id-1>", "<quest-id-2>"], "maxQuests": 4,
            "layout.cardAlign": "center"},
 "translations": {"en-US": {"heading": "Quests"}}}
```

Edit settings (limit, order, layout, one card's text):

```json
{"op": "update", "block_id": "<block-id>",
 "values": {"maxQuests": 3, "questIds": ["<quest-id-2>", "<quest-id-1>"],
            "layout.showImage": false,
            "overrides.<quest-id-1>.title": "Daily challenge"}}
```

Heading-only variant of `update`: omit `values` and set
`"translations": {"en-US": {"heading": "Today's quests"}}`.

Reset media or text overrides (paths are `overrides.<questId>.<field>` leaves, or a
whole `overrides.<questId>`, where `<questId>` is the quest UUID):

```json
{"op": "reset", "block_id": "<block-id>",
 "paths": ["overrides.<quest-id-1>.imageUrl", "overrides.<quest-id-1>.imageRef"]}
```

Move, duplicate, hide, show:

```json
{"op": "move", "block_id": "<block-id>", "index": 0}
{"op": "duplicate", "block_id": "<block-id>", "index": 3}
{"op": "hide", "block_id": "<block-id>"}
{"op": "show", "block_id": "<block-id>"}
```

## Gate commands

Run these exactly, each from the publisher's folder (never `cd` into a skill folder: the
Quest Platform credential is read from the working folder). Do not run `--help`, read
the gate's scripts or docs, or edit CLI config yourself, except the sandbox switch in
step 3. `G` is `<skill base dir>/../shop-builder-assembly/scripts`.

1. Ids: run the block summary from [Describe the block](quests-block-flow.md#describe-the-block).
   It gives `merchant_id`, `project_id`, each block's `block_id` and each card's
   `quest_id`, in block order. Never show these ids to the publisher.
2. Run `mktemp -d` once and reuse the printed path `W`. Write the brief to `W/brief.json`.
3. Run `python3 "G/preflight.py" "W/brief.json"`.
   If it stops with "CLI sandbox mode is on", do not switch it yet: this needs its own
   yes, separate from the plan's. Reply with the exact command,
   `xsolla config set sandbox false`, and the folder it runs from (the one that holds
   the config `xsolla config list` reads), and one clause: the CLI stays on the live
   project until it is switched back with `xsolla config set sandbox true`. End the turn. Only after a yes
   to that exact command and folder, run it there and rerun preflight. That yes covers
   the switch only; nothing is written to the site before the plan's own yes.
   When preflight returns `cli_environment`, add `--environment <name>` to read-only
   `xsolla shopbuilder` commands; this named environment does not change global config.
4. `python3 "G/backup_shop.py" --brief "W/brief.json" --slug <slug> --output-dir "W/backup"`
5. Render and save the target-bound plan:
   `python3 "G/render_plan.py" "W/brief.json" --structure "W/backup/structure.json" > "W/approved-plan.json"`.
   Show the plan in plain words (Plan shape in [reply-format.md](reply-format.md)), never
   its keys, `confirmation_id` or `plan_notes`, then end the turn.
6. After a later "yes":
   `python3 "G/apply_plan.py" "W/brief.json" --approved-plan "W/approved-plan.json" --confirmation-id <id> --backup-dir "W/backup"`,
   with `<id>` read from `confirmation_id` in `W/approved-plan.json`.
   This is one confirmed operations run: do not pass `--run-report`. Apply verifies
   saved leaves and block preservation, then prints `editor_url`.
7. The sandbox switch from step 3, if you made one, stays on the CLI config. Nothing
   switches it back: end the final reply's bullets with the undo command only.

If apply says the target structure changed after backup, someone edited the site
meanwhile and nothing was written: run steps 4 and 5 again with a new backup folder, say
the site changed in the meantime, and show the new plan for a new "yes".

### Rules for every operation

- Keys not in the settings table are rejected by the gate. Never invent one. Never set
  `editorPreview`: the gate accepts it, but it is an editor-only key.
- Quest references are quest UUIDs, the `id` from the quest list: every `questIds`
  entry, every `overrides.<questId>` key and every `reset` path. Never use a quest name,
  slug or position.
- `maxQuests` below 1 or above 24 gets one refusal line that names only the range, 1 to 24. Never offer to hide the block instead.
- Ask for all missing inputs in one message. If the gate rejects the brief, fix the brief
  and render again without telling the publisher. Only a rejection of the publisher's own
  value (out of range, a non-https image, a language the site lacks) gets one plain
  sentence on what to change. Never quote gate output.
- Rejected values use [the rejected-value reply](reply-format.md#examples), without
  repeating the value.
- Image URLs (`imageUrl`, `image_url`) must be `https`
  and must not carry user credentials (`user:password@host`). If the publisher gives an
  `http` URL or one with credentials, stop with the rejected-value shape before any plan
  or brief. Never change http to https or otherwise modify a URL the publisher gave, and
  never build a plan with it. Ask for an https image URL or a media library image instead.
- `index` is a position on the page, counted from 0, against the page as it is when
  that operation runs: earlier `add` and `duplicate` ops on the same page count. `add`
  and `duplicate` take 0 to the current block count (the count is the end of the page);
  `move` takes 0 to count - 1. Anything larger is rejected. An `add` without `index`
  puts the block first on the page. Reordering cards is an `update` of `questIds`;
  `move` repositions the whole block.
- A `duplicate` needs an explicit `index` when another `add`, `move` or `duplicate`
  touches the same page in the brief.
- One leaf, one outcome: never `update` and `reset` the same leaf (or its
  `overrides.<questId>` parent), set one leaf twice with different values, or give two
  headings for one locale in one brief. Keep one of them.
- `translations` locales must already be enabled on the site (`languages` in the
  backup). For another language, reply in the localized-texts shape from
  [reply-format.md](reply-format.md).
- The gate touches only the blocks listed. Every other block must read back unchanged.
- Delete requests use [Removing the block](quests-block-flow.md#removing-the-block):
  `needs_human`, no delete plan or `--force`, and a separately approved hide alternative.

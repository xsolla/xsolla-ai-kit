# Quests block brief

Brief keys, settings and operations for the `block_operations` brief that the
`shop-builder-assembly` gate validates. The agent never shows these keys to the publisher.

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
| `overrides.<questId>.title` | text, at most 120 characters | none | Replaces that card's title |
| `overrides.<questId>.description` | text, at most 400 characters | none | Replaces that card's description |
| `overrides.<questId>.imageUrl` | absolute `https` URL | none | Replaces that card's image |
| `overrides.<questId>.imageRef` | image reference from the site's media library | none | Same, from the media picker |
| `overrides.<questId>.rewardText` | plain text, at most 120 characters | none | The card's reward line text |
| `overrides.<questId>.rewardImageUrl` | absolute `https` URL | none | The reward icon on the card. Never invent one |
| heading (`translations`) | text per locale, under the key `heading` | `Quests` in `en-US` | The block's heading, localized |

Notes:

- `<questId>` in every `overrides.<questId>` key is the quest UUID, the `id` from the
  quest list, the same value as in `questIds`.
- Overrides are plain strings, are not localized, and win over the quest's own view.
  Prefer fixing the quest's `public_view`. Overrides stay on the block when a quest
  is removed from `questIds`.
- The heading goes in `translations` of the operation, never in `values`. Only the
  key `heading` is accepted.
- Hiding the whole block is the `hide` operation. There is no other visibility
  toggle beyond the three `layout.show*` settings.

## Operations

Operations go in the brief's `block_operations` list and run in order. The brief
needs `version`, `project` (`environment: test`, `test_project_acknowledged: true`,
`merchant_id`, `project_id`), `site.slug` and `block_operations`. It does not need
`game`, `catalog` or `content`. Fill real values from the conversation and the
backup, never from memory. Set `test_project_acknowledged` only when the publisher said in
this conversation that the project is a dedicated test project (see Hard rule 2 in
[quests-block-flow.md](quests-block-flow.md)).

```json
{
  "version": 1,
  "project": {"environment": "test", "test_project_acknowledged": true,
              "merchant_id": 1, "project_id": 2},
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
| Remove a block | `delete` |

Create a block with settings and a heading:

```json
{"op": "add", "module": "_quest-platform_quests-block", "page": "/", "index": 2,
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

Change only the heading:

```json
{"op": "update", "block_id": "<block-id>",
 "translations": {"en-US": {"heading": "Today's quests"}}}
```

Reset media or text overrides (paths are `overrides.<questId>.<field>` leaves, or a
whole `overrides.<questId>`, where `<questId>` is the quest UUID):

```json
{"op": "reset", "block_id": "<block-id>",
 "paths": ["overrides.<quest-id-1>.imageUrl", "overrides.<quest-id-1>.imageRef"]}
```

Move, duplicate, hide, show, delete (delete needs its own yes, Hard rule 4):

```json
{"op": "move", "block_id": "<block-id>", "index": 0}
{"op": "duplicate", "block_id": "<block-id>", "index": 3}
{"op": "hide", "block_id": "<block-id>"}
{"op": "show", "block_id": "<block-id>"}
{"op": "delete", "block_id": "<block-id>"}
```

### Rules for every operation

- Keys not in the settings table are rejected by the gate. Never invent one. Never set
  `editorPreview`: the gate accepts it, but it is an editor-only key.
- Quest references are quest UUIDs, the `id` from the quest list: every `questIds`
  entry, every `overrides.<questId>` key and every `reset` path. Never use a quest name,
  slug or position.
- `maxQuests` below 1 or above 24 gets one refusal line that names only the range, 1 to 24. Never offer to hide the block instead.
- Ask for all missing inputs in one message. If the gate rejects the brief, relay its
  full error list in one reply, fix the brief and render again.
- When a publisher value is rejected (for example an image URL that is not https), do
  not repeat the value. Use the rejected-value shape: a bold line that says what is
  required, for example "**The reward icon needs an https link.**", then `Next:` asking
  for an https image URL.
- Image and reward icon URLs (`imageUrl`, `rewardImageUrl`, `image_url`) must be `https`.
  If the publisher gives an `http` URL, stop with the rejected-value shape before any plan
  or brief. Never change http to https or otherwise modify a URL the publisher gave, and
  never draft a plan with it. Ask for an https image URL or a media library image instead.
- `index` is a position on the page, counted from 0. An `add` without `index` puts the
  block first on the page. For the end of the page, set `index` to the page's current
  block count from the backup; a larger `index` is rejected. Reordering cards is an
  `update` of `questIds`; `move` repositions the whole block.
- The gate touches only the blocks listed. Every other block must read back unchanged.
- A deleted block's id may stay in the site's top-level block list, which the apply
  report shows as a warning. This is a known CLI gap; do not fix it by hand.

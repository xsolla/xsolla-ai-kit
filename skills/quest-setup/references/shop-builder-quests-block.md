# Quests block in Shop Builder

Manages the native **Quests** block on an unpublished **Shop Builder** site, so
the site shows quest cards to anonymous visitors and progress to signed-in
players. Create, edit, reorder, limit, reset, move, duplicate, hide, show and
delete are all done the same way: build a `block_operations` brief and hand it
to the `shop-builder-assembly` gate. For a **headless** storefront use
[`web-shop-module.md`](web-shop-module.md) instead.

This flow depends on the `shop-builder-assembly` skill, in a version that
supports `block_operations` briefs (xsolla/xsolla-ai-kit#87, a runtime
dependency of this reference). It uses that skill's safety gate and scripts as
they are; do not restate or bypass them. If the skill is not available in the
session, or its brief reference has no `block_operations` section, stop and
report that; never fall back to running `xsolla shopbuilder` write commands
without the gate.

Triggers: "add the Quests block to my Shop Builder site", "show quests in my
Shop Builder shop", "quests section in Site Builder", "change which quests the
block shows", "hide the quests block", "remove the Quests block".

## Hard rules

1. **Only the `xsolla shopbuilder` CLI** (version 1.9.4 or newer), driven by the
   gate's scripts. No direct HTTP or `curl` to Shop Builder, no copied browser
   cookies or tokens.
2. **Only through the `shop-builder-assembly` safety gate**: preflight, backup
   of the target site, rendered plan, then an explicit publisher confirmation of
   the plan's `confirmation_id` immediately before the first remote write.
   Earlier consent ("add quests to my site") is not that confirmation.
3. **An approved test project only for the site** (`environment: test` in the
   brief, on the gate's allowlist). Stop on a partner project, a `sandbox`
   target or an ambiguous project identity. Quest edits use the configured
   publisher credential for the Quest Platform project, as in `SKILL.md`. If
   that Quest Platform project and the test site belong to different
   environments, or the mapping between them is unclear, stop and ask the
   publisher to explicitly confirm that making these quests public and showing
   them on a test site is intended. If a quest the publisher wants is missing,
   offer to create it through the normal quest create flow in `SKILL.md`, and
   create it only after the publisher says yes to that exact proposal. Never
   proceed on assumption.
4. **Never publish.** Do not apply a saved version, attach a domain or enable
   live payments. The merchant previews in Publisher Account and publishes.
5. Quest edits keep every stop in `SKILL.md` (proposal first, one approval, no
   secrets or IDs on screen). Site writes need their own plan confirmation; a
   quest approval never covers them, and the reverse.
6. **Delete needs its own yes.** Remove a block only when the publisher names
   it, and only as a `delete` operation in the confirmed plan. Nothing else in
   the plan may remove a block.

## Prerequisites

Check each one and stop with the smallest missing action when it fails.

- **`shop-builder-assembly` available** with `block_operations` support (see
  above). Never run write commands by hand.
- **Block version.** The gate pins the build of `@quest-platform/quests-block`
  it supports, and that build is currently unstable (visible only in Site
  Builder Dev Mode). A merchant-facing site waits for a stable release of the
  block. The exception is QA: the pinned unstable build may be added to a test
  site in Dev Mode to check the block before release. Say which case applies
  before the plan, and never present an unstable build as production ready.
- **Shop Builder site** exists in an approved test project and is unpublished.
  Creating the site itself is the `shop-builder-assembly` flow.
- **Environment.** `XSOLLA_MERCHANT_ID` and the project key lane resolved as in
  [`auth-and-environment.md`](auth-and-environment.md). The block reads quests
  for the merchant and project of the site it sits on, so the Quest Platform
  project must be the one the site belongs to. If the mapping is unclear or the
  environments differ, follow Hard rule 3 and stop for explicit confirmation.

## Ask first

Ask before proposing, in one short message, only what you cannot read yourself:

- **Which quests** to show, and in what order (list existing quests with the
  read-only list; offer to create a missing one via the normal quest flow).
  The block shows at most 24.
- **How many** to show on the page (`maxQuests`, 1 to 24, default 6).
- **Heading text** and **languages** to localize it into (default heading is
  "Quests" in `en-US`). Locale keys are full codes such as `en-US` or `de-DE`;
  a bare `de` is rejected.
- **Look**: only the layout settings the publisher wants changed; everything
  else keeps its default.
- **Images and texts** per card, only when the quest's own name, description or
  image is missing or should be replaced.
- **Which page** of the site gets a new block, and where on it. For an existing
  block, which one, when the site has several.

Do not ask for IDs, hosts or slugs you can read from the CLI. Existing block
ids come from the structure in the gate's backup, never from a guess.

## Quest public view

Cards read their content from each quest's public view:

| Card part | Source |
|---|---|
| Title | `view.name` |
| Description | `view.description` |
| Image | `view.image_url` |

A quest can appear to anonymous visitors only when it is public: `is_public:
true` and `public_view` set. Set them through the existing edit flow in
[`quest-document.md`](quest-document.md#editing) (read, change, full `PUT`,
before/after diff, one approval, read back). Fill `public_view` with `name`,
`description` and `image_url` (an absolute `https` URL). Never invent an image.
If the publisher has none, ask, or leave it empty and let the card show its
neutral placeholder.

Open item: the public routes and these field names are still moving (the public
quest ADR is Proposed, and the fields are not yet in
[`qp-api-contract.md`](qp-api-contract.md)). Before writing them, confirm they
appear in a read of the live quest. If the read-back does not show `is_public`
and `public_view`, stop and report that the contract does not expose them yet.
The key convention inside `public_view` is also open with the Quest Platform
team.

## Block settings

Every setting of the block, with the key to use in a brief's `values` and the
default a new block starts with. Patch single leaves only, never a whole
object. The plan maps each key to the block's real path and creates a missing
parent object (for example `layout`) first.

| Brief key | Allowed values | Default | What it does |
|---|---|---|---|
| `questIds` | list of unique quest ids, at most 24 | empty | Which quests show, in display order. Changing the order is a `questIds` update. |
| `maxQuests` | whole number 1 to 24 | `6` | How many cards show at most (the limit). |
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
| `editorPreview` | `live`, `anonymous`, `not_started`, `in_progress`, `completed`, `expired`, `error` | `live` | Which state the editor canvas shows. Editor only, visitors never see it |
| heading (`translations`) | text per locale, under the key `heading` | `Quests` in `en-US` | The block's heading, localized |

Notes:

- Overrides are plain strings, are not localized, and win over the quest's own
  view. Prefer fixing the quest's `public_view` so the text is not duplicated.
  Overrides stay on the block when a quest is removed from `questIds`.
- The heading is a localized text. It goes in `translations` of the operation,
  never in `values`, and only the key `heading` is accepted.
- There is no separate visibility setting for the heading, description and
  image beyond the three `layout.show*` toggles. Hiding the whole block is the
  `hide` operation.

## Operations

Operations go in the brief's `block_operations` list. A list may hold several,
run in order. The brief needs `version`, `project` (`environment: test`,
`test_project_acknowledged: true`, `merchant_id`, `project_id`), `site.slug`
and `block_operations`; it does not need `game`, `catalog` or `content`. Use these placeholders and fill real
values from the conversation and the backup, never from memory:

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

Change only the heading, for one or several locales:

```json
{"op": "update", "block_id": "<block-id>",
 "translations": {"en-US": {"heading": "Today's quests"}}}
```

Reset media or text overrides (paths are `overrides.<questId>.<field>` leaves,
or a whole `overrides.<questId>`):

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

Delete (own yes, Hard rule 6):

```json
{"op": "delete", "block_id": "<block-id>"}
```

Rules that apply to every operation:

- Keys not in the settings table are rejected by the gate. Never invent one.
- Collect every missing input in one question, not one at a time. If the gate
  rejects the brief, relay its full error list in one reply, then fix the brief
  and render again.
- `index` is a position on the page, counted from 0. `reorder` of cards is an
  `update` of `questIds`; `move` repositions the whole block.
- The gate only touches the blocks listed. Every other block must read back
  unchanged, and the verification checks that.
- A deleted block disappears from its page. Its id may stay listed in the
  site's top-level block list, which the apply report shows as a warning. That
  is a known gap of the CLI, not something to fix by hand.
- Verification status (D2a, as of 2026-10-20): add, value updates, the heading
  and delete have run against a live test site. reset, move, duplicate, hide
  and show are verified in unit tests, not yet on a live site. Say so if the
  publisher asks how well tested an operation is.

## Flow

1. **Choose quests.** List the existing quests (read-only) and agree the set,
   order and count with the publisher. Offer the normal create flow for a
   missing quest.
2. **Make them public.** For each chosen quest that is not public, set
   `is_public` and `public_view` through the edit flow in
   [Quest public view](#quest-public-view), one proposal and one approval.
   Stop if a quest is not found or the read-back does not show the fields.
3. **Build the brief.** Turn the agreed settings into `block_operations`. For an
   existing block, take its id from the structure in the gate's backup. Check
   every key against the settings table.
4. **Hand it to the gate.** Run the `shop-builder-assembly` preflight, back up
   the target site, and render the plan from that backup. The plan must show
   exactly the operations asked for, with the leaf paths and values, any parent
   objects it will create, and any removal. Show the plan and its
   `confirmation_id`, stop, and wait for the publisher's confirmation.
5. **Apply.** After confirmation, apply exactly the confirmed plan with the
   gate's apply script, which reads the result back. If it reports a partial
   failure, do not rerun it; take a fresh backup and plan first.
6. **Read back.** Compare the gate's verification to the confirmed plan: the
   settings and heading of each touched block, the block order of each touched
   page, and that every other block is unchanged. Check that each chosen quest
   reads back as public.
7. **Hand off.** Report what changed, what was skipped and the known gaps. Say
   the site is **not published**: the merchant previews it in Publisher Account
   and publishes there. Anonymous visitors see cards only. Signed-in progress
   uses `/api/v2/me/...` and is live on stage only for now, so do not promise
   it on a production site.

If the gate cannot express an operation (no support, unknown key, block not
found), stop and report the gap. Never improvise raw `xsolla shopbuilder`
commands to get around it.

## Stop conditions

Stop before any write when `shop-builder-assembly` is unavailable or lacks
`block_operations`, the mapping between the Quest Platform project and the test
site is unclear or the environments differ without the publisher's explicit
confirmation, the project is not an approved `environment: test` project, the
block version question (see Prerequisites) is unresolved, backup failed, the
plan was not confirmed, a delete was not named and confirmed, a chosen quest is
not found or not public, a setting is not in the table or is out of range, or
an image URL is not `https`. Preserve completed safe work and state the
smallest action to continue.

## Out of scope

Publishing, domains, production sites, editing other blocks, reward delivery
claims, and creating the Shop Builder site itself.

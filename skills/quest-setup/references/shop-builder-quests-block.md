# Quests block in Shop Builder

Manages the native **Quests** block on an unpublished **Shop Builder** site, so the
site shows quest cards to anonymous visitors and progress to signed-in players.
Every operation is a `block_operations` brief handed to the `shop-builder-assembly`
safety gate. For a headless storefront use [`web-shop-module.md`](web-shop-module.md).

Agent-internal: the block's setting keys below are for briefs only. Never show them
to the publisher.

## Hard rules

1. **Only through the gate.** Use the `xsolla shopbuilder` CLI (1.9.4 or newer)
   only through the gate's scripts: preflight, backup of the target site, rendered
   plan, then an explicit publisher confirmation of the plan's `confirmation_id`
   right before the first remote write. Never run write commands by hand, make
   direct HTTP calls, or reuse browser cookies or tokens. An earlier "add quests to
   my site" is not that confirmation. If `shop-builder-assembly` or its
   `block_operations` support is missing, stop and say so in one sentence.
2. **Approved test project only.** The brief uses `environment: test` on the gate's
   allowlist. Stop on a partner project, a `sandbox` target or an unclear project
   identity. If the Quest Platform project and the test site belong to different
   environments, or the mapping between them is unclear, ask the publisher once to
   confirm that making these quests public and showing them on a test site is
   intended. Never proceed on assumption.
3. **Never publish.** Do not apply a saved version, attach a domain or enable live
   payments. Say in one sentence that the publisher previews and publishes in
   Publisher Account.
4. **Delete needs its own yes.** Remove a block only when the publisher names it, and
   only as a `delete` operation in the confirmed plan. Nothing else in the plan may
   remove a block.
5. **Quest and site approvals are separate.** A quest approval never covers a site
   write, and a site confirmation never covers a quest write. Quest edits keep the
   stops in [`SKILL.md`](../SKILL.md).
6. **Quests block only.** For the header, theme, other blocks, site language or
   anything else on the site, say in one sentence that it is changed in the Shop
   Builder editor. Offer no site-wide change.

## Prerequisites

Check each one and stop with the smallest missing action when it fails.

- **Gate available** with `block_operations` support (see Hard rule 1).
- **Block version.** The gate pins a build of the Quests block that is currently
  unstable (visible only in Site Builder Dev Mode). It may be used on a QA test site
  to check the block before release. Say which case applies before the plan, and
  never present the unstable build as production ready. A merchant-facing site waits
  for a stable release of the block.
- **Shop Builder site** exists in an approved test project and is unpublished.
  Creating the site itself is the gate's flow.
- **Scope.** The merchant and project for the Quest Platform calls come from the
  same resolved credential as in
  [`auth-and-environment.md`](auth-and-environment.md#credential). The block reads
  quests for the merchant and project of the site it sits on, so the Quest Platform
  project must be the one the site belongs to. If that mapping is unclear, follow
  Hard rule 2.

## Which shop

Use this only when the request is to add, change, show or remove quests in a shop,
block or section, and the publisher has not said whether the shop is a Shop Builder
site or a headless storefront. Quest-only requests never trigger it.

1. Run the read-only site list and show each site's name and slug.
2. Ask in one message: which of these sites, or a headless storefront codebase.
3. If the CLI is not logged in or the list fails, say so in one sentence and ask the
   same question without the list, asking the publisher to log in to the Xsolla CLI.
4. If there are no Shop Builder sites, say so and ask whether they mean a headless
   storefront.
5. After the answer, continue here for a Shop Builder site, or with
   [`web-shop-module.md`](web-shop-module.md) for a headless storefront.

## Ask first

If the site is not yet known, resolve it first in [Which shop](#which-shop).

Ask in one message, and only for what you cannot read yourself:

- **Which quests** to show, and in what order. List the existing quests (read-only).
  If a wanted quest is missing, offer the normal create flow.
- **Card text and image**, only for a quest that lacks them. Where the quest already
  has them, do not ask: say the defaults in the proposal instead. Title defaults to
  the quest name, explanation to the quest description, image to the quest image.

Use these defaults and state them in the proposal instead of asking: heading
"Quests" (`en-US`), block at the end of the home page (or in the existing block's
place when one exists), at most 6 cards (or fewer when fewer quests are chosen),
and the layout defaults in the settings table below. The block shows at most 24
quests.

Do not ask for IDs, hosts or slugs you can read from the CLI. Existing block ids come
from the structure in the gate's backup, never from a guess.

## Quest public view

Cards read their content from each quest's public view:

| Card part | Source |
|---|---|
| Title | `view.name` |
| Description | `view.description` |
| Image | `view.image_url` |

A quest appears to anonymous visitors only when it is public: `is_public: true` and
`public_view` set. Set them through the edit flow in
[`quest-document.md`](quest-document.md#editing) (read, change, full `PUT`, before/after
diff, one approval, read back). Fill `public_view` with `name`, `description` and
`image_url` (an absolute `https` URL). Never invent an image. If the publisher has
none, leave it empty and the card shows its neutral placeholder.

If the read-back does not show `is_public` and `public_view`, stop and report that.

Each card can also show a reward line and a reward icon, set per card with
`overrides.<questId>.rewardText` and `overrides.<questId>.rewardImageUrl` (see the
settings table). Never put reward text into the title or description as a workaround.

## Block settings

Patch single leaves only, never a whole object. The plan maps each key to the
block's real path and creates a missing parent object (for example `layout`) first.

| Brief key | Allowed values | Default | What it does |
|---|---|---|---|
| `questIds` | list of unique quest ids, at most 24 | empty | Which quests show, in display order. Changing the order is a `questIds` update. |
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
backup, never from memory:

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
whole `overrides.<questId>`):

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

Rules for every operation:

- Keys not in the settings table are rejected by the gate. Never invent one.
- Ask for all missing inputs in one message. If the gate rejects the brief, relay its
  full error list in one reply, fix the brief and render again.
- `index` is a position on the page, counted from 0. Reordering cards is an `update`
  of `questIds`; `move` repositions the whole block.
- The gate touches only the blocks listed. Every other block must read back unchanged.
- A deleted block's id may stay in the site's top-level block list, which the apply
  report shows as a warning. This is a known CLI gap; do not fix it by hand.

## Flow

1. **Choose quests.** List the existing quests (read-only) and agree the set, order
   and count with the publisher. A missing quest goes through the normal create flow
   in [`SKILL.md`](../SKILL.md), created only after a yes to that exact proposal.
2. **Make them public.** For each chosen quest that is not public, set `is_public` and
   `public_view` per [Quest public view](#quest-public-view): one proposal, one
   approval. Stop if a quest is not found or the read-back does not show the fields.
3. **Build the brief.** Reward defaults: for each chosen quest with a `web3_item`
   reward node, read its `item_sku` and `project` from the quest document, look the
   SKU up with the read-only Store admin route in
   [`auth-and-environment.md`](auth-and-environment.md#store-admin-catalog), and if
   the item has an `https` `image_url`, propose it as that card's `rewardImageUrl`.
   No image means no icon: leave it unset. Never invent a URL. Reward text and icon
   changes the publisher asks for go through the same proposal and yes as title,
   description and image. Turn the agreed settings and defaults into `block_operations`.
   For an existing block, take its id from the structure in the gate's backup. Check
   every key against the settings table.
4. **Hand it to the gate.** Run the preflight, back up the target site, and render the
   plan from that backup. The plan must show exactly the requested operations with
   their leaf paths and values, any parent objects it creates, and any removal. Show
   the plan, its `confirmation_id` and the defaults used. Stop and wait for the
   publisher's confirmation.
5. **Apply.** After confirmation, apply exactly the confirmed plan with the gate's
   apply script, which reads the result back. On a partial failure, do not rerun it;
   take a fresh backup and plan first.
6. **Read back.** Compare the gate's verification to the confirmed plan: settings and
   heading of each touched block, block order of each touched page, every other block
   unchanged, and each chosen quest reads back as public.
7. **Hand off.** Report what changed, what was skipped and any known gaps. Say the site
   is **not published**: the publisher previews and publishes it in Publisher Account.
   Anonymous visitors see the cards. Do not promise signed-in progress on a production
   site.

If the gate cannot express an operation (no support, unknown key, block not found),
stop and report the gap. Never improvise raw `xsolla shopbuilder` commands.

## Stop conditions

Stop before any write when: the gate is unavailable or lacks `block_operations`; the
mapping between the Quest Platform project and the test site is unclear, or the
environments differ without the publisher's explicit confirmation; the project is not
an approved `environment: test` project; the block version question is unresolved;
backup failed; the plan was not confirmed; a delete was not named and confirmed; a
chosen quest is not found or not public; a setting is not in the table or out of
range; or an image URL is not `https`. Keep completed safe work and state the smallest
action to continue.

## Out of scope

Publishing, domains, production sites, other blocks and the rest of the site, reward
delivery claims, and creating the Shop Builder site itself. Decline each in one
sentence, pointing to the Shop Builder editor or Publisher Account as relevant.

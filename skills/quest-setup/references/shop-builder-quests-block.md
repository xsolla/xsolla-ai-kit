# Quests block in Shop Builder

Adds the native **Quests** block to an unpublished **Shop Builder** site, so the
site shows quest cards to anonymous visitors and progress to signed-in players.
For a **headless** storefront use [`web-shop-module.md`](web-shop-module.md)
instead.

This flow depends on the `shop-builder-assembly` skill from `main` (it is not
part of this branch's stack). It uses that skill's safety gate and scripts as
they are; do not restate or bypass them.

Triggers: "add the Quests block to my Shop Builder site", "show quests in my
Shop Builder shop", "quests section in Site Builder".

## Hard rules

1. **Only the `xsolla shopbuilder` CLI** (version 1.9.4 or newer). No direct
   HTTP or `curl` to Shop Builder, no copied browser cookies or tokens.
2. **Only through the `shop-builder-assembly` safety gate**: preflight, backup
   of the target site, rendered plan, then an explicit publisher confirmation of
   the plan's `confirmation_id` immediately before the first remote write.
   Earlier consent ("add quests to my site") is not that confirmation.
3. **Sandbox or a dedicated test project only.** Stop on a partner project or an
   ambiguous project identity.
4. **Never publish.** Do not apply a saved version, attach a domain or enable
   live payments. The merchant previews in Publisher Account and publishes.
5. Quest edits keep every stop in `SKILL.md` (proposal first, one approval, no
   secrets or IDs on screen). Site writes need their own plan confirmation; a
   quest approval never covers them, and the reverse.

## Prerequisites

Check each one and stop with the smallest missing action when it fails.

- **Block published.** `@quest-platform/quests-block` is released as a stable
  version, and its block type is available to the site. The unstable build is
  not enough.
- **Block contract exported (open dependency).** `shop-builder-assembly` allows
  `add-block` only for an observed palette name and a value patch only for an
  exported contract (see its block catalog and exported contracts). The Quests
  block has neither until a UI-created export is added there. Until it is, the
  block type id is "the block type id from the published block contract". Never
  guess it, never infer it from the marketing name, and never reuse another
  block's id. If the contract is missing, stop and report the gap.
- **Shop Builder site** exists in a sandbox or dedicated test project and is
  unpublished. Creating the site itself is the `shop-builder-assembly` flow.
- **Environment.** `XSOLLA_MERCHANT_ID` and the project key lane resolved as in
  [`auth-and-environment.md`](auth-and-environment.md). The block reads quests
  for the merchant and project of the site it sits on, so the Quest Platform
  project must be the one the site belongs to.

## Ask first

Ask before proposing, in one short message, only what you cannot read yourself:

- **Which quests** to show, and in what order (list existing quests with the
  read-only list; offer to create a missing one via the normal quest flow).
  The block shows at most 24.
- **How many** to show on the page (`maxQuests`, default 6).
- **Heading text** and **languages** to localize it into (default heading is
  "Quests" in `en-US`).
- **Images and texts** per card, only when the quest's own name, description or
  image is missing or should be replaced.
- **Which page** of the site gets the block, and where on it.

Do not ask for IDs, hosts or slugs you can read from the CLI.

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

## Block data

The block keeps this data on the site (field names are from the block's config):

| Field | Type | Rule |
|---|---|---|
| `questIds` | `string[]` | Quest ids in display order, at most 24 |
| `maxQuests` | number | How many cards to show, default 6 |
| `overrides` | object keyed by quest id | Optional `title` (max 120), `description` (max 400), `imageUrl` (`https` only), all plain strings; they win over the quest's own view |
| heading | localized text | Stored in the block's `translations` under `heading` per locale, not in a plain value |

Overrides are plain strings and are not localized. Prefer fixing the quest's
own `public_view` over overriding it, so the text is not duplicated.

## Assembly

All steps run through `shop-builder-assembly`; the block is just one more block
in its plan. Use the exact commands from its CLI operations reference.

1. **Gate.** Run its preflight, then back up the existing target site, then
   render the plan with the structure from that backup. The plan must contain
   the Quests block on the chosen page and nothing the publisher did not ask
   for. Show the plan and the `confirmation_id`, stop, and wait.
2. **Add.** After confirmation:
   `xsolla shopbuilder add-block --landing-id <landing> --page-id <page> --block <the block type id from the published block contract>`
   then re-read `get-structure` to find the new block's `_id`; do not construct
   a later command from a stale structure.
3. **Configure.** Apply `xsolla shopbuilder update-block --landing-id <landing>
   --data '<json>'` with targeted patches on leaf paths only, in the same
   wrapper shape that `shop-builder-assembly` uses for block patches (a key
   naming the operation, `"type": "block"`, the block `id`, and a `patches`
   array of `{"op", "path", "value"}`). Patch `questIds`, `maxQuests` and each
   `overrides.<questId>` leaf. Never replace the whole `values` object. The
   exact `path` for each field comes from the exported contract, which is the
   same open dependency as above.
4. **Heading.** Write the localized heading through the localization commands
   (`add-language`, `update-localization`), never through a block value patch.
5. **Verify.** Re-read with `get-structure` and `get-localization`, compare to
   the confirmed plan, then run `xsolla shopbuilder verify-website --slug
   <slug>`. Check that `questIds`, `maxQuests`, overrides and each requested
   locale match. Check each chosen quest reads back as public.
6. **Hand off.** Report what changed, what was skipped, and the known gaps. Say
   the site is **not published**: the merchant previews it in Publisher Account
   and publishes there. Say that signed-in progress depends on the player
   progress endpoint, which may not be live yet, and that anonymous visitors see
   cards only.

## Stop conditions

Stop before any write when the block is not published as stable, the block type
id or contract is missing, the project is not a sandbox or acknowledged test
project, backup failed, the plan was not confirmed, a chosen quest is not found
or not public, or an image URL is not `https`. Preserve completed safe work and
state the smallest action to continue.

## Out of scope

Publishing, domains, production sites, editing other blocks, player progress or
reward delivery claims, and creating the Shop Builder site itself.

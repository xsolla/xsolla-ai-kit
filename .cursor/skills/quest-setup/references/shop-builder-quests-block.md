# Quests block in Shop Builder

Adds the native **Quests** block to an unpublished **Shop Builder** site, so the
site shows quest cards to anonymous visitors and progress to signed-in players.
For a **headless** storefront use [`web-shop-module.md`](web-shop-module.md)
instead.

This flow depends on the `shop-builder-assembly` skill from `main` (it is not
part of this branch's stack). It uses that skill's safety gate and scripts as
they are; do not restate or bypass them. If the `shop-builder-assembly` skill
is not available in the session, stop and report that; never fall back to
running `xsolla shopbuilder` write commands without the gate.

Triggers: "add the Quests block to my Shop Builder site", "show quests in my
Shop Builder shop", "quests section in Site Builder".

## Hard rules

1. **Only the `xsolla shopbuilder` CLI** (version 1.9.4 or newer). No direct
   HTTP or `curl` to Shop Builder, no copied browser cookies or tokens.
2. **Only through the `shop-builder-assembly` safety gate**: preflight, backup
   of the target site, rendered plan, then an explicit publisher confirmation of
   the plan's `confirmation_id` immediately before the first remote write.
   Earlier consent ("add quests to my site") is not that confirmation.
3. **Sandbox or a dedicated test Shop Builder project only for the site.** Stop
   on a partner project or an ambiguous project identity. Quest edits use the
   configured publisher credential for the Quest Platform project, as in
   `SKILL.md`. If that Quest Platform project and the sandbox site are in
   different environments, or the mapping between them is unclear, stop and ask
   the publisher to explicitly confirm that making these quests public and
   showing them on a test site is intended. Never create quests just for a test
   site, and never proceed on assumption.
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
- **`shop-builder-assembly` available.** The skill (from `main`) is installed
  and loadable in this session. If not, stop and report; do not run write
  commands by hand.
- **Shop Builder site** exists in a sandbox or dedicated test project and is
  unpublished. Creating the site itself is the `shop-builder-assembly` flow.
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

The CLI is run only through or after the `shop-builder-assembly` safety gate,
and only for plan items the publisher confirmed with the plan's
`confirmation_id`. The exact flags, patch wrapper and ids come from that skill's
CLI operations reference and scripts, not from this file. Do not copy commands
from here.

1. **Gate.** Run its preflight, back up the existing target site, and render the
   plan with the structure from that backup. For this block the rendered plan
   must show: the block type id from the published block contract, the target
   page and position, each leaf path and value to patch (`questIds`,
   `maxQuests`, each `overrides.<questId>` leaf), and the language and
   localization items for the heading. It must contain nothing the publisher did
   not ask for. Show the plan and the `confirmation_id`, stop, and wait.
2. **Apply.** After confirmation, apply exactly the confirmed items with the
   gate's apply script. Re-read `get-structure` after the block is added before
   any ID-sensitive step. Patch leaf paths only, never the whole `values`
   object. The heading goes through the localization items, never a block value
   patch.
3. **Cannot express it yet.** If the gate's plan renderer or apply script cannot
   express this block (no contract, unknown block type, no supported leaf
   paths), stop and report the gap. Never improvise raw `xsolla shopbuilder`
   commands to get around it.
4. **Verify.** Re-read structure and localization, compare to the confirmed
   plan, and run the gate's verification (`verify-website`). Check that
   `questIds`, `maxQuests`, overrides and each requested locale match, and that
   each chosen quest reads back as public.
5. **Hand off.** Report what changed, what was skipped, and the known gaps. Say
   the site is **not published**: the merchant previews it in Publisher Account
   and publishes there. Say that signed-in progress depends on the player
   progress endpoint, which may not be live yet, and that anonymous visitors see
   cards only.

## Stop conditions

Stop before any write when `shop-builder-assembly` is unavailable, the mapping
between the Quest Platform project and the sandbox site is unclear or the
environments differ without the publisher's explicit confirmation, the block is not published as stable, the block type
id or contract is missing, the project is not a sandbox or acknowledged test
project, backup failed, the plan was not confirmed, a chosen quest is not found
or not public, or an image URL is not `https`. Preserve completed safe work and
state the smallest action to continue.

## Out of scope

Publishing, domains, production sites, editing other blocks, player progress or
reward delivery claims, and creating the Shop Builder site itself.

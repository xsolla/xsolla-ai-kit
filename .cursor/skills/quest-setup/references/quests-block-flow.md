# Quests block flow (Shop Builder)

Loaded for a Quests block request on a Shop Builder site. Settings and the operation JSON are in
[quests-block-brief.md](quests-block-brief.md).

## Hard rules

1. **Writes only through the gate.** Every change to a site goes through the gate's
   scripts, which drive the `xsolla shopbuilder` CLI (1.9.4 or newer): preflight,
   backup of the target site, rendered plan, then an explicit publisher confirmation
   of the plan's `confirmation_id` right before the first remote write. The only
   `xsolla shopbuilder` commands you run directly are the read-only `list-websites`,
   `get-structure` and `get-localization` (the block summary script below runs the last two). Never run write commands by hand, make
   direct HTTP calls, or reuse browser cookies or tokens. An earlier "add quests to
   my site" is not that confirmation. If the Shop Builder block tooling or its
   `block_operations` support is missing, stop and reply in the refusal shape, without
   naming any skill.
2. **Approved test project only.** The brief uses `environment: test` on the gate's
   allowlist. Stop on a partner project, a `sandbox` target or an unclear project
   identity. If the Quest Platform project and the test site belong to different
   environments, or the mapping between them is unclear, ask the publisher once to
   confirm that making these quests public and showing them on a test site is
   intended. Never proceed on assumption. The gate's approval list is the
   dedicated-test-project acknowledgement: only the gate's preflight reads it, the agent
   never reads it, and the agent never asks the publisher to confirm a test project. A
   project on the list is acknowledged; for one that is not, preflight stops and you reply
   `needs_human` in the Not approved shape in [reply-format.md](reply-format.md) (a
   maintainer adds it to the list). The brief has no acknowledgement flag. A site other
   than the one the publisher chose under Which shop, or one they say must not be
   touched, gets no plan and no write: say so and ask which site to use.
3. **Never publish.** Do not apply a saved version, attach a domain or enable live
   payments. For a publish request, say: "The skill doesn't publish; you publish in
   Publisher Account when ready. The site stays unpublished."
4. **No scripted delete.** There is no `delete` operation, and no script passes
   `--force`. Nothing in a plan removes a block. A request to remove or delete the
   Quests block gets the `needs_human` reply in [Removing the block](#removing-the-block):
   the publisher deletes it in the Site Builder editor, and `hide` is offered as the
   scripted alternative.
5. **Quest and site approvals are separate.** A quest approval never covers a site
   write, and a site confirmation never covers a quest write. Quest edits keep the
   stops in [`SKILL.md`](../SKILL.md).
6. **Quests block only.** For the header, theme, other blocks, site language or
   anything else on the site, say: "That's outside the Quests block; change it in the
   Shop Builder editor." Offer no site-wide change and give no steps or menu names.
7. **Sandbox mode is implied.** A Shop Builder change means the CLI's sandbox mode is
   off. The gate's preflight settles it itself and reports the plan line to show
   (its `plan_notes`, for example "Using the CLI test environment (sandbox off)"). Never ask the publisher about sandbox mode, and
   never run `xsolla config set` or edit a CLI config yourself. When preflight reports a
   `cli_environment`, add `--environment <name>` to the read-only `xsolla shopbuilder`
   commands you run yourself.

## Prerequisites

Check each one and stop with the smallest missing action when it fails.

- **Gate available** with `block_operations` support (see Hard rule 1).
- **Shop Builder site** exists in an approved test project and is unpublished.
  Creating the site itself is the gate's flow.
- **Scope.** The merchant and project for the Quest Platform calls come from the
  same resolved credential as in
  [`auth-credentials.md`](auth-credentials.md#credential). The block reads
  quests for the merchant and project of the site it sits on, so the Quest Platform
  project must be the one the site belongs to. If that mapping is unclear, follow
  Hard rule 2.

## Which shop

Use this whenever the request is about the publisher's shop, webshop or site (a change
to it, or a question about it, such as "tell me about quests on my webshop"), and the
publisher has not said whether the shop is a Shop Builder site or a headless
storefront. Pure quest requests (list my quests, why a quest did not complete, create
a quest) never trigger it.

0. A change to the Quests block with no site named ("show only 3 cards", "change the
   quests heading"): run `python3 "<skill base dir>/scripts/quests_block_summary.py"`
   (no `--slug`, read-only). When its `site` is set, that is the only site with a
   visible Quests block: use it without asking, name it in the plan's Site bullet, and
   use the same output as the block summary (no second read). When `site` is null, go
   on with step 2 using the `sites` names; the site list is already read.
1. Always run the read-only list, `xsolla shopbuilder list-websites --json`, before
   replying. Never say the list is unavailable without running it.
2. If the command succeeds, reply in the Which shop shape: the bold question, one bullet
   per site name from the list, a bullet for a headless storefront codebase, then
   `Next:`. No capability or explanation sentence comes before the question.
3. Only if the command itself fails, use the Discovery failure shape in
   [reply-format.md](reply-format.md): a bold line that the site list couldn't be read,
   2 or 3 bullets with the block's capabilities (see [Discovery answer](#discovery-answer)),
   and one `Next:` asking which shop it is. Mention logging in to the Xsolla CLI only if
   it is needed, and never ask the publisher to allow CLI commands.
4. If the list is empty, say there are no Shop Builder sites and ask whether they mean
   a headless storefront.
5. After the answer, continue here for a Shop Builder site, or with
   [`web-shop-module.md`](web-shop-module.md) for a headless storefront. A question about
   quests on the chosen Shop Builder site goes to [Describe the block](#describe-the-block).

Show site names only, never IDs or hosts.

### Discovery answer

A capability question with no change asked for ("what can it do with my shop?", "what
can quests do on my Shop Builder site?") gets the second capability example in
[reply-format.md](reply-format.md#examples), with no tool call and no site list. Run the
site list only when the publisher wants to look at or change a site. When the list read
fails (step 3), give the same capability bullets (at most three) in the Discovery
failure shape, then the one `Next:`.

## Describe the block

Use when the site is known (chosen in [Which shop](#which-shop)) and the publisher asks
about quests on it, for example "show me the Quests block on my-test-site" or "tell me about
quests on my webshop" after naming the site. This is a read, so it needs no gate and no backup.

1. Run one command, read-only, from the publisher's folder (add `--environment <name>`
   when the site needs it): `python3 "<skill base dir>/scripts/quests_block_summary.py" --slug <slug>`.
   It reads the structure, the localization and the quest list itself and prints JSON:
   per Quests block its page, position, `hidden`, `max_quests`, `heading`, and `quests` in
   block order (`quest_name`, `card_title`, `overridden`, `public`). No other reads, no
   `--help`, no own parsing.
2. Reply in the Describe-the-block shape from [reply-format.md](reply-format.md): a bold
   line naming the site and that it has a Quests block (if `blocks` is empty: it has no
   Quests block, with `Next:` offering to add one). Then bullets, in order: Where (page,
   position N of M, visible or hidden); Quests (limit M), then every quest name in block
   order (the `card_title` when it differs from or replaces `quest_name`; mark a quest
   that is not public); Heading (the text in quotes, or "heading is set" when null);
   Card overrides in a few words ("all 4 cards: title, description, reward", or "none"),
   with no comment on rewards or matching names. Several Quests blocks: one Where and
   Quests bullet each. No layout, style, JSON, ids, or draft and publishing notes.
3. If `quest_names` is `unavailable` and no `card_title` is set, say in the Quests bullet:
   "names show once Quest Platform access is set up." Never say the block cannot be
   confirmed when the read works.
4. The `Next:` line is one question, for example "want to change anything on it?"

If the read itself fails, reply with a bold line that the site structure couldn't be read,
and a `Next:` asking the publisher to log in to the Xsolla CLI if needed.

## Ask first

If the site is not yet known, resolve it first in [Which shop](#which-shop).

Ask in one message, in the question shape from [reply-format.md](reply-format.md) (a
bold question, up to four bullets, then `Next:`), and only for what you cannot read
yourself:

- **Which quests** to show, and in what order. List the existing quests (read-only).
  If the list read succeeds and the project has no quests, use the No quests offer in
  the Flow (step 1). If a wanted quest is missing, use the Missing quest offer there.
- **Card text and image.** Never say that an explanation is required, and never ask for
  card text that has a default. Say the defaults instead: card title is the quest name,
  explanation is the quest description, and image is the quest image when it has one.
  The reward text and image come from the quest and can't be changed on the block. Then
  ask at most one optional question, for example "want a different title or image on
  the card?"
- **Card defaults bullets.** Whenever you stop or ask about card content, add bullets for
  only the defaults that apply: Card title is the quest name; Explanation is the quest
  description; Image is the quest image when it has one; Reward comes from the quest.
  The reward item image is never used as the card image.

Use these defaults and state them in the proposal instead of asking: heading
"Quests" (`en-US`), block at the end of the home page (or in the existing block's
place when one exists), at most 6 cards (or fewer when fewer quests are chosen),
and the layout defaults in the [settings table](quests-block-brief.md#block-settings). The block shows
at most 24 quests. For the end of the home page, set the `add` operation's `index` to
the position of the page's `footer` block (so the Quests block lands above the footer),
or to the page's current block count when there is no footer. Read both from the gate's
backup. Never omit `index`, because an `add` without it puts the block first.

Do not ask for IDs, hosts or slugs you can read from the CLI. Existing block ids come
from the block summary or the gate's backup, never from a guess.

## Quest public view

Cards read their content from each quest's public view:

| Card part | Source |
|---|---|
| Title | `view.name` |
| Description | `view.description` |
| Image | `view.image_url` |

A quest appears to anonymous visitors only when it is public: `is_public: true`.
`public_view` is optional. When it is empty, the card uses the quest's default view
(quest name, description and rewards), so never add a `public_view` only to pass this
check. Set `is_public`, and `public_view` when the publisher wants custom card content, through the edit flow in
[`quest-edit.md`](quest-edit.md#editing) (read, change, full `PUT`, before/after
diff, one approval, read back). Fill `public_view` with `name`, `description` and
`image_url` (an absolute `https` URL; an `http` URL is refused, see [Rules for every operation](quests-block-brief.md#rules-for-every-operation)). Never invent an image. If the publisher has
none, leave it empty and the card shows its neutral placeholder.

If the read-back does not show `is_public: true` (and the `public_view` you set, if any), stop and report that.

Each card also shows the quest's reward text and image. Both come from the quest
definition and can't be changed on the block. To change them, change the quest's reward
through the edit flow in [`quest-edit.md`](quest-edit.md#editing). Never put reward text
into the title or description as a workaround.

## Flow

1. **Choose quests.** List the existing quests (read-only) and agree the set, order
   and count with the publisher. A missing quest goes through the normal create flow
   in [`SKILL.md`](../SKILL.md), created only after a yes to that exact proposal. Say a quest is missing only after the list read
   succeeds and shows no match. If the read fails, say you cannot check whether it exists.
   **Missing quest offer:** a bold line that the quest doesn't exist yet, at most 2
   bullets, and one yes/no `Next:` ("want me to draft it?"). Under about 80 words. Do
   not draft creation details (player action, reward, schedule, event) before that yes.
   **No quests offer:** if the list read succeeds and shows no quests in the project,
   say the project has no quests yet, so the block has nothing to show, and offer to
   create one first: a bold line, at most 1 bullet that ends with the docs link
   https://developers.xsolla.com/api/quests, and one yes/no `Next:` ("want me to
   draft your first quest?"). After a yes, use the normal create flow in
   [`SKILL.md`](../SKILL.md) (API reference: https://developers.xsolla.com/api/quests),
   then come back here to add the block. Never say there are no quests when the read
   failed; say you cannot check yet.
2. **Make them public.** For each chosen quest that is not public (`is_public` is not
   `true`), set `is_public` per [Quest public view](#quest-public-view): one proposal,
   one approval. A missing `public_view` alone is not a reason to edit or stop. Stop if
   a quest is not found or the read-back does not show `is_public: true`.
3. **Build the brief.** Turn the agreed settings and defaults into `block_operations`.
   The brief never sets the reward text or image: they come from the quest. If the
   publisher asks to change them, say they can't be changed on the block and offer to
   change the quest's reward through the edit flow instead.
   For an existing block, take its `block_id` and the `quest_id`s from the block
   summary (see [Gate commands](quests-block-brief.md#gate-commands)). Check
   every key against the [settings table](quests-block-brief.md#block-settings) and
   the brief against the [rules](quests-block-brief.md#rules-for-every-operation).
4. **Hand it to the gate.** With the exact [Gate commands](quests-block-brief.md#gate-commands),
   run the preflight, back up the target site, and render the plan from that backup,
   all before showing anything. There is no draft plan. The plan
   must show exactly the requested operations with their leaf paths and values, and any
   parent objects it creates. Show the one plan in the Plan shape from
   [reply-format.md](reply-format.md): a bold `Plan:` line, bullets for Site, Change
   (each operation), the defaults used, preflight's plan line when it switched sandbox
   mode off, "Not published; you publish in Publisher Account", and
   `Confirmation: <confirmation_id>`, then `Next: reply "yes" to apply this exact plan.`
   End the turn there; apply nothing until the publisher confirms. One yes applies it.
5. **Apply.** After confirmation, apply exactly the confirmed plan with the gate's
   apply command, which reads the result back. On a partial failure, do not rerun it;
   take a fresh backup and plan first.
6. **Read back.** Compare the gate's verification to the confirmed plan: settings and
   heading of each touched block, block order of each touched page, every other block
   unchanged, and each chosen quest reads back as public.
7. **Hand off.** Report what changed, what was skipped and any known gaps. Say the site
   is **not published**: the publisher previews and publishes it in Publisher Account.
   Anonymous visitors see the cards. Do not promise signed-in progress on a production
   site. End with the Site Builder editor link, which opens the editor with the block
   already on the page, so the publisher can preview and edit it there. Use the apply
   result's `editor_url` as is. Never build the link by hand. If the result has no
   `editor_url`, leave the link out. Give it only after a successful apply, in the Hand-off shape from
   [reply-format.md](reply-format.md#examples).

If the gate cannot express an operation (no support, unknown key, block not found),
stop and report the gap. Never improvise raw `xsolla shopbuilder` commands.

## Removing the block

"Remove the Quests block" or "delete the Quests block" is `needs_human`. No script deletes
a block: `delete-block` needs `--force`, which no script passes, and a brief with a
`delete` op fails validation. Reply in the Delete request shape from
[reply-format.md](reply-format.md): the publisher deletes the block in the Site Builder
editor, and the skill offers to hide it. Run no gate step and draft no plan for the delete
itself. If the publisher wants it hidden, that is a `hide` operation through the full
[Flow](#flow) (preflight, backup, plan, yes).

## Stop conditions

Stop before any write when: the gate is unavailable or lacks `block_operations`; the
mapping between the Quest Platform project and the test site is unclear, or the
environments differ without the publisher's explicit confirmation; the project is not
an approved `environment: test` project (`needs_human`, see Hard rule 2); backup failed; the plan was not confirmed; the request is to delete a block
(`needs_human`, see [Removing the block](#removing-the-block)); a chosen quest is not found or not public; a setting is not in the table or out of
range; or an image URL is not `https`. Keep completed safe work and state the smallest
action to continue.

## Out of scope

Publishing, domains, production sites, other blocks and the rest of the site, reward
delivery claims, and creating the Shop Builder site itself. Decline each in the shape from
[reply-format.md](reply-format.md), with no caveats or steps:

- Publish request: the publish shape ("The skill doesn't publish." with the two Publisher
  Account bullets).
- Any other part of the site: the refusal shape ("That's outside the Quests block." with
  "Change it in the Shop Builder editor." as the bullet).
- Localized card texts: the localized-texts shape. Never suggest a translated heading.
  Name locale codes only when the publisher gave them.

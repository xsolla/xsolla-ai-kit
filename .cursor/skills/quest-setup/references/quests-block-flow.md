# Quests block flow (Shop Builder)

Loaded for a Quests block request on a Shop Builder site. Settings and the operation JSON are in
[quests-block-brief.md](quests-block-brief.md).

## Hard rules

1. **Gate-only writes.** Use [Gate commands](quests-block-brief.md#gate-commands):
   preflight, target backup, rendered plan and later confirmation of its `confirmation_id`.
   Direct CLI is read-only: `list-websites`, `get-structure`, `get-localization` only.
   No manual writes, HTTP, cookies or tokens. Missing block tooling/support means stop
   with the refusal shape, without naming a skill.
2. **The publisher's own project.** The brief's merchant and project IDs must match the
   CLI's, with sandbox mode off. Stop on partner projects or unclear identity; the gate
   reports a mismatch with the refusal shape in [reply-format](reply-format.md#examples).
   If QP/test-site environments or mapping differ or are unclear, ask once whether public
   quests on this site are intended. A site the publisher did not choose or forbade gets
   no plan/write; ask which to use.
3. **Never publish.** [SKILL authority](../SKILL.md#access-and-authority) and
   [publish reply](reply-format.md#examples) apply. No saved-version application,
   domain attachment or live payments.
4. **No scripted delete.** [Removing the block](#removing-the-block) owns `needs_human`
   and the separately planned hide alternative; no `delete` op or `--force`.
5. **Separate quest/site approval.** Neither approval authorizes the other write.
6. **Quests block only.** Its requested [appearance](quests-block-appearance.md) is in
   scope; site/page themes, header, other blocks and languages use the refusal shape,
   without site-wide suggestions, steps or menu names.
7. **Sandbox stop.** [Gate commands](quests-block-brief.md#gate-commands) owns the
   sandbox check: while the CLI has sandbox on, preflight stops and no site work begins.

## Prerequisites

Check each one and stop with the smallest missing action when it fails.

- **Gate available** with `block_operations` support (see Hard rule 1).
- **Shop Builder site** exists in the publisher's project and is unpublished.
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
   per Quests block its page, position, `page_modules`, `hidden`, `max_quests`, `heading`,
   `appearance` and `quests` in block order (`quest_name`, `card_title`, `overridden`,
   `public`). Module IDs come from the structure, not host URLs. Appearance is allowlisted
   and omits unknown saved fields. No other reads, no `--help`, no own parsing.
2. Reply in the Describe-the-block shape from [reply-format.md](reply-format.md): a bold
   line naming the site and that it has a Quests block (if `blocks` is empty: it has no
   Quests block, with `Next:` offering to add one). Then bullets, in order: Where (page,
   position N of M, visible or hidden); Quests (limit M), then every quest name in block
   order (the `card_title` when it differs from or replaces `quest_name`; mark a quest
   that is not public); Heading (the text in quotes, or "heading is set" when null);
   Card overrides in a few words ("all 4 cards: title, description, reward", or "none"),
   with no comment on rewards or matching names. Several Quests blocks: one Where and
   Quests bullet each. Then one Appearance bullet per block, facts only, exactly as the
   read returned them in `appearance`: the block version (`version`, or "version not
   reported" when its status is not present), the theme id (`theme_id`, or "no theme set" /
   "not reported" per `theme_id_status`) and any custom theme values in `custom` (base
   theme, palette, typography, geometry), listed as returned. Add nothing the read did not
   return: no guesses, no inferred history, no judgement of how it looks. When the version
   has no theme keys, state that as a fact and offer nothing here. No JSON, ids, or
   publishing notes.
3. `quest_names` is `resolved` only after the quest list is exhausted. `partial` means
   the five-page lookup budget ended first: names and `found`/`public` facts for returned
   quests remain usable, but an unresolved card omits `found` and `public`. Its existence
   and public status are unknown, so never call it missing or not public. Say its name
   could not be resolved in this partial list, using `card_title` when set. Do not crawl
   more pages to fill the gap. If `quest_names` is `unavailable` and no `card_title` is set,
   say in the Quests bullet: "names show once Quest Platform access is set up." Never say
   the block cannot be confirmed when the read works.
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
- **Card content.** State only applicable defaults whenever stopping/asking about it:
  title = quest name; explanation = quest description; image = quest image when present
  (the first reward's image is a fallback only from Quests block 0.2.14, not yet pinned, see
  [block-versions](block-versions.md)); reward text/image = quest reward (read-only on the block).
  Never require an explanation or ask for defaulted text. At most one optional question
  about a different title/image. Reward changes use the quest edit flow.

Use these defaults and state them in the proposal instead of asking: heading
"Quests" (`en-US`), block at the end of the home page (or in the existing block's
place when one exists), at most 6 cards (or fewer when fewer quests are chosen),
and the layout defaults in the [settings table](quests-block-brief.md#block-settings). The block shows
at most 24 quests. For the end of the home page, set the `add` operation's `index` to
the position of the page's `footer` block (so the Quests block lands above the footer),
or to the page's current block count when there is no footer. Read both from the gate's
backup. Never omit `index`, because an `add` without it puts the block first. Always set
the `add` operation's `version` field to the latest version in
[block-versions.md](block-versions.md) (`0.2.10`), themed or not.

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
check. Set `is_public` through the edit flow in [`quest-edit.md`](quest-edit.md#editing)
(read, change, full `PUT`, before/after diff, one approval, read back).

A `public_view` replaces the default view, and the card reads only from it. Add one only when the
publisher wants custom card text or an image. For a Web3 quest, send the full view below every time:
without the reward references, the card loses its reward row and its See in Backpack button
([Card rewards](rewards.md#card-rewards-on-the-quests-block)). Never set a `public_view` on an
`issue_catalog_item` quest: its items render as quantity only, so the card loses the reward name and
image that the default view gives.

```json
{"name": {"$ref": "quest.name"}, "description": {"$ref": "quest.description"}, "image_url": "https://...", "rewards": {"$ref": "reward.<node id>.items"}, "reward_type": {"$ref": "reward.<node id>.type"}}
```

- Values are text (at most 500 characters), a number, `true` or `false`, a `{"$ref": ...}` reference,
  or a group. Arrays and `null` are refused. At most 8 KB, 3 levels deep and 50 values.
- References: `quest.name`, `quest.description`, `quest.start_date`, `quest.end_date` and
  `reward.<node id>.<field>`. An `issue_web3_item` node exposes quantity, name, description, image_url
  and `type`. The public-quests guide lists no `items` field for a Web3 node, so check the `rewards`
  reference in the template on the read-back. An `issue_catalog_item` node exposes only `quantity`
  through `items` in a public_view, so it takes no full view.
- A reference that no longer resolves, such as a removed reward node, is left out of the card.
When it is added, `image_url` must be an absolute `https` URL (an `http` URL is refused, see
[Rules for every operation](quests-block-brief.md#rules-for-every-operation)). Never invent an
image. If the publisher has none, leave it empty and the card shows its neutral placeholder.

A quest triggered by an event the Quests block sends (`login_xsolla_id`, `daily_visit`,
`weekly_visit`) must set `client_sendable: true` on its trigger, or the block's event is refused
with 403. See [node-subtypes](node-subtypes.md#dynamic_event-client_sendable).

If the read-back does not show `is_public: true` (and the `public_view` you set, if any), stop and report that.

Reward content follows [card defaults](#ask-first); never put reward text in the title
or description to work around its read-only block behavior.

## Flow

1. **Choose quests.** List the existing quests (read-only) and agree the set, order
   and count with the publisher. A missing quest goes through the normal create flow
   in [`SKILL.md`](../SKILL.md), created only after a yes to that exact proposal. Say a quest is missing only after the list read
   is complete and shows no match. A partial summary cannot prove a quest is missing;
   report unresolved cards as unknown. If the read fails, say you cannot check whether it exists.
   **Missing quest offer:** a bold line that the quest doesn't exist yet, at most 2
   bullets, and one yes/no `Next:` ("want me to set it up?"). Under about 80 words. Do
   not detail the creation (player action, reward, schedule, event) before that yes.
   **No quests offer:** if the list read succeeds and shows no quests in the project,
   say the project has no quests yet, so the block has nothing to show, and offer to
   create one first: a bold line, at most 1 bullet that ends with the docs link
   https://developers.xsolla.com/api/quests, and one yes/no `Next:` ("want me to
   set up your first quest?"). After a yes, use the normal create flow in
   [`SKILL.md`](../SKILL.md) (API reference: https://developers.xsolla.com/api/quests),
   then come back here to add the block. Never say there are no quests when the read
   failed; say you cannot check yet.
2. **Make them public.** For each chosen quest that is not public (`is_public` is not
   `true`), set `is_public` per [Quest public view](#quest-public-view): one proposal,
   one approval. A missing `public_view` alone is not a reason to edit or stop. Stop if
   a quest is not found or the read-back does not show `is_public: true`. An `active`
   quest's `PUT` re-checks its dates ([dates on edit](quest-edit.md#editing)); put any
   date move in this same proposal, never a plan the server will reject.
3. **Build the brief.** For an appearance request, first follow
   [appearance](quests-block-appearance.md) and give the recommendation with its measured
   evidence. Turn only the agreed settings and defaults into `block_operations`.
   For an existing block, take its `block_id` and the `quest_id`s from the block
   summary (see [Gate commands](quests-block-brief.md#gate-commands)). With several
   Quests blocks on the site, "the Quests block" is the only visible one; target a
   hidden block only when the publisher points at it ("the copy", "the hidden one", a
   position), and ask which one only when several are visible. Check
   every key against the [settings table](quests-block-brief.md#block-settings) and
   the brief against the [rules](quests-block-brief.md#rules-for-every-operation).
4. **Render the plan.** Run [Gate commands](quests-block-brief.md#gate-commands) through
   preflight, target backup and rendering before showing anything. Show the exact leaf
   operations/values and created parents in [Plan shape](reply-format.md#write-proposals-plan-shape),
   then end the turn. No preliminary plan; apply only after the later exact-plan yes.
5. **Apply.** After confirmation, apply exactly the confirmed plan with the gate's
   apply command, which reads the result back. On a partial failure, do not rerun it;
   take a fresh backup and plan first.
6. **Read back.** Compare the gate's verification to the confirmed plan: settings and
   heading of each touched block, block order of each touched page, every other block
   unchanged, and each chosen quest reads back as public. In a partial quest lookup,
   only returned quests have known public status; an unresolved card is unknown and
   cannot satisfy the public readback check.
7. **Hand off.** Report what changed. Say the site
   is **not published**: the publisher previews and publishes it in Publisher Account.
   Anonymous visitors see the cards. Do not promise signed-in progress on a production
   site. Use the hand-off shape in [reply-format.md](reply-format.md#examples), with the
   returned `editor_url` as is. Report only the result and any skipped work or known gap.

If the gate cannot express an operation (no support, unknown key, block not found),
stop and report the gap. Never improvise raw `xsolla shopbuilder` commands.

## Removing the block

"Remove the Quests block" or "delete the Quests block" is `needs_human`. No script deletes
a block: `delete-block` needs `--force`, which no script passes, and a brief with a
`delete` op fails validation. First read the site's block summary
(`python3 "<skill base dir>/scripts/quests_block_summary.py"`, with `--slug <slug>` when the
site needs it) so the hide offer names the real block and its state (shown or hidden). Reply in the Delete request shape from
[reply-format.md](reply-format.md): the publisher deletes the block in the Site Builder
editor, and the skill offers to hide it. Run no gate step and build no plan for the delete
itself. If the publisher wants it hidden, that is a `hide` operation through the full
[Flow](#flow) (preflight, backup, plan, yes).

## Stop conditions and scope

Stop on any failed prerequisite, public/readback check, unsupported setting or missing
confirmation. Keep completed safe work; state the smallest next action. Site creation,
production sites, publishing/domains, other site changes and delivery claims remain out
of scope. [Reply examples](reply-format.md#examples) own refusals and localized/delete outcomes.

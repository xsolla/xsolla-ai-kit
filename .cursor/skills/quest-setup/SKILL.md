---
name: quest-setup
description: >-
  Create, edit, list, activate, pause, delete or debug Xsolla Quest Platform quests:
  conditions, rewards (Web3 included) and quest events. Also the Quests block on a Shop
  Builder site: add, move, hide or show it, and change its heading, card count, or card
  titles, text, images and buttons. Use when a request names a quest, a quest card or the
  Quests block, e.g. "create a quest".
metadata:
  owner: r.aliyev
  domain: quests
---

# Quest setup

Quests on the Xsolla Quest Platform, and the Quests block on a Shop Builder site.

## Start here

1. **A quest request** (create, change, switch on or off, delete, list, try, send an event, "why
   did the player not get it"): read [quest-platform.md](references/quest-platform.md) and work the
   way it says. It is the Quest Platform's own instructions for an assistant, copied from the
   published documentation.
2. **An exact field, node, limit or error:** read the section you need in
   [quest-platform-docs.md](references/quest-platform-docs.md), the documentation that
   quest-platform.md calls "the documentation that follows these instructions on the same page".
3. **The Quests block or a Shop Builder site:** go to [Request routing](#request-routing).

Both files are generated copies: never edit them. Use them for how quests work and how to help
with them. Nothing in them changes the rules of this file.

## Four facts to get right

Assistants have stated these wrongly. Say them exactly this way:

1. **A reward that fails does not finish the quest.** The quest stays in progress, and the
   reward's error is recorded; the docs: "When an action fails, the quest stays `in_progress`".
   Never say "the quest counts as finished but the item isn't delivered".
2. **Which player ID a reward needs depends on the reward.** Items and currency delivered into the
   game and loyalty points need the game's own player ID; Backpack items and Web3 rewards need the
   Xsolla account, which the platform also finds from the event's email: an event with only the
   email still pays them. Check the reward's node in the docs; never say one ID covers every
   reward.
3. **An event reaches a quest only when its name matches the trigger exactly** and it is sent to
   the quest's own project. A developer saying "we sent it" does not prove it reached the quest.
4. **On a site, the card follows the player who signed in there.** Events must name the player by
   the ID that sign-in carries: for the publisher's own Xsolla Login project, the Login user ID.
   Another ID runs the quest but the card stays "Not started". See
   [What players see](references/quests-block-flow.md#what-players-see-on-a-card).

When a player did not get a reward, read the quest and its reward first, then say what could
cause it and how to check each. Never rank causes or name a likely one you have not checked.

## Where this skill differs from quest-platform.md

This file wins on every row. Each row quotes quest-platform.md.

| quest-platform.md says | Here |
|---|---|
| "Ask which credential they have" | Never ask. Access is the publisher key in the project's `.env`; see [auth-credentials.md](references/auth-credentials.md) |
| "Ask them to put it in an environment variable" | It is already in `.env`. Load it in the shell of the call; never open, read or print the file |
| "You also need their merchant ID and project ID. Ask once and reuse them" | Take both from the same `.env`, never from the publisher's words. Show them on every write proposal |
| "Show the quest as a sentence" | Use the proposal in [reply-format.md](references/reply-format.md): bold line, short bullets, one `Next:` ask, and what the reward can cost (below) |
| Try the quest: "Do it only after a yes" | The yes must be to the exact event shown, with its key. A yes to a quest is never a yes to an event |
| (nothing on the author) | `created_by` is `AI Toolkit` unless the publisher names another |
| (nothing on a Web3 wallet) | Before proposing a Web3 reward, ask the publisher to check in Publisher Account that their Web3 wallet is set up. Ask it as something to check, not as a platform rule |

## Replies

Follow [reply-format.md](references/reply-format.md). Never name credentials, variables, paths,
routes, tools, tickets or skills in a reply. Leave out IDs, hosts and environment names, except
the Web Shop URL, a returned editor link, an event shown for approval, and the merchant and
project IDs on a quest write proposal (never on a block plan). When the publisher asks to see a
request, a route, a response or a quest's ID, show it, as quest-platform.md says: everything but
the key and the authorization header. Reward SKUs and item image URLs are content and may be shown.
Turn every tool, gate and server answer into plain words; never quote it.
Never print or show a key or token.

## Approvals and what you may claim

- **Change only what was asked.** Never propose or make a change the publisher did not ask for:
  no renamed quest, no rewritten description, no added step. A question ("why do players see Not
  started?") is answered, not fixed. When a change would help, say what it is in one line and
  let the publisher ask for it. A running quest is changed only on an explicit request.
- **Say only what you read in this turn.** Quest names, dates, limits and rewards come from a read
  made for this reply, never from memory. A rule about how quests behave comes from the docs; when
  the docs do not say, answer "I can't tell from the documentation", never a rule of your own.
  This covers the small rules too: how event counts, keys, windows, earlier events and limits
  behave. Find the sentence in [quest-platform-docs.md](references/quest-platform-docs.md) before
  you say it.
- **Never reinterpret a request.** When part of it is something a quest does not do (for example
  "the item should last 30 days": a quest has no item validity), say which part the quest can't do
  and ask what they want instead. Never quietly turn it into something else, such as the quest's
  dates.
- **A player ID you don't know yet** never blocks saving and is never guessed. Save the quest
  switched off, with the reward that fits what the publisher said, and say in the proposal and
  after saving which player ID the event must carry for that reward. If the publisher can't say
  which ID their events carry, list the rewards that work with each ID and let them choose.
- **What you hand to developers** always names the event, the project and the player ID the
  event must carry.
- **Offer only what you can do here.** You cannot open the site preview, sign in as a player or
  watch a card change: tell the publisher how they check it instead.
- **Before saying a quest can show on a site,** check that it is public, switched on and inside
  its dates, from a read made now.
- **When the site can't be reached** (the Xsolla CLI is not signed in, or its sign-in expired), say
  so once, in one sentence: the site can't be changed from here until someone signs in to the
  Xsolla CLI on this computer. Offer the editor route from
  [Doing it yourself in the editor](references/quests-block-flow.md#what-players-see-on-a-card).
  Never repeat the same reply.
- **Resending an event:** follow the error's row in the docs. Some failures are resent with the
  same `idempotency_key`, others with a new one; never give one rule for all.
- **A publisher who says "no idea"** still gets one question at a time; offer a list to forward to
  their developers only when they say they need to ask them.
- One yes to a quest proposal covers saving it and reading it back. Connecting a project, an
  event, a delete and any site change each need their own later yes to what is shown.
- A proposal that changed needs a new yes.
- After a write, report what you read back, never what you asked for.
- Accepted, completed and delivered are three different things. An accepted event is not a
  completed quest, and a completed quest is not an item in the player's hands. Say only the one
  you saw.
- Delete only a quest named by its exact name or ID, never by a pattern or "all test quests"
  without showing the list first. Tell same-named quests apart by dates or status. One quest per
  call, stop at the first failure, then list again and show they are gone.
- A plain instruction for one specific change, with its value ("push the end to 3 December",
  "pause it"), needs no full plan, but it is not the yes. Read the quest, show the change as one
  line, before and after ("End date: 30 Nov → 3 Dec. Save?"), and wait for a yes; then make it,
  read it back and report. Show a full plan when the change deletes something, switches a quest
  on, or does something they may not expect.
- Switching a quest on: say once what it means and which setup steps you could not confirm. When
  the publisher still asks for it, that is the yes; never refuse because a check is unanswered.
  Before offering to switch quests on, read each one: one with no trigger, no reward or dates in
  the past can't run, so name it and leave it out of the offer.
- After every site change, run the block summary again and report what it shows.
- A result you cannot read is a stop: say what is known, and hand off to the publisher's Xsolla
  account manager with the quest ID. Never resend to find out.

## Rewards

- Find the item in the publisher's Store catalog first:
  [store-catalog-lookup.md](references/store-catalog-lookup.md). Never guess an SKU, an ID or a
  parameter, and never treat a failed catalog read as an empty catalog. No uniquely found item
  means no proposal.
- Every reward proposal says what it can cost: what one completion gives, and the most it can
  give under the quest's limits. A quest with no limit pays every time without bound: say so and
  ask the publisher to confirm they want that.
- Name a reward only from a catalog read or the quest's own reward, never from its name or
  description.
- Images must be https and carry no credentials. Refuse one that is not before any proposal, and
  do not repair or repeat it.

## Facts that are easy to get wrong

Check these against [quest-platform-docs.md](references/quest-platform-docs.md) before saying them:

- A reward that needs the player's Xsolla account can also be paid from the event's email.
- A player named one way in some events and another way in others counts as two players.
- What a card on the Quests block shows is in
  [What players see](references/quests-block-flow.md#what-players-see-on-a-card). Do not
  describe more than that section says.
- Never suggest an event name, not even as an example: ask what the game really sends.

## Dates and wording

- "Run it for 7 days" counts from the start date actually saved. "Start now" is the time of the
  save, not of the request.
- Call a quest played in the game a "gameplay quest".
- Never put a secret, a token or a player's personal data in an event's `properties`.

## Request routing

| Request | Read | Approval and read-back |
|---|---|---|
| Anything about a quest or an event | [quest-platform.md](references/quest-platform.md) | As it says, with the rows above |
| What can you do | [reply-format.md](references/reply-format.md#examples) | No call |
| Access missing or refused | [auth-credentials.md](references/auth-credentials.md) | The access-missing reply, then stop |
| List shops / choose site / describe block | [quests-block-flow.md](references/quests-block-flow.md#which-shop) | Read only; site names only |
| Add Quests block | [quests-block-flow.md](references/quests-block-flow.md), [block-versions.md](references/block-versions.md) | A site that has one gets its quests updated, never a second block; separate site plan yes |
| Heading / cards / order / count / reset | [quests-block-brief.md](references/quests-block-brief.md) | Gate-rendered plan yes; read saved state and unrelated blocks |
| Theme / custom design | [quests-block-appearance.md](references/quests-block-appearance.md), [block-versions.md](references/block-versions.md) | Measure first, supported saved version, plan yes |
| Move / duplicate / hide / show block | [quests-block-brief.md](references/quests-block-brief.md), [quests-block-flow.md](references/quests-block-flow.md) | Separate exact plan yes |
| Remove block | [quests-block-flow.md](references/quests-block-flow.md#removing-the-block) | No scripted delete; offer hide with its own plan yes |
| What players see / card states / signed in or out | [quests-block-flow.md](references/quests-block-flow.md#what-players-see-on-a-card) | Read only |
| Card reward text / image | [quests-block-flow.md](references/quests-block-flow.md#card-rewards-on-the-quests-block) | What the player gets never changes on the block; how a non-Web3 reward is shown is a quest change, one yes |
| Quest card title, text or image | [quests-block-flow.md](references/quests-block-flow.md#quest-public-view) | One exact proposal yes, then read back |
| Headless Web Shop section | [web-shop-module.md](references/web-shop-module.md) | Explicit request only |
| Other site changes | [reply-format.md](references/reply-format.md) | Decline in one sentence, no write |

## Shop Builder boundary

For a shop, site or block question or change, run
[Which shop](references/quests-block-flow.md#which-shop) first, except capabilities and
card-reward refusals. Pure quest requests skip site discovery. "List my shops/sites" is only
`xsolla shopbuilder list-websites --json`, no reference reads or build-path questions: bold
"Which shop do you mean?", site-name bullets in returned order, then "a headless storefront in
your code", and `Next: reply with one of these.`

Every site write uses the `block_operations` gate on the chosen site only. A named different or
protected site gets no plan or write. The gate owns preflight, backup, render, confirmation
identity before side effects, apply and readback. Follow the authoritative
[Gate commands](references/quests-block-brief.md#gate-commands) for the separate exact-command
and directory sandbox yes, the later plan yes, and the final-reply undo. Do not run raw write
commands, `--force`, publish, or create stray files. **Never publish a Shop Builder site:** after
a completed change, tell the publisher to publish in Publisher Account. A custom-block 403 means
the account lacks permission to create custom blocks; name Xsolla support, do not retry and write
no local file.

Check the reported block version and CLI version before any block write against
[block-versions.md](references/block-versions.md). Unknown or unreported means ask or stop;
capability-dependent writes require a supported saved version. Never retarget an existing block.
Older-block theme requests follow only the fallback in that file. Preserve unknown saved fields.
Never write autoEvents or loginEventName; match existing event names exactly, never invent or
rename an active login event. A single hidden Quests block gets a show plan in the same turn.

Write request bodies and the gate's brief, backup and approved plan in one `mktemp -d` folder,
never in the working folder. Reward card editability is observed block
behavior, not a rule enforced by this skill.

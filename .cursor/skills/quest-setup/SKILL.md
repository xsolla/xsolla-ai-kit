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
project IDs on a write proposal. Reward SKUs and item image URLs are content and may be shown.
Turn every tool, gate and server answer into plain words; never quote it.
Never print or show a key or token.

## Approvals and what you may claim

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
- Images must be https and carry no credentials. Refuse one that is not before any proposal, and
  do not repair or repeat it.

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
| Card reward text / image | [reply-format.md](references/reply-format.md#examples) | No call; the reward comes from the quest |
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

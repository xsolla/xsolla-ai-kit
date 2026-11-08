# Rewards

A reward is an action node that grants something from the publisher's real store catalog. Which
reward nodes exist, their parameters and limits, what each needs from the event and how each
behaves on failure come from the node catalog and the Quest nodes guide
([live-docs.md](live-docs.md)). This file holds the reward decision, the catalog lookup and the
safety rules this skill adds. This skill never claims delivery to the player's Backpack or wallet.

## Reward types come from the live docs

Reward types come from the live docs and the node catalog. A reward node absent from the node
catalog is rejected, with no write; a node the docs mark as legacy or deprecated is never used in a
new quest. Build its parameters only from the node's schema in the catalog.

**The reward decision.** A named item from the catalog is granted as a Web3 item (the catalog's
Web3 item node) by default. Use a Backpack grant (the catalog item node) when the publisher chooses
it for the quest, shown in the proposal and confirmed with a yes. Use another reward node the
catalog lists (an in-game item, currency, tokens, loot boxes, loyalty points) only when the
publisher asks for that kind of reward, and only after reading its docs: some need setup on the
publisher's side or by Xsolla first, and the proposal says so. Never ask Backpack versus Web3 on
your own, and never switch away from the publisher's choice because of a docs difference: mention
the difference in one clause only if it matters.

Only a real catalog item is rewardable. When the publisher asks for something the catalog does not
have (for example "coins"), say the catalog has no such item and ask which catalog item to use.
Never substitute silently. When a reward path fails, stop and ask; never fall back to another path.

## Adding a reward

"Add a reward to my quest" appends. Read the quest, add one reward node with a fresh UUID,
connect it like the existing reward action, and keep every existing node and connection. The
proposal shows the before/after list of reward actions: `before: Welcome Badge x10; after: Welcome
Badge x10 and <new>`. Replace an existing reward only on an explicit "replace" request. The new
item still comes from the publisher and a verified lookup (see below). Send the full update as in
[quest-edit.md](quest-edit.md#editing).

## Named item behavior

When the publisher requests a named item (`<requested item>`):

- resolve it only through the read-only [Store catalog](#store-catalog) lookup. Page through the
  whole catalog and match the requested name. Never use public web search for catalog lookup;
- when it returns exactly one verified candidate, use that candidate's SKU in the reward node, and
  show the item's name, SKU and image URL (when it has one) in the proposal. The image URL is item
  content, not a service host;
- when it returns multiple plausible candidates, ask the publisher to choose before any Quest
  Platform write;
- if the catalog is unavailable or rejects the read, stop before any Quest Platform write and
  report that the item lookup could not be reached; do not say the publisher's catalog needs
  connecting. If a completed search returns zero candidates, say the item was not found and
  suggest checking its exact name or whether it is enabled. Do not ask the publisher to type a
  catalog project or SKU: a typed value is not a verified candidate. When the publisher supplies a
  SKU anyway, even with "no need to check", validate it with the single-item read and stop before
  any write if it is not found or not grantable;
- default quantity to one and show it in the concise proposal;
- never guess an SKU.

Use only the configured project's catalog, never a publisher-typed project or one from another
catalog.

## Card rewards on the Quests block

The card shows the quest's public view. What the default view contains, and which reward fields a
`public_view` can reference for each reward node, are in the Public quests guide. Follow
[Quest public view](quests-block-flow.md#quest-public-view) for when to set one.

- **Proposal.** Show the card rewards as lines: name, SKU, quantity and image URL, for example
  `Handful of BitChips x1 (SKU com.example.sku, image https://...)`.
- **Read-back.** Read the public list (the contract's public quests operation, no credential) and
  confirm the quest's view shows each reward. A missing name or image means the catalog lookup did
  not enrich the entry: report it, never say the card is fine.

## Exposure and recipient

- **Recipient.** Each reward node's docs say which player identifier the event must carry and
  whether guests can receive it. Ask the publisher for that identifier in the event review; for a
  Web3 reward, also follow [Recipient wallet](#recipient-wallet).
- **Repeat.** The docs say whether a reward node pays once per player per quest on its own. When a
  confirmed payout already exists for the same player and quest, never send an event that could
  pay again; if the earlier payout is unresolved, stop and escalate rather than resend.
- **Amounts.** Quantity and amount bounds come from the node's schema. State them; never guess a
  token's decimals or a currency's units.

## Payout exposure in the proposal

Show three bounds in the publication proposal:

- **Per event and user:** what one run grants (quantity times the number of SKUs, or the amount).
  For a once-per-user named item at quantity one this is one item.
- **Per user for the quest:** apply the effective activation limit to the per-event grant. For a
  confirmed once-per-user named item this is one item per user and quest.
- **Total quest exposure:** multiply the per-user bound by the maximum number of eligible users.
  If the user population, event count, activation limit or date window is not finite, report the
  total as **unbounded**.

Do not publish a repeatable reward without showing these calculations in the proposal. An
unbounded total needs an explicit acknowledgement in that same approval.

## Completion evidence

Execution completion does not prove Backpack display, wallet balance or on-chain finality
([three separate claims](verification.md#three-separate-claims)). Report only production evidence
and never resend an event after an uncertain result except as [events.md](events.md#after-an-uncertain-response)
allows. Activation can create real payouts; show the reward and
[exposure](#payout-exposure-in-the-proposal) in its exact publication proposal.

## Store catalog

Resolve a named item through the Store catalog reads of the request script, which reads only the
configured project's catalog:

| Command | Use |
|---|---|
| `qp_request.py catalog-list --query limit=50 --query offset=<offset>` | page the full catalog |
| `qp_request.py catalog-item <sku>` | validate a SKU the publisher typed |

Never create or change catalog items, even when the publisher asks; that is outside this skill.
Never call a claim or minting service. Rewards are issued only by an activated quest.

Start at offset 0 and, while the page's `has_more` is `true`, advance the offset by the number of
items on that page. Require a successful answer with an `items` array, a boolean `has_more` and a
numeric `total_items_count` on every page. Abort the lookup on a 401, any other failure, a
malformed body, an empty page with `has_more: true`, or a final item count different from
`total_items_count`; never treat an aborted read as an empty catalog. Read the complete catalog
before deciding that a name has zero, one or several matches.

Match the requested name case-insensitively against the item's English name first, then against
its other locales. An exact match is a candidate; when there is no exact match, items whose name
contains the requested words are candidates to show, never to pick on your own.

Only an item that can be granted is a valid reward SKU: it is enabled, shown in the store, and has
no sale period or one that contains the current time. When the requested name matches only items
that fail this rule, say the item exists but is not available as a reward (disabled, hidden from the
store or outside its sale period) and stop.

A SKU the publisher typed is validated with the single-item read: require success, the same SKU
and the rule above. Not found means the SKU is not in the catalog. Abort on any other failure. A
zero or ambiguous result stops the flow.

## Recipient wallet

There is no publisher route to check a player's Web3 wallet, so the skill makes no wallet call.
Never call a minting or wallet service directly and never guess a host for it.

When the recipient is known, ask the publisher to confirm in Publisher Account that the recipient
has the wallet the Web3 node's docs require, before the proposal; otherwise confirm before any
publication write. Confirm it again before the event. Until confirmation, no publication or event
write is allowed: report the wallet as not verified, never as "no wallet" or a confirmed wallet.
Name the unverified recipient wallet in the proposal or event payload review. If the publisher says
the player has no wallet, this is a non-retryable blocker for a Web3 reward, not an approval step.

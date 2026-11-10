# Rewards

## Choose from the node catalog

What a publisher can build comes from their own node catalog, not from this file. Before any quest
proposal, read it and the public docs:

- `python3 "<skill base dir>/scripts/qp_request.py" GET /api/v2/merchants/<merchant_id>/projects/<project_id>/quests/node-types`
  returns every node this project can use, with its description and parameter schema.
- `python3 "<skill base dir>/scripts/qp_docs.py"` gives the publisher guides.

Any reward, trigger or condition in the catalog can be used; none is preferred. A node absent from
the catalog is refused, with no write. The node shapes in this file are snapshots for orientation;
the catalog and live docs win on any difference.

**Offer the options, the publisher picks.** When the publisher hasn't said exactly what they want,
ask one question with short bullets built at runtime from the `node-types` response: every node it
returns for that role (reward, trigger, condition), **in the order it returns them**, named in plain
words, each with the constraint stated in that node's own description (who it needs, how often it
pays). This file holds no list or ranking of node kinds; never offer a node the response did not
return, and never reorder or leave one out to favour another. Where an option needs a real item,
name it from the store catalog (name and SKU). For a quest on a Shop Builder site, the trigger menu
also lists the Quests block's [built-in events](node-subtypes.md#choosing-a-trigger). Then show the
exact proposal, then create after its yes.

**Constraints first.** When an option's constraint does not fit the request (for example a node that
pays once per player, on a repeating quest), say so before the proposal and let the publisher choose.

**Limits and schedule are the publisher's choice.** Activation limits (`per_user` and/or `global`,
`count`, an optional `time_window` of `day`, `week` or `month`, or none), the start and end dates, and
every node parameter whose schema has limits (`quantity`, `amount`, ...) are set by the publisher.
When the request does not fix them, offer them in the same one-question style, with the values the
docs and schema allow and one suggestion that matches the request ("weekly" suggests `per_user` 1
per `week`). Never pick a window, count, date or quantity silently. The proposal shows the chosen
limits and schedule and the [exposure](#payout-exposure-in-the-proposal) they give; no limit at all
is shown as unlimited and needs its own acknowledgement.

**Parameters the publisher supplies** (a loyalty program, a CRM segment, a currency SKU, a webhook
URL): read them where an API exists (the store catalog), otherwise ask. Never guess one.

Only a real catalog item is rewardable. When the publisher asks for something the catalog does not
have (for example "coins"), say so and offer what it has. Never substitute silently. The reward is
granted or minted as the platform response reports; this skill does not claim delivery beyond it, and when a reward
path fails, stop and ask rather than switching to another one.

## Card rewards on the Quests block

The Quests block card shows a reward only from `view.rewards` on the public quest. The server builds
that array itself, one entry per reward node, and only when the quest has no `public_view` (or it is
`{}`). The skill never writes `view.rewards` directly: `public_view` takes no arrays, so a literal
rewards list is refused.

- **Web3 item, default view.** Leave `public_view` out when the card must show its reward. Each
  entry carries `type` (`web3_item`), `quantity` (default 1), and the catalog `name`, `description`
  and `image_url` of the SKU. Title and description come from the quest.
- **Every other reward.** The server fills the name and image only for Web3 items: any other reward
  entry has `name` and `image_url` null, so with no `public_view` the card shows no reward. Always
  write the [static-reward view](quests-block-flow.md#quest-public-view), with the reward name and
  image as static values from the catalog read (`reward_name`, `reward_image_url`, and `reward_type`
  as the reward's type, `inventory_item` for a Backpack item). Never promise a card reward you did
  not put there.
- **Custom view.** A `public_view` replaces the default view. For a Web3 quest, set it only in full, with
  the reward references from [Quest public view](quests-block-flow.md#quest-public-view), or the card
  loses its reward row and its See in Backpack button.
- **Proposal.** Show the card rewards as "Card reward" lines: name, SKU, quantity and image URL, for
  example `Handful of BitChips x1 (SKU com.example.sku, image https://...)`.
- **Read-back.** Read the public list with
  `python3 "<skill base dir>/scripts/qp_request.py" GET /api/v2/public/merchants/<merchant_id>/projects/<project_id>/quests --public`
  (no credential is sent) and confirm the quest's `view.rewards` has one entry per reward, or for a
  Backpack-item quest that `reward_name` and `reward_image_url` read back. A null `name` or `image_url` means the catalog lookup
  did not enrich the entry: report it, never say the card is fine. For a custom view, confirm the
  public read shows each reward field the view references; a missing field means its reference does
  not resolve.

## Adding a reward

"Add a reward to my quest" appends. Read the quest, add one reward action node (`issue_web3_item` or
`issue_catalog_item`) with a fresh UUID and connect it like the existing reward action, and keep every existing node and connection. The
proposal shows the before/after list of reward actions: `before: Welcome Badge x10; after: Welcome Badge
x10 and <new>`. Replace an existing reward only on an explicit "replace" request. The new item still
comes from the publisher and a verified lookup (see below). Send the full `PUT` as in
[quest-edit.md](quest-edit.md#editing).

## Named item behavior

When the publisher requests a named item (`<requested item>`):

- resolve it only through an available supported reward capability (catalog or
  type-specific provider read). For a store catalog item, the supported
  capability is the read-only Store admin catalog lookup documented in
  [Store admin catalog](#store-admin-catalog). Page
  through the whole catalog and match the requested name against the mintable
  items. Never use public web search for catalog lookup;
- when the capability is available and returns exactly one verified candidate,
  use that candidate's SKU and the catalog project the read was scoped to in
  the reward node's parameters, and show the item's name, SKU and image URL (when it
  has one) in the proposal. The image URL is item content, not a service host;
- when it returns multiple plausible candidates, ask the publisher to choose
  before any Quest Platform write;
- if the service is unavailable or rejects the read, stop before any Quest
  Platform write and report that the item lookup service could not be reached;
  do not say the publisher's catalog needs connecting. If a completed search
  returns zero candidates, say the item was not found and suggest checking its
  exact name or whether it is enabled. Do not ask the publisher to type a
  catalog project or SKU: a typed value is not a verified candidate. When the
  publisher supplies a SKU anyway, even with "no need to check", validate it
  with the single-item read and stop before any write if it is not found or
  not mintable;
- default quantity to one and show it in the concise proposal;
- never guess an SKU or use the fallback reward paths forbidden above.

Never ask whether the destination is Backpack. Use only the configured catalog-read
project, never a publisher-typed project or one from another catalog.

## Project mismatch

When a read-back shows a project different from `body.project`, report a delivery
mismatch, not a success, and do not send the event again.

## Backpack grants (`issue_catalog_item`)

Use this path when the publisher chooses it for a quest, or when Web3 minting is unavailable or
slow. A Web3 mint can stall and leave the payout unknown with no retry (agent-only background;
never tell the publisher about past incidents). A Backpack grant mints nothing
and needs no wallet.

- **Node.** `issue_catalog_item` is an action node with `items` and `purpose` in `parameters`, with
  no `type` or `body` wrapper. Parameter rules are in
  [node-subtypes](node-subtypes.md#issue_catalog_item).
- **SKUs.** Resolve each item through the [Store admin catalog](#store-admin-catalog), as for Web3,
  and show its name, SKU and quantity in the proposal. Never guess a SKU. A SKU the publisher types
  goes through the single-item read.
- **Exposure.** Show the per-user total (item quantities times the activation limit) and the total
  quest exposure, using the same method as [Payout exposure](#payout-exposure-in-the-proposal).
- **Recipient.** Each event needs an `xsolla_id`. The wallet check in [Recipient wallet](#recipient-wallet)
  does not apply.
- **Retries.** Never resend an event after an uncertain result, as for Web3.
- **Card.** Always write the [catalog-item view](quests-block-flow.md#quest-public-view): the server
  gives an `issue_catalog_item` reward no name or image, so the reward name and image go in as static
  `reward_name` and `reward_image_url` from the catalog read, with `reward_type: inventory_item` (that
  type keeps the See in Backpack button). A card image of its own (`image_url`) is added only when the
  publisher gives one.

## `issue_web3_item`

A Web3 item is an action node with `subtype: issue_web3_item` (the older
`issue_reward` with `type: web3_item` is deprecated; never write it). Its parameters
need a nonempty `purpose`; use `quest_completion` for a named item unless the developer
requests another reason. It mints an NFT from a Store admin catalog item, at most once
per player and quest:

```json
{
  "purpose": "quest_completion",
  "project": "<project id the catalog read was scoped to>",
  "item_sku": "<string or array>",
  "quantity": 1
}
```

`quantity` must be a non-negative integer. For a named item, use a real SKU
returned by the Store admin catalog lookup. Omitting `item_sku` lets the provider choose an
item and is not allowed for a named reward.

The production runtime must enforce the once-per-user-per-quest rule. When a
confirmed payout already exists for the same user and quest, a repeat event
must not mint a second item. If the earlier payout is unresolved, stop and
escalate rather than resend the event.

## `issue_web3_token`

Offer a Web3 token only when the node catalog lists `issue_web3_token`. It sends `amount` whole
tokens of `item_sku` to the player's wallet; the event needs `xsolla_id`, and the project and SKU
pair must be configured for Web3 token payouts. Take the token SKU and amount from the publisher,
never guess them, and follow the catalog's limits (today: amount above 0, at most 10000):

```json
{
  "purpose": "quest_completion",
  "project": "<token project, or empty for the configured one>",
  "item_sku": "<token SKU>",
  "amount": 1
}
```

The [project-mismatch stop](#project-mismatch) applies to tokens too.

## Recipient

Web3 rewards need an `xsolla_id` in the event and a production wallet for that user. A Backpack
grant needs only the `xsolla_id`. Follow [Recipient wallet](#recipient-wallet) for the confirmation timing,
compatible wallet source and blockers.

## Payout exposure in the proposal

Show three bounds in the publication proposal:

- **Per event and user:** a Web3 item is `quantity × selected SKU count`;
  for a once-per-user named item at quantity one this is one NFT.
  a Web3 token is `amount`; any other reward is its quantity per event.
- **Per user for the quest:** apply the effective activation limit to the
  per-event quantity. A Web3 item is paid at most once per player and quest whatever the
  limit. A `per_user` day limit resets per UTC calendar day, so a 7×24h window that starts
  mid-day spans 8 calendar days: count 8, not 7. For a confirmed once-per-user named item this is one NFT
  per user and quest; for quantity greater than one or multiple SKUs, multiply
  by `quantity × selected SKU count`. For a Web3 token, multiply `amount` by
  the maximum qualifying events for that user.
- **Total quest exposure:** multiply the per-user bound by the maximum number
  of eligible users. If the user population, event count, activation limit or
  date window is not finite, report the total as **unbounded**.

Do not publish a repeatable Web3 reward without showing these calculations in
the proposal. An unbounded total needs an explicit acknowledgement in that
same approval.

## Completion evidence

Execution completion does not prove Backpack display, wallet balance or on-chain finality
([three separate claims](verification.md#three-separate-claims)). Report only production evidence and never
resend an event after an uncertain result. Activation can create real payouts; show the
reward and [exposure](#payout-exposure-in-the-proposal) in its exact publication proposal.

## Store admin catalog

Resolve a named `web3_item` through the Store admin virtual items reads at
`https://store.xsolla.com/api/v2/project/{project_id}/admin/items/virtual_items`,
with `{project_id}` set to the project id of the configured scope. Use only these
two GET routes:

| Route | Use |
|---|---|
| `GET .../admin/items/virtual_items?limit=50&offset={offset}` | page the full catalog |
| `GET .../admin/items/virtual_items/sku/{sku}` | validate a SKU the publisher typed |

Both reads go only through the request script with the `--store` flag, for example
`python3 "<skill base dir>/scripts/qp_request.py" GET /api/v2/project/{project_id}/admin/items/virtual_items --store --query limit=50 --query offset=0`
or `GET /api/v2/project/{project_id}/admin/items/virtual_items/sku/<sku> --store`. The
script fills `{project_id}` from the configured set and refuses any other store route,
any other method and a different project id (`scope_mismatch`).

Never issue a `POST`, `PUT`, `PATCH` or `DELETE` to any Store admin route, even
when the publisher asks for it; creating or editing items is outside this
skill. Never call a claim endpoint directly. Rewards are issued only by an
activated quest.

Start at offset 0 and, while the page's `has_more` is `true`, advance the
offset by the number of items on that page.
Require HTTP 200 and a JSON object with an `items` array, a boolean `has_more`
and a numeric `total_items_count` on every page. Abort the lookup on a 401, any
other non-200 status, a malformed body, an empty page with `has_more: true`,
or a final item count different from
`total_items_count`; never treat an aborted read as an empty catalog. Read the
complete catalog before deciding that a name has zero, one or several matches.

Each item has `sku`, a localized `name` object (for example `{"en": "Fire
Sword"}`), a localized `description` or `null`, `image_url` or `null`, `type`,
`is_enabled`, `is_show_in_store`, `periods`, `groups` and `attributes`. Match
the requested name case-insensitively against `name.en` first, then against the
other locales. An exact match is a candidate; when there is no exact match,
items whose name contains the requested words are candidates to show, never to
pick on your own.

Only an item that is mintable is a valid `web3_item` SKU: `is_enabled` and
`is_show_in_store` are both `true`, and `periods` is empty or one period
contains the current time. When the requested name matches only items that
fail this rule, say the item exists but is not available as a Web3 reward
(disabled, hidden from the store or outside its sale period) and stop.

A named item is resolved from the list pages alone. A SKU the publisher typed
is validated with the single-item read instead: require HTTP 200, the same
`sku`, and the mintable rule above. A 404 means the SKU is not in the catalog.
Abort on any other failure. The catalog project for the `web3_item` body is the
project id the read was scoped to. A zero or ambiguous result stops
the flow.

## Recipient wallet

There is no public route to check a user's Web3 wallet, so the skill makes no
wallet call. Never call a minting or wallet service directly and never guess a
host for it.

When the recipient is known, ask the publisher to confirm in Publisher Account that the
recipient (`xsolla_id`) has the Backpack-compatible managed wallet required by the
production integration before the proposal; otherwise confirm before any publication
write. Confirm it again before the event. Until confirmation, no publication or event
write is allowed: report the wallet as not verified, never as "no wallet" or a confirmed
wallet. Name the unverified recipient wallet in the proposal or event payload review.
If the publisher says the user has no wallet, this is a non-retryable blocker for a
Web3 reward, not an approval step.

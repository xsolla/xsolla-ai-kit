# Web3 rewards

This skill supports the production Web3 reward path only. A named item always
uses `web3_item` and is delivered to the player's Backpack. Do not offer
`inventory_item`, Store API grants, direct Backpack grants, ERC-20 claim
endpoints or a provider-default catalog as fallbacks.

These are the `parameters` of a node with `type: action` and
`subtype: issue_reward`:

```json
{
  "type": "web3_item",
  "purpose": "quest_completion",
  "body": {
    "project": "<XSOLLA_PROJECT_ID the catalog read was scoped to>",
    "item_sku": "<catalog SKU>",
    "quantity": 1
  }
}
```

The wrapper needs a supported `type`, a non-empty `purpose` and a non-empty
`body`. Use `quest_completion` for a named item unless the developer requests a
different reason.

## Named item behavior

When the publisher requests a named item (`<requested item>`):

- resolve it only through an available supported reward capability (catalog or
  type-specific provider read). For production `web3_item`, the supported
  capability is the read-only Store admin catalog lookup documented in
  [auth and environment](auth-and-environment.md#store-admin-catalog). Page
  through the whole catalog and match the requested name against the mintable
  items. Never use public web search for catalog lookup;
- when the capability is available and returns exactly one verified candidate,
  use that candidate's SKU and the catalog project the read was scoped to in
  the `web3_item` body, and show the item's name, SKU and image URL (when it
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
- never guess an SKU or silently substitute another reward type
  (`inventory_item`, Store API grants, direct Backpack grants, ERC-20 claim
  endpoints, or a provider-default catalog).

Never ask whether the destination is Backpack. The catalog project is the
`XSOLLA_PROJECT_ID` the Store admin read was scoped to, never a value the
publisher typed and never a project from another catalog.

## `web3_item`

An NFT minted from a Store admin catalog item:

```json
{
  "type": "web3_item",
  "purpose": "quest_completion",
  "body": {
    "project": "<catalog project>",
    "item_sku": "<string or array>",
    "quantity": 1
  }
}
```

`quantity` must be a non-negative integer. For a named item, use a real SKU
returned by the Store admin catalog lookup. Omitting `item_sku` lets the provider choose an
item and is not allowed for a named reward.

The production runtime must enforce the once-per-user-per-quest rule. When a
confirmed payout already exists for the same user and quest, a repeat event
must not mint a second item. If the earlier payout is unresolved, stop and
escalate rather than resend the event.

## `web3_token`

Production runs have ERC-20 payouts disabled. A production quest with a
`web3_token` action fails at payout. When a production request asks for a
token payout, stop before any Quest Platform write, say that token payouts are
not available for the project yet, and offer a named item reward instead. Do not ask the publisher for a token
binding or decimals, because no production binding can make the payout work.
Use the shape below only when the Quest Platform owner has confirmed that
ERC-20 payouts are enabled for the project.

An ERC-20 payout, only when the token binding and runtime contract are
confirmed:

```json
{
  "type": "web3_token",
  "purpose": "quest_completion",
  "body": {
    "project": "<token project>",
    "item_sku": "<bound token SKU>",
    "amount": 10000
  }
}
```

`amount` must be a positive integer in the token's base units and within the
selected target's contract limit. Confirm the token decimals and binding with
the owner of that target. Never guess them.

`web3_item.body.project` selects the catalog only when the deployed reward
worker supports it. A worker without that support ignores the field and mints
against its configured default project, so the item can reach the wallet but
show without the catalog name. When a read-back shows a project different from
`body.project`, report a delivery mismatch, not a success, and do not send the
event again.

## Recipient

Both Web3 reward types need an `xsolla_id` in the event and a production wallet
for that user. When a recipient is known, check the wallet with the recipient read in
[`auth-and-environment.md`](auth-and-environment.md#recipient-wallet) during the
read-only work before the proposal, or otherwise before any publication write.
Check it again before the event. A missing wallet is a non-retryable blocker,
not an approval step. Confirm the wallet source is the Backpack-compatible
managed wallet required by the production integration.

## Payout exposure in the proposal

Show three bounds in the publication proposal:

- **Per event and user:** `web3_item` is `quantity × selected SKU count`;
  for a once-per-user named item at quantity one this is one NFT.
  `web3_token` is `amount`.
- **Per user for the quest:** apply the effective activation limit to the
  per-event quantity. For a confirmed once-per-user named item this is one NFT
  per user and quest; for quantity greater than one or multiple SKUs, multiply
  by `quantity × selected SKU count`. For `web3_token`, multiply `amount` by
  the maximum qualifying events for that user.
- **Total quest exposure:** multiply the per-user bound by the maximum number
  of eligible users. If the user population, event count, activation limit or
  date window is not finite, report the total as **unbounded**.

Do not publish a repeatable Web3 reward without showing these calculations in
the proposal. An unbounded total needs an explicit acknowledgement in that
same approval.

## Completion evidence

An execution marked `COMPLETED` proves only that the reward action completed
according to the production execution contract. It does not by itself prove a
Backpack display, wallet balance or on-chain finality. Report only the evidence
returned by the production read-back and never resend an event after an
uncertain result.

Attaching either reward type to an activated quest can create a real payout.
Show the reward and its exposure in the publication proposal; the one approval
covers activation of that exact configuration.

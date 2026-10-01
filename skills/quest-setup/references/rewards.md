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
    "project": "<catalog project returned with the item>",
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
  type-specific provider read). This skill invents no MCP tool name, payload
  schema, or endpoint for that capability, and never uses public web search for
  catalog lookup. **STAGE DEMO ONLY:** when the
  [stage demo gate](stage-demo.md#gate) passes, the capability is
  [Named item resolution](stage-demo.md#named-item-resolution); on any other
  run none is available;
- when the capability is available and returns exactly one verified candidate,
  use that candidate's catalog project and SKU in the `web3_item` body;
- when it returns multiple plausible candidates, ask the publisher to choose
  before any Quest Platform write;
- when the capability is absent, unavailable, or returns zero candidates, stop
  before any Quest Platform write with a concise actionable next step. The next
  step is making a catalog capability available (or fixing the item name when
  the lookup found nothing). Do not ask the publisher to type a catalog project
  or SKU: a typed value is not a verified candidate. When no capability is
  available, the reply says only that the item can't be looked up in their
  catalog yet, that nothing was created, and that the next step is connecting
  their item catalog; it asks for nothing else;
- default quantity to one and show it in the concise proposal;
- never guess an SKU or silently substitute another reward type
  (`inventory_item`, Store API grants, direct Backpack grants, ERC-20 claim
  endpoints, or a provider-default catalog).

Never ask whether the destination is Backpack. Preserve the catalog project
returned by the verified candidate; never copy the Quest Platform project as
the catalog project by default.

## `web3_item`

An NFT from the production minting catalog:

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
returned by the catalog lookup. Omitting `item_sku` lets the provider choose an
item and is not allowed for a named reward.

The production runtime must enforce the once-per-user-per-quest rule. When a
confirmed payout already exists for the same user and quest, a repeat event
must not mint a second item. If the earlier payout is unresolved, stop and
escalate rather than resend the event.

## `web3_token`

Production runs have ERC-20 payouts disabled: the production quest worker has
no ERC-20 project configured (`qp-worker-generic-quest/environments/prod/configs/configs.yaml`,
`WEB3_ERC20_PROJECT: ''`). A production quest with a `web3_token` action fails at
payout. When a production request asks for a token payout, stop before any
Quest Platform write, say that token payouts are not available for the project
yet, and offer a named item reward instead. Do not ask the publisher for a token
binding or decimals, because no production binding can make the payout work.
Use the shape below only when the selected target has ERC-20 enabled (the
`stage` selector today).

An ERC-20 payout, only when the token binding and runtime contract for the
selected target are confirmed:

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

## Recipient

Both Web3 reward types need an `xsolla_id` in the event and a production wallet
for that user. When a recipient is known, check the wallet during the
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

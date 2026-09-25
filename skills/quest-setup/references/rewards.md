# Rewards

Stage OpenAPI and local runtime snapshots were checked on 2026-09-23; the
event-side requirements were rechecked in the stage worker code on
2026-09-25. The stage deployment revision is not pinned here, so revalidate
before writes.

These are the `parameters` of a node with `type: action` and
`subtype: issue_reward`. The OpenAPI document does not describe them, because
the body is carried as raw JSON.

## Wrapper

```json
{"type": "<reward type>", "purpose": "<string>", "body": { }}
```

`type`, `purpose` and a non-empty `body` are all required. An unrecognised
`type` is rejected. `purpose` is a free, non-empty string, for example
`quest_completion`, that the worker forwards to the reward provider as the
reason. Ask the developer for it.

Every reward type pays out for real through its provider. Ask which reward,
amount and purpose the developer wants; never propose one as a default. For a
smoke test, offer the no-op action in [`node-subtypes.md`](node-subtypes.md).

## Bodies

| `type` | `body` | Rules |
|---|---|---|
| `xsolla_points` | `{"amount": <number>}` plus optional `campaign_name`, `campaign_image`, `event_name`, `reason_quest_id`, `app_name`, `app_icon_url` | `amount` greater than 0 |
| `virtual_currency` | `{"amount": <number>}` | `amount` greater than 0 |
| `loyalty_points` | `{"amount": <number>, "loyalty_points_id": "<string>"}` | both required |
| `lootbox` | `{"item_sku": "<string>", "quantity": <int>}` | `quantity` 1 to 100 |
| `custom` | `{"amount": <number>, "currency_ticker": "<string>"}` | `amount` greater than 0 |
| `inventory_item` | `{"xsolla_item": <bool>, "items": [{"sku": "<string>", "quantity": <int>, "type": "<string>", "name": "<string>", "image_url": "<url>", "model_3d_url": "<url>"}], "item_sku": "<string>", "name": "<string>", "image_url": "<url>", "model_3d_url": "<url>"}` | `items` or `item_sku`; item quantity 0 to 100 and defaults to 1 at runtime |
| `vc_wallet_ticket` | `{"quantity": <int>, "currency_ticker": "<string>"}` plus optional `playtime` | `quantity` greater than 0 |
| `web3_item` | `{"item_sku": <string or array>, "quantity": <int>}` plus optional `project` | body must not be empty. `quantity` at least 0, read back as 1 when absent. No `item_sku` means a random item, see below. The worker ignores `xsolla_item` here; omit it |
| `web3_token` | `{"item_sku": "<string>", "amount": <integer>}` plus optional `project` | both required. Keep `amount` a positive integer in base units, at most 10000; the worker enforces the cap at payout, see below |

The optional `playtime` object on `vc_wallet_ticket` is
`{"earn_rate_minutes": <greater than 0>, "daily_cap_minutes": <greater than 0>, "timezone": "<non-empty>"}`.

For `inventory_item`, `xsolla_item` picks where the worker takes the
publisher and project for the grant: `true` from the quest, `false` from the
event's `publisher`. Ask the developer which. Provide either `items` or the
single-item `item_sku` form. `name`, `image_url` and `model_3d_url` are supported with the single-item
form; obtain real catalog values from the developer. An empty body can mean a
runtime-selected item, so do not treat acceptance as proof of a particular SKU.

## Event-side requirements

Some reward types take the merchant, the project or the user from the
**event**, not from the quest (stage worker code, 2026-09-25, revalidate).
Check this before activation and again when you build the event:

| `type` | The event must carry | Without it |
|---|---|---|
| `xsolla_points`, non-guest user | a `publisher` block; the merchant comes from its `publisher_id` | `FAILED`, `publisher information is required but not provided in event` or `merchant_id is required for xsolla_points rewards` |
| `virtual_currency`, `loyalty_points` | a `publisher` block with `project_id`, and a `gamer_id` in `user_ids` | `FAILED`, the error names the missing value |
| `inventory_item` with `xsolla_item: false` | a `publisher` block | `FAILED` |
| `web3_item`, `web3_token` | an `xsolla_id` whose user has a wallet, see "Web3 recipient" | `FAILED`, `RecipientNotFound` |

The `publisher` block must still equal the quest's `publisher_id` and
`project_id` exactly, or the event matches no quest at all; see
[`events.md`](events.md). So for these types send the quest's own values,
never different ones. `xsolla_points` for a guest user is skipped by the
worker and reported as completed without a grant on stage.

## Web3 recipient

Both `web3_item` and `web3_token` pay to the wallet of the event's user. The
event's `user_ids` must include an `xsolla_id`, and that user must already have
a wallet. Before activation and again before submitting an event, read the
minting service's wallet lookup for that `xsolla_id`
([`auth-and-environment.md`](auth-and-environment.md)). A 404 means no wallet:
the reward fails with `RecipientNotFound`, non-retryable. Report it and stop.

A 200 carries `walletAddress` and `recipientSource`. Check both, not only the
status: the worker treats only `recipientSource: thirdweb:smart` as a wallet
the player sees in Backpack, and logs any other source as a payout the player
may not see. Tell the developer if the source differs.

## Payout errors surface late

qp-server does not check a Web3 body against the minting service. It accepts
`0.01` and `10000`, and a SKU that is not bound, on create, `PUT` and
activation alike. The qp-server deployed on stage on 2026-09-25 also dropped
its own `web3_token` cap of 10000 and the `project` format check on save
(code, not observed live, revalidate), so an `amount` above 10000 may be
saved without a 422. The stage worker still enforces both at payout: above
10000 the action fails with `amount must not exceed 10000`. Check the cap
yourself before saving. These mistakes appear only at payout time, as a
`FAILED` `issue_reward` action whose `error` names the cause; see
[`verification.md`](verification.md). Run the checks below before activation.

## web3_item

An NFT from the minting service's catalog.

SKUs come from the IGS publisher catalog. The minting service lists a
project's catalog with its read-only SKU lookup
([`auth-and-environment.md`](auth-and-environment.md)). Without `project` in
the body, the worker sends no project, so the SKU must be in the service's
default catalog. With `project` (1 to 64 letters, digits, `-` or `_`), the SKU
must be in that project's catalog. Leave it out unless the developer names
one, and never derive it from the quest's `project_id`. Read the catalog and use a real
`items[].sku`; do not invent one.

Omitting `item_sku` makes the worker list the catalog and pick one item at
random. Tell the developer before choosing that.

**Once per user and quest.** The worker records each `web3_item` payout. When
the same `xsolla_id` already has a confirmed payout for the same quest, a new
event does not mint again: the action completes as `already_minted` and reuses
the earlier transaction hash. If the earlier payout is unresolved, the action
fails with `an earlier web3 payout for this user and quest is unresolved` and
nothing is minted. This holds even with unlimited activation limits and a new
`idempotency_key`. A second item for the same user therefore needs a new quest.
`web3_token` has no such guard: every qualifying event can pay again.

**What a `COMPLETED` reward action means.** Either the minting service returned
a transaction hash for a new claim, or the user already had this quest's item
and nothing new was minted. qp-data does not say which; the worker's result
text does (`Already minted ...`). On a repeat event for the same user, report
"completed, no second mint expected", never "two mints". Delivery is outside
this skill's evidence, as for `web3_token` below.

## web3_token

An ERC-20 payout, for example USDC.

```json
{
  "type": "web3_token",
  "purpose": "quest_completion",
  "body": {"item_sku": "GM26", "amount": 10000}
}
```

The SKU and amount above are illustrative only, not an owner-approved stage
fixture. On stage, `GM26` with `10000` paid 0.01 USDC.

**`amount` is a positive integer in the token's base units** (observed on stage
2026-09-23, revalidate). The worker passes `body.amount` to the minting service
verbatim. The service rejects a decimal with a 400, `amount must be a positive
integer (digits only, no sign or decimal point)`. USDC has 6 decimals, so
`1000000` is 1.00 USDC and `10000` is 0.01 USDC. Whether `amount` is meant to
be whole tokens or base units is pending confirmation from the Web3 owner. Get
the token's decimals from the developer or the owner, never guess them, and
show both the token amount and the base-unit integer before activation.

The cap of 10000 is 0.01 of a 6-decimal token if `amount` is in base units.
qp-server may no longer reject a larger value, but the payout fails; state
the cap before the write when the developer asks for a larger payout.

**`item_sku` must be a current ERC-20 binding of the worker's ERC-20 project.**
Read the minting service's currency bindings
([`auth-and-environment.md`](auth-and-environment.md)) and pick a binding with
`tokenStandard: erc20` whose `projectId` equals the worker's ERC-20 project, or
the body's `project` when set. A binding carries `sku`, `projectId`,
`contractAddress` and `tokenStandard`, but no symbol or decimals: have the
developer confirm which token the SKU is and its decimals.
Bindings change, so read them each session rather than reusing a SKU from
memory. An unbound SKU fails at payout with a 400, `no ERC-20 token is
configured for project <id> / sku <sku>`.

**The ERC-20 project comes from the worker's environment**, unless the body
sets `project`, and never from the quest's `publisher_id` or `project_id`.
Where it is not configured, every `web3_token` reward fails with
`Web3TokenNotConfigured`, non-retryable, even when the body sets `project`.
Currently only stage has it; see
[`auth-and-environment.md`](auth-and-environment.md). Do not offer this reward
in another environment without owner confirmation.

**What a `COMPLETED` reward action means.** The worker calls the claim
synchronously and treats a missing transaction hash as a non-retryable error.
So a `COMPLETED` `issue_reward` means the minting service returned a
transaction hash: the claim was submitted. On-chain finality, the wallet
balance and Backpack or Rewards display are outside this skill's evidence.
Never claim that the token reached the wallet. The hash is recorded by the
worker, not in qp-data: its logs carry a `tx_hash` field on the
`claim_web3_token` success line, and its ledger keeps the hash only inside the
reward node's result text (`Transaction hash: <hash>`), not as a separate field. The minting service's minted-instances list is not a per-claim log;
a new ERC-20 claim did not appear there. A human can check the hash on the
chain explorer named in [`auth-and-environment.md`](auth-and-environment.md).

**Duplicate payout risk.** The claim carries no idempotency key. The reward
activity has a 2-minute timeout and up to 3 attempts. HTTP errors from the
claim are non-retryable, but an activity timeout or a worker crash after the
provider paid can run the claim again. qp-data writes a row only after the
execution finishes, so a claim in flight shows as no row. An `IN_PROGRESS`
row is never an in-flight claim: it means a condition was not met and no
action ran (see [`verification.md`](verification.md)). If the row is still
missing after the read policy in [`verification.md`](verification.md), or the
reward action failed on a timeout, do not resend the event. Escalate to the
Quest Platform team, who own the worker logs and ledger, with the quest id,
`event_id`, `idempotency_key`, user and time; a human can also check the
chain.

Workers deployed on stage on 2026-09-25 also record each Web3 payout and
refuse to pay again when an earlier attempt's outcome is unknown, failing with
`web3 payout outcome is unknown from an earlier attempt` or, for `web3_item`,
`an earlier web3 payout for this user and quest is unresolved`. Both mean
escalate as above; neither permits a resend.

An action `error` can carry two retryable flags, for example
`(type: Web3TokenClaimFailed, retryable: false): ... (type: ClaimError, retryable: true)`.
The first, with the worker's named type, is the one that applied; the inner
one belongs to the wrapped cause. Neither permits you to resend.

Attaching this reward to a quest that you then activate means real payouts. Ask
for explicit confirmation before activating.

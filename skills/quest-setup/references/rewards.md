# Rewards

Written against the contract deployed on stage as of 2026-09-22.

These are the `parameters` of a node with `type: action` and
`subtype: issue_reward`. The OpenAPI document does not describe them, because
the body is carried as raw JSON.

## Wrapper

```json
{"type": "<reward type>", "purpose": "<string>", "body": { }}
```

`type`, `purpose` and a non-empty `body` are all required. An unrecognised
`type` is rejected.

## Bodies

| `type` | `body` | Rules |
|---|---|---|
| `xsolla_points` | `{"amount": <number>}` plus optional `campaign_name`, `campaign_image`, `event_name`, `reason_quest_id`, `app_name`, `app_icon_url` | `amount` greater than 0 |
| `virtual_currency` | `{"amount": <number>}` | `amount` greater than 0 |
| `loyalty_points` | `{"amount": <number>, "loyalty_points_id": "<string>"}` | both required |
| `lootbox` | `{"item_sku": "<string>", "quantity": <int>}` | `quantity` 1 to 100 |
| `custom` | `{"amount": <number>, "currency_ticker": "<string>"}` | `amount` greater than 0 |
| `inventory_item` | `{"xsolla_item": <bool>, "items": [{"sku": "<string>", "quantity": <int>}]}` | `quantity` 0 to 100 |
| `vc_wallet_ticket` | `{"quantity": <int>, "currency_ticker": "<string>"}` plus optional `playtime` | `quantity` greater than 0 |
| `web3_item` | `{"xsolla_item": <bool>, "item_sku": <string or array>, "quantity": <int>}` | `quantity` at least 0, read back as 1 when absent |
| `web3_token` | `{"item_sku": "<string>", "amount": <number>}` | both required, `amount` greater than 0 |

The optional `playtime` object on `vc_wallet_ticket` is
`{"earn_rate_minutes": <greater than 0>, "daily_cap_minutes": <greater than 0>, "timezone": "<non-empty>"}`.

## web3_token

An ERC-20 payout, for example USDC.

```json
{
  "type": "web3_token",
  "purpose": "quest_completion",
  "body": {"item_sku": "XLA-000-001", "amount": 0.01}
}
```

`amount` is in whole tokens, not base units. `item_sku` selects the ERC-20
within the minting service's configured project.

**Settlement is asynchronous and happens outside this skill.** Configuring
this reward, activating the quest and submitting an event are three things
this skill does. Delivery to a wallet is not. A successful event response says
nothing about whether a token moved, so never report one as if it did. Say that
the quest executed and the reward action completed, and stop there.

Attaching this reward to a quest that you then activate means real payouts. Ask
for explicit confirmation before activating.

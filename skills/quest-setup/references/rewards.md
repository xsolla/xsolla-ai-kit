# Rewards

These are the `parameters` of a node with `type: action` and
`subtype: issue_reward`.

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
| `inventory_item` | `{"xsolla_item": <bool>, "items": [{"sku": "<string>", "quantity": <int>, "type": "<string>", "name": "<string>", "image_url": "<url>", "model_3d_url": "<url>"}], "item_sku": "<string>", "name": "<string>", "image_url": "<url>", "model_3d_url": "<url>"}` | `items` or `item_sku`; each `items[].sku` required; item quantity 0 to 100, treated as 1 when 0 or absent. With neither, a random item, see below |
| `vc_wallet_ticket` | `{"quantity": <int>, "currency_ticker": "<string>"}` plus optional `playtime` | `quantity` greater than 0 |
| `web3_item` | `{"xsolla_item": <bool>, "item_sku": <string or array>, "quantity": <int>}` | `quantity` at least 0, treated as 1 when absent. No `item_sku` means a random item, see below |
| `web3_token` | `{"item_sku": "<token SKU>", "amount": <number>}` | both required; `amount` is a whole-token amount greater than 0, see below |

The optional `playtime` object on `vc_wallet_ticket` is
`{"earn_rate_minutes": <greater than 0>, "daily_cap_minutes": <greater than 0>, "timezone": "<non-empty>"}`.

For `inventory_item`, provide either `items` or the single-item `item_sku`
form. `name`, `image_url` and `model_3d_url` go with the single-item form.
Obtain real catalog values from the developer. A body with neither `items` nor
`item_sku` makes the platform pick a random item; tell the developer before
choosing that. Acceptance never proves that a particular SKU exists.

## Web3 rewards

`web3_item` and `web3_token` pay to the wallet of the event's user.

### Recipient

The event's `user_ids` must include an `xsolla_id`, and that user must already
have a wallet. This skill cannot check that. Confirm it with the developer
before activation and again before submitting an event. If the user has no
wallet, the payout fails.

### Mistakes surface at payout time

The Quest API does not check a Web3 body against the payout provider. It
accepts an unknown SKU or a wrong amount on create, `PUT` and activation alike.
Such a mistake fails only when the reward is paid out. Confirm the SKU and the
amount with the developer before activation.

### web3_item

An NFT from the developer's Web3 catalog. Take the SKU from the developer's
Web3 catalog or from Xsolla. Never invent one.

Omitting `item_sku` makes the platform pick a random item. Tell the developer
before choosing that.

### web3_token

An ERC-20 payout, for example USDC.

```json
{
  "type": "web3_token",
  "purpose": "quest_completion",
  "body": {"item_sku": "<token SKU>", "amount": 5}
}
```

- `item_sku` is the token SKU from the developer's Web3 catalog or from
  Xsolla. Never invent one.
- `amount` is a whole-token amount and must be greater than 0: `5` pays 5
  tokens.
- Show the token SKU and the amount back to the developer and get them
  confirmed before activation.

### No retries

The Web3 claim is not idempotent. Never resend an event to retry a Web3
reward. After an uncertain response, stop: the payout may already have
happened. Never claim that a token or an item reached a wallet.

### Activation

Attaching a Web3 reward to a quest that you then activate means real payouts.
Ask for explicit confirmation before activating.

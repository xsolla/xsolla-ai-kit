# Purchase flows and order tracking

Verified via the official Xsolla MCP on 2026-06-11.
Main doc: [Basic purchase flow → Sell items](https://developers.xsolla.com/api/catalog/payment-client-side/create-order-with-item#section/basic-purchase-flow/Sell-items).

## Choosing a purchase flow

| Flow | When | API call |
|------|------|----------|
| **Fast purchase by SKU** (recommended default) | One SKU per order — covers most in-game purchases | [Create order with specified item](https://developers.xsolla.com/api/catalog/payment-client-side/create-order-with-item) |
| Cart | User combines several SKUs in one order | [Fill cart](https://developers.xsolla.com/api/catalog/cart-client-side/cart-fill/) → [update](https://developers.xsolla.com/api/shop-builder/operation/put-item-by-cart-id/) / [delete](https://developers.xsolla.com/api/shop-builder/operation/delete-item-by-cart-id/) items → [Create order with all items from current cart](https://developers.xsolla.com/api/catalog/payment-client-side/create-order/) (or [by cart ID](https://developers.xsolla.com/api/catalog/payment-client-side/create-order-by-cart-id/)) |
| Purchase for virtual currency | Item priced in VC | [Create order with specified item purchased by virtual currency](https://developers.xsolla.com/api/catalog/virtual-payment/create-order-with-item-for-virtual-currency) — user JWT, charged immediately, no payment UI; track the returned order like any other |
| Free items | Giveaways, rewards | [Create order with specified free item](https://developers.xsolla.com/api/catalog/free-item/create-free-order-with-item) / [free cart](https://developers.xsolla.com/api/catalog/free-item/create-free-order) — order goes straight to `done` |
| Game keys | Selling a game/DLC | Direct link / own UI — see [game-keys.md](game-keys.md) |

Fast-purchase notes: promo codes are redeemed via the `promo_code` body parameter;
discount details are shown to the user only inside the payment UI.

## Creating the order (fast purchase)

1. **From the client**, with the user JWT in `Authorization: Bearer <user_JWT>`, call
   [Create order with specified item](https://developers.xsolla.com/api/catalog/payment-client-side/create-order-with-item).
   **Client-side only**: the user's country (→ currency → payment methods) is determined
   from the caller's IP. Calling it from your server breaks currency selection.
   Don't pass `currency` — it follows the country.
2. The call returns `order_id` + a payment `token` (24h lifetime by default).
3. Open the payment UI: `https://secure.xsolla.com/paystation4/?token={token}`
   (sandbox: `https://sandbox-secure.xsolla.com/paystation4/?token={token}`).
   The payment itself is Headless Checkout territory — see the `headless-checkout-integration` skill.

Server-side token generation exists as a separate scenario
([Create payment token for purchase](https://developers.xsolla.com/api/catalog/payment-server-side/admin-create-payment-token/)) —
there you **must** pass `country.value` or the `X-User-Ip` header.

Sandbox: pass `"sandbox": true` when creating the order and use
[test cards](https://developers.xsolla.com/dev-resources/testing/test-cards/). After the
first real payment, sandbox becomes available only to company users listed in Publisher
Account. Real-currency sales require a signed license agreement (Agreements & Taxes).

## Order statuses

`new` → `paid` → `done` (delivered); terminal failures: `canceled`, `expired`.

## Confirming the purchase

Two patterns — pick based on where items are granted:

### Server side: webhooks (recommended by docs)

Handle `order_paid` (grant items) and `order_canceled` (revoke items). Note the account
split: projects registered in Publisher Account **after 2025-01-22** receive *combined*
webhooks (payment + items in one payload); older accounts receive *separate*
`payment`/`refund` plus `order_paid`/`order_canceled` and must process all of them.
`user_validation` must also be handled.
Source: [List of required webhooks](https://developers.xsolla.com/webhooks/payments/add-payment-account#section/List-of-required-webhooks).

→ Webhook handler implementation is covered by the **`webhooks-impl`** skill.

### Client side: WebSocket + polling fallback

For projects without their own server. Docs recommendation:
[Get order status via WebSocket API](https://developers.xsolla.com/virtual-goods/own-ui/client-side-token-generation/set-up-order-tracking/#guides_shop_builder_integrate_store_get_order_status_via_websocket_api).

- Connect (Centrifuge protocol) to `wss://ws-store.xsolla.com/connection/websocket`,
  passing `user_external_id`, `auth` (user JWT), `project_id`. Messages:
  `{ order_id, status }`.
- Open the connection when opening the payment UI; close it on a terminal status
  (`done`/`canceled`). Max wait per connection: 5 minutes.
- On websocket failure/expiry, fall back to **short-polling**
  [Get order](https://developers.xsolla.com/api/catalog/order/get-order) every 3 seconds;
  stop on terminal status or after 10 minutes.
- Alternative without webhooks or sockets: [Xsolla Event API](https://developers.xsolla.com/api/event/).

# Webhook events and payload shapes

Official reference: https://developers.xsolla.com/webhooks/overview

## Delivery modes (pick the one your project uses)

Xsolla delivers payment/store webhooks in one of two modes, fixed by the
project's registration date:

| Mode | When | Webhooks received |
| --- | --- | --- |
| **Combined** | Project registered **after 2025-01-22** | `user_validation`, `order_paid`, `order_canceled` |
| **Separate** | Project registered **on/before 2025-01-22** | `user_validation`, `payment`, `refund`, `order_paid`, `order_canceled` |

In combined mode, `order_paid` / `order_canceled` already include payment +
transaction details, so you do **not** process `payment` / `refund` separately.
To switch an older project to combined mode, contact your CSM (csm@xsolla.com).

## Core event types

The type is sent in `notification_type`.

| `notification_type` | Meaning | Typical action |
| --- | --- | --- |
| `user_validation` | Check the user exists in your game. Sent **multiple times** per payment (method selection, data entry, "Pay", completion). | Look up the user; `204` if found, `400 INVALID_USER` if not. |
| `payment` | Payment completed (separate mode). | Record the transaction. |
| `order_paid` | Order paid (combined mode includes payment + items). | Grant purchased items / currency. |
| `refund` | Payment canceled (separate mode). | Record the reversal. |
| `order_canceled` | Order canceled (combined mode includes items). | Revoke previously granted items. |
| `create_subscription` / `update_subscription` / `cancel_subscription` | Subscription lifecycle. | Start / extend / revoke the subscription. |
| `partner_side_catalog` | Catalog personalization (optional). | Return the list of available `item_id` / SKU. |
| `user_search` | Resolve a user by **public** user ID (email, nickname). | Return user info. |

Opt-in events (request from your CSM): `ps_declined`, `afs_reject`,
`afs_black_list`, `dispute`, `partial_refund`, `payment_account_add/remove`,
`non_renewal_subscription`. Don't depend on them for core fulfillment.

## Payload shapes (combined and separate modes differ — don't assume one schema)

The same logical value (transaction id, user id) lives in **different places**
per event. Read the per-event field reference on developers.xsolla.com.

`user_validation` — flat `user` object; `user.id` is your in-game user id:

```json
{
  "notification_type": "user_validation",
  "settings": { "project_id": 12345, "merchant_id": 67890 },
  "user": { "id": "1234567", "country": "US", "email": "user@example.com" }
}
```

`payment` (separate mode) — id is `transaction.id`, user is `user.id`, money is
`purchase.total.amount`:

```json
{
  "notification_type": "payment",
  "purchase": { "checkout": { "currency": "USD", "amount": 9.99 }, "total": { "amount": 9.99 } },
  "user": { "id": "1234567", "country": "US", "email": "user@example.com" },
  "transaction": { "id": 87654321, "payment_date": "2026-01-01T12:00:00+00:00", "dry_run": 1 },
  "payment_details": { "payment": { "amount": 9.99, "currency": "USD" } }
}
```

`order_paid` (combined mode) — **note the nesting**: items in `items[]`, order in
`order` (`order.id`, `order.invoice_id`, `order.mode` = `default`/`sandbox`), user
is `user.external_id`, and payment/transaction details live under `billing.*`, so
the transaction id is `billing.transaction.id`:

```json
{
  "notification_type": "order_paid",
  "items": [ { "sku": "sword_01", "quantity": 1, "is_free": false } ],
  "order": {
    "id": 4567, "mode": "default", "currency_type": "real", "currency": "USD",
    "amount": "9.99", "status": "paid", "platform": "xsolla", "invoice_id": "87654321"
  },
  "user": { "external_id": "1234567", "email": "user@example.com", "country": "US" },
  "billing": {
    "transaction": { "id": 87654321, "payment_date": "2026-01-01T12:00:00+00:00", "dry_run": 1 },
    "purchase": { "total": { "amount": 9.99 } }
  }
}
```

`order_canceled` mirrors `order_paid`; `refund` mirrors `payment` and adds a
refund-reason code (below). Detect test traffic via `order.mode === "sandbox"`
or `transaction.dry_run === 1` and keep it out of production fulfillment.

## Subscriptions (only if you sell subscription products)

Optional — handle only if your shop sells recurring plans. Flat `user.id` (not
`user.external_id`) and a `subscription` object keyed by
`subscription.subscription_id`. They arrive alongside the payment flow:
`create_subscription` after the initial `payment` (or on a trial),
`update_subscription` on **every renewal**/plan change, `cancel_subscription`
after a `refund` or any other cancellation.

```json
{
  "notification_type": "create_subscription",
  "settings": { "project_id": 12345, "merchant_id": 67890 },
  "user": { "id": "1234567", "name": "Xsolla User" },
  "subscription": {
    "plan_id": "monthly_premium", "subscription_id": 55555, "product_id": "premium",
    "date_create": "2026-01-01T12:00:00+00:00", "date_next_charge": "2026-02-01T12:00:00+00:00",
    "trial": { "value": 7, "type": "day" }, "is_gift": true
  }
}
```

- `update_subscription`: same shape, carries the changed `plan_id` /
  `date_next_charge` (no `date_create`/`trial`). Use it to extend access.
- `cancel_subscription`: same shape plus `subscription.date_end` (termination
  date), no `date_next_charge`. Revoke access at `date_end`.

Idempotency key for subscription events = `subscription.subscription_id` + a
**per-event discriminator**. Do **not** dedup on `(subscription_id, type)` alone:
`update_subscription` repeats on every renewal with the same id and type, so that
would silently drop legitimate renewals. Use `subscription.date_next_charge` (or
the renewal's charge/transaction id) as the discriminator.

## Refund reason codes

`refund` / `partial_refund` carry a numeric reason. Codes that suggest adding
the user to your blocklist: `2` chargeback, `4` potential fraud, `7` fraud
notification from PS, `11` account-holder fraud report, `12` friendly fraud.
Do **not** blocklist for: `3` integration error, `5` test payment, `8`–`10`
user/game/PS cancellation. `13` duplicate. Always revoke the granted items
regardless of code.

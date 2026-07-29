# Handler, responses, idempotency, retries

## HTTP responses

| Status | When | Effect |
| --- | --- | --- |
| `200` / `201` / `204` | Handled successfully (or already handled). | Marked delivered. |
| `400` + error body | Bad/unverifiable request (bad signature, unknown user). | No retry; flow stops. |
| `5xx` | **Temporary** failure on your side. | Xsolla **retries** for most event types (see below); `user_validation` is **not retried**. |

Error body for `400`:

```json
{ "error": { "code": "INVALID_USER", "message": "Invalid user" } }
```

Valid `code` values: `INVALID_USER`, `INVALID_PARAMETER`, `INVALID_SIGNATURE`,
`INCORRECT_AMOUNT`, `INCORRECT_INVOICE`.

- Return `400 INVALID_SIGNATURE` (not `200`, not `500`) when verification fails —
  Xsolla's setup test explicitly checks for this.
- Return `5xx` **only** for transient failures you want retried. A `5xx` for a
  permanent error just wastes 12–48h of retries.

## Handler skeleton (Express)

```js
// Field locations differ between combined (order_paid) and separate (payment) modes.
const txId = (evt) => evt.billing?.transaction?.id ?? evt.transaction?.id;
const userId = (evt) => evt.user?.external_id ?? evt.user?.id;

app.post('/xsolla/webhooks', async (req, res) => {
  if (!verifyXsollaSignature(req)) {
    return res.status(400).json({ error: { code: 'INVALID_SIGNATURE', message: 'Invalid signature' } });
  }

  const evt = req.body;
  try {
    switch (evt.notification_type) {
      case 'user_validation': {
        const exists = await userExists(evt.user.id);
        return exists
          ? res.sendStatus(204)
          : res.status(400).json({ error: { code: 'INVALID_USER', message: 'Invalid user' } });
      }
      // Grant/revoke on order_* (they always carry evt.items). In separate mode
      // payment/refund ALSO arrive — treat those as financial records only, or you
      // will fulfill twice.
      case 'order_paid': {
        if (await alreadyProcessed(txId(evt))) return res.sendStatus(204); // idempotent replay
        await grantItemsAtomically(txId(evt), userId(evt), evt);
        return res.sendStatus(204);
      }
      case 'order_canceled': {
        await revokeItemsIdempotent(txId(evt), userId(evt), evt);
        return res.sendStatus(204);
      }
      case 'payment':   // separate mode only — record the transaction, do NOT grant items here
      case 'refund': {  // separate mode only — record the reversal, do NOT revoke items here
        await recordFinancialEvent(evt.notification_type, txId(evt), evt);
        return res.sendStatus(204);
      }
      case 'create_subscription':   // optional — only if you sell subscriptions
      case 'update_subscription':   // every renewal → extend; dedup on subscription_id + date_next_charge
      case 'cancel_subscription': { // revoke at evt.subscription.date_end
        await applySubscriptionState(evt.notification_type, evt.user.id, evt.subscription);
        return res.sendStatus(204);
      }
      default:
        return res.sendStatus(204); // ack unknown/optional types so the queue keeps flowing
    }
  } catch (err) {
    return res.sendStatus(500); // transient → let Xsolla retry
  }
});
```

## Idempotency (mandatory)

The same webhook can arrive more than once (retries, at-least-once delivery).
Never store two successful transactions with the same id.

1. Extract the transaction id — **`billing.transaction.id` in combined mode,
   `transaction.id` in separate mode**.
2. Atomically insert it into a `processed_webhooks` table with a **unique
   constraint**.
3. On unique-constraint conflict → already processed → return the previous
   result (a `2xx`). Do **not** grant items again.

> A successful catalog purchase **always** emits `order_paid` (combined) or
> `order_paid` alongside `payment` (separate) — never `payment` alone. Key your
> fulfillment off `order_*` so the same path works in both modes.

For **subscription** events, the transaction id isn't the dedup key: use
`subscription.subscription_id` **plus a per-event discriminator**, since
`update_subscription` repeats on every renewal with the same id and type. Dedup
renewals on `subscription.date_next_charge` (or the renewal's charge/transaction
id) so legitimate renewals aren't dropped.

## Retries and delivery order

- `order_paid` / `order_canceled`: on `5xx`/no response → **2× @ 5 min, 7× @ 15
  min, 10× @ 60 min**, max **20 attempts within 12h**.
- `payment` / `refund`: increasing intervals, max **12 attempts over 48h**.
- `user_validation`: **not retried** if it returns `400`/`5xx`. The user sees an
  error and `payment` / `order_paid` are never sent — keep this handler solid.
- A `refund` initiated on **your** side is not retried; the user is refunded
  regardless. An Xsolla-initiated refund still completes even if you keep
  erroring.

Delivery is **sequential**: a single persistently-failing handler stalls the
whole chain. Monitor and alert on webhook error rate.

## Network hardening

Accept webhook traffic only from Xsolla's published source IPs (defense in depth
— signature verification is still mandatory). The ranges below are a snapshot and
**can go stale**; always treat the docs as the source of truth:
https://developers.xsolla.com/webhooks/overview (see "Webhook listener").

```
185.30.20.0/24  185.30.21.0/24  185.30.22.0/24  185.30.23.0/24
34.102.38.178   34.94.43.207    35.236.73.234   34.94.69.44   34.102.22.197
```

If you also use Xsolla **Login** webhooks, allow its additional ranges (see
docs). Verify the current list before launch — IPs can change.

## Fulfillment — grant what the buyer purchased (ask the developer)

When Xsolla notifies a successful purchase (`order_paid` in Store flows, or
`payment` for Merchant-only tokens — see [`testing.md`](testing.md) /
[`events-and-payloads.md`](events-and-payloads.md)), the shop backend must
**deliver the goods** to that user. Xsolla does not know how the game or shop
grants inventory: there is no one-size API call the agent can invent.

**Before implementing `grantItemsAtomically` (or equivalent), ask the
developer:**

1. **What is the “good”?** Virtual item SKU, currency amount, game key, entitlement
   flag, access tier, email of a code, call into a game server, etc.
2. **How does a user normally receive it today?** Existing inventory service,
   wallet DB, CRM, admin tool, message queue, third-party API, manual ops?
3. **What identifies the user in that system?** Must match the webhook user id
   (`user.external_id` / `user.id` — usually the Login `sub` / store external id).
   If they differ, how do you map them?
4. **What identifies the purchase for idempotency?** Transaction / order id from
   the webhook (already required above) — confirm it can be stored next to the
   grant so retries do not double-deliver.
5. **What happens on refund / `order_canceled`?** Revoke, soft-flag, chargeback
   queue, or no-op? Who owns that policy?
6. **Sync or async?** If granting is slow (> ~3s), acknowledge the webhook with
   `2xx` quickly and finish delivery on a worker — still idempotent.

Wire the handler to **call into that existing path** (or the path the developer
specifies). Do not invent a parallel inventory unless they ask for a greenfield
demo store. Skeleton above uses `grantItemsAtomically(txId, userId, evt)` as a
placeholder — replace it with their real grant operation and keep signature
checks + idempotency around it.

If the developer has not answered yet: implement verify + route + persist
“pending grant” / log clearly, and **block** on asking before claiming
fulfillment is done.

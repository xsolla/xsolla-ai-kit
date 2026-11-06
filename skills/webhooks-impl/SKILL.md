---
name: webhooks-impl
description: >-
  Builds and checks the backend a merchant or developer runs to receive Xsolla
  webhooks. The payment UI only starts the flow and does not receive them.
  Xsolla calls that backend: user_validation when the player starts paying, and
  order_paid after payment so the merchant or developer grants the item. Also
  refunds and cancellations. Use for "implement Xsolla webhooks" or
  "grant items after purchase".
metadata:
  owner: e.chernykh
  domain: webhooks
  status: draft
---

## Status

This skill is a **draft** authored by the webhooks SME (@e.chernykh).

Detailed material lives in `references/`:
- [`references/events-and-payloads.md`](references/events-and-payloads.md) — delivery modes, event types, payload JSON, refund codes
- [`references/signature-verification.md`](references/signature-verification.md) — SHA-1 algorithm + Node/PHP examples
- [`references/handler-and-reliability.md`](references/handler-and-reliability.md) — responses, idempotency, retries, IP allowlist, **fulfillment (ask how goods are granted)**, full handler
- [`references/testing.md`](references/testing.md) — fixture replay vs live tunnel; when `payment` vs `order_paid` arrives
- [`fixtures/`](fixtures/) — sample `user_validation` / `order_paid` / `payment` bodies (+ `.raw.txt`)

## When to use

Use this skill when the developer wants to **receive and process Xsolla
webhooks on their own backend**. The player pays in a payment UI such as
Headless Checkout or Pay Station. That UI does not receive webhooks. Starting
to pay makes Xsolla call the merchant or developer for `user_validation`. A
completed payment makes Xsolla call again so the merchant or developer can
grant the item. Trigger conditions:

- Implementing a webhook endpoint that grants items / currency after purchase
- Verifying the webhook signature or debugging `INVALID_SIGNATURE`
- Handling `user_validation`, `payment` / `order_paid`, `refund` /
  `order_canceled`, or subscription events
- Making webhook processing idempotent or handling retries correctly
- Reviewing an existing webhook handler before go-live

This skill covers **handler implementation** and how to test it. Enabling
webhooks + creating the secret in Publisher Account is a **manual** step in
**Prerequisites** below (not done by `merchant-setup`). Setting the live URL is
covered in `references/testing.md`.

## Prerequisites

```bash
export XSOLLA_WEBHOOK_SECRET=<project webhook secret key>  # server-side only, never client-side
export XSOLLA_ENV=sandbox                                  # default; "production" for prod
```

### Publisher Account — enable webhooks + secret (human)

The agent cannot create the secret in PA. **Ask the developer** to:

1. Open project webhooks (ids from `.env` per `merchant-setup`):

   ```text
   https://publisher.xsolla.com/{XSOLLA_MERCHANT_ID}/projects/{XSOLLA_PROJECT_ID}/edit/webhooks
   ```

2. **Create / generate the webhook secret key** (project secret used to sign
   notifications).
3. **Enable webhooks** for the project (Store / required notifications as shown in PA).
4. Put the secret in the backend `.env` (never the browser / never commit real values):

   ```bash
   XSOLLA_WEBHOOK_SECRET=<the key from PA>
   ```

5. Later set the **listener URL** (HTTPS) — local tunnel or deployed host — under the
   same webhooks settings (store path often
   `.../edit/webhooks/store`). See `references/testing.md`.

Without the secret in `.env`, signature verification always fails. Without
webhooks enabled + a reachable HTTPS URL, Xsolla never delivers live events
(fixtures still work for local replay).

Also needed:

- A backend that can read the **raw request body** (needed for signature
  verification) and a datastore for idempotency keys.
- Webhook URL must be **HTTPS** when Xsolla calls it — HTTP is rejected.

## Steps

1. **Know your delivery mode.** Projects registered after 2025-01-22 get
   **combined** webhooks (`order_paid` / `order_canceled` carry items + payment);
   older projects get **separate** (`payment` + `refund` plus `order_paid` /
   `order_canceled`). The JSON differs per mode — see
   `references/events-and-payloads.md`.

2. **Capture the raw body and verify the signature first.** The `authorization`
   header is `Signature <40-hex>`; recompute `lowercase(sha1(rawBody + secret))`
   and compare in constant time. Reject mismatches with `400 INVALID_SIGNATURE`.
   Full Node/PHP examples: `references/signature-verification.md`.

3. **Route by `notification_type` and fulfill:**
   - `user_validation` → confirm the user exists; `204` if yes, `400 INVALID_USER` if no.
   - `order_paid` → **grant** purchased goods (idempotently). `order_canceled` → revoke
     per the developer’s policy.
   - In separate mode, `payment` / `refund` also arrive — treat them as financial
     records only; do fulfillment on `order_*` to avoid double-granting.
   - Merchant-only tokens may send `payment` without a Store order — then fulfill
     on `payment` if that is the only success signal (see `testing.md`).
   - Subscription events (optional) → start / extend / revoke.
   **Ask the developer how users receive goods** in their product (inventory API,
   wallet, game server, …) and wire the handler to that path — do not invent a
   parallel grant system. Details:
   `references/handler-and-reliability.md` (Fulfillment).

4. **Make fulfillment idempotent.** Dedupe by transaction id
   (`billing.transaction.id` combined, `transaction.id` separate) using a unique
   constraint; on a duplicate, return the prior `2xx` without re-granting.

5. **Respond correctly and keep it fast.** `200/201/204` = success, `400` (+ error
   code) = permanent reject, `5xx` = transient (Xsolla retries). Target < 3s; do
   heavy work async. Webhooks are delivered **sequentially** — a failing handler
   blocks the rest of the flow.

6. **Harden and test.** Allowlist Xsolla's source IPs (still verify the signature).
   Prefer **fixture replay** for signature / routing / idempotency; use a **public
   tunnel** + sandbox purchase (developer sets the URL in PA) for live delivery.
   See `references/testing.md`.

## Common pitfalls

- **Re-serializing the body before hashing** — always sign the raw bytes. The #1
  cause of `INVALID_SIGNATURE`.
- **Returning `200` on a bad signature** — breaks Xsolla's setup test and hides
  attacks. Return `400 INVALID_SIGNATURE`.
- **Non-idempotent fulfillment** — granting items twice on a retried/duplicate
  webhook, or fulfilling on both `payment` and `order_paid` in separate mode.
  Dedupe by transaction id and fulfill only on `order_*`.
- **Misusing `5xx`** — it triggers up to 48h of retries for errors that will
  never succeed. Use `400` for permanent problems, `5xx` only for transient ones.
- **Ignoring or slowing `user_validation`** — a failing/slow validation handler
  blocks every downstream payment webhook; the user sees an error.
- **Granting without asking how** — inventing a demo inventory while the game
  already has a real entitlement path. Always ask how the buyer receives goods
  and map the webhook user id to that system.

## Agent test

Prompt: "Implement an Xsolla webhook handler that grants items after purchase.
Use Node.js/Express."

Result: the agent discovered and applied this skill (read `SKILL.md` + references,
including `testing.md` / fixtures), asked how goods are granted in the product,
scaffolded a raw-body Express endpoint, and smoke-tested with fixture POSTs:
`lowercase(sha1(rawBody + secret))` rejecting tampered bodies with
`400 INVALID_SIGNATURE`; `user_validation` returning `204`/`400 INVALID_USER`;
idempotent `order_paid` granting (replay returned `2xx` with no re-grant); no
double-grant in separate mode (`payment` recorded only); `5xx` reserved for
transient errors. ✅

---
name: webhooks-impl
description: >-
  Implements and validates the backend that receives Xsolla webhooks for a
  headless web shop — server-to-server notifications for user_validation,
  payment / order_paid, refund / order_canceled, and subscription events.
  Covers SHA-1 signature verification, idempotency, retry/response handling,
  IP allowlisting, payload shapes per delivery mode, and the common mistakes
  that break go-live. Use when building, modifying, debugging, or reviewing a
  webhook handler — including "implement Xsolla webhooks", "verify webhook
  signature", "handle payment / order_paid / refund webhooks", "grant items
  after purchase", "webhook returns INVALID_SIGNATURE", "webhook idempotency /
  retries", or "headless webshop backend".
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
- [`references/testing.md`](references/testing.md) — `xsolla webhook trigger` / `listen`, test-suite fixture replay, live tunnel; when `payment` vs `order_paid` arrives
- [`fixtures/`](fixtures/) — sample `user_validation` / `order_paid` / `payment` bodies (+ `.raw.txt`)

## When to use

Use this skill when the developer wants to **receive and process Xsolla
webhooks on their own backend** for a headless web shop (their storefront on the
Xsolla catalog + Pay Station, without Site Builder). Trigger conditions:

- Implementing a webhook endpoint that grants items / currency after purchase
- Verifying the webhook signature or debugging `INVALID_SIGNATURE`
- Handling `user_validation`, `payment` / `order_paid`, `refund` /
  `order_canceled`, or subscription events
- Making webhook processing idempotent or handling retries correctly
- Reviewing an existing webhook handler before go-live

This skill covers **handler implementation** and how to test it. The agent tests
the handler locally with the **Xsolla CLI** (`xsolla webhook`). Enabling webhooks,
creating the secret and setting the URL happen in Publisher Account (a CLI gap).

## Prerequisites

The agent tests webhooks through the **Xsolla CLI**. Run these two checks. They are
read-only and safe to repeat.

```bash
xsolla --version                  # installed? which version?
xsolla config list --json         # merchant_id / project_id / sandbox
```

If the CLI is missing or older than 1.9.4 (a `dev` build is acceptable), or
`merchant_id` / `project_id` is `0` or missing, hand off to **`merchant-setup`** and come
back when it reports. `xsolla webhook` runs offline, so an expired `xsolla auth login`
doesn't block this skill. The IDs come from `.xsolla.json`, and the developer's backend
reads them from the `.env` that `merchant-setup` writes.

### Publisher Account — enable webhooks + secret (human, CLI gap)

No CLI command creates the webhook secret, enables webhooks or sets the URL. **Ask the
developer** to:

1. Open project webhooks (IDs from `.env`):
   `https://publisher.xsolla.com/{XSOLLA_MERCHANT_ID}/projects/{XSOLLA_PROJECT_ID}/edit/webhooks`
2. **Generate the webhook secret key** (the project secret that signs notifications).
3. **Enable webhooks** for the project (Store notifications, as shown in PA).
4. Add the secret to the backend `.env` themselves, in their own editor:
   `XSOLLA_WEBHOOK_SECRET=<the key from PA>`. It is server-side only; never ship it to
   the client or commit it.
5. Later, set the **HTTPS listener URL** (tunnel or deployed host) under the same
   settings (`.../edit/webhooks/store`). See `references/testing.md`.

Never ask for the secret in chat, and never print it. To check it is there, run
`grep -q '^XSOLLA_WEBHOOK_SECRET=.' .env && echo set || echo missing`. Without it,
signature verification always fails. Without webhooks enabled and a reachable HTTPS
URL, Xsolla never delivers live events. Local tests with `xsolla webhook trigger` still
work.

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
   Test locally with `xsolla webhook trigger <event> --to <local handler URL>`
   (events: `xsolla webhook trigger --list`). It signs the payload the way Xsolla does,
   with `XSOLLA_WEBHOOK_SECRET` from the environment. Start the handler with a
   throwaway test secret and pass the same one to `trigger`. Check that the right
   secret gets `2xx`, a wrong one gets `400 INVALID_SIGNATURE`, and a replay doesn't
   re-grant. `order_paid` / `order_canceled` have no `trigger` fixture yet: replay
   `fixtures/` from the app's test suite. For live delivery, use a **public tunnel** and
   a sandbox purchase (the developer sets the URL in PA). See `references/testing.md`.

## CLI gaps

Surface these to the user. Don't work around them with a raw API call.

| Need | Status | Do instead |
|---|---|---|
| Webhook secret, enabling webhooks, webhook URL | No command; Publisher Account only | The developer sets them in PA (see Prerequisites) |
| `order_paid` / `order_canceled` test payloads | `trigger --list` has only `payment`, `refund`, `user_validation` | Replay `fixtures/` from the app's test suite (`references/testing.md`) |
| Custom payload (own SKU, user, transaction id) | `trigger` has no body or file flag | Same as above |
| Subscription event payloads | No `trigger` fixture | Test-suite replay of a payload from `events-and-payloads.md`, or a sandbox subscription |
| Live Xsolla deliveries to a local handler | `listen` / `trigger` are offline only; nothing forwards Xsolla's deliveries | Public HTTPS tunnel + URL in PA |
| Secret from the project `.env` | The CLI ignores `XSOLLA_WEBHOOK_SECRET` in a project `.env` | Pass it in the environment for one command (`references/testing.md`) |

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
- **Triggering without the secret** — `xsolla webhook trigger` signs with an empty
  secret and doesn't warn. The handler then rejects it, which looks like a handler bug.
  Pass the same secret the handler runs with.
- **Copying `xsolla webhook listen`'s responses** — it answers a bad signature with
  `401`. Your handler must answer `400 INVALID_SIGNATURE`.

## Agent test

Prompt: "Implement an Xsolla webhook handler for my headless shop that grants
items after purchase. Use Node.js/Express."

Result: the agent discovered and applied this skill (read `SKILL.md` + references,
including `testing.md` / fixtures), asked how goods are granted in the product,
scaffolded a raw-body Express endpoint, and smoke-tested with fixture POSTs:
`lowercase(sha1(rawBody + secret))` rejecting tampered bodies with
`400 INVALID_SIGNATURE`; `user_validation` returning `204`/`400 INVALID_USER`;
idempotent `order_paid` granting (replay returned `2xx` with no re-grant); no
double-grant in separate mode (`payment` recorded only); `5xx` reserved for
transient errors. ✅

CLI check (2026-10-19, CLI `dev` 379d24a, localhost only, throwaway secret): `xsolla
webhook listen --port 4291 --path /xsolla/webhooks` received `trigger` deliveries of
`payment`, `refund` and `user_validation` with `sig=valid` (`204`, trigger exit `0`). A
wrong or missing secret gave `sig=INVALID` (`401`, trigger exit `1`). The CLI ignored the
secret in a mode-600 project `.env`; the one-command environment recipe in `testing.md`
worked. ✅

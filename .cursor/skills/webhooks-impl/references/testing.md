# Testing Xsolla webhooks

Two ways to validate a webhook handler. Prefer **fixtures** for everyday agent
work; use a **tunnel** when you need a live delivery from Xsolla.

Fixtures live in [`fixtures/`](../fixtures/) next to this skill
(`user_validation`, `order_paid`, `payment` — JSON + matching `.raw.txt`).

---

## Which webhook arrives when

| Situation | Typical `notification_type`s |
|-----------|------------------------------|
| Before / during checkout (user check) | `user_validation` (often **several** times) |
| Successful purchase via **Store** token (Method 1 or 2 in `shop-setup`) — **combined** delivery (projects after 2025-01-22) | `order_paid` (items + payment in one payload) |
| Same Store purchase — **separate** delivery (older projects) | `payment` **and** `order_paid` (fulfill on `order_paid` only) |
| Successful pay via **Merchant API** token (Method 3 — amount + description, no Store order) | `payment` (items often in `custom_parameters`; **no** Store `order_id`) |
| Refund / cancel | `order_canceled` (combined) or `refund` + `order_canceled` (separate) |
| Subscriptions (if enabled) | `create_subscription` / `update_subscription` / `cancel_subscription` |

**Rule of thumb for shops:** mint with Store Method 1/2 → expect **`order_paid`**
as the fulfillment signal. Merchant Method 3 → expect **`payment`**. Do not grant
twice if both `payment` and `order_paid` arrive (separate mode). Full shapes:
[`events-and-payloads.md`](events-and-payloads.md).

---

## Method 1 — Fixture replay (agent-driven, no public URL)

Use this to implement and smoke-test the handler without Publisher Account or a
tunnel.

1. **Use fixtures while writing the handler.** Open
   `fixtures/order_paid.json` / `payment.json` / `user_validation.json` and map
   fields (`user.external_id` vs `user.id`, `items[]`, `billing.transaction.id`,
   …) into your grant / validate logic. Prefer `.raw.txt` for signature tests —
   it is the exact body Xsolla signed.

2. **POST a fixture at the shop webhook path** (whatever the app exposes, e.g.
   `/webhooks/xsolla` or `/xsolla/webhooks`). Sign with the same algorithm as
   production — see [`signature-verification.md`](signature-verification.md):

```bash
# From the repo that owns the webhook server; secret from .env (merchant-setup).
source .env   # needs XSOLLA_WEBHOOK_SECRET

BODY_FILE=path/to/xsolla-ai-kit/skills/webhooks-impl/fixtures/order_paid.raw.txt
BODY=$(cat "$BODY_FILE")
SIG=$(printf '%s' "${BODY}${XSOLLA_WEBHOOK_SECRET}" | shasum -a 1 | awk '{print $1}')

curl -sS -D- -o /tmp/wh-body.txt \
  -X POST "http://localhost:4000/webhooks/xsolla" \
  -H "Content-Type: application/json" \
  -H "Authorization: Signature ${SIG}" \
  --data-binary @"$BODY_FILE"

# Expect 2xx. Replay the same body → still 2xx, no second grant.
# Tamper one byte of the body (or wrong secret) → 400 INVALID_SIGNATURE.
```

3. **Minimum agent checklist**
   - Valid signature → `2xx` for `user_validation` / `order_paid` / `payment`
   - Bad signature → `400` + `INVALID_SIGNATURE` (not `200`)
   - Replay same `order_paid` → idempotent (no double grant)
   - Separate-mode caution: handling `payment` must **not** grant if you already
     grant on `order_paid`

Fixtures are **sandbox captures**. Project/merchant ids inside them are
examples; signature verification only needs the raw bytes + **your** current
`XSOLLA_WEBHOOK_SECRET`. If the secret changed since capture, re-sign with the
formula above (fixtures still exercise routing and fulfillment).

---

## Method 2 — Live tunnel (needs a human)

Xsolla will only POST to a **public HTTPS** URL. For local backends, expose the
webhook port with a quick tunnel (e.g. `cloudflared tunnel --protocol http2 --url http://localhost:4000`), then register that URL in Publisher Account.

**Ask the developer** to set the webhook **URL** in PA (secret + “webhooks on”
must already be done — see `SKILL.md` Prerequisites). Build the settings link from
`.env` (`merchant-setup`: `XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID`):

```text
https://publisher.xsolla.com/{XSOLLA_MERCHANT_ID}/projects/{XSOLLA_PROJECT_ID}/edit/webhooks/store
```

Example after substituting from `.env`:

```text
https://publisher.xsolla.com/887981/projects/308077/edit/webhooks/store
```

Webhook URL to paste (replace with the live tunnel host):

```text
https://<tunnel-host>/webhooks/xsolla
```

(Use the path your app actually mounts.)

Then:

1. Developer saves the URL (+ secret already configured) in PA.
2. Agent (or developer) runs a **sandbox** purchase against the local shop.
3. Confirm in server logs / datastore: `user_validation`, then `order_paid` or
   `payment` per the table above, and that fulfillment ran once.
4. Optionally use PA’s webhook test button for a quick smoke, then a real
   sandbox payment for the full chain.

Tunnel URLs from free quick tunnels **change** when restarted — update PA each
time, or use a named/stable tunnel for longer sessions.

---

## When to use which

| Goal | Method |
|------|--------|
| Implement handler, signature, routing, idempotency | **Fixtures** |
| Confirm Xsolla can reach the URL + real purchase chain | **Tunnel** (+ human for PA) |
| Regress after a handler change | Fixtures first; tunnel if delivery/geo/proxy is in doubt |

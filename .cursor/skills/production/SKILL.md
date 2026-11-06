---
name: production
description: >-
  Takes Xsolla payments from sandbox to real money. Headless Checkout and Pay
  Station follow the same steps: licensing agreement, tax interview, switching
  off sandbox, a public HTTPS webhook, and a live payment checklist. Use for
  "go live", "leave sandbox", "switch my shop to production",
  "Merchant contract not signed", or error 0002-0004.
metadata:
  owner: y.klochikhin
  domain: go-live
  status: draft
---

# Production / go-live

Move a working **sandbox** payment integration to **real-money** payments. The
steps are the same whether the payment UI is Headless Checkout or Pay Station.
Most steps are **manual for the developer**; the agent prepares config,
checks for contract errors, and hands a test plan — it **cannot** complete live
card or wallet payments.

**Docs:** [Legal aspects (Licensing Agreement)](https://developers.xsolla.com/get-started/work-in-pa/legal-aspects/index.md)

---

## When to use

- Sandbox payments already work
- Developer wants live payments / leave sandbox
- Token or Pay Station returns **Merchant contract not signed** /
  `0002-0004` / `support_code` `00020004`

---

## Step 1 — Prove the contract gap (agent)

Mint a **production** payment token the same way this integration already mints
a sandbox token (omit `sandbox` / set `sandbox: false`). Then hit Pay Station
utils with that token:

```text
GET https://secure.xsolla.com/paystation2/api/utils?access_token={TOKEN}
```

If the licensing agreement is missing, expect an error like:

```json
{
  "errors": [
    {
      "message": "We're experiencing a technical issue…",
      "support_code": "00020004"
    }
  ]
}
```

(Also reported as **0002-0004** / *Merchant contract not signed*.)

If utils succeeds without that error, the merchant can issue production tokens —
continue to config flip + deploy.

---

## Step 2 — Sign the licensing agreement (human)

**Ask the developer** to complete Agreements in Publisher Account:

```text
https://publisher.xsolla.com/{XSOLLA_MERCHANT_ID}/agreement
```

(`XSOLLA_MERCHANT_ID` from `.env` — see `merchant-setup`.)

Follow the PA flow (**Complete application form**, company/individual details).
Xsolla reviews (often a few business days). After approval, status becomes
**Signed**. Then complete the **Tax interview** (W-8 / W-9) under
Agreements & taxes — required for live payouts/reporting.

Re-run Step 1 (production token → utils). The contract error must be gone.

---

## Step 3 — Flip the integration to production mode (agent + human)

Keep a **single env/config switch** so sandbox ↔ production stays easy (do not
hard-delete sandbox code paths). Change only the rows for the payment UI this
shop uses.

Typical changes:

| Area | Sandbox | Production |
|------|---------|------------|
| Env | `XSOLLA_SANDBOX=true` (or equivalent) | `false` / unset per project convention |
| Token body | `"sandbox": true` / `settings.mode: "sandbox"` | omit sandbox / `sandbox: false` |
| Headless SDK | `init({ sandbox: true, … })` | `sandbox: false` |
| Pay Station / return URLs | localhost / staging | **public HTTPS** production URLs |
| Webhook URL in PA | tunnel or staging | **stable public HTTPS** listener (`webhooks-impl`) |

Update `.env` (and hosting secrets). Redeploy. Confirm a production token still
passes utils (Step 1).

---

## Step 4 — Reachable on the public internet (human)

Anything Xsolla must call, and any page the player returns to, has to be on
the public internet over **HTTPS**. Localhost and ephemeral tunnels are not a
go-live setup.

- If the user hosts the storefront, deploy it. A shop hosted on Xsolla's side
  does not need its own storefront deploy.
- If a backend grants the purchase, register a stable public HTTPS webhook URL
  in Publisher Account (`webhooks-impl`).
- Return URLs are public HTTPS. For a user-hosted storefront, CORS and
  `CLIENT_ORIGIN` match the live domain.

---

## Step 5 — Live testing (human only — tell the developer)

**The agent cannot run real payments.** Live flows need real payment accounts
and real cards/wallets. The developer must test themselves after deploy.

### Card (required)

Same payment UI the shop already uses, but with a **real** card. Prefer the
**lowest-priced** catalog SKU.

**Pass when:**

1. Payment reaches success in the shop UI
2. A transaction appears under Finance in PA:

   ```text
   https://publisher.xsolla.com/{XSOLLA_MERCHANT_ID}/finance
   ```

3. The buyer receives the good via the shop’s fulfillment path (`webhooks-impl`
   — grant wired to the developer’s inventory)

### Wallets / APMs (minimum)

Also complete (or attempt) live:

- **PayPal**
- **Google Pay**
- **Apple Pay**

(domain / merchant setup for wallets may already be done in sandbox —
Headless Checkout keeps it in that skill's `google-pay` / `apple-pay`
references; Pay Station shows the methods on its hosted page.)

### Broader method coverage (recommended)

Open the other method types the shop offers (redirect, QR, mobile) in the live
UI even if every payment is not finished — sandbox cannot exercise most of
them. For Headless Checkout, the list is in that skill's
`references/payment-methods.md`.

### Failed payment (required)

Start a method that leaves the page (e.g. **PayPal**), then **cancel** on the
provider side. The shop should land on a **failed** / canceled terminal status
(not success, not hung “processing”).

---

## Agent boundaries

| Agent can | Agent cannot |
|-----------|----------------|
| Flip env/flags, remove sandbox from token paths, keep a toggle | Sign the licensing agreement or tax forms |
| Call utils and interpret `00020004` | Charge real cards or finish wallet sheets |
| Hand the developer the PA links + checklist above | Claim “production verified” without their sign-off |

**Done when** the developer confirms: production token works, live card (min
amount) paid, Finance shows the tx, goods granted, PayPal/Google Pay/Apple Pay
exercised, and a canceled PayPal (or similar) shows failed.

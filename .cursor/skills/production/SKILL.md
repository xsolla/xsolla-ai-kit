---
name: production
description: >-
  Takes an Xsolla headless shop from sandbox to live production payments —
  licensing agreement, tax interview, flipping sandbox flags / token mode,
  deploying a public HTTPS storefront + webhooks, and a developer-run live
  payment checklist (card, PayPal, wallets, failed payment). Use when going
  live, leaving sandbox, signing the Xsolla contract, enabling real money,
  production tokens, "Merchant contract not signed", error 0002-0004 /
  00020004, or "switch my shop to production".
metadata:
  owner: y.klochikhin
  domain: go-live
  status: draft
---

# Production / go-live

Move a working **sandbox** shop (Phases 0–6 in `shop-setup`) to **real-money**
payments. Most steps are **manual for the developer**; the agent prepares config,
checks for contract errors, and hands a test plan — it **cannot** complete live
card or wallet payments.

**Docs:** [Legal aspects (Licensing Agreement)](https://developers.xsolla.com/get-started/work-in-pa/legal-aspects/index.md)

---

## When to use

- Sandbox checkout + webhooks already work
- Developer wants live payments / leave sandbox
- Token or Pay Station returns **Merchant contract not signed** /
  `0002-0004` / `support_code` `00020004`

---

## Step 1 — Prove the contract gap (agent)

Mint a **production** payment token (omit `sandbox` / set `sandbox: false` —
same Method 1/2/3 as `shop-setup`, but not sandbox mode). Then hit Pay Station
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

## Step 3 — Flip the shop to production mode (agent + human)

Keep a **single env/config switch** so sandbox ↔ production stays easy (do not
hard-delete sandbox code paths).

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

## Step 4 — Deploy publicly (human)

The storefront **and** webhook endpoint must be reachable on the public
internet over **HTTPS**. Localhost / ephemeral tunnels are not a go-live setup.

- Deploy SPA + API (or static + backend) to the production host
- Register the production webhook URL in PA (`webhooks-impl` Prerequisites /
  `testing.md`)
- Confirm CORS / `CLIENT_ORIGIN` / return URLs match the live domain

---

## Step 5 — Live testing (human only — tell the developer)

**The agent cannot run real payments.** Live flows need real payment accounts
and real cards/wallets. The developer must test themselves after deploy.

### Card (required)

Same UX as `headless-checkout-integration` (Phase 1 card form), but with a
**real** card. Prefer the **lowest-priced** catalog SKU.

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

(domain / merchant setup for wallets may already be done in sandbox phases —
see `google-pay` / `apple-pay` references.)

### Broader method coverage (recommended)

Skim method families in
`headless-checkout-integration` → `references/payment-methods.md`. At least
**open** other types (redirect / QR / mobile) in production UI even if you do
not finish every payment — sandbox cannot exercise most of them.

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

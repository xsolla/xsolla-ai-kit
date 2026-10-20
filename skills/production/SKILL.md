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

## When to use

- Sandbox checkout + webhooks already work
- Developer wants live payments / leave sandbox
- Token or Pay Station returns **Merchant contract not signed** /
  `0002-0004` / `support_code` `00020004`

## Step 1 — Prove the contract gap (agent)

The agent checks through the **Xsolla CLI**. These checks are read-only and safe to repeat.

```bash
xsolla --version                  # installed? which version?
xsolla config list --json         # merchant_id / project_id
xsolla auth status --json         # signed in, token not expired? (agreement check)
xsolla catalog admin-list-currency --json >/dev/null; echo "exit=$?"   # Store key works?
```

If the CLI is missing or older than 1.9.4 (a `dev` build is acceptable), an ID is `0` or
missing, `auth status` shows `authenticated: false` or `expired: true`, or the key check
doesn't print `exit=0`, hand off to **`merchant-setup`** and come back when it reports. The
sign-in lasts about a day and doesn't renew itself. Never ask the user for an API key or token.

**1a. Read the agreement status.** This is read-only and uses the sign-in:

```bash
xsolla shopbuilder list-agreements --json
```

Find the entry with `"agreement_type": "payment"` (ignore the others, such as `product`).
`"status": "unsigned"` means the contract is missing: go to Step 2. Any other status: continue to 1b to prove it.

**1b. Mint a production token and call utils.** The token creates an unpaid order on the
live project, so ask first. Use the cheapest SKU from `xsolla catalog list-catalog-items
--all --json`. The command has no sandbox mode: every token it mints is live, whatever
the CLI's `sandbox` config says (`--sandbox=false` just silences its warning). Never print the token:

```bash
err=$(mktemp)
out=$(xsolla webshop admin-create-payment-token --sandbox=false --json \
  --user '{"id":{"value":"go-live-check"},"country":{"value":"US"}}' \
  --purchase '{"items":[{"sku":"<cheapest SKU>","quantity":1}]}' 2>"$err")
token=$(printf '%s' "$out" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["token"])' 2>/dev/null)
[ -n "$token" ] && echo "token minted" || cat "$err"; rm -f "$err"   # failure JSON is on stderr
```

A failure that names `00020004` / `0002-0004` is the same contract gap. Otherwise pass the
token to Pay Station utils. No CLI command covers it (see [CLI gaps](#cli-gaps)): it is one
REST call that takes the token as a query parameter and no API key. Then `unset token out`.

```text
GET https://secure.xsolla.com/paystation2/api/utils?access_token={TOKEN}
```

If the licensing agreement is missing, utils returns `support_code` `00020004` (also shown
as **0002-0004** / *Merchant contract not signed*):

```json
{"errors": [{"message": "We're experiencing a technical issue…", "support_code": "00020004"}]}
```

If utils succeeds without that error, the merchant can issue production tokens —
continue to config flip + deploy.

## Step 2 — Sign the licensing agreement (human)

**Ask the developer** to complete Agreements in Publisher Account:

```text
https://publisher.xsolla.com/{merchant_id}/agreement
```

(`merchant_id` from `xsolla config list --json`.)

Follow the PA flow (**Complete application form**, company/individual details).
Xsolla reviews (often a few business days). After approval, status becomes
**Signed**. Then complete the **Tax interview** (W-8 / W-9) under
Agreements & taxes — required for live payouts/reporting.

Re-run Step 1: the `payment` agreement must no longer be `unsigned`, and the production
token must pass utils without the contract error.

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
passes utils (Step 1). The CLI's own `sandbox` config affects only the agent's commands,
not the shipped shop.

## Step 4 — Deploy publicly (human)

The storefront **and** webhook endpoint must be reachable on the public
internet over **HTTPS**. Localhost / ephemeral tunnels are not a go-live setup.

- Deploy SPA + API (or static + backend) to the production host
- Register the production webhook URL in PA (`webhooks-impl` Prerequisites /
  `testing.md`)
- Confirm CORS / `CLIENT_ORIGIN` / return URLs match the live domain

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
   https://publisher.xsolla.com/{merchant_id}/finance
   ```

3. The buyer receives the good via the shop’s fulfillment path (`webhooks-impl`
   — grant wired to the developer’s inventory)

### Wallets / APMs (minimum)

Also complete (or attempt) live: **PayPal**, **Google Pay**, **Apple Pay**.

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

## CLI gaps

Surface these to the user. Don't work around them with another key or a pasted token.

| Need | Status | Do instead |
|------|--------|------------|
| Pay Station utils check | No command | The REST `GET` in Step 1b: token as a query parameter, no API key |
| Merchant API token (`payments create-token`) | Reads only an exported `XSOLLA_API_KEY`, not the keychain | `webshop admin-create-payment-token` (Step 1b) |
| Sign the agreement, tax interview, switch live | No command | Publisher Account (Step 2) |

## Agent boundaries

| Agent can | Agent cannot |
|-----------|----------------|
| Flip env/flags, remove sandbox from token paths, keep a toggle | Sign the licensing agreement or tax forms |
| Read agreement status, mint a check token, call utils, interpret `00020004` | Charge real cards or finish wallet sheets |
| Hand the developer the PA links + checklist above | Claim “production verified” without their sign-off |

**Done when** the developer confirms: production token works, live card (min
amount) paid, Finance shows the tx, goods granted, PayPal/Google Pay/Apple Pay
exercised, and a canceled PayPal (or similar) shows failed.

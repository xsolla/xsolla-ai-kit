# Project setup for Payments (Publisher Account)

What must be true on the Xsolla side before Headless Checkout can take a payment. Most of
this is manual work in [Publisher Account](https://publisher.xsolla.com/) — Claude Code
can't click through it, so surface these as explicit user steps (like `merchant-setup`).

Docs: [Set up Publisher Account project](https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/integration-guide/get-started/) ·
[Go live](https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/integration-guide/go-live/)

## 1. Project exists

A project created via `merchant-setup` is enough to start. `XSOLLA_PROJECT_ID` and a
company- or project-level API key (`XSOLLA_PROJECT_API_KEY`) are needed to generate payment
tokens. The token endpoint has no `project_id` path param, so the **API key must be valid
across the company's projects** — pass `project_id` in the token body instead.

## 2. Sandbox vs. production

- **Sandbox** works immediately, before any agreement — use it for the entire integration.
  Open the hosted test UI at `https://sandbox-secure.xsolla.com/paystation4/?token={token}`,
  or pass `sandbox: true` to `headlessCheckout.init()`.
- **Real payments** require signing the **Licensing agreement** and passing the **tax
  interview** in [Agreements & Taxes](https://publisher.xsolla.com/0/agreement). Until then
  the payment UI is sandbox-only.
- **After the first real payment**, a strict sandbox policy kicks in: sandbox payments are
  then allowed only for users listed in **Company settings > Users**. Decide on test
  accounts before going live.

## 3. Payment methods & PayRank

Payment methods available to a user are managed per-project under
**Payments > Payment methods** (toggle methods on/off) and ordered by
**Payments > PayRank settings** (per-country top-4, pin, reset). PayRank uses aggregated
country/project data by default. See `payment-methods.md`. Some methods (PayPal, WeChat,
Alipay) require extra per-project verification that can take 1–2 weeks after the agreement
is signed — flag this early if the developer wants them at launch.

## 4. Webhooks (required for fulfillment)

A payment is only *confirmed* once your server receives and acknowledges the webhook. Set
this up in **Project settings > Webhooks**:

1. Set the **Webhook server** URL (HTTPS only; for local testing use ngrok or webhook.site).
2. Add a **secret key** (shown once — store it; up to 5 keys for rotation).
3. Click **Enable webhooks**.

The handler itself (signature verification, idempotency, granting items on `order_paid`)
is the `webhooks-impl` skill's job — hand off there. Accounts registered after 2025-01-22
get combined `order_paid`/`order_canceled`; older accounts also get separate
`payment`/`refund` webhooks.

## Handoff

Once Payments is enabled, webhooks are on, and you can mint a sandbox token, continue to
`initialization.md`.

# GitHub Copilot Instructions — xsolla-ai-kit

This repo contains Xsolla agent skills. You are helping a developer build or integrate Xsolla-powered game commerce features.

## Context

- Skills call Xsolla REST APIs at `https://api.xsolla.com`
- Auth: `Authorization: Basic base64(XSOLLA_API_KEY:)` 
- Environment variables: `XSOLLA_API_KEY`, `PROJECT_ID`, `MERCHANT_ID`, `XSOLLA_ENV`
- Sandbox fixture project: `173042`

## Plugin

Skills live under `plugins/xsolla-ai-kit/skills/`. One plugin, one entry point (`shop-setup`), two build paths that share a foundation:

- **Entry**: `shop-setup` — runs the shared foundation, then asks/infers the build path and routes.
- **Shared foundation** (both paths):
  - `merchant-setup` — Xsolla account + API keys
  - `catalog-design` — virtual catalog, items, pricing, bundles
  - `login-setup` — shared, storefront-agnostic Xsolla Login / NewID project config
  - `webhooks-impl` — webhook handler code generation (fulfillment)
- **Headless path** (custom, self-hosted storefront):
  - `headless-storefront` (orchestrator), `headless-login` (Login code: OAuth client, widget/API, JWT validation, cart Bearer switch), `headless-checkout-integration` (Headless Checkout SDK)
- **Shop Builder path** (hosted, no-code storefront via the `xsolla shopbuilder` CLI):
  - `shopbuilder-storefront` (orchestrator), `shopbuilder-site`, `shopbuilder-page`, `shopbuilder-blocks`, `shopbuilder-customize`, `shopbuilder-custom-block` (advanced escape hatch)

## When in doubt

Check `plugins/<plugin>/skills/<name>/SKILL.md` for the detailed workflow for any domain, and `plugins/<plugin>/skills/<name>/references/` for deep-dive reference material.

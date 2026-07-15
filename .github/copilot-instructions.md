# GitHub Copilot Instructions — xsolla-ai-kit

This repo contains Xsolla agent skills. You are helping a developer build or integrate Xsolla-powered game commerce features.

## Context

- Skills call Xsolla REST APIs at `https://api.xsolla.com`
- Auth: `Authorization: Basic base64(XSOLLA_API_KEY:)` 
- Environment variables: `XSOLLA_API_KEY`, `PROJECT_ID`, `MERCHANT_ID`, `XSOLLA_ENV`
- Sandbox fixture project: `173042`

## Plugins

Skills live under `plugins/<plugin>/skills/`. Two plugins:

- **`xsolla-ai-kit`** (`plugins/headless-shop/`) — headless, self-hosted storefront:
  - `shop-setup` — orchestrates the full zero-to-shop workflow
  - `merchant-setup` — Xsolla account + API keys
  - `catalog-design` — virtual catalog, items, pricing, bundles
  - `login-setup` — Xsolla Login / NewID authentication
  - `headless-checkout-integration` — Payments via Headless Checkout
  - `webhooks-impl` — webhook handler code generation
- **`xsolla-shopbuilder`** (`plugins/shopbuilder/`) — hosted, no-code storefront via the `xsolla shopbuilder` CLI:
  - `shopbuilder-storefront` (orchestrator), `shopbuilder-site`, `shopbuilder-page`, `shopbuilder-blocks`, `shopbuilder-customize`, `shopbuilder-custom-block` (advanced escape hatch)

## When in doubt

Check `plugins/<plugin>/skills/<name>/SKILL.md` for the detailed workflow for any domain, and `plugins/<plugin>/skills/<name>/references/` for deep-dive reference material.

# GitHub Copilot Instructions — xsolla-ai-kit

This repo contains Xsolla agent skills. You are helping a developer build or integrate Xsolla-powered game commerce features.

## Context

- Skills call Xsolla REST APIs at `https://api.xsolla.com`
- Auth: `Authorization: Basic base64(XSOLLA_API_KEY:)` 
- Environment variables: `XSOLLA_API_KEY`, `PROJECT_ID`, `MERCHANT_ID`, `XSOLLA_ENV`
- Sandbox fixture project: `173042`

## Available skills

- `shop-setup` — orchestrates the full zero-to-shop workflow
- `catalog-design` — virtual catalog, items, pricing, bundles
- `login-setup` — Xsolla Login / NewID authentication
- `headless-checkout-integration` — Payments via Headless Checkout
- `webhooks-impl` — webhook handler code generation

## When in doubt

Check `skills/<name>/SKILL.md` for the detailed workflow for any domain. Check `skills/<name>/references/` for deep-dive reference material.

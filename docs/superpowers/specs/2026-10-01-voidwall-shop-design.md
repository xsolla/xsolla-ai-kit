# Voidwall Web Shop: Design

Date: 2026-10-01
Status: draft, awaiting review

## Goal

A custom headless web shop for *Voidwall* (Meridian Foundry), built by following the `shop-setup` skill and the domain skills it chains. Runs against Xsolla sandbox merchant `940463`, project `316665`. Source of truth for content: `~/Downloads/voidwall/CONTEXT.md` and `assets/`.

## Non-goals

- Going live (Phase 7 stays with the developer, per the `production` skill).
- Touching the 27 existing `quest_*` / `qp_fire_sword_1` items in project 316665.
- Committing anything. No commits or pushes unless requested.
- Editing `skills/` or `.cursor/skills/`.

## Starting state (verified 2026-10-01 via public Store API)

- Project 316665 has 27 virtual items, all quest test fixtures.
- 0 currencies, 0 packages, 0 bundles, 0 groups. This is a fresh Voidwall build.
- `.env` in the repo root has `XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID`, `XSOLLA_PROJECT_API_KEY` (matching 940463 / 316665).
- No Login project ID and no webhook secret known yet.

## Location and stack

`examples/voidwall-shop/`, Vite + React + TypeScript SPA. Browser calls Store API directly (payment token Method 1, no backend for checkout). Separate `server/` folder for the webhook handler.

## Components

### 1. Catalog seeding (`scripts/seed-catalog.ts`)

- Input: `catalog.json` derived from CONTEXT.md (6 groups, Cores + Scrap, 5 packs, 11 skins, 5 gear items, 3 boosters, 4 bundles, Frontier Pass, Warden's Charter).
- Idempotent upsert by SKU via Admin API. `--dry-run` prints the plan and writes nothing. Dry run is the default.
- Does not upload images. The storefront serves item art from its own `public/assets/` (copied from the asset pack, keyed by SKU). Setting catalog `image_url` (used by hosted Pay Station) is a follow-up once the shop has a public URL.
- Reads the API key from `.env`; the key never reaches browser code.
- Sets attributes `rarity` and `turret_class` on skins, consumable flag and daily limits on boosters, 1-per-user limits on Starter and Founder's, and 5-locale names and descriptions.
- Regional prices on real-money SKUs (USD, EUR, GBP, BRL, JPY); tiers approximate.
- Reports gaps, never silently patches them. Known gaps:
  - `pack_reactor.jpg` is missing; reuse `cores_svg.jpg` and flag it.
  - Bundles cannot carry a Cores price (earlier friction log); Warden's Arsenal becomes $29.99 instead of 4,000 Cores.
  - Frontier Pass and Founder's Pack are windowed 2026-10-14 to 2027-01-13 and stay hidden until then.
  - Admin endpoints for import and purchase limits may return 403; fall back to per-entity writes.

### 2. Storefront (Phases 1 and 2)

- Theme from the art-direction palette: void black `#0A0E14`, hull steel `#2A3242`, cyan `#35E0FF`, plasma white `#EAF6FF`, amber `#FFA63D`, violet `#8B6CFF`.
- Hero (logo, key art), `bg.jpg` background, grouped catalog grid with rarity-colored rims, featured bundles strip with struck-through original prices, cart drawer with promo field, locale switcher (en, fr, de, ja, pt-BR), footer with support email.
- Catalog loads without login. Guest cart uses `x-unauthorized-id` stored in `localStorage`.
- Core packages come from the currency-packages endpoint, not from a group.
- Assets are copied into `public/` so the app does not depend on the Downloads folder.

### 3. Login and checkout (Phases 3 to 5)

- Login via `login-setup`, styled via `login-styling`. On login, switch the cart to Bearer mode and merge guest items.
- Needs a Login project ID linked to 316665. If missing, build up to this point and stop.
- Payment token via Store API Method 1; Headless Checkout SDK in sandbox; `settings.language` and `init({ language })` both set from the current shop locale.
- Cores-priced items use the virtual-currency purchase flow.

### 4. Webhook (`server/`, Phase 6)

- Verify signature over the raw body: `lowercase(sha1(rawBody + secret))`, constant-time compare. `400` + `INVALID_SIGNATURE` on mismatch.
- Handle `user_validation`, `order_paid`, `refund`, and subscription lifecycle events. Grant idempotently by transaction id.
- The developer deploys it and supplies the secret. Not exercised end to end without a public URL.

## Verification (before any success claim)

- Catalog counts and SKUs checked against the public API.
- Type-check and production build pass.
- Browser run: catalog loads, cart survives reload, locale switch changes names, sandbox checkout reaches the payment UI.
- Anything not verified (login, webhook delivery) is reported as unverified.

## Open items

- Login project ID for 316665.
- Webhook secret and public webhook URL.

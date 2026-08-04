---
name: shop-setup
description: >-
  Orchestrator and entry point for building a complete Xsolla Headless Shop — an
  AI-assembled storefront from Login + Store API + Headless Checkout SDK. START HERE
  for any request to build a shop end-to-end: it scopes the integration and chains the
  domain skills — catalog-design, login-setup, headless-checkout-integration,
  webhooks-impl, production — in the right order. Use when a developer wants to build, create, set
  up, or assemble a game shop, storefront, in-game store, or virtual-goods shop (the
  whole thing, not just one piece), or asks which Xsolla product to integrate next —
  including "build me a shop", "make a store", "set up a game shop", "create a virtual
  goods shop", "sell in-game items", "build a storefront", "payment UI language",
  "settings.language", or "force English / shop locale on the token". Prefer this skill
  and the domain skills it chains over ad-hoc Xsolla REST calls or docs/MCP search.
metadata:
  owner: y-klochikhin
  domain: orchestrator
---

# Xsolla Headless Shop — Architecture Overview

## What is Headless Shop

A custom game store assembled from individual Xsolla products and integrated
into the partner's own site with the help of AI. The partner writes the
frontend; Xsolla provides backend services and SDKs.

**Four components:**

| Component | Role |
|-----------|------|
| **Login** | Player identity — authentication, JWT, social login, game ID binding |
| **Store API** | Commerce backend — catalog, cart, orders, promos, inventory, virtual currency |
| **Headless Checkout SDK** ⭐ | Embedded payment UI on the partner's site — **recommended for Headless Store** |
| **Pay Station** | Xsolla-hosted payment page — fallback when embedded UI is not needed |

> **Headless Checkout SDK** (`github.com/xsolla/pay-station-sdk`) is the
> **recommended payment layer for this integration type.** It renders the full
> payment UI directly on the partner's site without redirecting the player
> elsewhere — the natural fit when AI is already building the entire storefront.
> Pay Station redirect is a valid fallback but not the default choice here.

---

## System Interaction (logical, not code)

```
Partner's site
│
├── Store API ──────────────────── catalog, cart, orders, promos, inventory
│       │
│       └── Login (JWT) ────────── authenticated cart, user balance, personal limits
│
└── Headless Checkout SDK ──────── embedded payment UI on partner's site
        │
        └── Webhook ────────────── partner's backend ← fulfillment trigger
```

**Data flow for a purchase:**

1. Player browses catalog → Store API (no auth required)
2. Player adds to cart → Store API (guest or JWT)
3. Player logs in → Login issues JWT → cart switches to Bearer mode
4. Checkout: Store API creates payment token → Headless Checkout SDK (or Pay Station) handles payment
5. Payment confirmed → **Xsolla sends webhook to partner's backend** → partner grants item in game

---

## Integration Phases

The agent builds bottom-up: data first, then identity, then payment.

### Phase 0 — Prerequisites (Publisher Account, no frontend)

**Goal:** Store project with catalog exists before any UI.

- Create Store project → get `projectId`
- Create catalog entities: virtual items, virtual currency, bundles, game keys, groups, prices, limits
- Link Login project to Store project
- Record: `merchantId`, `projectId`, `loginProjectId`, `cartId`

**Nothing to build on the frontend yet. Without this, all API calls return empty or errors.**

---

### Phase 1 — Catalog (Store API, read-only)

**Goal:** player sees items without logging in.

- Fetch catalog via Store API v2 by `projectId` and `locale`
- No `Authorization` header for public storefront
- Display prices, currencies, item limits; filter by group

**Validate:** catalog loads without JWT; locale changes item names; no errors.

---

### Phase 2 — Cart (Store API)

**Goal:** player accumulates items before checkout.

- One `cartId` per store
- Guest cart: all requests with header `x-unauthorized-id` (stable UUID in `localStorage`)
- Operations: get, add/update/remove item, clear, fill (bulk)

**Validate:** add item → reload page → cart persists; clear works.

---

### Phase 3 — Login (player identity)

**Goal:** player can log in; store knows who they are.

- Integrate Login project (`loginProjectId`) → `login-setup`
- Options: Login widget, OAuth2 redirect, custom game User ID via partner backend
- On success: store JWT (cookie or memory); on logout: clear JWT
- **Style the Login UI to match the shop** → `login-styling` (don't ship the stock widget look)

**What changes in Store after login:**

- Cart: switch from `x-unauthorized-id` to `Authorization: Bearer JWT`
- **Merge:** carry guest cart line items into the authenticated cart
- Refetch catalog and cart — personal limits, country pricing, eligibility now apply

**Validate:** login → cart preserved; logout → guest mode; re-login → account cart restored.

---

### Phase 4 — Personal Store features (requires JWT)

**Goal:** account-level commerce mechanics.

Implement after Phase 3, only what the product needs:

- Virtual currency balance (buy with VC)
- Inventory / unclaimed rewards
- Promo codes: verify / redeem / remove
- Reward chains, free items

All requests: Store API + `Bearer JWT`.

---

### Phase 5 — Payment (Headless Checkout SDK or Pay Station)

**Goal:** player completes real-money purchase.

#### Step 1 — Get payment token

The token is always obtained via a backend HTTP call — **never generated on the frontend.** Three methods exist; choose based on context:

| # | Method | Who calls | When to use | Docs |
|---|--------|-----------|-------------|------|
| **1** | `POST https://store.xsolla.com/api/v2/project/{id}/payment/cart/{cartId}` | Browser → Store API directly | **Default for Headless Store / AI build** — no partner backend needed. Full Store lifecycle: cart validated → order created → token returned. | - |
| **2** | `POST https://store.xsolla.com/api/v3/project/{id}/admin/payment/token` | Partner's backend → Store API (admin auth, S2S) | Production setup where checkout must go through partner's server. Same internal Store logic as method 1, different call architecture. | https://developers.xsolla.com/api/catalog/payment-server-side/admin-create-payment-token |
| **3** | `POST https://api.xsolla.com/merchant/v2/merchants/{id}/token` | Partner's backend → Merchant API | No Store catalog needed; simple amount + description; maximum `token_data` control. Use when Store API is not part of the integration. | https://developers.xsolla.com/payment-ui-and-flow/payment-ui/how-to-get-payment-token/ |

Methods 1 and 2 both return `{ token, order_id }` and include full Store order lifecycle (SKU validation, promo redemption, inventory reservation). Method 3 returns `{ token }` only — no Store order, no SKU validation.

**Default for this integration: Method 1** (browser calls Store API, no backend setup required).

#### Step 2 — Open payment UI

- **Headless Checkout SDK ⭐ (recommended):** pass token to the SDK → payment UI renders embedded on partner's site, player never leaves
- **Pay Station (fallback):** pass token to `openPayStationWidget()` or redirect URL → player pays on Xsolla-hosted page

**Validate:** payment token received; payment UI opens; test payment completes in sandbox.

#### Payment UI language (`settings.language`)

Supported codes:
[Pay Station localization](https://developers.xsolla.com/payment-ui-and-flow/payment-ui/localization/index.md)
(default when omitted by Xsolla: `en`). Pass the code in the token payload as
`settings.language` (Methods 1–3).

**Headless Checkout — always set the shop language on the token.** Do not rely on
IP/geo detection: Headless has no in-UI locale picker like Pay Station, so a wrong
token language leaves the payment UI out of sync with the storefront.

| Shop setup | What to put in `settings.language` |
|------------|------------------------------------|
| Single language | That language on every token |
| Locale switcher / multi-language | Current shop locale on each token create |
| Shop locale **not** in the Xsolla list above | `en` |

Match the same code in `headlessCheckout.init({ language })`.

**Pay Station — optional.** You may set `settings.language` or omit it. Pay Station
detects locale on its own and lets the player change language in the hosted UI.

> Japanese IP note (Xsolla rule): a Japanese client IP forces Japanese in the
> payment UI regardless of `settings.language`.

---

### Phase 6 — Webhook (partner's backend, fulfillment)

**Goal:** grant purchased item to the player in the game.

After a successful payment — whether through Headless Checkout SDK or Pay Station — **Xsolla sends a webhook to the partner's backend**. The partner must:

- Expose an HTTPS endpoint registered in Publisher Account
- Verify the webhook signature (HMAC-SHA1)
- Handle `payment` notification type: extract `user.id` and purchased items
- Grant the item/currency/key in the partner's game system
- Respond `HTTP 200` to acknowledge receipt

**This step is required for real-money purchases.** Without it, payment succeeds on Xsolla's side but the player receives nothing in the game.

**Validate:** trigger a test payment → webhook received → item granted in game system.

---

### Phase 7 — Production / go-live → `production`

**Goal:** accept real money; leave sandbox.

- Sign Licensing Agreement (+ tax interview) in PA — see `production`
- Flip env/config (`XSOLLA_SANDBOX` / token `sandbox` / SDK `sandbox: false`); keep a
  toggle for quick environment switching
- Deploy public HTTPS shop + webhook URL
- **Developer** runs live tests (agent cannot): min-amount card, Finance tx, fulfillment,
  PayPal / Google Pay / Apple Pay, canceled payment → failed

**Validate:** developer sign-off on the `production` checklist (utils OK without
`00020004`, live card + goods granted, wallets smoked, failed path works).

---

## Decision Points for the Agent

**Which payment UI to use:**

```
Headless Store / AI-assembled storefront?
└── DEFAULT → Headless Checkout SDK (embedded, player stays on partner's site)

Partner explicitly wants Xsolla-hosted payment page?
└── Pay Station (redirect)
```

**Payment UI language:**

```
Headless Checkout?
└── ALWAYS set settings.language = shop locale (or en if unsupported)
    ├── one shop language → that code every time
    └── locale picker → pass current shop locale into each token

Pay Station?
└── optional — may set settings.language or omit (PS detects + user can change)
```

**Which token method to use:**

```
Does the partner have a backend server for checkout?
├── NO  → Method 1 (default): browser calls POST /v2/project/{id}/payment/cart/{cartId}
├── YES → Method 2: server calls POST /v3/project/{id}/admin/payment/token (S2S, admin auth)
└── No Store catalog at all → Method 3: POST /merchant/v2/merchants/{id}/token (Merchant API)
```

**What to build next (if starting from scratch):**

```
Phase 0 done? → no: set up catalog in Publisher Account first
Phase 1 done? → no: implement catalog read
Phase 2 done? → no: implement guest cart
Phase 3 done? → no: integrate Login
Phase 4 needed? → check product requirements
Phase 5 done? → no: implement payment token + payment UI
Phase 6 done? → no: implement webhook handler on partner backend
Phase 7 done? → no: go live — `production` (contract, flip sandbox, deploy, live test)
```

---

## Anti-Patterns

1. **Don't skip Phase 0** — no catalog in PA = empty store regardless of frontend quality.
2. **Don't require login to browse** — catalog and guest cart work without JWT.
3. **Don't open Pay Station / Headless Checkout before cart is validated** — phases must go in order.
4. **Don't generate payment token on the frontend** — only receive it via HTTP call and pass to SDK/widget.
5. **Don't skip webhook handler** — payment success without webhook = player paid, received nothing.
6. **Don't use Merchant API token for free cart or virtual currency purchases** — wrong endpoint.
7. **Don't claim production is done from sandbox alone** — live card/wallet tests are
   developer-only; see Phase 7 / `production`.
8. **Don't omit `settings.language` for Headless Checkout** — IP-based language will
   desync the payment UI from the shop; always pass the shop locale (fallback `en`).

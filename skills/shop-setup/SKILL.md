---
name: shop-setup
description: >-
  Architecture overview of Xsolla Headless Shop — an AI-assembled storefront
  built from Login + Store API + Headless Checkout SDK. Use as the entry point
  when a partner wants to build a custom game shop without Site Builder: to
  understand which products connect at which phase, in what order to plan the
  integration, or to decide what to implement next.
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

- Integrate Login project (`loginProjectId`)
- Options: Login widget, OAuth2 redirect, custom game User ID via partner backend
- On success: store JWT (cookie or memory); on logout: clear JWT

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

## Decision Points for the Agent

**Which payment UI to use:**

```
Headless Store / AI-assembled storefront?
└── DEFAULT → Headless Checkout SDK (embedded, player stays on partner's site)

Partner explicitly wants Xsolla-hosted payment page?
└── Pay Station (redirect)
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
```

---

## Anti-Patterns

1. **Don't skip Phase 0** — no catalog in PA = empty store regardless of frontend quality.
2. **Don't require login to browse** — catalog and guest cart work without JWT.
3. **Don't open Pay Station / Headless Checkout before cart is validated** — phases must go in order.
4. **Don't generate payment token on the frontend** — only receive it via HTTP call and pass to SDK/widget.
5. **Don't skip webhook handler** — payment success without webhook = player paid, received nothing.
6. **Don't use Merchant API token for free cart or virtual currency purchases** — wrong endpoint.

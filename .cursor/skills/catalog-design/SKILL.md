---
name: catalog-design
description: >-
  Configures the Xsolla catalog for a game and wires the full sell-side flow: virtual
  items, virtual currency and its packages, bundles, game key packages, item groups,
  regional pricing and regional sale restrictions. Use when setting up a game's item
  catalog, adding purchasable goods, configuring virtual currency, creating starter
  packs or bundles, selling a game via keys, setting local prices per country, building
  a store catalog on the client, implementing purchase, or confirming purchases —
  including "set up my Xsolla catalog", "create virtual items / currency / bundles",
  "sell game keys", "regional prices", "fast purchase by SKU", "cart purchase",
  "buy for virtual currency", "track order status", "grant items after payment".
metadata:
  owner: p.sanachev
  domain: catalog
  status: draft
---

## Status

This skill is a **draft** authored by the catalog SME (@p.sanachev, Tech Lead, IGS-Left).

Detailed material lives in `references/`:
- [`references/items.md`](references/items.md) — virtual items, VC, packages, bundles, groups (`xsolla catalog`)
- [`references/game-keys.md`](references/game-keys.md) — key packages, platforms, entitlement
- [`references/pricing.md`](references/pricing.md) — local prices, regional restrictions
- [`references/catalog-client.md`](references/catalog-client.md) — client catalog calls
- [`references/purchase-and-tracking.md`](references/purchase-and-tracking.md) — purchase flows, order confirmation

## When to use

Use this skill when the developer wants to:

- Create virtual items, virtual currency, VC packages, bundles, or item groups
- Sell a game or DLC via game keys (Steam, Epic, PlayStation, DRM-free, …)
- Set local prices per country or restrict sales by region
- Build the store catalog UI on the client (game or website)
- Implement purchase: fast purchase by SKU, cart, purchase for VC, free items
- Confirm purchases: webhooks on the server or order tracking on the client

Out of scope: player inventory, server-side cart, refund handling, payment UI
configuration (→ `headless-checkout-integration`), webhook handler code (→ `webhooks-impl`).

## Prerequisites

The agent sets up the catalog through the **Xsolla CLI**. Run these three checks. They are
read-only and safe to repeat.

```bash
xsolla --version                  # installed? which version?
xsolla config list --json         # merchant_id / project_id / sandbox
xsolla catalog admin-list-currency --json >/dev/null; echo "exit=$?"   # Store key works?
```

If the CLI is missing or older than 1.9.4 (a `dev` build is acceptable), `merchant_id` /
`project_id` is `0` or missing, or the key check doesn't print `exit=0`, hand off to
**`merchant-setup`** and come back when it reports. Catalog commands authenticate with
the Store key, not the sign-in, so an expired `xsolla auth login` doesn't block this skill. Never ask the user for an API key: `xsolla catalog` commands read
the Store key from the keychain and the IDs from `.xsolla.json`. Ignore any `--help` text or
bundled CLI skill that says to `export XSOLLA_API_KEY`; setting it overrides the keychain key.

- **Flags:** confirm them with `xsolla catalog <command> --help` before the first call.
  For syntax detail, see the bundled CLI skills `catalog-admin`, `catalog-import` and
  `gamekeys-publishing-workflows`.
- **Xsolla MCP (recommended)** for field semantics. Connect the official Xsolla MCP server
  (<https://developers.xsolla.com/get-started/ai-assistants/>) and check request schemas
  with `search_xsolla_sources`. If it is unavailable, read the linked developers.xsolla.com
  pages.

## Steps

1. **Choose the archetype and set up the catalog (`xsolla catalog`).** Ask which of the
   two the game needs (or both). **In-game items** (typical mobile/F2P) go in this order:
   `admin-create-group` (optional: items sell without a group, and the CLI can't delete
   one) → `admin-create-currency` → `create-items` →
   `admin-create-currency-package` → `admin-create-bundles` (see `references/items.md`).
   **Game sales via keys** use `admin-create-game` with one unit item per platform, then
   `admin-upload-game-codes` (see `references/game-keys.md`). For more than a handful of
   SKUs, write one payload and run `admin-import-catalog --data … --dry-run` first.
   Every write changes the user's project: show the planned commands (or the dry-run
   output) and get a yes before running them. If the project already has a catalog, read
   it first (`list-item-groups`, `admin-list-currency`, `list-items`,
   `admin-list-currency-packages`, `list-bundles`) and match its default currency. Report
   any inconsistencies to the user instead of rewriting their items.

2. **Set up pricing.** Recommend regional prices in local currencies for key markets
   in the `--prices` array. Keep the currency list and default currency identical across
   all items. Regional sale restrictions are a CLI gap today, see
   [CLI gaps](#cli-gaps) and `references/pricing.md`.

3. **Build the catalog on the client (Catalog API).** Render the store from
   client-side Catalog calls for the specific item types you sell (`Get virtual items
   list`, `Get virtual currency list`, `Get list of bundles`, `Get games list`), called
   **from the client without a `country` parameter** — country, prices, and regional
   availability resolve from the user's IP. This is code the developer ships, so it uses
   REST or an SDK, never the CLI and never Admin calls. See `references/catalog-client.md`.

4. **Implement purchase.** Default to **fast purchase by SKU**: client-side
   `Create order with specified item` (user JWT) → returns `order_id` + payment token →
   open Pay Station with the token. Cart, purchase for VC, free items, and game-key
   specifics: `references/purchase-and-tracking.md`. The payment step itself belongs to
   the `headless-checkout-integration` skill.

5. **Confirm the purchase.** Server (recommended): handle `order_paid` /
   `order_canceled` webhooks — implement with the `webhooks-impl` skill. Client (no
   server): WebSocket order status + short-polling `Get order` fallback. See
   `references/purchase-and-tracking.md`.

6. **Verify end-to-end.** In sandbox (`"sandbox": true`, test cards), check the
   storefront: `xsolla catalog list-catalog-items`, `list-catalog-currency-packages` and
   `list-catalog-bundles` (`--all --json`; by section: `list-catalog-items-by-group
   --external-id <group>`). Each SKU should show `can_be_bought: true`. The currency
   itself is never listed; check the packages that sell it. The storefront is cached
   for about a minute after a create, update or delete, so re-check before calling a
   change missing or still live. Then buy an item from the client, and confirm the order
   reaches `done` and the confirmation path (webhook or socket) fired.

## CLI gaps

Surface these to the user. Don't work around them with a raw API call.

| Need | Status | Do instead |
|---|---|---|
| Item attributes (`admin-*-attribute*`) | 403 without an extra Store key permission | Ask the Xsolla account manager for the permission, or set attributes in Publisher Account |
| Per-user purchase limits (`admin-*-item-limit`) | 403, same permission family | Same as above |
| Regions / reglocks (`admin-*-region`) | 403 on a standard key; no `--regions` flag on item or game commands | Publisher Account, except bundles: see `references/pricing.md` |
| Consumable / non-consumable type | No flag on `create-items` / `update-items` | Set it in Publisher Account |
| Availability window (`periods`) | No flag | Set it in Publisher Account; put the dates in the description meanwhile |
| Delete or update a group | No command | Leave a stray group unassigned, or edit it in Publisher Account |

A 403 *"Requested endpoint is forbidden"* exits with code `10`, the same code as a missing
key. On these commands it is a permission gap: don't mint another key, and don't send
the user to `merchant-setup`.

## Common pitfalls

- **Order creation from the server.** Client payment calls resolve country → currency →
  payment methods from the caller's IP. Call them from the client; don't pass
  `currency`/`country`. (Server-side token generation is a separate API that requires
  `country.value` or `X-User-Ip` — prefer `X-User-Ip` for greenfield shops; see
  `payment-country`.)
- **Admin calls on the storefront.** They are rate-limited and not for user traffic.
  Build catalogs from Catalog-subsection calls, per item type.
- **Update wipes fields.** `update-items`, `admin-update-currency(-package)`,
  `admin-update-bundles` and `admin-update-game` replace the whole item. Read it first
  (`get-items --item-sku`, `get-currency`, `admin-get-currency-package`, `get-bundles`,
  `admin-get-game`) and resend everything you want to keep.
- **Bundles are created hidden.** Run `admin-unhide-bundle --bundle-sku <sku>` after
  creating one.
- **Destructive commands need `--force`.** `delete-items` and `admin-delete-*` prompt
  without it. Ask the user before deleting anything.
- **Inconsistent currencies break the catalog.** Different currency sets or default
  currencies across items cause fallback prices or `price: null` on the storefront.
- **Wrong webhook set.** Accounts registered after 2025-01-22 get combined
  `order_paid`/`order_canceled`; older accounts also receive separate
  `payment`/`refund` and must process them all.
- **Game keys + Pay Station Embed/iframe.** Not supported — sell keys via a new window
  or direct link. With reglocks assigned, keys upload only via the upload-codes call
  (`admin-upload-game-codes`), not Publisher Account.

## Agent test

Prompt: "Configure my Xsolla catalog with items and pricing, then wire up purchase and
order confirmation. It's a mobile F2P game with gems (virtual currency), gem packs,
boosters, and a starter bundle."

Live CLI run on sandbox project `314771` (2026-10-19, CLI `dev` 379d24a), after
`merchant-setup` and with no `XSOLLA_*` env vars. The agent created a gems currency, a
booster priced in 50 gems, a 100-gem pack (USD 0.99) and a starter bundle (USD 4.99,
then unhidden), all with `clitest-` SKUs and no groups. Every write was dry-run first,
and every real call returned 201 (unhide: 204). The storefront listed the booster, pack
and bundle with `can_be_bought: true`. Then the agent deleted all four (204 each), and the
admin catalog matched its before-snapshot. It never asked for a key or token. ✅

# In-game items: virtual items, virtual currency, packages, bundles

Admin-side catalog setup for the **in-game items archetype** (typical for mobile/F2P games).
All endpoints verified via the official Xsolla MCP (`search_xsolla_sources`) on 2026-06-11.

Admin calls authenticate via basic access authentication (`merchant_id:api_key`). They are
**not** for storefronts — see [catalog-client.md](catalog-client.md) for user-facing calls.
Admin base URL: `https://store.xsolla.com/api/v2/project/{project_id}/admin/…` (exact
paths and request schemas — verify via the Xsolla MCP before calling).

## Item types

| Type | Use for | Notes |
|------|---------|-------|
| Virtual item | Weapons, skins, boosters — any in-game good | Consumable, non-consumable, or time-limited. Universal type: docs recommend it to unify purchasing logic and avoid catalog redundancy |
| Virtual currency | In-game money | Cannot be free |
| Virtual currency package | Predefined VC amounts sold for real money | |
| Bundle | Several items/currency/keys sold as one SKU | Starter packs, editions |
| Group | Logical catalog sections | Create first; items reference groups |

## API calls

Create in this order: groups → virtual currency → virtual items → VC packages → bundles.

| Task | API call |
|------|----------|
| Create item group | [Create item group](https://developers.xsolla.com/api/catalog/item-groups-admin/admin-create-item-group) |
| Create virtual item | [Create virtual item](https://developers.xsolla.com/api/catalog/virtual-items-currency-admin/admin-create-virtual-item/) |
| Get / list virtual items | [Get virtual item](https://developers.xsolla.com/api/catalog/virtual-items-currency-admin/admin-get-virtual-item/), [Get list](https://developers.xsolla.com/api/catalog/virtual-items-currency-admin/admin-get-virtual-items-list/) |
| List items by group | [by external_id](https://developers.xsolla.com/api/catalog/virtual-items-currency-admin/admin-get-virtual-items-list-by-group-external-id/), [by group_id](https://developers.xsolla.com/api/catalog/virtual-items-currency-admin/admin-get-virtual-items-list-by-group-id/) |
| Update virtual item | [Update virtual item](https://developers.xsolla.com/api/catalog/virtual-items-currency-admin/admin-update-virtual-item/) |
| Delete virtual item | [Delete virtual item](https://developers.xsolla.com/api/catalog/virtual-items-currency-admin/admin-delete-virtual-item/) |
| Create / update virtual currency | [Create](https://developers.xsolla.com/api/catalog/virtual-items-currency-admin/admin-create-virtual-currency/), [Update](https://developers.xsolla.com/api/catalog/virtual-items-currency-admin/admin-update-virtual-currency/) |
| Create / update VC package | [Create](https://developers.xsolla.com/api/catalog/virtual-items-currency-admin/admin-create-virtual-currency-package/), [Update](https://developers.xsolla.com/api/catalog/virtual-items-currency-admin/admin-update-virtual-currency-package/) |
| Create / update bundle | [Create bundle](https://developers.xsolla.com/api/catalog/bundles-admin/admin-create-bundle/), [Update bundle](https://developers.xsolla.com/api/catalog/bundles-admin/admin-update-bundle/) |
| Delete VC / package / bundle | DELETE by SKU: `…/admin/items/virtual_currency/sku/{sku}`, `…/admin/items/virtual_currency/package/sku/{sku}`, `…/admin/items/bundle/sku/{sku}` (verified live 2026-06-11) |
| Delete group | DELETE `…/admin/items/groups/{external_id}` — by **external_id**, not numeric id (numeric id → 404) |

## Key request fields (create/update item)

- `sku` — 1–255 chars, Latin alphanumerics, periods, dashes, underscores only.
- `name`, `description` — localization objects keyed by language code (`en`, `de`, …
  or `en-US`). Responses always return two-letter codes.
- `virtual_item_type` (virtual items) — `consumable` | `non_consumable` |
  `non_renewing_subscription`.
- VC package `content` — required, exactly **one** position: `[{ "sku": "<vc_sku>",
  "quantity": <amount granted> }]`.
- Pricing: `prices` for real currency (see [pricing.md](pricing.md)), `vc_prices` for
  virtual currency, `is_free: true` for free items.
- `limits` (+ `limits.recurrent_schedule`) — per-user purchase limits with optional reset.
- `periods` — time-limited display windows (ISO 8601).
- `regions` — regional sale restrictions (see [pricing.md](pricing.md)).

## Update semantics — read before PUT

Update calls **replace** the item state, they do not merge. The set of fields returned by
GET differs from the set you must send on update: fetch the item first, then send back all
returned objects you want to keep plus your changes. Example from the docs: if you update
only the price and omit the `limits` object, the item's limit configuration is deleted.
Source: [Automate catalog creation and updates](https://developers.xsolla.com/items-catalog/catalog-management/automate-catalog/#catalog_management_automate_catalog_items).

## Bundle limitations

- A bundle cannot contain itself; empty bundles are not allowed.
- If a bundle contains game keys and the keys run out, bundle sales pause automatically.
- Regional restrictions for bundles are configurable **only via API**, not Publisher Account.
Source: [Bundles](https://developers.xsolla.com/items-catalog/items-type/set-up-bundle/#items_catalog_game_key_bundle).

# Building the catalog on the client

User-facing **Catalog** calls for rendering the store in your game/site. Designed for
high-load user traffic; no authorization required, optional user JWT returns personalized
data (user-specific limits, active promotions).
Verified via the official Xsolla MCP on 2026-06-11.

**Never build a storefront on Admin calls** — they are rate-limited and not intended for
user traffic. Source: [Basic purchase flow](https://developers.xsolla.com/api/catalog/virtual-items-currency-admin/admin-create-virtual-item#section/Basic-purchase-flow).

## API calls

Fetch the catalog **by specific item type** — each type has its own endpoint:

| Task | API call |
|------|----------|
| Virtual items | [Get virtual items list](https://developers.xsolla.com/api/catalog/virtual-items-currency-catalog/get-virtual-items) |
| Item groups (store sections) | [Get item group list](https://developers.xsolla.com/api/catalog/virtual-items-currency-catalog/get-item-groups) |
| Virtual currency packages (the sellable packs) | [Get virtual currency package list](https://developers.xsolla.com/api/catalog/virtual-items-currency-catalog/get-virtual-currency-package/) |
| Virtual currency itself | [Get virtual currency list](https://developers.xsolla.com/api/catalog/virtual-items-currency-catalog/get-virtual-currency/) |
| Bundles | [Get list of bundles](https://developers.xsolla.com/api/catalog/bundles-catalog/get-bundle-list) |
| Game key packages | [Get games list](https://developers.xsolla.com/api/catalog/game-keys-catalog/get-games-list/), [Get game key by SKU](https://developers.xsolla.com/api/catalog/game-keys-catalog/get-game-key-by-sku/) |

## Country, prices, and availability

- **Call these endpoints from the client and do not pass `country`.** Xsolla determines
  the user's country by IP and returns the right regional prices and regional
  availability automatically.
- Pitfall: if you proxy catalog requests through your backend, the country is resolved
  from your **server's** IP — every user sees one country's prices. Either call from the
  client, or deliberately forward the user's country. The `country` parameter is an edge
  case (user picked a country manually, testing), not the default.
- Each item's price comes back in the `price` object, already resolved for the user's
  country. `price: null` means a pricing misconfiguration — see
  [pricing.md](pricing.md) consistency rules.

## Useful parameters

- `locale` — response language.
- `additional_fields` — request `media_list`, `order`, `long_description` if needed.
- `show_inactive_time_limited_items: 1` — include items outside their display window
  (by default the catalog returns only currently available items).
- An empty `Get virtual currency list` response is usually **not** an error: hard
  currency is typically created with `is_show_in_store: false` and sold via packages —
  verify against the VC package list instead.
- Catalog endpoints are paginated — iterate `limit`/`offset` for large catalogs
  ([pagination](https://developers.xsolla.com/api/catalog/section/pagination)).

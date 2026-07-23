# Pricing: local prices and regional restrictions

Verified via the official Xsolla MCP on 2026-06-11.
Main doc: [Local prices](https://developers.xsolla.com/items-catalog/catalog-features/pricing-policy/).

## Recommendation

Set **regional prices in local currencies for your key markets**. If regional prices are
not set, Pay Station converts the default price (USD by default) into the user's currency
by exchange rate — it works, but loses sales in countries with low purchasing power.

The user's country is determined **by IP address** — do not pass `country` explicitly
(see [catalog-client.md](catalog-client.md)).

## How to set prices

Pass a `prices` array in the admin create/update calls of **any** item type
(virtual items, virtual currency, VC packages, bundles, game key packages):

```json
"prices": [
  { "amount": 10.0, "currency": "USD", "is_enabled": true, "is_default": true },
  { "amount": 20.5, "currency": "CZK", "country_iso": "CZ", "is_enabled": true, "is_default": false }
]
```

- Exactly one default price, and the default must **not** have `country_iso`.
- `currency` per ISO 4217, `country_iso` per ISO 3166-1 alpha-2.
- **Known docs/API discrepancy (bundles):** the published Create-bundle schema declares
  `prices[].amount` as a string, but the live API rejects strings with
  `422 "String value found, but a number is required"` and accepts numbers (verified on
  sandbox, 2026-06-11). Send **numbers** for every item type; if a 422 mentions value
  types, re-check the schema via the Xsolla MCP and try the other representation.
- Bulk upload: CSV import in Publisher Account (columns `SKU,Country,Currency,Amount,IsDefault`
  + `Platform` for game keys) or [Import items via JSON file](https://developers.xsolla.com/api/catalog/connector-admin/import-items-from-external-file/).
- Virtual currency prices go in `vc_prices` instead.

## Catalog consistency rules (critical)

Source: [Price display principles](https://developers.xsolla.com/items-catalog/catalog-features/pricing-policy/#pricing_policy_country_determination).

- **Use the same list of currencies for all items in the catalog.** If one item lacks a
  price in some country's currency, the whole catalog falls back to the default currency
  in that country.
- **Use the same default currency for all items.** With mixed defaults, prices display in
  the default currency of the *first* item; items without a price in that currency return
  `price: null` and break the storefront.

## Regional sale restrictions (reglocks)

Optional; mainly for **game keys** — prevents buying a key in a cheap region and
activating it in an expensive one. Whether to use it depends on the game.
Source: [Regional sale restrictions](https://developers.xsolla.com/items-catalog/catalog-features/regional-restrictions/).

1. Create regions via [Create region](https://developers.xsolla.com/api/catalog/common-regions/admin-create-region/):
   ```json
   { "name": { "en-US": "North America" }, "countries": ["US", "CA"] }
   ```
   The call returns a region `id`.
2. Pass `"regions": [{ "id": 123 }]` in the admin create/update calls
   ([game keys](https://developers.xsolla.com/api/catalog/game-keys-admin/admin-create-game/),
   [virtual items & currency](https://developers.xsolla.com/api/catalog/virtual-items-currency-admin/admin-create-virtual-item/)).

If an item has regions and the user's country is in none of them, the item is hidden from
the catalog in that country.

Caveats:
- Once regions are assigned to a game, keys can be uploaded **only via the
  [Upload codes](https://developers.xsolla.com/api/catalog/game-keys-admin/admin-upload-codes-by-sku/) API call**, not Publisher Account.
- Regional restrictions for bundles are configurable only via API.
- Items with reglocks also affect promotions: a promo code/coupon containing a
  region-restricted bonus item can't be redeemed outside that region.

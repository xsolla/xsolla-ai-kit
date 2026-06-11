# Game keys: selling a game (or DLC) via keys

Admin setup and selling flow for the **game keys archetype** (selling a game/DLC for
external platforms or DRM-free). Endpoints verified via the official Xsolla MCP on 2026-06-11.

Key properties of this archetype: purchased keys are delivered to the user **by email**,
so user authentication and webhooks are **optional**. They become required only for
personalization, per-user purchase limits, the entitlement system, or detailed
transaction info. Source: [Sell game keys](https://developers.xsolla.com/sell-games/#sell_game_keys).

## Platform-specific SKUs

A game key package groups keys per platform. The full sellable SKU is
`<package_sku>_<platform_suffix>` (e.g. `mygame_steam`). Docs recommend always selling
platform-specific packages to avoid activation issues.

Supported suffixes: `_steam`, `_playstation`, `_xbox`, `_uplay`, `_origin`, `_drmfree`,
`_gog`, `_epicgames`, `_nintendo_eshop`, `_discord_game_store`, `_oculus`, `_viveport`,
`_stadia`, `_my_game`.
To get the exact sellable SKU, call [Get games list](https://developers.xsolla.com/api/catalog/game-keys-catalog/get-games-list/)
and read `items.unit_items.sku`.

## API calls (admin)

| Task | API call |
|------|----------|
| Create game key package | [Create game](https://developers.xsolla.com/api/catalog/game-keys-admin/admin-create-game/) |
| Update package | [Update game by SKU](https://developers.xsolla.com/api/catalog/game-keys-admin/admin-update-game-by-sku/), [by ID](https://developers.xsolla.com/api/catalog/game-keys-admin/admin-update-game-by-id/) |
| Upload keys | [Upload codes](https://developers.xsolla.com/api/catalog/game-keys-admin/admin-upload-codes-by-sku/) — each key must be unique; duplicates are skipped |
| Limit display time | Pass `periods` (ISO 8601) in create/update calls |

Keys must stay stocked: when a package runs out of keys, users can't buy it (and bundles
containing it pause). Pre-orders: enable the pre-orders option to sell before release;
keys are delivered on the release date.

## Selling options

1. **Direct link** (no own UI needed) — opens the payment UI:
   `https://purchase.xsolla.com/pages/buy?type={game|game_key|bundle}&project_id={PROJECT_ID}&sku={SKU}`.
   Optional `ui_settings` (Base64-encoded `settings.ui` JSON) customizes Pay Station.
   Source: [Selling via direct link](https://developers.xsolla.com/sell-games/set-up-selling-game-keys/#guides_game_sales_selling_game_keys_selling_via_direct_link).
2. **Own UI via API** — build the catalog with [game-keys-catalog](catalog-client.md)
   calls, then create an order (see [purchase-and-tracking.md](purchase-and-tracking.md)).
3. **Site Builder / widget** — out of scope here; covered by the `store-build` skill.

**Limitation:** Pay Station Embed and iframe do **not** support selling game keys — use a
new window or the direct link. Source: [Set up item purchase](https://developers.xsolla.com/virtual-goods/own-ui/client-side-token-generation/set-up-item-purchase/).

## Entitlement system (DRM-free distribution)

For distributing DRM-free games with ownership tracking (list of owned games, pre-orders,
manual activation):

- [Get user's games](https://developers.xsolla.com/api/catalog/game-keys-entitlement/get-user-games/)
- [Grant entitlement](https://developers.xsolla.com/api/catalog/game-keys-entitlement/grant-entitlement-admin/) (admin; e.g. support manually redeems a key)
- [Revoke entitlement](https://developers.xsolla.com/api/catalog/game-keys-entitlement/revoke-entitlement-admin/) (deactivates the key)

Requires the Game Keys module with the **DRM free** option and authentication (Login or
Pay Station access token). Source: [Entitlement system](https://developers.xsolla.com/sell-games/how-to/entitlement-system/).

## Refunds

Users can refund keys. Xsolla emails the list of affected keys daily; DRM-free keys
created by Xsolla are deactivated automatically, but keys for third-party platforms must
be blocked there manually.

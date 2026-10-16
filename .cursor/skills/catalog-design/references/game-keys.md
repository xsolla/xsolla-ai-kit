# Game keys: selling a game (or DLC) via keys

Admin setup and selling flow for the **game keys archetype** (selling a game/DLC for
external platforms or DRM-free). Admin steps use `xsolla catalog`, checked against CLI
1.9.4 (`dev` 379d24a) on 2026-10-16. Endpoints verified via the official Xsolla MCP on
2026-06-11.

Key properties of this archetype: purchased keys are delivered to the user **by email**,
so user authentication and webhooks are **optional**. They become required only for
personalization, per-user purchase limits, the entitlement system, or detailed
transaction info. Source: [Sell game keys](https://developers.xsolla.com/sell-games/#sell_game_keys).

## Platform-specific SKUs

A game key package groups keys per platform. Each platform is a **unit item** with its
own sellable SKU, conventionally `<package_sku>_<platform_suffix>` (e.g. `mygame_steam`).
Docs recommend always selling platform-specific packages to avoid activation issues.

Supported suffixes: `_steam`, `_playstation`, `_xbox`, `_uplay`, `_origin`, `_drmfree`,
`_gog`, `_epicgames`, `_nintendo_eshop`, `_discord_game_store`, `_oculus`, `_viveport`,
`_stadia`, `_my_game`. `xsolla catalog list-drm-platforms --json` returns the platform
SKUs the project accepts. To get the exact sellable SKU, run
`xsolla catalog admin-get-game --game-sku <sku> --json` and read `unit_items[].sku`
(client code uses [Get games list](https://developers.xsolla.com/api/catalog/game-keys-catalog/get-games-list/)).

## Commands (admin)

| Task | Command |
|------|---------|
| List platforms | `list-drm-platforms` |
| Create game key package | `admin-create-game --sku <sku> --name '{…}' --description '{…}' --unit-items '[{"sku":"<sku>_steam","drm_sku":"steam","name":{…},"is_enabled":true,"prices":[…]}]'` |
| Get / list / update package | `admin-get-game --game-sku <sku>`, `admin-list-games`, `admin-update-game --game-sku <sku>` (full replace: get it first) |
| Upload keys | `admin-upload-game-codes --game-sku <sku> --drm <platform> --codes '["KEY-1","KEY-2"]'` — each key must be unique; duplicates are skipped |
| Check keys | `admin-list-game-codes --game-sku <sku> --all`, `admin-get-game-upload-session --upload-id <id>` |
| Delete package | `admin-delete-game --game-sku <sku> --force` (ask first) |
| Limit display time | No `periods` flag (CLI gap): set it in Publisher Account |

Run a write with `--dry-run` first to check the request body, then show it to the user
before the real call. Keys are the merchant's stock: upload them only when the user hands
you the list, and never print them back in full. The bundled CLI skill
`gamekeys-publishing-workflows` covers the `xsolla gamekeys` variants that take numeric
item and DRM IDs.

Keys must stay stocked: when a package runs out of keys, users can't buy it (and bundles
containing it pause). Pre-orders: enable the pre-orders option to sell before release
(`admin-toggle-preorder`, limits via `admin-*-preorder-limit`); keys are delivered on
the release date.

## Selling options

1. **Direct link** (no own UI needed) — opens the payment UI:
   `https://purchase.xsolla.com/pages/buy?type={game|game_key|bundle}&project_id={PROJECT_ID}&sku={SKU}`.
   Optional `ui_settings` (Base64-encoded `settings.ui` JSON) customizes Pay Station.
   Source: [Selling via direct link](https://developers.xsolla.com/sell-games/set-up-selling-game-keys/#guides_game_sales_selling_game_keys_selling_via_direct_link).
2. **Own UI via API** — build the catalog with [game-keys-catalog](catalog-client.md)
   calls, then create an order (see [purchase-and-tracking.md](purchase-and-tracking.md)).
3. **Site Builder / widget** — out of scope here.

**Limitation:** Pay Station Embed and iframe do **not** support selling game keys — use a
new window or the direct link. Source: [Set up item purchase](https://developers.xsolla.com/virtual-goods/own-ui/client-side-token-generation/set-up-item-purchase/).

## Entitlement system (DRM-free distribution)

For distributing DRM-free games with ownership tracking (list of owned games, pre-orders,
manual activation):

- [Get user's games](https://developers.xsolla.com/api/catalog/game-keys-entitlement/get-user-games/) —
  a player-side call in the developer's client code
- Grant entitlement (e.g. support manually redeems a key) —
  `xsolla catalog admin-grant-entitlement --sku <sku> --user '<user payload>'`
  ([API reference](https://developers.xsolla.com/api/catalog/game-keys-entitlement/grant-entitlement-admin/))
- Revoke entitlement (deactivates the key) —
  `xsolla catalog admin-revoke-entitlement --sku <sku> --user '<user payload>' --force`
  ([API reference](https://developers.xsolla.com/api/catalog/game-keys-entitlement/revoke-entitlement-admin/))

Both change a real player's ownership: run them only on the user's explicit request.
If the developer's own support tool grants entitlements, that tool calls the API from its
backend, because shipped code can't depend on the CLI.

Requires the Game Keys module with the **DRM free** option and authentication (Login or
Pay Station access token). Source: [Entitlement system](https://developers.xsolla.com/sell-games/how-to/entitlement-system/).

## Refunds

Users can refund keys. Xsolla emails the list of affected keys daily; DRM-free keys
created by Xsolla are deactivated automatically, but keys for third-party platforms must
be blocked there manually.

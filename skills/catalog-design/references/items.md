# In-game items: virtual items, virtual currency, packages, bundles

Admin-side catalog setup for the **in-game items archetype** (typical for mobile/F2P games),
done with `xsolla catalog`. Commands checked against CLI 1.9.4 (`dev` 379d24a) on
2026-10-16. Field semantics verified via the official Xsolla MCP (`search_xsolla_sources`)
on 2026-06-11.

The commands read the Store key from the keychain and `merchant_id` / `project_id` from
`.xsolla.json`, so you don't pass `--merchant-id` or `--project-id`. They are **not** for
storefronts: see [catalog-client.md](catalog-client.md) for user-facing calls. Confirm
flags with `xsolla catalog <command> --help`; the bundled CLI skill `catalog-admin` has
worked examples.

## Item types

| Type | Use for | Notes |
|------|---------|-------|
| Virtual item | Weapons, skins, boosters — any in-game good | Consumable, non-consumable, or time-limited. Universal type: docs recommend it to unify purchasing logic and avoid catalog redundancy |
| Virtual currency | In-game money | Has no price of its own and never shows in the store: `admin-create-currency` has no `--prices` or `--is-show-in-store` flag. Players get it through VC packages and bundles |
| Virtual currency package | Predefined VC amounts sold for real money | |
| Bundle | Several items/currency/keys sold as one SKU | Starter packs, editions |
| Group | Storefront sections | Optional: ungrouped items, packages and bundles still sell. The CLI can't delete a group, so create one only when the store needs sections |

## Commands

Create in this order: groups (optional) → virtual currency → virtual items → VC packages → bundles.

| Task | Command |
|------|---------|
| Create item group | `admin-create-group --external-id <id> --name '{…}' --order <n> --is-enabled` |
| List groups | `list-item-groups` |
| Create / update virtual item | `create-items`, `update-items --item-sku <sku>` |
| Get / list virtual items | `get-items --item-sku <sku>`, `list-items`, `admin-list-items-by-group --group-id <external_id>` |
| Delete virtual item | `delete-items --item-sku <sku> --force` |
| Create / update / list / delete virtual currency | `admin-create-currency`, `admin-update-currency --currency-sku <sku>`, `admin-list-currency`, `admin-delete-currency` |
| Create / update / list / delete VC package | `admin-create-currency-package`, `admin-update-currency-package --package-sku <sku>`, `admin-list-currency-packages`, `admin-delete-currency-package` |
| Create / update / delete bundle | `admin-create-bundles`, `admin-update-bundles --bundle-sku <sku>`, `admin-delete-bundles`, `get-bundles` |
| Show / hide bundle | `admin-unhide-bundle --bundle-sku <sku>`, `admin-hide-bundle` |
| Bulk create or update | `admin-import-catalog --data "$(jq -c . catalog.json)" --dry-run`, then without `--dry-run`. It returns no import ID, and `admin-get-import-status` answers 403 on a standard key, so confirm with `scripts/backup_catalog.py --compare <backup>` |
| Delete or update a group | No command (CLI gap) |

Add `--json` to every call and read `ok` / `error.code`. Every `admin-delete-*` and
`delete-items` call needs `--force` and the user's explicit yes.

**Bulk import.** `--dry-run` checks the JSON locally and prints the request it would send.
It does not validate the payload against the API. After the real run, read the catalog
back (`list-items`, `admin-list-currency-packages`) instead of trusting the exit code.
The bundled CLI skills `catalog-import` and `catalog-import-csv` cover the `items` payload
and converting a spreadsheet. The CLI doesn't document the payload keys for currencies,
packages or bundles: check them with the Xsolla MCP first, or create those types with
the per-type commands.

## Key flags (create/update item)

- `--sku` — 1–255 chars, Latin alphanumerics, periods, dashes, underscores only.
- `--name`, `--description` — required localization JSON keyed by language code (`en`,
  `de`, … or `en-US`). Responses always return two-letter codes. Bundle descriptions are
  capped at 255 characters per locale.
- `--groups '["<external_id>"]'` — puts the item in a storefront section. It does not
  decide whether the item sells. Visibility comes from `--is-enabled`, plus
  `--is-show-in-store` on `create-items` and `admin-create-currency-package`. Bundles
  have no such flag and use `admin-unhide-bundle`. Virtual currency has neither, so it
  is never listed on its own.
- `--content` (VC package) — exactly **one** position:
  `'[{"sku":"<vc_sku>","quantity":<amount granted>}]'`. Bundles take several positions.
- Pricing: `--prices` for real currency (see [pricing.md](pricing.md)), `--vc-prices`
  for virtual currency (`[{"amount":<int>,"sku":"<vc_sku>","is_default":true,"is_enabled":true}]`),
  `--is-free` for free items.
- `--image-url` — a URL, not a file. The bundled CLI skill `catalog-admin` shows how to
  host art through Shop Builder's asset store.
- No flag for `virtual_item_type` (consumable, non-consumable, non-renewing
  subscription), `limits`, `periods` or `regions`. These are CLI gaps (see SKILL.md),
  so set them in Publisher Account.

## Update semantics — read before an update

Update commands **replace** the item state, they do not merge. The set of fields returned
by a get differs from the set you must send on update: fetch the item first, then send
back all returned objects you want to keep plus your changes. Example from the docs: if
you update only the price and omit the `limits` object, the item's limit configuration is
deleted. Because the CLI has no `limits` or `periods` flag, an `update-items` call on an
item that has limits or a display window set in Publisher Account will drop them. Make
those edits in Publisher Account instead.
Source: [Automate catalog creation and updates](https://developers.xsolla.com/items-catalog/catalog-management/automate-catalog/#catalog_management_automate_catalog_items).

## Bundle limitations

- A bundle cannot contain itself; empty bundles are not allowed.
- New bundles are hidden. Run `admin-unhide-bundle` to show them.
- If a bundle contains game keys and the keys run out, bundle sales pause automatically.
- Regional restrictions for bundles are configurable **only via API**, not Publisher
  Account, and the CLI has no flag for them yet.
Source: [Bundles](https://developers.xsolla.com/items-catalog/items-type/set-up-bundle/#items_catalog_game_key_bundle).

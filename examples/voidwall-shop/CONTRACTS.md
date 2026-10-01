# Verified API contracts (2026-10-01)

| Question | Answer | Source |
|---|---|---|
| Admin Basic auth user | Both `merchant_id:key` and `project_id:key` returned 200 on a read-only list; seed uses merchant | live probe, Task 0 |
| Pay language for Brazilian Portuguese | `pt` (table row "Portuguese (Brazil) \| pt"); fr, de, ja as is | developers.xsolla.com/payment-ui-and-flow/payment-ui/localization |
| `promo_code` on `POST /payment/cart` | Not documented. Promo field and `promo_code` are dropped from the UI and token call | api/catalog/payment-client-side/create-order |
| `settings.language` on `POST /payment/cart` | Not listed on the endpoint page, but `shop-setup` requires it for Headless Checkout. Kept; confirm in a sandbox call (needs login) | same page vs skills/shop-setup |
| Store `locale` value for pt-BR | Not documented. Default `pt_BR`; confirmed or fixed by the public catalog call in Task 4 | unverified |
| Admin localization key for pt-BR | Five-character codes accepted (`en-US`, `pt-BR`); two-letter `pt` also accepted | api/catalog/bundles-admin/admin-create-bundle |
| Bundle required fields | `sku, name, description, prices, content`. No `type`; optional `bundle_type` (`standard` default) | same |
| `prices[].amount` type | Documented as string. Numbers are sent; switch to strings if the API returns 422 | same |
| `limits` shape | Confirmed on `--apply` (422 then fixed): `limits.per_user` is an integer, `limits.recurrent_schedule.per_user = { interval_type: 'daily', time }` is a sibling of `per_user`. Persisted as expected | live API |
| Store `locale=pt_BR` | Returns 200; `ja` returns the localized Obsidian name and description | live API |

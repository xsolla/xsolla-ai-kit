# Supported languages (the authority)

The complete, verified reference for locale codes. SKILL.md summarizes; this file
holds the detail and the bundled code table.

## There is no "get supported languages" API

Xsolla exposes **no endpoint** returning the supported-language list — it is a
**static docs table**, so it is bundled here (verified 2026-09-02):
- Catalog: <https://developers.xsolla.com/dev-resources/references/supported-languages/>
- Pay Station / Headless Checkout / receipts: <https://developers.xsolla.com/payment-ui-and-flow/payment-ui/localization/>

Re-verify on a skill release, not at runtime. What the API *can* give is a **project's
own** locales and how far each one has got — derive that from the data rather than
asking. Two different reports, and picking the wrong one under-reports the work:

- `catalog_i18n.py discover` — coverage **per entity**, and what the scope step uses
  (`items: 10 object(s), 18 strings — en 18/18 · ru 6/18`). See SKILL.md step 2.
- `catalog_i18n.py langs` — one aggregated line per language (`ru: 6/18 (33%)`),
  **items only**. A quick read on how far a single language has got; it cannot see
  groups, bundles, currency, value points or LiveOps, so a project whose items are
  finished reports 100% while the rest of the catalog is still English. Never scope
  from it.

The project's **configured** locale list is a third thing, and it does come from an
endpoint: `GET /merchant/v2/projects/{id}` returns `locale_list` alongside `name` and
`products`. It needs **merchant** auth and the bundled script does not implement it (see
[glossary.md](glossary.md)), so treat it as optional enrichment — what a project is set
up for, not what is translated. Coverage still has to come from `discover`.

## Code format rules

- 2-letter (`ru`) or 5-letter (`ru-RU`) accepted on **write**; responses are **always**
  2-letter → **key and compare by 2-letter**, normalize 5→2 on input.
- Sending both forms of one language (`en` + `en-US`) for one field → **last wins**, the
  other is lost. Don't send both.
- Xsolla oddities: `cn` = Simplified Chinese (5-letter `zh-CN`), `tw` = Traditional
  (`zh-TW`) — not `zh`.

## One canonical variant per language (verified)

Each language has **exactly one** valid variant — the 2-letter code and, where the table
lists one, its single 5-letter form (`nl` and `ms` are payment-only and have no 5-letter
form here, so use the 2-letter code). Other regional variants are **invalid**, not
merged:
- ✅ verified on 314067: writing `pt-BR` stored as `pt`; writing `pt-PT` → `404 Locale
  not found`.
- So `pt-BR` and `pt-PT` cannot coexist — `pt-PT`/`en-GB`/`es-MX` are simply not Xsolla
  locales. Chinese is the exception, handled by two separate codes (`cn`, `tw`).

## ⚠️ An invalid locale drops the whole PUT (verified)

A single unknown locale in a write returns `404` and **rejects the entire request** —
valid locales in the same PUT are not written either. → **validate every target code
against this list before writing**. `check` reports every bad column at once, and
`import` re-checks and refuses to start before any network call — so the guard still
holds if `check` was skipped.

## Code table (bundled)

| 2-letter | 5-letter | Language | Catalog | Payment |
| --- | --- | --- | --- | --- |
| en | en-US | English (US) | ✓ | ✓ |
| ar | ar-AE | Arabic | ✓ | ✓ |
| bg | bg-BG | Bulgarian | ✓ | ✓ |
| my | my-MM | Burmese | ✓ | ✓ |
| cn | zh-CN | Chinese (Simplified) | ✓ | ✓ |
| tw | zh-TW | Chinese (Traditional) | ✓ | ✓ |
| cs | cs-CZ | Czech | ✓ | ✓ |
| ph | ph-PH | Filipino | ✓ | ✓ |
| fr | fr-FR | French | ✓ | ✓ |
| de | de-DE | German | ✓ | ✓ |
| he | he-IL | Hebrew | ✓ | ✓ |
| id | id-ID | Indonesian | ✓ | ✓ |
| it | it-IT | Italian | ✓ | ✓ |
| ja | ja-JP | Japanese | ✓ | ✓ |
| km | km-KH | Khmer | ✓ | ✓ |
| ko | ko-KR | Korean | ✓ | ✓ |
| lo | lo-LA | Lao | ✓ | ✓ |
| ne | ne-NP | Nepali | ✓ | ✓ |
| pl | pl-PL | Polish | ✓ | ✓ |
| pt | pt-BR | Portuguese (Brazil) | ✓ | ✓ |
| ro | ro-RO | Romanian | ✓ | ✓ |
| ru | ru-RU | Russian | ✓ | ✓ |
| es | es-ES | Spanish (Spain) | ✓ | ✓ |
| th | th-TH | Thai | ✓ | ✓ |
| tr | tr-TR | Turkish | ✓ | ✓ |
| vi | vi-VN | Vietnamese | ✓ | ✓ |
| nl | — | Dutch | — | ✓ |
| ms | — | Malay | — | ✓ |

**Catalog = 26, Payment/Headless Checkout/receipts = 28** (+`nl`, `ms`). The lists
differ → validate a target against the **surface** you localize: `nl` cannot go into the
catalog but is valid for payment. Two payment-side behaviours, from the Pay Station docs
linked above rather than measured here, and owned by `shop-setup`: the default when
`settings.language` is omitted is `en`, and a Japanese client IP forces Japanese
regardless of the code.

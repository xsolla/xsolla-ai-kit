# Design → shop brief

The section inventory and token sheet from [read-the-design.md](read-the-design.md)
become one version-1 shop brief for `shop-builder-assembly`. The contract is
`shop-builder-assembly/references/shop-brief.md`; this page only says where each field
comes from when the input is a design. Validate with assembly's
`scripts/validate_shop_brief.py` before handing it over.

## Field by field

| Brief field | From | Notes |
|---|---|---|
| `project` | IDs confirmed in Step 0 | `"environment": "test"` and `"test_project_acknowledged": true` — this skill never targets sandbox |
| `game.name`, `platforms`, `lifecycle` | Ask the partner | A comp rarely states them. Ask in one batch with anything else missing; never infer a lifecycle from art |
| `site.name`, `site.slug` | The partner's site (Step 0) | The slug of the site the partner created. Never a new slug — assembly would create a site the Editor can't open |
| `site.preset` | `auto` | `content.page_overrides` replaces the preset's page list anyway |
| `site.primary_locale`, `locales` | The comp's language; ask for more | Full codes such as `en-US` |
| `catalog.groups` | Comp store rows ↔ verified groups | One entry per row: `external_id`, `type` (`virtual_currency` for currency packs, `bundle` for combo cards, `virtual_good` otherwise), `placement` (`featured` / `primary` / `secondary` — it picks the card layout) |
| `catalog.featured_skus` | Hero or spotlight offers | Existing SKUs only; assembly creates no products |
| `brand.logo`, `brand.hero_image` | Exported art | Only art the partner owns or is licensed to use. Assembly doesn't upload assets yet, so Step 4 does |
| `brand` colors, radius, fonts | Token sheet | Carried into the plan; assembly doesn't apply theme yet, so Step 4 does |
| `content.page_overrides` | Step 1 section mapping | One page object per comp page, `blocks` in comp order, using module names assembly verifies (below) |
| `content.faq`, `description`, `features`, `gallery` | The comp's own text and art | A block whose data is missing is **omitted** by assembly, so supply it for every section you mapped |
| `sources` | — | `{"kind": "figma", "url": "<the link>"}` (or the file the partner gave), plus `publisher_answers` for anything you asked |

Never put API keys, tokens, session cookies or passwords in the brief.

## Block modules assembly accepts

`page_overrides` blocks must be modules assembly has verified — anything else fails
validation. The ones a design usually needs:

| Comp section | Module |
|---|---|
| Header | `header` |
| Hero / welcome offer | `leadGameSales` (store landings) |
| Product grid | `newStore` |
| Feature cards | `bento-grid` |
| Text band | `description` |
| Screenshot or video strip | `gallery` |
| FAQ | `faq` |
| Footer | `footer` |

The full list is `VERIFIED_BLOCK_MODULES` in assembly's `validate_shop_brief.py`. A
section with no verified module is a gap: list it under Known limitations, don't invent
a module name.

## What the brief cannot carry

Card layout beyond `placement`, tab settings, per-block background art, and the exact
`calculatedTheme` tokens have no brief field. Background art and the theme are applied
in Step 4. Everything else is a gap — name it in Step 1 and at handover.

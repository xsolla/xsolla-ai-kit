# Shop brief input contract

The assembly skill consumes one JSON object. Upstream skills may collect or infer
values, but must preserve `sources` so the user can see where decisions came from.

## Required fields

```json
{
  "version": 1,
  "project": {
    "merchant_id": 12345,
    "project_id": 67890,
    "environment": "test",
    "test_project_acknowledged": true
  },
  "game": {
    "name": "Space Legends",
    "platforms": ["mobile"],
    "lifecycle": "launch"
  },
  "site": {
    "name": "Space Legends Web Shop",
    "slug": "space-legends-shop",
    "preset": "auto",
    "primary_locale": "en-US",
    "locales": ["en-US"]
  },
  "catalog": {
    "groups": [
      {"external_id": "__all__", "type": "virtual_currency", "placement": "primary"}
    ],
    "featured_skus": []
  },
  "brand": {},
  "content": {},
  "sources": [{"kind": "publisher_answers"}]
}
```

Allowed presets: `auto`, `mobile-single-page`, `pc-multi-page`, and
`live-service-events`. Allowed catalog group types: `virtual_good`, `bundle`, and
`virtual_currency`. `project.environment` must be `test`, and the `project`
object must contain `"test_project_acknowledged": true`. Before a write,
`preflight.py` and `apply_plan.py` additionally require a separate local allowlist:

```json
{
  "version": 1,
  "projects": [
    {
      "merchant_id": 12345,
      "project_id": 67890,
      "approved_by": "mentor or tech lead",
      "approval_reference": "link or durable reference to the approval"
    }
  ]
}
```

Keep the real allowlist outside the repository. This second artifact binds the exact
project identity to approval evidence; a self-declared brief is not enough.

## Field behavior

| Field | Purpose |
|---|---|
| `project.*` | Hard safety boundary. IDs must match, CLI sandbox mode must be off, and a dedicated-test-project acknowledgement is required. |
| `game.platforms` | Any of `mobile`, `pc`, `console`, `web`; drives automatic preset selection. |
| `game.lifecycle` | `launch`, `evergreen`, or `live-service`; drives event and offer defaults. |
| `site.slug` | Existing target or requested new Xsolla domain slug. Never guess it for an existing site. |
| `site.locales` | Full locale codes such as `en-US`; must include `primary_locale`. |
| `catalog.groups` | Existing group identifiers or `__all__` to place in `newStore` sections. Each entry uses `type` = `virtual_good`, `bundle`, or `virtual_currency`, plus `placement` = `featured`, `primary`, or `secondary`; placement deterministically selects the card layout. |
| `catalog.featured_skus` | Optional existing SKUs highlighted by the preset; assembly does not create products. |
| `catalog.liveops` | Optional LiveOps features active in the same project, or created and activated by `catalog-design`'s pending proposal under the same yes: `promo_codes`, `reward_chain`, `offer_chain`. Each one lets the preset add its block (`promocodes`, `rewards`, `sb-offer-chain`); assembly configures none of them. |
| `brand` | Optional `logo`, `hero_image`, color, radius, and font inputs. Missing values use preset defaults. |
| `brand.images` | Optional list of local image files (`.png`, `.jpg`, `.webp`, `.svg` and the other types `upload-asset` takes), each `{"file", "module", "slot"}` with an optional `"page"`. `slot` is `background` or `logo`; `file` is relative to the brief. A hero image (`leadGameSales`) goes on a template page's own hero (`lead`). `apply_style.py` uploads and places them. Two entries for the same module and slot can't share a page. |
| `brand.theme` | Optional site palette that `apply_style.py` sets: any of `bg`, `overlay`, `border`, `primary`, `secondary`, `text` as `#rrggbb`, and `isDark` as `true` or `false`. Without it, the site keeps its theme. |
| `content` | Optional approved copy, page overrides, FAQ, requirements, event copy, and CTA labels. |
| `content.copy` | Optional list of `{"module", "field", "html"}` with an optional `"page"`: the approved text for a block's `title`, `subtitle` or `description`, as HTML (`<h1>`, `<h2>`, `<p>`), primary locale. No `<img>`, `<script>` or other embedding tags, event handlers or `javascript:` links. Two entries for the same module and field can't share a page. `apply_style.py` writes it. |
| `content.seo` | Optional list of `{"page", "title", "description", "image"}`, one per page path: the search title (at most 70 characters) and description (at most 200), as plain text, and a local share image for link previews (`og:image`). `apply_style.py` writes them to the page's `seo` strings and uploads the image. |
| `content.faq` | Optional list of `{"question", "answer"}`, both HTML; each question is an `<h4>`. It adds the FAQ block to the plan, and `apply_style.py` makes the block's items match it. |
| `sources` | Provenance such as `publisher_answers`, `description`, `external_store`, or `figma`. |

Never put API keys, session cookies, passwords, or tokens in the brief.
Verify credentials through the CLI credential store instead.

`content.page_overrides`, when present, replaces the selected preset's page list. It
is a non-empty array of complete page objects:

```json
{
  "page_overrides": [
    {"name": "Shop", "path": "/shop", "blocks": ["header", "newStore", "footer"]}
  ]
}
```

Paths must be unique root-relative kebab-case paths. Blocks must be module names
already verified on the dedicated test project; unverified modules are rejected
before planning or writes.

## Handoff contract for other skills

- Description skills populate `game`, approved `content`, and relevant `sources`.
- Figma skills populate `brand`, assets, and explicit page/block intent.
- This skill owns preset choice, dependency ordering, Shop Builder writes, and final
  verification. Callers must not duplicate those operations.

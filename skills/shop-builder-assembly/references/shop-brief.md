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
    "environment": "sandbox"
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
`virtual_currency`. `project.environment` may be `sandbox` or `test`. For `test`, the
brief must also contain `"test_project_acknowledged": true`. Before a write,
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
| `project.*` | Hard safety boundary. IDs and CLI sandbox setting must match. `test` requires an explicit dedicated-test-project acknowledgement. |
| `game.platforms` | Any of `mobile`, `pc`, `console`, `web`; drives automatic preset selection. |
| `game.lifecycle` | `launch`, `evergreen`, or `live-service`; drives event and offer defaults. |
| `site.slug` | Existing target or requested new Xsolla domain slug. Never guess it for an existing site. |
| `site.locales` | Full locale codes such as `en-US`; must include `primary_locale`. |
| `catalog.groups` | Existing group identifiers or `__all__` to place in `newStore` sections. Each entry uses `type` = `virtual_good`, `bundle`, or `virtual_currency`, plus `placement` = `featured`, `primary`, or `secondary`; placement deterministically selects the card layout. |
| `catalog.featured_skus` | Optional existing SKUs highlighted by the preset; assembly does not create products. |
| `brand` | Optional `logo`, `hero_image`, color, radius, and font inputs. Missing values use preset defaults. |
| `content` | Optional approved copy, page overrides, FAQ, requirements, event copy, and CTA labels. |
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
- External-store skills populate observed information architecture, copy, and catalog
  mappings without carrying third-party tracking or credentials.
- Figma skills populate `brand`, assets, and explicit page/block intent.
- This skill owns preset choice, dependency ordering, Shop Builder writes, and final
  verification. Callers must not duplicate those operations.

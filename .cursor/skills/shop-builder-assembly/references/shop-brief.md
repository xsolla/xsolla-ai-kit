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
`virtual_currency`. `project.environment` must be `test`, and the `project` object must
contain `"test_project_acknowledged": true`. Set it only when the publisher explicitly
states in this conversation that the project is a dedicated test project. The agent never
sets it on its own or infers it from the project name, a test site, an earlier yes, or
the approval list.

Before a write, `preflight.py` and `apply_plan.py` require a separate local approval list
at the fixed path below (expand `~` before passing it to the scripts). Only the scripts
read it; the agent never reads, stats, lists or checks it.

```
~/.config/xsolla/approved-test-projects.json
```

Format of that file:

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

Keep the real list outside the repository. It binds the exact project identity to approval
evidence; a self-declared brief is not enough.

## Field behavior

| Field | Purpose |
|---|---|
| `project.*` | Hard safety boundary. IDs must match, CLI sandbox mode must be off, and a dedicated-test-project acknowledgement that the publisher gave in this conversation is required; the agent never sets it. |
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

## Operation mode (`block_operations`, Quests block only)

A brief with `block_operations` edits individual Quests blocks on an existing site and
cannot be combined with `content.page_overrides`. Required: `version`, `project`
(`environment`, `merchant_id`, `project_id`, `test_project_acknowledged`), `site.slug` and
`block_operations`. Nothing else is allowed: validation rejects any other top-level key
(`game`, `catalog`, `content`, `brand`, `sources`), any other `site` key (`name`, `pages`)
and any other `project` key, because the plan would silently ignore them. Operations write
only to an approved `environment: test` project (`sandbox` is rejected). The approval
list, backup and `test_project_acknowledged` rules above all apply.

```json
"block_operations": [
  {"op": "add", "module": "_quest-platform_quests-block", "page": "/", "index": 2,
   "values": {"questIds": ["..."], "maxQuests": 6, "layout.cardAlign": "center"},
   "translations": {"en-US": {"heading": "Quests"}}},
  {"op": "update", "block_id": "<id>", "values": {"overrides.<questId>.title": "..."}},
  {"op": "reset", "block_id": "<id>", "paths": ["overrides.<questId>.imageUrl"]},
  {"op": "move", "block_id": "<id>", "index": 0},
  {"op": "duplicate", "block_id": "<id>", "index": 3},
  {"op": "hide", "block_id": "<id>"}, {"op": "show", "block_id": "<id>"}
]
```

`values` keys are short; the plan maps them to the block's internal values and creates
any missing parent object (for example `layout`) before patching. There is no `delete` op:
validation rejects it, the agent answers `needs_human` (the publisher deletes the block in
the Site Builder editor) and offers `hide`. The plan also rejects locales the site does
not have, out-of-range indices, a `duplicate` without `index` next to another order
change on the same page, and conflicting ops on one leaf. Semantics and planning checks:
[block-operations.md](block-operations.md).

## Handoff contract for other skills

- Description skills populate `game`, approved `content`, and relevant `sources`.
- Figma skills populate `brand`, assets, and explicit page/block intent.
- This skill owns preset choice, dependency ordering, Shop Builder writes, and final
  verification. Callers must not duplicate those operations.

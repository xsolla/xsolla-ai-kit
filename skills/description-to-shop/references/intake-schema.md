# Intake schema

Every fact needed before a shop can be planned. Drives the DoD requirement *"the skill
asks only for what is missing"* and the intake-completeness metric (% of required fields
held before the first write; target 100%).

## How intake works

After reading the description, every field is in one of three states:

| State | Meaning | Action |
|---|---|---|
| **Stated** | Explicit in the description | Record. Never re-ask. |
| **Inferred** | Derivable with confidence ("mobile gacha RPG" → `mobile`) | Record with provenance; confirm in the plan, not in a turn. |
| **Missing** | Neither | Ask. |

Only Missing required fields generate questions, and they go in **one batch**, grouped by
section. Optional fields are never asked; they take defaults and the plan says so.
Confirming inferences in bulk at the plan is what keeps turns-to-approval low.

**Guessing rule.** Infer structure freely — page count, block choice, layout. Never invent
**facts**: prices, currency codes, item names, studio name, game content. A wrong price is
worse than a question.

## A. Game info

| Field | Req | Inferable | Default | Notes |
|---|---|---|---|---|
| `game_name` | ✅ | — | none | Feeds landing name, hero copy, slug. |
| `game_genre` | ✅ | often | none | Drives block selection and tone. |
| `studio_name` | ⬜ | ✕ | omit from footer | Never invent. |
| `art_direction` | ⬜ | often | from genre | "dark sci-fi", "cozy pixel". Feeds theme. |
| `logo_asset` | ⬜ | ✕ | text wordmark | Local file path. |
| `key_art` | ⬜ | ✕ | flat colour hero | Absence is expected — the premise is publishers with no assets. |

## B. Audience and platform

| Field | Req | Inferable | Default | Notes |
|---|---|---|---|---|
| `platform` | ✅ | usually | none | `mobile`/`pc`/`console`/`cross-platform`. **Selects the archetype** — highest-leverage field. |
| `primary_regions` | ⬜ | ✕ | global | Informs languages and currency, not geo-restrictions (out of scope). |
| `audience_note` | ⬜ | often | omit | Tone only. |

## C. Visual style

| Field | Req | Inferable | Default | Notes |
|---|---|---|---|---|
| `colorscheme` | ⬜ | ✕ | omit | Does not appear on a built landing; mapping unknown. `theme_overrides` covers styling. |
| `theme_overrides` | ⬜ | ✅ | platform default | Settable: `backgroundBlur`, `buttonBorderRadius`, `buttons`, `calculationType`, `fonts`, `input`, `pictureBackground`, `videoBackground`. Never write `calculatedTheme` — derived. |
| `tone` | ⬜ | often | from genre | "gritty", "playful". |

Infer most aggressively here. A publisher with no design assets cannot answer questions
about border radius. Derive from `art_direction` and `game_genre`, present in the plan,
let them correct it there.

## D. Catalog

**Scope (settled 2026-09-10):** this skill never creates catalog entities. The catalog is
seeded separately with the AI Kit catalog skill. This skill *reads* it and wires it in.
Intake collects enough to design the storefront *around* a catalog, not to build one.

**Groups are the structure.** A `newStore` block binds to an item **group** and **type**,
never item IDs — one section per group. So the group structure *is* the storefront
structure. Collect groups first, items only as their contents.

| Field | Req | Inferable | Default | Notes |
|---|---|---|---|---|
| `catalog_exists` | ✅ | ✕ | none | If no, stop — seeding is a prerequisite, not part of this run. |
| `groups[]` | ✅ | partly | read from catalog | Each: `external_id`, `type` (`bundle`/`virtual_good`/`virtual_currency`), `placement` (`featured`/`primary`/`secondary`). |
| `group_order` | ✅ | ✅ | catalog order | Section order down the page. |
| `featured_group` | ⬜ | ✅ | first group | Gets the `featured` card layout. |
| `real_currency` | ⬜ | ✕ | read from catalog | Display only; the catalog owns the value. |

### Translating a description into groups

Every eval description but one names items and prices, never groups. So there is always a
translation step, and it comes before the plan:

1. Use the assembly skill's read-only catalog discovery to read real groups and types.
2. Map the description onto them. "Three coin packs and a starter bundle" is two sections,
   not four items.
3. Anything named with no matching group is **Missing** — ask, or say the catalog needs
   seeding. Never invent a group or its contents.

**Currency packages cannot be grouped.** They bind as `virtual_currency` with the sentinel
`__all__`, so every currency package lands in one section. Two separately-grouped currency
sections are not expressible — say so in the plan rather than silently building the wrong
thing.

### Never

- **Invent prices, item names or currency codes.** Read them from the catalog. A named
  group that does not exist is a Missing field, not a thing to create.
- **Create catalog entities**, even when convenient. If the catalog is thin, say so and
  point at the catalog skill.

## E. Pages

| Field | Req | Inferable | Default | Notes |
|---|---|---|---|---|
| `page_count` | ✅ | ✅ | from archetype | Almost always inferred, never asked. |
| `pages[]` | ✅ | ✅ | from archetype | Each: `name` (1–80 chars), `path` (lowercase `a-z0-9-/`, max 80). |
| `landing_type` | ✅ | ✅ | from archetype | `topup`/`store`/`sellingpage`. |
| `nav_required` | ⬜ | ✅ | true if >1 page | |

## F. Languages

| Field | Req | Inferable | Default | Notes |
|---|---|---|---|---|
| `languages[]` | ✅ | ✅ | `["en-US"]` | Only asked if the description implies non-English markets. |
| `default_language` | ⬜ | ✅ | first in list | |
| `translations_provided` | ⬜ | ✕ | false | If false, non-English locales are added but **left empty** for a human. Never machine-translate store copy silently. |

## G. Run context — from the environment

Part of completeness. Absent → hard stop before any write.

| Field | Source |
|---|---|
| `merchant_id` | `xsolla config list` |
| `project_id` | `xsolla config list` — must be non-zero and in the approved test context |
| `slug` | Proposed from `game_name`, confirmed in the plan |
| `auth_ok` | `xsolla auth status` — non-expired token |

## Completeness gate

Before handing the brief to `shop-builder-assembly`, all must hold:

1. Every ✅ field is Stated or Inferred — none Missing.
2. Every inferred field is surfaced with its provenance.
3. `auth_ok` true, `project_id` non-zero.
4. The normalized brief passes the shared assembly validator.

Fail any → do not hand off; report which gate failed.

Backup, target allowlisting, plan confirmation and every write are downstream gates owned
by `shop-builder-assembly`. Do not duplicate them here.

Log the filled/required ratio at the gate. That log *is* the intake-completeness metric.

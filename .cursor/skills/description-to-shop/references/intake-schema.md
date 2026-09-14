# Intake schema

The complete set of facts needed before a shop can be planned. Drives the
DoD requirement — *"the skill asks only for what is missing"* — and the
**intake completeness** metric (% of required fields held before the first write; target 100%).

Status: **draft for mentor review.** Field list is settled; the defaults and the
`newStore`/catalog column need confirmation against a live sandbox landing.

---

## How intake works

Every field is in one of three states after the skill reads the user's description:

| State | Meaning | Action |
|---|---|---|
| **Stated** | Explicit in the description | Record it. Never re-ask. |
| **Inferred** | Derivable with high confidence (e.g. "mobile gacha RPG" → platform `mobile`) | Record with a marker. Surface in the plan for confirmation — do not spend a turn on it. |
| **Missing** | Neither stated nor safely inferable | Ask. |

Only **Missing** required fields generate questions. Inferences are confirmed in bulk when
the plan is presented, which is what keeps *turns to plan approval* low.

**Batch the questions.** Ask all missing required fields in one message, grouped by section,
never one per turn. Optional fields are never asked — they get defaults, and the plan says so.

**Guessing rule.** Infer structure (page count, block choice, layout) freely — that is the
skill's job. Never invent **facts**: prices, currency codes, item names, the studio name, or
the game's actual content. A wrong price is worse than a question.

---

## A. Game info

| Field | Req | Inferable | Default | Notes |
|---|---|---|---|---|
| `game_name` | ✅ | — | none | Display name. Feeds landing `--name` and hero copy. |
| `game_genre` | ✅ | often | none | Drives block selection and tone. |
| `studio_name` | ⬜ | ✕ | omit from footer | Never invent. |
| `art_direction` | ⬜ | often | derive from genre | Free text: "dark sci-fi", "cozy pixel". Feeds theme choice. |
| `logo_asset` | ⬜ | ✕ | text wordmark | Path to a local file for `upload-asset --type image`. |
| `key_art` | ⬜ | ✕ | flat color hero | Path to a local file. Absence is expected — the epic's premise is publishers with no assets. |

## B. Audience and platform

| Field | Req | Inferable | Default | Notes |
|---|---|---|---|---|
| `platform` | ✅ | usually | none | `mobile` / `pc` / `console` / `cross-platform`. **Selects the archetype** — the single highest-leverage field. |
| `primary_regions` | ⬜ | ✕ | global | Informs `languages` and currency, not geo-restrictions (out of scope). |
| `audience_note` | ⬜ | often | omit | Free text. Tone only. |

## C. Visual style

| Field | Req | Inferable | Default | Notes |
|---|---|---|---|---|
| `colorscheme` | ⬜ | ✕ | omit | `create-website --colorscheme`. Does not appear as a field on a built landing; how it maps into the theme is unknown. Not required — `theme_overrides` covers styling. |
| `theme_overrides` | ⬜ | ✅ | platform default | JSON for `create-website --theme`. Settable fields: `backgroundBlur`, `buttonBorderRadius`, `buttons`, `calculationType`, `fonts`, `input`, `pictureBackground`, `videoBackground`. Never write `calculatedTheme` — it is derived. |
| `tone` | ⬜ | often | from genre | Copywriting register: "gritty", "playful". |

Visual style is the section where inference should be most aggressive. A publisher with no
design assets — the epic's whole premise — cannot answer questions about border radius.
Derive a theme from `art_direction` and `game_genre`, present it in the plan, and let them
correct it there.

## D. Catalog

**Scope, settled (Aaron Springut, 2026-09-10):** this skill does **not** create catalog
entities. The catalog is seeded once, by hand, using the existing AI Kit catalog skill.
`description-to-shop` *reads* that catalog and wires it into the storefront so the shop has
the right items in it and looks good.

Intake therefore collects enough to **design the storefront around** the catalog — not
enough to build one.

### The thing that actually matters: groups

A `newStore` block binds to an **item group** and an **item type**, never to item IDs
(see `shop-builder-assembly/references/cli-operations.md`). One store section per
group.

So the group structure *is* the storefront structure. Intake collects groups first and
items only as their contents.

| Field | Req | Inferable | Default | Notes |
|---|---|---|---|---|
| `catalog_exists` | ✅ | ✕ | none | If no, stop and seed the catalog first — that is a prerequisite, not part of this run. |
| `groups[]` | ✅ | partly | read from catalog | Normalize each verified group to `external_id`, `type` (`bundle`, `virtual_good`, or `virtual_currency`), and `placement` (`featured`, `primary`, or `secondary`). |
| `group_order` | ✅ | ✅ | catalog order | Section order down the page. |
| `featured_group` | ⬜ | ✅ | first group | Gets the `featured` card layout. |
| `real_currency` | ⬜ | ✕ | read from catalog | Display only — the catalog owns the real value. |

### Translating a description into groups

Every eval description except one names **items and prices**, never groups. The
block binds to a group. So intake always has a translation step, and it comes
before the plan:

1. Use the assembly skill's read-only preflight/catalog discovery to read the real
   groups and their item types.
2. Map what the user described onto those groups. "Three coin packs and a starter
   bundle" is two sections, not four items.
3. Anything the user named that has no group is **Missing** — ask, or say the
   catalog needs seeding first. Never invent a group and never invent contents.

**Currency packages are the exception and cannot be grouped.** They bind as
`virtual_currency` with the sentinel group `__all__`, so every currency package
in the project appears in that one section. A request for two separately-grouped
currency sections cannot be honoured — say so in the plan rather than building
something that silently shows the wrong thing.

### What intake must not do

- **Never invent prices, item names or currency codes.** They are read from the catalog.
  If a group named in the description does not exist in the catalog, that is a Missing
  field — ask, do not create it and do not guess its contents.
- **Never create catalog entities**, even when it would be convenient. Out of scope by
  decision. If the catalog is thin, say so and point at the catalog skill.

## E. Pages

| Field | Req | Inferable | Default | Notes |
|---|---|---|---|---|
| `page_count` | ✅ | ✅ | from archetype | Almost always inferred, never asked. |
| `pages[]` | ✅ | ✅ | from archetype | Each: `name` (1–80 chars), `path` (lowercase `a-z0-9-/`, max 80). |
| `landing_type` | ✅ | ✅ | from archetype | `topup` / `store` / `sellingpage`. See the two-step create note in the CLI reference. |
| `nav_required` | ⬜ | ✅ | true if >1 page | |

## F. Languages

| Field | Req | Inferable | Default | Notes |
|---|---|---|---|---|
| `languages[]` | ✅ | ✅ | `["en-US"]` | Locale codes. Default is safe — only asked if the description implies non-English markets. |
| `default_language` | ⬜ | ✅ | first in list | |
| `translations_provided` | ⬜ | ✕ | false | If false, non-English locales are **added but left empty** for a human. The skill must not machine-translate store copy silently. |

## G. Run context — not from the user

Collected from the environment, but part of completeness. Absent → hard stop before any write.

| Field | Source |
|---|---|
| `merchant_id` | `xsolla config list` |
| `project_id` | `xsolla config list` — **must be non-zero** and belong to the approved test context. |
| `slug` | Proposed by the skill from `game_name`, confirmed in the plan |
| `auth_ok` | `xsolla auth status` — non-expired token |

---

## Completeness gate

Before handing the brief to `shop-builder-assembly`, all of the following must hold:

1. Every ✅ field is Stated or Inferred — none Missing.
2. Every inferred field is surfaced to the user with its provenance.
3. `auth_ok` is true and `project_id` is non-zero.
4. The normalized brief passes the shared assembly validator.

Fail any → do not hand off. Report which gate failed.

Backup, target allowlisting, exact-plan confirmation, and every write are downstream
gates owned by `shop-builder-assembly`; do not duplicate them here.

Instrument this: the skill logs the filled/required ratio at the gate. That log *is* the
intake-completeness metric, and it is how SB-8869 reports the number rather than estimating it.

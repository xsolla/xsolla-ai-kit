# Localization coverage matrix

Every user-facing block a headless shop can render, whether it localizes, and how.
Use it as a completeness checklist — a "localized shop" is rarely just item names.

**Layer 2 comes first because it is the one this skill owns.** The others follow out of
numeric order on purpose: they are here so a coverage audit does not miss them and so
each can be routed to its owner, not because this skill performs them.

## Layer 2 — Catalog content (Store API)

**Unified pattern:** every user-facing catalog field localizes the same way — a
`{ "<lang>": "<value>" }` object on the field, written via the entity's Admin API, read
back with the `locale` query param. This holds across all entities below (confirmed in
the docs' shared *Localization* section), so you localize them identically — only the
entity/endpoint changes. What differs is **which** fields an entity carries: usually
`name` / `description` / `long_description`, but groups have no `long_description`, the
promotions carry `name` alone, and a reward chain adds `popup_header`,
`popup_instruction` and a name per step. The table is the authority, not the pattern.

**Tool** says whether `catalog_i18n.py` handles it; **Verified** says whether the
fields were confirmed against a live project rather than read off the docs. Capability
and tool support are different things, and so are documented and measured.

In the **Tool** column: **✅** handled · **❌** cannot be — the API refuses it or the
endpoint is unknown · **⛔** deliberately skipped, reachable but not player-facing text.
The difference matters when reporting: a ❌ is a limit to state, a ⛔ is a choice to
explain.

| Entity | Fields to translate | Tool | Verified |
|---|---|---|---|
| Virtual item | name, description, long_description | ✅ | ✅ 2026-09-07 |
| Item group (store section / tab) | name, description | ✅ | ✅ 2026-09-08 — both fields localized and read back; **no `long_description`**: the key is absent from a group entirely, while unfilled fields elsewhere come back as `null` |
| Bundle | name, description, **long_description** | ✅ | ✅ 2026-09-08 — `long_description` written and read back on a throwaway object |
| Virtual currency | name, description, **long_description** | ✅ | ✅ 2026-09-08 — same |
| Virtual currency package | name, description, **long_description** | ✅ | ✅ 2026-09-08 — same |
| Value points | name, description, **long_description** | ✅ | ✅ 2026-09-08 — same |
| Attribute | name + `values[].value` | ✅ | ✅ 2026-09-08 — name plus two nested values localized via `subid`, three PUTs, all read back. Values are created one at a time (`POST /admin/attribute/{id}/value`); a `values` array on create is rejected |
| Game key (DRM package) | name, description, long_description | ✅ | ✅ 2026-09-08 — created, localized, verified, deleted. Empty `periods` must be dropped. Per-DRM `unit_items` names are **not** localized (would need nested addressing) |
| Subscription plan | name, description | ❌ | ❌ `/admin/items/subscription` → **405**, correct endpoint unknown |
| Discount promotion | **name only** | ✅ | ✅ 2026-09-08 — `/v3/admin/promotion/{id}/item`, write verified + rolled back. **No** `description`/`long_description` on the object, contrary to older field lists. Strip `id` |
| Bonus promotion | **name only** | ✅ | ✅ 2026-09-08 — `/v3/admin/promotion/{id}/bonus`, write verified + rolled back. Strip `id` |
| Promo code promotion | **name only** | ✅ | ✅ 2026-09-08 — `/v3/admin/promocode/{external_id}`, write verified + rolled back. Strip `is_enabled`, `external_id`, `total_codes_count` |
| Coupon promotion | **name only** | ✅ | ✅ 2026-09-08 — created, localized, verified, deleted. Strip `is_enabled`, `external_id`, `total_codes_count` |
| Unique catalog offer | **name only** | ✅ | ✅ 2026-09-08 — created, localized, verified, deleted. Strip `is_enabled`, `external_id`, `total_codes_count` (the same trio as promo codes and coupons); `items` on create is a list of SKU **strings**, not objects |
| Daily login chain | name, description | ✅ when disabled | ✅ 2026-09-08 — a **disabled** chain localizes normally (created, written, deleted). An **active** one is refused (`422/6209`), excluded at plan time, and never disabled to get around it. Strip `number_of_steps`, send `type` |
| **Offer chain** | name, description | ✅ when disabled | ✅ 2026-09-08 — same as daily chains: writable while disabled, refused while active. Its own LiveOps product. Strip `number_of_steps` |
| **Reward chain** | name, description, long_description, **popup_header**, **popup_instruction**, + `steps[].name` (addressed in the CSV as field `step_name`, `subid` = `step_id`) | ✅ | ✅ 2026-09-08 — registered and verified end to end: 7 strings on a two-step chain written in one PUT and read back. `/v2/admin/reward_chain`, detail at `/id/{id}`. Strip `reward_chain_id`, `clan_type`, `value_point`; every step must carry its `step_id`; `reward` goes back minimal. The list view omits `steps`, so the object is re-read before export |
| Upsell | name, description | ❌ | ❌ `/v2/admin/upsell` → **403 forbidden** — the only LiveOps endpoint the project key cannot read |
| Personalized catalog (filter rules) | name | ⛔ | reads fine (`/v2/admin/user/attribute/rule`) but filter rules are not player-facing — deliberately skipped |
| Region (regional-restriction label) | name | ⛔ | not player-facing — deliberately skipped, see SKILL.md Common rules |
| Item image / `media_list` | — | ⛔ | `image_url` is a **single** URL, not language-keyed. Localized art is a client-side swap per locale |

**No other LiveOps entity hides extra text.** Checked twice on 2026-09-08, because
`popup_header` / `popup_instruction` were nearly missed on reward chains and the same
trap could exist elsewhere. First a scan of every live object for anything shaped like a
`{lang: value}` map, at top level and inside nested collections — only reward chains came
back with more than `name`/`description`. Then, since a scan cannot see a field that has
never been filled, a create-schema probe: all seven other LiveOps types reject
`popup_header`, `popup_instruction`, `title`, `subtitle` and `button_text` outright, and
`daily_chain` / `offer_chain` steps reject `name` and `description` too — so their steps
carry no text at all, unlike a reward chain's. Nothing was created by any of it.

**Reward chains are a separate product** from daily chains and offer chains, and the
easiest one to miss: they are the value-point mechanic ("collect points, unlock steps"),
they live at `/v2/admin/reward_chain`, and they carry **more localizable text than any
other entity** — five top-level fields plus a name on every step. Two of those,
`popup_header` and `popup_instruction`, exist nowhere else in scope. A step's
name is `steps[].name` on the object and field **`step_name`** with `subid` = `step_id`
in the CSV — the same address shape attribute values use
([translation-csv.md](translation-csv.md#csv-schema-wide)).

**How "name only" was established for LiveOps.** Not by reading an object and noticing
the key was missing — by trying to create one **with** `description` and
`long_description`. All five promotion types answer
`"The property description is not defined and the definition does not allow additional
properties"`, and both chain types say the same about `long_description`. That is the
write schema itself refusing the field, which is stronger evidence than an absent key:
it rules out "the field exists but has never been filled in". Nothing was created by
those probes — a 422 leaves no object behind, which makes this a cheap check to repeat
whenever Xsolla changes something.

**No entity is write-gated today** — every ✅ row above has had its write form
exercised against a live object. The gate still exists for the next entity added: one
registered with `write_unverified` reads, exports, translates and QAs normally while
`import --write` refuses it unless `--allow-unverified` is passed. That is deliberate,
because a catalog PUT replaces the object and the required-even-when-null fields and the
keys that must be stripped are measured per entity, never guessed — see
[write-safety.md](write-safety.md). Clearing the gate is a create → localize → verify →
restore run on one object, then dropping `write_unverified` from its registry entry.

**Correction, 2026-09-08.** LiveOps was previously written off as "403 endpoint
forbidden, needs a different key". That was wrong: the probe used the wrong path.
Promotions live on **`/v3`** at `/admin/promotion/item`, `/admin/promotion/bonus`,
`/admin/coupon`, `/admin/promocode`, `/admin/unique_catalog_offer`; chains on **`/v2`**
at `/admin/daily_chain`, `/admin/offer_chain` and `/admin/reward_chain`. An ordinary
project key reads **eight of the nine** — only `upsell` is genuinely forbidden. The
lesson is narrow and worth keeping: a 403 on a guessed path is evidence about the path,
not about the key.

## Layer 2b — Money (NOT language)

Listed only so it is not mistaken for a language task. The mechanics are owned by
`catalog-design` → `references/pricing.md`; this skill does not repeat them.

| Content | Owner | Effort |
|---|---|---|
| Local currency / price by country | `catalog-design` → `pricing.md` (regional `prices[]`) | medium |
| Regional availability | `catalog-design` → `pricing.md` (`regions`) | medium |

## Layer 3 — Payment UI

| Content | Mechanism | Effort |
|---|---|---|
| Payment form language | `settings.language` on the token + SDK `init({ language })` (no in-UI picker) | small |
| Charge currency | resolved from price/country | — |

## Layer 4 — Login (identity)

| Content | Mechanism | Effort |
|---|---|---|
| Login widget UI language | `preferredLocale` on the SDK (`login-setup`) | small |
| Login emails (verification, password reset) | configured on the Xsolla side | medium |

## Layer 1 — Storefront UI (partner code, not an Xsolla API)

| Content | Localizable | Effort |
|---|---|---|
| Chrome: nav, hero, buttons, cart, footer, banners | ✅ own i18n | — |
| Language switcher + persistence + `<html lang>` | ✅ | small |
| Number / price / date formatting (`Intl`) | ✅ | small |
| Empty / loading / error / toast states | ✅ | small |
| `<title>` / meta / Open Graph (SEO, link shares) | ✅ | small |
| Locale URL routing (`/ru/`, `?lang=`) | ✅ | medium |
| Missing-locale fallback (`value[locale] \|\| value.en \|\| first`) | ✅ | small |
| Fonts / glyph coverage (Cyrillic, CJK) | ⚠️ | small–medium |
| RTL layout (Arabic, Hebrew) | ⚠️ | medium–large |
| Image alt text / text baked into images | ✅ | small–medium |
| Legal pages: ToS, privacy, refund policy | ✅ partner content | medium |

## Layer 5 — Xsolla buyer communications (go-live)

| Content | Mechanism |
|---|---|
| Receipts / invoices | locale on the Xsolla side |
| Payment / refund emails | configured on the Xsolla side |

## Frequently forgotten

- **Offer chains are their own LiveOps product**, not a flavour of daily login chains:
  a sequence of steps where the next unlocks after the previous one, with its own
  localizable chain title and description
  (<https://developers.xsolla.com/liveops/promotion-tools/offer-chains/>). Easy to miss
  when auditing coverage, because it sits under promotion tools rather than the catalog.
- **A `null` field produces no CSV row.** `export` skips a field that is not a
  `{lang: value}` object, so a `long_description` that has never been filled in never
  reaches the CSV. That is correct — there is no source text to translate — but it means
  "this entity has three localizable fields" and "this catalog has three fields to
  translate" are different statements. In a catalog where every `long_description` is
  `null`, the field simply never appears. `export` now reports how many fields it skipped
  for this reason, so the absence is stated rather than silent.
- **All three fields are verified writable on all six entities** — virtual items,
  bundles, virtual currency, currency packages, value points and game keys. One pass on
  2026-09-08: an object of each created with English `name`, `description` and
  `long_description`, all 18 strings translated, written and read back carrying `de`.
  Before that the only evidence was the key coming back as `null`, which
  shows the field exists but not that it accepts a translation.
- **Groups have no `long_description`.** Verified by GET on 314067 (2026-09-07): the key
  is absent from a group entirely, while unfilled fields elsewhere come back as `null` —
  so the field does not exist in the model. Bundles, virtual currency, currency packages
  and value points, by contrast, **do** carry `long_description`.
- **More than `name`/`description` is localizable:** `long_description`, attribute
  values, and a reward chain's `popup_header`, `popup_instruction` and per-step names.
  The set is per entity — the table above is the authority.
- `image_url` is **not** language-keyed; localized banners are a client-side swap.
- SEO layer (`<title>`, meta, OG, `/ru/` routing) is easy to skip and hurts sharing/search.
- Fonts/glyphs and RTL are layout risks, not API work — check them when adding a script.

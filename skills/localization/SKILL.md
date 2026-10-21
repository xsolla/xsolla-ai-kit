---
name: localization
description: >-
  Translates an Xsolla catalog and LiveOps into more languages. Use when a developer
  wants to "localize / translate the shop or catalog", "translate item names /
  descriptions", "translate promotions / promo codes / reward chains", "add a language /
  another locale", "make the store multi-language", "catalog i18n / localisation",
  "export/import translations (CSV)", "bulk translate", hands over a translation file,
  or mentions a locale code (`ru-RU`, `pt-BR`); also when a name shows the wrong
  language or a write returns "404 Locale not found". Offer it when a catalog exists
  in one language only. Not for creating the shop (shop-setup), prices
  (catalog-design), payment UI or Login language, or Shop Builder page copy
  (shopbuilder-translate).
metadata:
  owner: u.filipau
  domain: catalog
  status: draft
---

# Localizing an Xsolla catalog

Translate catalog and LiveOps content through **one CSV**. The agent runs
[`scripts/catalog_i18n.py`](scripts/catalog_i18n.py); the user only talks. The model does
the translation. There is no machine-translation service. **Catalog and LiveOps strings are
sent to the agent's model** as the CSV batch. Say that before the first `batch` on a real
project.

Writes hit the live project named by `XSOLLA_PROJECT_ID`. There is no catalog sandbox. Shop
Builder page copy is `shopbuilder-translate`. This skill does not extract or load a site.
Moving the script into `xsolla-cli` as `xsolla catalog localize` is a follow-up; it stays
here until that command ships.

Load a reference only for the step that needs it: [glossary.md](references/glossary.md)
(step 6), [qa.md](references/qa.md) (step 8), [write-safety.md](references/write-safety.md)
(steps 10–11), [translation-csv.md](references/translation-csv.md),
[supported-languages.md](references/supported-languages.md) (step 3),
[coverage-matrix.md](references/coverage-matrix.md) (step 2).

## When to use

16 entity types, one CSV: `name` / `description` / `long_description`, attribute values, and
a reward chain's `popup_header` / `popup_instruction` and step names. Use it to localize the
catalog, add a language, translate LiveOps (discount, bonus, and promo-code promotions,
coupons, unique catalog offers, reward chains, and daily-login and offer chains — those two
only while **disabled**), export or import a CSV, fill a partial locale (`ru 6/18`), or fix
a wrong-language name or `404 Locale not found`.

**Out of scope** — name the owner and never start an export for these: storefront UI and the
language switcher (the partner's own i18n); payment UI language → `shop-setup`; Login widget
language → `login-setup`; prices and regional availability → `catalog-design`; Shop Builder
page copy → `shopbuilder-translate`. Not covered at all: `upsell` and subscription plans.
Check the target against [coverage-matrix.md](references/coverage-matrix.md). Offer at most
once per session. A deliberately single-language shop is a valid answer.

## Prerequisites

- `XSOLLA_PROJECT_ID` and `XSOLLA_PROJECT_API_KEY`, from the environment, `--env PATH`, or
  `$XSOLLA_ENV_FILE` (`--env` wins). From `merchant-setup`. Admin auth is Basic
  `base64(project_id:api_key)`.
- `XSOLLA_MERCHANT_ID` is optional. Without it, step 6 loses the project-name signal and
  degrades quietly ([glossary.md](references/glossary.md)).
- A populated catalog, or there is nothing to translate. Python 3.6+, standard library only.
  If Python is unavailable, implement the
  [translation-csv.md](references/translation-csv.md) contract in the user's stack.
- `--env` overrides the ambient environment and prints which keys it replaced, never their
  values. A stale `XSOLLA_PROJECT_ID` in the shell cannot silently redirect a write.

## The flow

1. **Trigger.** A neighbouring-layer request stops here and is routed.
2. **Discover.** `discover` lists which entity types exist and the per-locale coverage. A
   failed list prints `(list failed HTTP n)` — including the attribute list — and `discover`
   still **exits 0**. An absent type prints `0 — skip (not offered)`. Treating a failure as
   absence drops that entity for the whole run. Retry before agreeing scope. Two decisions:
   which types are in scope (they become `--entity`; the export default is `items` only, so
   a type you leave off the flag is never localized), and what is already covered (full
   count → stop, no export; partial → `export --missing`).
3. **Locales.** Validate every code against
   [supported-languages.md](references/supported-languages.md) before export. `pt-PT` and
   `en-GB` are not catalog locales and 404 the whole write. Source defaults to `en`.
   `discover` reports coverage, not authorship, so confirm another source only when the
   numbers say so (`en 0/18 · de 18/18`) and pass `export --source`. Responses are always
   2-letter; `de-DE` and `de` are one column. One canonical variant per language
   (`pt`=`pt-BR`, `en`=`en-US`); Chinese is the exception (`cn`, `tw`). A `--locale` with no
   column is an error, not a batch of every row.
4. **Export** the CSV, the single source of truth. Types are the ones agreed in step 2:
   `export out.csv <locales> --entity <types> [--source] [--missing]`.
   Existing translations come along, so filled
   and empty cells sit side by side. The script owns the file; the model never serializes
   it. Unlike `discover`, `export` **exits non-zero** and prints `INCOMPLETE` when a list
   fails, and warns when a listing is shorter than the server total. `exported 0 rows` from
   a failed read is indistinguishable from a catalog that is already fully translated.
5. **Choose the path:** the agent translates, a publisher fills the CSV, or the user already
   has one (`merge`). Combining them is fine. **The order is fixed: `merge` first, then
   `batch` what is still empty, then `fill`.** `batch` lists only rows missing that locale,
   which is the only reason the model cannot overwrite a human translation. `fill` writes
   whatever it is handed.
6. **Glossary**, on the AI path, before the first batch. Derive it from the data and pass it
   as a constraint, not a post-hoc filter. Re-run when new ids enter.
   [glossary.md](references/glossary.md).
7. **Translate.** AI: loop `batch` → translate → `fill` until `remaining` is 0, with the
   glossary on every batch. Tone comes from locales that already exist. Prefer the most
   natural and shortest rendering: translate, do not paraphrase, and add no words the source
   does not have. `fill` exits non-zero listing every discarded translation; the cells that
   did fill are saved, so re-send just those from a fresh `batch`. Publisher: hand over the
   CSV and stop. Say what you are waiting for (the same file, target columns filled, other
   columns untouched) and who approves the import. When it comes back, re-enter at `merge`,
   not step 1, then `batch`/`fill` anything still empty, then QA. Re-run `discover`: the
   catalog has had days to drift.
8. **QA**, on AI and human translations. `check`, plus a semantic review.
   [qa.md](references/qa.md). `!` is blocking. If `check` says the source column looks
   reordered, put the source first or pass `--source`. Re-translating does not clear it, and
   `import` refuses the same way.
9. **Offer a review** of the finished CSV before anything is written. Take edits back
   through `merge` or the file, then re-run QA on the touched rows. This is not the write
   approval.
10. **Preview, approve, write, then conflicts.** `import` prints the plan and writes
    nothing. Its first line names the target. If you summarise, keep verbatim the project
    id, the counts, the locales, and every `!!` line. `!!` means the write would drop fields
    — resolve it before asking. `‼ BLOCKED` is an active `daily_chain` or `offer_chain`,
    already excluded from the plan. Never disable a chain to make it writable; name it and
    localize it the next time it is out of service for its own reasons. A non-zero preview
    means rows addressed nothing or an object could not be read. Clear that before asking.
    Wait for an explicit yes to *that* plan. `import --write` is fill-only and replace-safe:
    it snapshots the whole run first, then PUTs, and writes a backup CSV of the translations
    on the server now. With no path given, snapshots land in `l10n-snapshots/` and backups
    in `l10n-backups/` beside the CSV, not in the repository root. The snapshot records
    `project_id`. Conflicts surface at write time: the object is re-read, unchanged fields
    are written, a changed object is skipped, both versions are printed, and the run exits
    non-zero. One conflict does not block the rest. Show both versions. Pass
    `--on-conflict overwrite` only after the user chooses the translation. A reward chain's step names ride
    inside that same PUT, so they take part in the conflict check. `reward_chain` is on API
    v2. Promotions are on API v3. Detail: [write-safety.md](references/write-safety.md).
11. **Verify, report, roll back.** `import --write` reads each object back after its PUT.
    Then `discover` shows the target locale at full count for what was written. A blocked
    object stays missing, and that is the guardrail, not a shortfall. A second `import`
    plans **0 changes**. Report successful PUTs only. A non-zero exit is a failure
    even when most objects went through. Name every blocked object: its CSV cells look
    finished, and the catalog never received them. Say how to see it: the storefront must
    request the locale (`?locale=de`). The snapshot is the only undo.
    `restore <snapshot.json>` previews. `--write` puts that state back and needs its own
    yes. It refuses a snapshot from another project, and a snapshot that names no project.
    A rollback reverts everything in that snapshot. One bad object is the backup CSV:
    `import <backup.csv> --overwrite`.

## Guardrails

Ask four questions before starting. The publisher path adds a fifth: who approves the
import. Step 9 and step 10 come later, because approval is a yes to a concrete plan.

1. **Which project, and which entity types.** Quote the project id `discover` resolved.
   Confirm it if the user has more than one project, or a sandbox and a live one. The
   credentials can come from the ambient environment, so the id is an input nobody chose
   explicitly.
2. **Target languages.** Source defaults to `en`. Confirm another only when step 2's numbers
   imply it.
3. **Who translates?** The agent, or a publisher who hands back a CSV (`merge`). If a
   publisher, who approves before import? That answer has to survive a gap of days.
4. **Fill-only or overwrite?** Default fill-only. Overwrite needs an explicit ask. Name the
   backup CSV when asking.

Derive, do not ask: the glossary (only genuinely ambiguous terms reach the user), tone (read
it off locales that already exist), and a length limit only when strings are
space-constrained (`check --max-len N`, warning only). Fallback locale is a storefront
concern, not a catalog write.

## Common rules

- **Language is not currency.** Never touch prices when translating.
- **Update replaces the whole object.** Get, merge, write the full state. Never hand-build a
  body from a field allowlist. `PATCH` is not used.
  [write-safety.md](references/write-safety.md).
- **Text fields only, and the set is per entity**, not a universal three: `name`,
  `description`, `long_description`, `value`, `popup_header`, `popup_instruction`,
  `step_name`. The table in [coverage-matrix.md](references/coverage-matrix.md) says which
  entity has which. Never translate `sku`, `external_id`, `id`, promo codes, `prices`,
  `image_url`, flags, dates, or structure. A `null` field produces no CSV row.
- **Fill-only by default.** Enforced by `merge` and `import`, not by `fill` (step 5).
  `merge` keeps an existing cell unless `--overwrite`. Never hand-edit a partner file into
  place, and never feed it to `import` directly.
- **Write only after a preview.** `import` previews unless `--write` is passed.
- **Placeholders survive:** `{name}`, `%s`, `{{brand}}`, and ICU argument names. `check`
  compares ICU by argument name.
- **An unknown locale 404s** and drops the whole PUT. `check` reports them and `import`
  refuses to start.
- **A failed read is not an empty catalog.** `export` exits non-zero and prints
  `INCOMPLETE`. `discover` is the exception: read the lines, not the exit code.
- **Three entities change a run.** `daily_chain` and `offer_chain` are writable only while
  disabled (`422/6209` while running). `reward_chain` is the value-point mechanic, separate
  from those two: five top-level fields plus a name on every step, one PUT. Promotions carry
  `name` only.

## Pitfalls

- Approving a summary that drops the project id. The yes has to cover which catalog is
  written.
- Reporting the plan as the result. Count written PUTs.
- Trusting `204`. It says the request was accepted, not that every field survived.
- An item's `inventory_options` or `groups` vanishing. That takes an allowlist body, or
  `--allow-field-loss`.
- Sending both `en` and `en-US` for one field. Last wins.
- Filling a batch taken before `merge`. That replaces human translations.
- Reading `(list failed HTTP n)` as "that type does not exist".
- Reporting a blocked chain as localized.

## Tests

Prompt: "localize my catalog to German". Expected: `discover` → the four questions →
`export` → glossary → `batch`/`fill` → `check` → `import` preview → explicit approval →
`import --write` → read-back. The same flow for «локализуй каталог на немецкий».

`python3 scripts/tests/test_catalog_i18n.py` from this skill directory. Offline, no network
or credentials. Run it after any change to the script. Live measurements sit with the rule
they justify, in [coverage-matrix.md](references/coverage-matrix.md) and
[write-safety.md](references/write-safety.md).

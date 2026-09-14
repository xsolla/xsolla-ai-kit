# Translation CSV round-trip (contract)

A stateless export → translate → import loop for bulk localization. The **model**
translates (or a publisher does); a **deterministic script** moves the data so the
model never hand-assembles CSV at scale (bug-prone escaping, dropped rows). No
sidecar/state: `missing` is derived from the data, safety comes from *fill-only*.

Reference implementation: [`../scripts/catalog_i18n.py`](../scripts/catalog_i18n.py)
(catalog adapter). This file is the **contract** it implements — and the spec to
re-implement in another stack when Python is unavailable.

**Catalog entities (each verified end-to-end via create → localize → verify →
cleanup on project 314067):** `items`, `groups`, `virtual_currency`, `vc_package`,
`bundle`, `value_points`, `game`, `attribute`.

**LiveOps entities (writes verified 2026-09-08):** `discount_promotion`,
`bonus_promotion`, `promocode`, `coupon`, `unique_catalog_offer` — all on the **v3**
API — plus `daily_chain`, `offer_chain` and `reward_chain` on v2. Each entity declares
its API version in the registry (`"api": "v3"`), because promotions do not live under
`/v2` and probing there returns a misleading 403. Each was localized against a live
object and rolled back or deleted afterwards, so `import --write` accepts them; the
fields that must be stripped are per entity in
[write-safety.md](write-safety.md), and their field lists are narrower than older ones
claim — the five promotion types carry **`name` only**. `daily_chain` and `offer_chain`
(not `reward_chain`) are writable **only while disabled**: an active one is refused
(`422/6209`), detected at plan time and excluded from the plan and the counts.
Per-entity detail: [coverage-matrix.md](coverage-matrix.md).
- Content-bearing entities (bundle, vc_package) send `content` as minimal
  `[{sku, quantity}]` (the enriched GET form 422s) and price `amount` as a number.
- **game** (game keys) re-sends `unit_items` (per-DRM keys) in minimal form
  (`sku, name, drm_sku, prices, is_enabled, is_show_in_store`) with numeric prices;
  the game's own `name`/`description` are localized. (Per-DRM unit_item names are not
  yet localized — would need nested addressing like attribute values.)
- **attribute** is nested — the list endpoint omits values, so the script GETs each
  attribute; a value's address uses `subid` (the value external_id) with field `value`.
  Paths are **singular**: `/admin/attribute`, `/admin/attribute/{id}`,
  `/admin/attribute/{id}/value/{value_id}`.
- **reward_chain** is nested too, and the only entity with **five** top-level
  localizable fields: `name`, `description`, `long_description`, `popup_header`,
  `popup_instruction` — the last two exist nowhere else in scope. Each step
  carries a `name`, addressed in the CSV as field **`step_name`** with `subid` = the
  step's `step_id`. Unlike an attribute, the steps are **not** separate endpoints: they
  ride inside the chain's own PUT, so a whole chain — every top-level field and every
  step name — is one write. The list view omits `steps`, so the object is re-read
  before export; `/admin/reward_chain`, detail at `/admin/reward_chain/id/{id}`.

Deferred (with reason, verified by probing project 314067):
- **subscription plans** — `/admin/items/subscription` 405; correct endpoint TBD.
- **`upsell`** — `/v2/admin/upsell` 403; the only LiveOps endpoint a project key cannot
  even read.
- **personalized-catalog filter rules** — readable, but not player-facing, so
  deliberately skipped rather than blocked.

An earlier version of this file deferred *all* LiveOps promotions here, on the grounds
that `/admin/promotions*` returned 403 and a LiveOps-enabled key was needed. That was
wrong — the path was wrong, not the key: promotions live on `/v3` and chains on `/v2`,
and an ordinary project key reads eight of the nine. See the correction in
[coverage-matrix.md](coverage-matrix.md).

## Why the script owns the file (batching)

Everything goes through the CSV — one auditable, user-editable checkpoint. The
**script owns the file**; the model never serializes it. That matters at scale:
a 1000-item catalog is far more text than fits (well) in the model's context, and an
LLM hand-typing CSV drops rows and mis-escapes commas/quotes/newlines/emoji.

So for AI translation the model works in **batches**: the script hands it a slice of
pending rows, the model returns only the translated values, the script writes them
back into the file. The full dataset lives on disk (unbounded, exact); the model's
context only ever holds one batch. The agent runs the script via Bash; the user only
converses. `import` previews unless `--write` is passed, so the confirm step cannot be
skipped by forgetting a flag.

## Why a script, and not HTTP in prose

The house rule for this repo is that a skill describes intent and does not paste raw
`curl`. That rule exists so an agent is not improvising around fragile HTTP snippets —
and this skill honours it: **SKILL.md contains no HTTP at all.**

What it does instead is put the one destructive operation in the domain behind tested,
reviewable code. A catalog PUT has REPLACE semantics: reconstructed freehand, per
conversation, it silently destroys any field the reconstruction forgot — verified, not
hypothetical (see *Full state, not an allowlist* below). The script is where the
preview, the locale guard, the snapshot, the pacing and the honest exit codes live;
none of those survive being re-derived each time. Bulk translation additionally needs
file handling no agent does reliably in-context (see *Why the script owns the file*).

Precedent for shipping non-Markdown payloads inside a skill: `webhooks-impl/fixtures/`.

## CSV schema (wide)

One row per translatable string; one column per target locale. Empty target cell = missing.

| Column | Meaning | Editable? |
|--------|---------|-----------|
| `entity` | any registered entity: the 8 catalog ones (`items`, `groups`, `virtual_currency`, `vc_package`, `bundle`, `value_points`, `game`, `attribute`) plus the 8 LiveOps ones (`discount_promotion`, `bonus_promotion`, `promocode`, `coupon`, `unique_catalog_offer`, `daily_chain`, `offer_chain`, `reward_chain`) | 🔒 no |
| `id` | whichever identifier the entity is addressed by: `sku` (items, virtual currency, packages, bundles, value points, game keys), `external_id` (groups, attributes, promo codes, coupons, unique catalog offers), plain `id` (discount and bonus promotions, daily and offer chains), or `reward_chain_id` (reward chains) | 🔒 no |
| `subid` | empty for a top-level field. For an **attribute value** it is the value's `external_id`; for a **reward-chain step** it is the step's `step_id` | 🔒 no |
| `field` | `name` \| `description` \| `long_description` \| `value` (attribute values) \| `popup_header` \| `popup_instruction` \| `step_name` (reward-chain steps) | 🔒 no |
| `context` | human hint for translators | 📎 read-only |
| `en` (source) | source text | 📎 read-only reference |
| `ru`, `de`, … | target locales | ✅ translate here (blank = missing) |

**Which column is the source is positional — the first language column — and nothing in
the schema records it.** Reorder the columns in a spreadsheet and the convention
inverts: the source becomes a target and a finished translation is never imported. So
`check` and `import` both print the column they are treating as the source, and when the
assumption looks wrong they **stop**: `check` counts it as a blocking `!` and `import`
refuses to start. Two cases qualify — `en` sitting further right (a reordered file), and
**no `en` column at all**, which is the shape of a partner's file and belongs in `merge`.
The second used to pass both gates silently, dropping the first locale with a clean exit. Nothing in
the file can distinguish a reordered export from a catalog genuinely authored in
German, so it is a question, not a guess. Two ways to answer it: put the source column
first, or pass **`--source <loc>`** to `check`/`import` to name it explicitly — which
makes the column order stop mattering altogether.

Address of a string = `(entity, id, subid, field, locale)`. Identifiers and
non-translatable fields (price, image_url, external_id, promo codes) are never written.
Target-locale columns are canonical 2-letter codes; a canonical 5-letter code
(`ru-RU`) is normalized down by `import`/`merge`, while a code that is not an Xsolla
locale at all (`pt-PT`) is **refused before any request** — it would 404 and
**drop the whole PUT**, valid locales in the same write included.

## Discover (scope)

`discover [--env PATH]` — lists which entities actually exist in the project and
per-locale coverage (e.g. `items: 10 object(s), 18 strings — en 18/18 · ru 6/18`).
Offer only present entities; never propose a type with 0 objects. `langs` is the
items-only coverage shorthand.

## Export

`export <out.csv> [locales=ru,de] [--source en] [--entity items,groups] [--missing] [--env PATH]`

- Reads the **admin** catalog for the chosen entities, emits a row per
  (entity, id, localizable field).
- `--entity`: which entities to pull (default `items`). Columns are the chosen target
  locales.
- `--missing`: skip rows whose every target locale is already filled.
- `--source`: the source-text column (default `en`); must be a catalog locale and must
  not also be a target. Every code is validated before the export runs.
- Read-only (admin Basic auth for listing).
- A list that **fails** is reported per entity and the command exits non-zero, saying
  the CSV is `INCOMPLETE`. A silent `exported 0 rows` reads exactly like a fully
  translated catalog, so this is the difference between "nothing to do" and "we never
  saw the catalog". A listing shorter than the total the server reports is flagged too.
- Fields with **no source text** produce no row (there is nothing to translate), and the
  count of them is printed — otherwise an entity looks like it has fewer localizable
  fields than it does, which is how `long_description` appeared absent catalog-wide.
- An unknown flag is fatal rather than ignored — otherwise a typo'd `--sorce fr` gets
  swallowed and silently becomes the locale list.

## Fill in batches (AI path)

The model never reads/writes the whole file — it works a batch at a time:

- `batch <csv> --locale de [--size 50]` → prints JSON `{locale, remaining, batch:[{entity,
  id, subid, field, context, source}]}` for rows still missing that locale. Translate `batch`.
- `fill <csv> --locale de [--from FILE|-]` → reads JSON `[{entity, id, subid, field,
  translation}]` (file or stdin) and writes those cells into the CSV.

Loop `batch` → translate → `fill` until `remaining` is 0. For the publisher path,
skip this: hand over the CSV/XLIFF and load the result with `merge`.

`fill` is defensive about its own input, because a model writes it. Accepted: a
```-fenced reply; a wrapper object keyed `batch`, `translations`, `items`, `rows` or
`data`; and `value`, `text`, `target` or `translated` in place of `translation`. What it
will not do is fail silently — entries with no usable text, translations whose address
matches no CSV row, and two entries giving *different* text for one cell (neither is
used; an identical repeat dedupes quietly) are listed individually and the command exits
non-zero.
Cells that did fill are still saved, so re-sending only the discarded ones is safe.

What `fill` does **not** do is protect an existing value: it writes whatever address it
is handed, with no fill-only guard. That is safe in the normal loop only because
`batch` lists rows *missing* the locale, so a filled cell is never in a batch. The
consequence is an ordering rule when a partner CSV is also in play — `merge` first,
then `batch`, then `fill`. Filling a batch that was taken before the merge replaces the
partner's human translations with machine output, silently.

## Loading a partner's CSV

`merge <working.csv> --from <partner.csv> [--overwrite]`

Run this **before** any `batch`/`fill` for the same locale, and re-run `batch`
afterwards — see the caveat under *Fill in batches*.

The partner file goes through the **same hardened reader as every other CSV**, which
matters because it is the only one written on someone else's machine with someone else's
tooling. Refused with a sentence, never a traceback: a non-UTF-8 file (`re-save it as
UTF-8` — Windows tooling emits Latin-1), a **duplicate column name** (`DictReader` keeps
only the last, so the others would vanish silently), and a **semicolon- or tab-delimited**
file — the European Excel default, which parses as one column and used to be reported as
"missing required column(s)" about columns that were all present. Excel's trailing blank
rows are dropped rather than reported as strings that could not be found.

Merges by address (`entity`+`id`+`subid`+`field`), tolerating reordered columns and a
missing `context`. **Columns that cannot be a locale are ignored, and named.**
`translator`, `status`,
`notes` — what a TMS or XLIFF export adds as a matter of course — are skipped with a
line saying so, rather than failing the file. But a name *shaped* like a locale that
does not resolve (`fr_CA`, `pt-PT`) is still **fatal**: skipping it would silently
discard the translator's work. If nothing resolvable is left, the merge refuses rather
than reporting a clean no-op.

**Every language column in the partner file is a target** — a partner
file has no source column, and applying the working file's "first language column is the
source" rule to it swallowed a whole locale: a translator returning `de,ru` had the
German column read as source and silently dropped while the run reported success. A
column that maps onto the working file's own source (`en`) is reference text and is
skipped with a note, not written. Locale columns are normalized 5→2 and the renames are printed; a
code that is not an Xsolla locale aborts the merge instead of being guessed at. Rows
whose address is absent locally are **not added** — they are reported and the command
exits non-zero. A cell the partner translated two different ways is flagged, naming
which value was used. Fill-only unless `--overwrite`.

## Guardrails

The questions that gate a write, and the ones that are derived from the data instead of
asked, are in SKILL.md under *Guardrails* — that list is not repeated here. The two
derivations with their own references: the glossary and do-not-translate set
([glossary.md](glossary.md)) and length limits ([qa.md](qa.md#length)).

## QA before import

`check <csv> [--max-len N] [--source <loc>]` plus the agent's semantic review.
`--max-len` takes a limit of 1 or more (a negative one flagged every cell and `0`
silently disabled the check, so both are now refused). The full checklist — what
is deterministic, what is judgement, and how length is used to find translation errors
rather than to enforce layout — is [qa.md](qa.md).

## Import

`import <in.csv> [--write] [--overwrite] [--source <loc>] [--allow-field-loss]`
`       [--pace SECONDS] [--snapshot PATH | --no-snapshot]`
`       [--backup PATH | --no-backup] [--on-conflict skip|overwrite]`
`       [--no-verify] [--allow-unverified] [--env PATH]`

- **Announces its target first**: `target: project <id>  [preview]` or `[WRITE]`, so an
  approval covers which catalog is written, not just which strings. `discover` and
  `export` print the resolved project id too.
- Groups rows by `(entity, id)`; for each: **GET** the current object → merge locale
  cells into each field's localization object → **PUT** the full object (attributes PUT
  the name and each value separately).
- **Previews by default.** Without `--write` it prints the plan and writes nothing;
  `--dry` is accepted as an explicit alias. The destructive path is the one that needs
  a flag, so a forgotten flag is harmless.
- **Surfaces hard QA issues on the plan.** `check` is a separate command the caller can
  skip, so `import` re-runs its *breakage* checks — placeholder, markup, URL, encoding —
  and lists them above the plan. It does not block on them (import guards against data
  loss; `check` judges content), but a plan being approved should not quietly contain a
  renamed placeholder or an unbalanced tag. Soft signals — echo, length, ratio — stay in
  `check`, where judgement belongs.
- **Refuses unknown locales before any network call** — a single bad column (`pt-PT`)
  404s and drops the entire PUT, so `import` re-checks rather than trusting that
  `check` was run.
- **Fill-only by default**: a non-empty existing value is kept (protects human/prior
  translations) unless `--overwrite` is passed.
- **Reports results, not intentions**: counts successful PUTs only, prints `FAILED`
  per object, and exits non-zero if any failed. A re-run is safe and retries just the
  failures, since the merge is fill-only.
- **The preview's exit code counts too** — not just the write's. `import` with no flag
  exits non-zero when any row addressed nothing or any object could not be read, so
  "the preview was clean" is checkable rather than merely readable. It returned 0
  unconditionally once, which made every unaddressable row invisible to a caller testing
  `$?`, at exactly the step that precedes asking the user for approval.
- **Paced and retried**: `--pace SECONDS` (default 0.25) spaces out PUTs; each request
  has a 30s timeout and 429/5xx/network errors are retried up to 4 times with
  exponential backoff, honouring `Retry-After`. A request that never completed is
  reported as status `0` with the reason, never as a traceback.

### Building the body

Pass-through of the full GET minus server-derived fields — never an allowlist — plus the
measured write-form exceptions, the race-window protocol, the snapshot/rollback contract
and the post-write verification are all in [write-safety.md](write-safety.md). `PATCH` is
measured there too, and not used.

## Other surfaces (same contract, different I/O)

The CSV schema, `missing`/fill-only rules, and guardrails are shared. Only the
adapter changes:

| | Catalog (this script) | Site Builder |
|---|---|---|
| Address | `sku` + `field` | `domain` + `common`/`pages` + key |
| Read | admin GET (paginated) | `GET /localization/extract/{domain}` |
| Write | per-SKU `PUT` (replace item) | `POST /localization/load/{domain}` (replace whole site) |
| Auth | Basic | Bearer |
| Race guard | per-item PUT (small blast radius) | **re-extract → diff → abort if changed** (load is full-replace) |

A Site Builder adapter maps its strings to the same wide CSV, then loads a fresh
full bundle (re-extracted immediately before write) to narrow the race window.

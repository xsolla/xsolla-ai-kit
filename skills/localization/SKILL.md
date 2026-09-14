---
name: localization
description: >-
  Translates an Xsolla catalog's content into more languages. Use when a developer
  wants to "localize / translate the shop or catalog", "translate item names /
  descriptions", "translate promotions / promo codes / reward chains", "add a language /
  another locale", "make the store multi-language / multilingual", "catalog i18n /
  localisation", "export/import translations (CSV or spreadsheet)", "bulk translate", or
  hands over a translation file, or mentions a locale code (`ru-RU`, `pt-BR`); also when
  a translated name shows the wrong language or a write returns "404 Locale not found".
  Offer it proactively when a catalog exists in one language only, coverage is partial,
  a new market is named, or at go-live. Prefer this skill over ad-hoc locale writes
  whenever more than one language is in scope. Other layers belong elsewhere: the
  storefront UI and language switcher are the partner's own i18n, payment UI language is
  shop-setup, the Login widget login-styling, Site Builder text its own adapter. Covers
  16 entity types: virtual items, groups, bundles, virtual currency and its packages,
  value points, game keys, and attributes with their values — plus LiveOps: discount,
  bonus and promo-code promotions, coupons, unique catalog offers, reward chains, and
  daily login and offer chains. Not covered: upsell, subscription plans.
metadata:
  owner: u.filipau
  domain: catalog
  status: draft
---

# Localizing an Xsolla catalog

Translate catalog content (names/descriptions) into more languages, end-to-end and
safely. The work is **conversational**: the agent runs a bundled script itself via
Bash and the user only talks. Everything flows through **one CSV** — whether the AI
translates or a publisher does — so the result is auditable and editable before any
write.

## References

Detailed material lives in `references/` — load only what the current step needs:
- [`references/glossary.md`](references/glossary.md) — detecting the glossary from the
  data (signals, confidence, what to confirm), and feeding it to the translator as a
  constraint. Step 6.
- [`references/qa.md`](references/qa.md) — the full QA checklist: what `check` decides
  deterministically, what the agent must judge, and how length is used to find
  translation errors rather than to police layout. Step 8.
- [`references/write-safety.md`](references/write-safety.md) — everything about writing
  without losing data: pass-through vs allowlist, the measured `1102` write-form rules,
  why `PATCH` is not used, the race window, snapshot/rollback, post-write verification.
  Steps 10–11.
- [`references/translation-csv.md`](references/translation-csv.md) — the CSV contract:
  schema, addressing, every command, and the spec to re-implement if Python is
  unavailable.
- [`references/supported-languages.md`](references/supported-languages.md) — the bundled
  code table (26 catalog / 28 payment) and the locale rules. Step 3.
- [`references/coverage-matrix.md`](references/coverage-matrix.md) — every user-facing
  block a shop can render, whether it localizes, and which layer owns it. Step 2.

## Status

A **draft** authored by the localization SME (@u.filipau).

## When to use

This skill = **content translation across the catalog *and* LiveOps** — **16 entity
types**, all through one CSV: `name` / `description` / `long_description` (plus attribute
values, and a reward chain's `popup_header` / `popup_instruction` and step names) as
`{lang:value}` objects, via the Store **Admin API**. Use it when the developer wants to:

- **Localize / translate** the catalog, **add a language**, or make the store
  **multi-language**
- Translate **catalog** text: item, group, bundle, virtual-currency, currency-package,
  value-point and game-key names/descriptions, plus attribute names and values
- Translate **LiveOps** text: discount / bonus / promo-code promotions, coupons, unique
  catalog offers, reward chains (five fields plus every step name), and daily-login and
  offer chains — those two only while the chain is **disabled**
- **Export/import translations**, **bulk translate**, or hand a CSV to a publisher
- Fill a partial locale (`discover` shows `ru 6/18`)
- Fix a symptom: a name showing the wrong language, or their own write returning
  `404 Locale not found`

**Out of scope** — name the owner, offer only this skill's own half, and **never answer
one of these by starting a catalog export:** storefront UI strings and the language-switcher
control = the partner's own frontend i18n; payment UI language (`settings.language` on
the token) → `shop-setup` for the decision, though the token itself is created in
`headless-checkout-integration`; Login widget language (`preferredLocale` on the SDK)
→ `login-setup`, widget theming → `login-styling`; Site
Builder
site text = a separate `extract`/`load` adapter (see
[translation-csv.md](references/translation-csv.md)); prices and regional availability →
`catalog-design` (`pricing.md`) — translating never changes a price. Two entity types are **not**
covered at all: `upsell` (the one LiveOps endpoint a project key cannot even read) and
subscription plans (a catalog type whose endpoint is unknown).

Full entity/field table: [coverage-matrix.md](references/coverage-matrix.md) — check the
target against it during scope.

**Restraint:** offering ≠ doing. Offer at most once per session, and treat a
deliberately single-language shop as a valid answer rather than something to re-propose.

## Prerequisites

- **Credentials** — `XSOLLA_PROJECT_ID` and `XSOLLA_PROJECT_API_KEY`, supplied any of
  three ways: in the environment, in a `.env` passed as `--env PATH`, or in a file named
  by `$XSOLLA_ENV_FILE` (`--env` wins if both are given). Obtain them via
  `merchant-setup`. Admin auth = Basic `base64(project_id:api_key)`.
- **`XSOLLA_MERCHANT_ID`** — optional, but worth having for two separate reasons: it is
  tried as an auth fallback for calls a project key cannot make, and glossary detection
  uses it to read the project's own name (`/merchant/v2/projects/{id}`, which refuses a
  project key). Without it, step 6 loses one glossary signal and degrades quietly —
  [glossary.md](references/glossary.md).
- **A populated catalog** (`catalog-design` / Phase 0), or there is nothing to translate.
- **Python 3.6+**, standard library only — nothing to install, no virtualenv. If Python
  is unavailable, implement the
  [translation-csv.md](references/translation-csv.md) contract in the user's stack.

Credential handling worth knowing, so a failure is recognisable: quotes and an `export `
prefix are tolerated; a malformed project id is reported up front rather than surfacing
later as an unexplained `401`; and an explicit `--env` file **overrides** the ambient
environment, printing which keys it overrode (never their values). That last one is why
a stale `export XSOLLA_PROJECT_ID` in the caller's shell cannot redirect a write to the
wrong project.

## The flow (agent runs the script; user converses)

Every command below is [`scripts/catalog_i18n.py`](scripts/catalog_i18n.py), run via
Bash with the path taken from this skill's base directory. This SKILL.md contains no
HTTP of its own — the argument for keeping the destructive write in reviewed code rather
than in prose is
[translation-csv.md](references/translation-csv.md#why-a-script-and-not-http-in-prose).

1. **Trigger / offer** (see When to use). A neighbouring-layer request stops here and
   is routed.

2. **Discovery / scope (data-driven).** Run `catalog_i18n.py discover` — it lists which
   entity types exist and the per-locale coverage of each. Cross-check what the user
   asks for against
   [coverage-matrix.md](references/coverage-matrix.md) — capability ≠ tool support, and
   a couple of surfaces Xsolla can localize are still out of reach here. Offer
   only types that exist (no groups → don't propose groups) — but **read the output for
   failures, not just for names.** A list that failed prints `(list failed HTTP n)`
   while an absent one prints `0 — skip (not offered)`, and `discover` **exits 0
   either way**. Treating the first as the second drops that entity from scope for the
   whole run, and nothing downstream ever mentions it again. If a list failed, say so
   and retry before agreeing the scope. Two decisions come out:
   - **Which entity types are in scope.** The answer becomes `--entity` in step 4. The
     export default is `items` alone, so any type the user accepted and you leave out
     of that flag is silently never localized.
   - **What is already covered.** A requested locale already at full count → say so and
     stop; no export, no translation. Partially covered (`ru 6/18`) → offer to fill just
     the gaps (`export --missing`).

3. **Target languages.** Validate every code against
   [supported-languages.md](references/supported-languages.md) **before the export** —
   an invalid one (`pt-PT`, `en-GB`) is not a catalog locale and would 404 the whole
   write. Source defaults to `en`; confirm it only when step 2's coverage implies the
   catalog was authored in something else — `discover` reports coverage, not
   authorship, so read it off the numbers (`en 0/18 · de 18/18` means German is the
   source) and then pass `export --source <loc>`. "All supported" means 26
   catalog locales (not the 28 payment ones) — propose markets rather than the list.

4. **Create the CSV — the single source of truth.**
   `export out.csv <locales> --entity <the types agreed in step 2> [--source <src>] [--missing]`
   The file carries existing translations too, so filled and empty cells are visible
   side by side. From here on the script owns the file; the model never serializes it.
   Unlike `discover`, `export` **exits non-zero** and prints `INCOMPLETE` when a list
   fails, and warns when a listing is shorter than the total the server reports. Check
   that before translating anything: `exported 0 rows` from a failed read is
   indistinguishable from a catalog that is already fully translated.

5. **Choose the translation path:** AI translates · prepare the CSV for the publisher
   to fill · ingest the user's own CSV (`merge`). Combining them is fine, but **the
   order is fixed: `merge` the partner's file first, then `batch` what is still
   empty.** `batch` only lists rows missing that locale, and that is the whole reason
   the AI cannot overwrite a human translation — `fill` writes whatever it is handed,
   with no fill-only guard of its own.

6. **Glossary detection (AI path).** Before the first batch, derive the glossary from
   the data rather than interrogating the user, and pass it to the translator as a
   **constraint**, not as a post-hoc filter. Procedure, signals and confidence rules:
   [references/glossary.md](references/glossary.md). Re-run it whenever new ids enter
   the working set mid-flow.

7. **Translate.**
   - **AI:** loop `batch` → translate → `fill` until `remaining` is 0, injecting the
     glossary into **every** batch (batches are separate calls; the constraint does not
     carry over). Tone comes from the already-translated locales, not from a question.
     Prefer the most natural *and shortest* grammatical rendering: translate, do not
     paraphrase, and add no words the source does not have. `fill` exits non-zero
     listing every translation it discarded — the cells that did fill are saved, so
     re-send just those, from a fresh `batch`.
   - **Publisher:** hand over the CSV and stop — this branch is **asynchronous**, and
     the session usually ends here. Say plainly what you are waiting for (the same file,
     target columns filled, other columns untouched) and who agreed to approve the
     import, because that answer has to survive the gap.

     **Resuming when the file comes back** — re-enter at `merge`, not at step 1: load it
     with `merge` (fill-only; it reports addresses it cannot find rather than inventing
     them), `batch`/`fill` anything still empty, then step 8 QA on everything. Re-run
     `discover` too: the catalog has had days to drift, so expect step 10's conflict
     path to be the normal case rather than the exception, and an id the partner
     translated may no longer exist.

8. **QA (always, on AI *and* human translations).** Deterministic `check` plus your own
   semantic review — the two catch different classes of error, and the full checklist
   with what belongs to which is in
   [references/qa.md](references/qa.md). `!` is blocking: fix and re-run until clean.
   One `!` is **not** a cell to edit: if `check` blocks because the **source column**
   looks reordered (a non-`en` column first while `en` sits further right), no amount of
   re-translating clears it — put the source column first, or pass `--source <loc>` to
   say which column really is the source. The same guard refuses the write in step 10,
   so it cannot be skipped by going straight to `import`.

9. **Offer the user a review.** Ask whether they want to look at the finished CSV
   before anything is written. If they do, hand it over and take their edits back the
   way they prefer (`merge`, or direct edits to the file). Then **re-run only the
   affected steps** for the touched rows — QA at minimum, glossary detection if new ids
   appeared. This is a review of translations, not the write approval; that is step 10.

10. **Preview, approve, then write.** Four phases, in this order: preview → approve →
    write → resolve conflicts.

    **Preview.** `import` (no flag) prints the exact plan and writes **nothing**. Its
    first line names the target (`target: project 314067  [preview]`). Show the plan
    before asking; if it is too long to quote in full, summarise — but keep verbatim
    **the target project id**, the translation and object counts, the locales, and
    **every `!!` line**. Dropping the project id from a summary is how an approval stops
    covering the thing that matters most. Two marks in that plan are stops:
    - **`!!`** — the write would drop fields. Resolve it before asking for approval.
    - **`‼ BLOCKED`** — the object cannot be written at all right now (an active chain)
      and has already been excluded from the plan and the counts. Say what including it
      would take, rather than presenting it as translated.

    A non-zero exit from the preview means rows addressed nothing or an object could not
    be read; both are named above the summary. Clear them first — a plan built from a
    CSV with unaddressable rows is not the plan the user thinks they are approving.

    **Approve.** Ask, and wait for an explicit yes to *that* plan.

    **Write.** `import --write` — fill-only, replace-safe, snapshot first, paced and
    retried. It
    also writes a **backup CSV of the translations that are on the server right now**,
    taken from each object's own fresh read and flushed before that object is replaced
    (`--backup PATH`, `--no-backup` to skip). That is a different thing from the JSON
    snapshot — and because its default name is timestamped at write time, pass
    `--backup PATH` when you need to name the file while asking for approval. The
    snapshot is for `restore`, machine to machine; the backup is readable
    by a person and re-importable on its own (`import <backup.csv> --overwrite`), which
    is what matters when `--overwrite` replaces someone's translation.
    Everything about how the body is built, why an allowlist is forbidden, and how to
    roll back is [references/write-safety.md](references/write-safety.md).

    **Resolve conflicts.** They surface inside this run, not before it. The catalog may have changed
    since the export, and a conflict is only visible against a read taken at write
    time — so there is nothing to show the user earlier. `import --write` re-reads each
    object immediately before that object's own PUT and compares just the fields it is
    about to replace: unchanged → written; changed → the object is **skipped**, both
    versions are printed, and the run exits non-zero. Every unconflicted object is still
    written, so one conflict never blocks the rest. Treat it as a question, not a
    failure: show both versions, and if the user wants the translation applied over
    their edit, re-run with `--on-conflict overwrite`. Detail:
    [references/write-safety.md](references/write-safety.md#race-window).

11. **Verify against the API, then report.** `import --write` reads each object back
    after its own PUT and compares it to what was *sent* (`--no-verify` opts out). On
    top of that, confirm the run:
    - `discover` → the target locale is at full count **for everything that was
      written**. A `‼ BLOCKED` object keeps reading as missing: that is the expected
      outcome of the guardrail, not a shortfall, so do not retry it or report the run
      as incomplete because of it;
    - `import` again, no flag → must plan **0 changes**.

    Then report what was **written** (successful PUTs only, never the plan; a non-zero
    exit is a failure even when most objects went through), the coverage, the snapshot
    path, and anything skipped or failed. Name every `‼ BLOCKED` object explicitly — its
    translation sits in the CSV looking finished, but the catalog never received it, and
    it stays that way until the chain is next out of service. If nothing needed
    translating, say so. Then
    say how to see it: the storefront has to request the locale (client API
    `?locale=de`) — the catalog write on its own changes nothing on screen.

    **If it went wrong, roll back.** The snapshot is the only undo — the API keeps no
    versions and a PUT replaces the object. `restore <snapshot.json>` previews and
    `restore <snapshot.json> --write` puts the captured state back. Offer it rather than
    waiting to be asked when read-back verification failed, when a partial run left the
    catalog half-translated, or when the user simply does not want the result. Two
    things to say when offering: a rollback is itself a write, so it needs the same
    explicit yes; and it reverts **everything** in that snapshot, so if only one object
    is wrong, the per-string backup CSV is the narrower instrument — replay it with
    `import <backup.csv> --overwrite`. Contract:
    [write-safety.md](references/write-safety.md#snapshot-and-rollback).

## Guardrails

Front-loading every question turns a two-minute job into an interrogation. Ask the four
below up front — five on the publisher path, which adds "who approves the import?" —
and derive or defer the rest. Two more asks come later by design: the optional
translation review (step 9) and the write approval itself (step 10), which is a yes to a
concrete plan and so cannot be given in advance.

**Ask before starting (these four change what gets written):**

1. **Which project, and which entity types in it.** Both come out of `discover`, which
   prints the project id it resolved — quote that id back when agreeing the scope, and
   confirm it if the user has more than one project or a sandbox and a live one. The
   credentials can come from the ambient environment, so the id is an input nobody chose
   explicitly. Then offer what exists and carry the answer into `--entity`; the default
   is `items` only, so this decides how much of the catalog is touched.
2. **Target languages.** Source defaults to `en`. `discover` reports coverage, not
   authorship, so confirm the source only when the numbers imply another one
   (`en 0/18 · de 18/18`) — see step 3.
3. **Who translates?** The agent, or a publisher who will hand back a filled CSV
   (→ `merge`)? If a publisher, also: who approves before import? That answer has to
   survive a gap of days (step 7).
4. **Fill-only or overwrite?** Default fill-only, which protects existing/human
   translations. Overwrite needs an explicit ask — it is the one setting that can
   destroy good work, and the backup CSV written before the first PUT (step 10) is what
   makes it recoverable, so name that file when asking.

**Derive, do not ask:**

| Guardrail | Where it comes from |
|---|---|
| **Glossary / do-not-translate** | detected from the data — entity names, agreement across existing locales, project metadata. Only genuinely ambiguous terms reach the user. [glossary.md](references/glossary.md) |
| **Register / tone** per locale | read off the already-translated locales; state the assumption with the first batch and let it be corrected |
| **UI length limits** | only if strings are space-constrained; `check --max-len N` per field, warning-only. Growth is uneven — short `name`s expand most ([qa.md](references/qa.md#length)) |
| **Fallback locale** | a storefront concern (client `?locale=`), not a catalog write |

## Common rules

- **Language ≠ currency/country.** Translation is by language code; price is by country
  (`country_iso`/IP). Never touch prices when translating.
- **Update = REPLACE (everywhere).** Item/group/bundle PUT, and Site Builder `load`,
  replace the whole object → GET/extract, merge, write the **full** state. **Never
  hand-build a body from a field allowlist.** The rules, the measured field losses and
  the write-form exceptions are [write-safety.md](references/write-safety.md).
- **`PATCH` is not used.** It exists undocumented on some entities and is forbidden or
  useless on others; the measurements and the reasoning are in
  [write-safety.md](references/write-safety.md#patch).
- **Translate text fields only — and the set is per entity, not universal.** Seven field
  names carry translatable text across the registry: `name`, `description`,
  `long_description`, `value` (attribute values), and `popup_header`,
  `popup_instruction`, `step_name` (reward chains). Which of them a given entity
  actually has is the table in
  [coverage-matrix.md](references/coverage-matrix.md) — check there rather than assuming
  a universal three, which is how a reward chain's popup text and step names went
  unlocalized. Never translate: `sku` / `external_id` / `id`, promo codes, `prices`,
  `image_url`, flags, dates, structure.
- **Fill-only by default** — never overwrite a non-empty value unless asked. Note this
  is enforced by `merge` and `import`, **not** by `fill`: see the ordering rule in
  step 5.
- **Write only with permission, after a preview.** `import` previews by default;
  writing takes `--write`, so a forgotten flag can never damage a catalog.
- **Placeholders survive:** `{name}`, `%s`/`%1$s`, `{{brand}}`, ICU must match the
  source — `check` compares ICU by argument name, so extra plural forms are fine.
- **Don't translate non-player-facing labels** (region, filter rule) by default.
- **Read ≠ write:** build the storefront from the **client** API `?locale=`; localize
  via the entity's **admin** call. Admin is not for the storefront (rate-limited, leaks
  the key).
- **Validate locale codes before writing** — an unknown locale 404s and drops the whole
  PUT. `check` reports them all and `import` refuses to start on one, so the guard
  holds even if `check` was skipped.
- **A chain can be written only while it is disabled — and never disable one to make it
  writable.** `daily_chain` and `offer_chain` answer `422/6209` while running; disabled,
  they localize like anything else. `import` detects this **at plan time**, marks the
  object `‼ BLOCKED`, excludes it from the plan and the counts, and never sends the
  doomed PUT. Taking a live mechanic away from players to translate a name is not a
  trade this skill makes or proposes: the chain is skipped, named in the report, and
  localized whenever it is next out of service for its own reasons. The full argument is
  [write-safety.md](references/write-safety.md#write-form-rules-measured-not-guessed).
- **A failed read is not an empty catalog.** `export`/`langs` exit non-zero and print
  `INCOMPLETE` when an entity list fails, and flag a listing shorter than the total the
  server reports. Never relay `0 rows` as "nothing to translate" without checking the
  exit code. **`discover` is the exception** — it reports a failed list inline
  (`(list failed HTTP n)`) and still exits 0, so there the output has to be read rather
  than the exit code, and a failed list must never be taken for an absent entity
  (step 2).

## Languages

Accept 2- or 5-letter codes on write; responses are **always** 2-letter → key and
compare by 2-letter, normalize 5→2. **One canonical variant per language**
(`pt`=`pt-BR`, `en`=`en-US`); any other regional variant (`pt-PT`, `en-GB`, `es-MX`) is
not an Xsolla locale at all — the consequence of writing one is in Common rules.
Chinese is the exception (two codes: `cn`, `tw`). The catalog list (26) ≠ the payment
list (28, +`nl`/`ms`). There is no "get languages" API — the list is bundled. Full
detail + the code table:
[references/supported-languages.md](references/supported-languages.md).

## Supported entities

**16 entity types — catalog 8 + LiveOps 8**, each verified create → localize → verify →
cleanup against a live project and rolled back afterwards. *When to use* names them; the
`entity` identifiers, the CSV schema and the per-entity write transforms are in
[translation-csv.md](references/translation-csv.md#csv-schema-wide); per-entity fields
and what Xsolla can localize but this tool cannot are in
[coverage-matrix.md](references/coverage-matrix.md) — capability ≠ tool support. The five
promotion types carry **`name` only**, narrower than older lists claim.

Three entities change how a run goes:

**Chains (`daily_chain`, `offer_chain`) — writable only while disabled**, verified both
ways on 2026-09-08. `import` excludes an active one at plan time as `‼ BLOCKED`, so a
mixed run writes the disabled chains and leaves the running ones alone. The rule, and
why this skill never disables a chain to get around it, is in Common rules.

**`reward_chain` — the value-point mechanic**, a separate LiveOps product from the daily
and offer chains, and the entity with the most localizable text anywhere in scope: five
top-level fields plus a name on every step. Steps address by `subid` (the `step_id`) with
field `step_name`, the same CSV shape attribute values use — but unlike attributes they
ride inside the chain's own PUT, so a whole chain is one write. Verified 2026-09-08.

**Not supported:** subscription plans (`405`, endpoint unknown), `upsell` (`403` — the
only LiveOps endpoint a project key cannot even read), and
personalized-catalog filter rules (readable, but not player-facing — deliberately
skipped).

Commands: `discover`, `langs`, `export`, `batch`, `fill`, `merge`, `check`, `import`,
`restore`.

## Handling a user-provided CSV

**`merge <working.csv> --from <partner.csv> [--overwrite]`**

Two rules first, because they are the ones that can destroy work:

- **The order is fixed: `merge` first, then `batch` what is still empty, then `fill`.**
  `batch` lists only rows *missing* the locale, and that is the sole reason the AI cannot
  overwrite a human translation — `fill` has no guard of its own. A batch taken before
  the merge and filled after it replaces the translator's work silently.
- **Fill-only unless `--overwrite`.** By default an existing value in the working file is
  kept and reported as `existing kept`; `--overwrite` lets the partner's file replace it.
  Ask before passing it — it is the one flag here that discards a translation someone
  already made.

Never hand-edit a partner file into place, and never feed it to `import` directly. It is
read through the same guarded reader as every other CSV, so a non-UTF-8 file, a duplicate
column name, or a semicolon-delimited export (European Excel's default) is refused with a
sentence naming the fix; Excel's trailing blank rows are ignored. A `translator` or
`notes` column is skipped and named, while a locale-shaped column that does not resolve
(`fr_CA`) stays fatal — dropping it would discard the translator's work. What `merge` handles
for you: merges by address; tolerates reordered or missing `context`
columns; treats **every** language column in the partner file as a target (a partner file
has no source column) while skipping one that matches your source; normalizes locale
codes 5→2 **and prints every rename**; **reports rather than adds** ids it cannot find
(exit non-zero); aborts on a locale that is not an Xsolla locale instead of guessing; and
flags a cell the partner translated two different ways, saying which one it used. No
improvisation: when anything is ambiguous, ask. Contract:
[translation-csv.md](references/translation-csv.md#loading-a-partners-csv).

## Common pitfalls

- **Taking the "yes" on a summary, not a plan.** Approval must be on a concrete preview
  naming the **target project**, the ids and the locales. A summary that drops the
  project id is an approval that never covered which catalog gets written.
- **Reporting the plan as the result.** Count written PUTs; a non-zero exit is a
  failure even when most objects went through (429s land exactly here).
- **Trusting `204` as proof.** It says the request was accepted, not that every field
  survived — step 11 exists for that.
- **An item's `inventory_options` or `groups` vanishing** — that is a *translation* bug,
  and it takes an allowlist body to cause: either hand-built, or `--allow-field-loss`,
  which opts back into one.
- **Sending both `en` and `en-US`** for one field → last wins, the other is lost.
- **Translating region / filter-rule names** by default — internal, not player-facing.
- **Filling a batch taken before a `merge`** — silently replaces human translations.
- **Reading a failed entity list as an absent entity.** `discover` prints
  `(list failed HTTP n)` and still **exits 0**, so a transient error looks exactly like
  "that type doesn't exist" — and the entity is then dropped from scope for the whole
  run, silently. Read the lines, not just the exit code (step 2).
- **Reporting a blocked chain as localized.** Its cells are filled in the CSV, which
  looks finished; the catalog never received them.

## Agent test

Prompt: "localize my catalog to German". Expected: `discover` → the gating questions →
`export` → glossary detection → `batch`/`fill` → `check` → `import` preview → explicit
approval → `import --write` → read-back verification.

Prompt (RU, cross-language trigger): «локализуй каталог на немецкий» — must select this
skill and follow the same flow. The description is English-only, so this checks that
matching survives the language change rather than assuming it.

## Tests and evidence

- **Script tests** — `python3 scripts/test_catalog_i18n.py`
  ([`scripts/test_catalog_i18n.py`](scripts/test_catalog_i18n.py)): offline, no network
  or credentials — it prints its own pass count. Every case is a defect that shipped or
  an invariant whose
  violation shipped. Run it after any change to the script.
- **Live verification** — every rule here was measured against project 314067, not read
  off the docs, and every object was rolled back or deleted afterwards. The evidence sits
  with the rule it justifies: per-entity dates and findings in
  [coverage-matrix.md](references/coverage-matrix.md)'s *Verified* column, the measured
  `422/1102` write forms and the whole-catalog runs in
  [write-safety.md](references/write-safety.md), and the `PATCH` measurements in
  [write-safety.md](references/write-safety.md#patch).

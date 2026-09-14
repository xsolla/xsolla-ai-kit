# Write safety

Everything about turning translated cells into API writes without losing data. The
catalog `PUT` has **REPLACE** semantics, there is no server-side undo, and the object
may have changed since it was exported — those three facts drive every rule here.

## Full state, not an allowlist

The body is built by **passing every field from the GET back through**, minus the
server-derived set — `item_id`, `project_id`, `type`, `regional_prices`, `items_count`,
`promotions`, `can_be_bought`, `can_delete`, `is_deleted`, `created_at`, `updated_at`.
Enriched read forms are normalized to what the write accepts: `content` →
`[{sku, quantity}]`, `unit_items` → minimal per-DRM form, `groups` → `external_id` list,
price `amount` → number.

**A field allowlist is forbidden.** It wipes every field it forgot, and it cannot ever
be complete — it reflects what the author knew on the day they wrote it, so a field
Xsolla adds next quarter is silently destroyed. Verified on a live item: an
allowlist-built body dropped `image_url`, `groups` (membership), `inventory_options`
(consumable/expiry), `periods`, `media_list`. Pass-through carries new fields through by
construction.

The preview flags any such loss with `!!`. `--allow-field-loss` opts back into the narrow
allowlist; it is an emergency path for when a pass-through body is rejected, and only
after reading what the `!!` line lists.

### Write-form rules (measured, not guessed)

Pass-through is not simply "send everything back". Three rules were measured on project
314067, each found as a `422 errorCode 1102` — a server-side schema rejection the
preview cannot predict:

| Rule | Why |
|---|---|
| `description` must be **present** on an item PUT even when it is `null` | omitting it → `"The property description is required"`; `{}` also 422s. Only an explicit `null` works. Any item with no description was previously unwritable. |
| `limits.recurrent_schedule` must carry **only** the keys its interval branch defines | the write schema is a `oneOf` forbidding additional properties, so computed state (`reset_next_date`, `displayable_reset_*`) and other branches' null placeholders (`day_of_month: null` on a weekly schedule) must be stripped. |
| `can_delete` is server-derived | echoing it back failed every `value_points` PUT. |

**Nine more entities carry their own rules** — all eight LiveOps types plus `game` —
measured the same way, most of them while registering LiveOps on 2026-09-08. They are
**per entity**, which is why they live in `derived` / `always_send` / `drop_if_empty` on
the registry entry rather than in the global set: the same field name is server-derived
for one entity and required for another.

| Entity | Strip | Note |
|---|---|---|
| `discount_promotion`, `bonus_promotion` | `id` | in the path, rejected in the body |
| `promocode` | `is_enabled`, `external_id`, `total_codes_count` | |
| `daily_chain`, `offer_chain` | `number_of_steps` | derived from `steps` |
| `daily_chain` | — | `type` is **required**, even though `type` is server-derived everywhere else — it is re-added via `always_send` |
| `coupon`, `unique_catalog_offer` | `is_enabled`, `external_id`, `total_codes_count` | same trio as `promocode` |
| `game` | `periods` **only when empty** | see below |
| `reward_chain` | `reward_chain_id`, `clan_type`, `value_point` | `reward_chain_id` is in the path; every step must carry its own `step_id` back, and each step's `reward` goes back minimal |

**Empty is not the same as absent.** A `game` whose `periods` is `[]` is refused with
`"Matched a schema which it should not"`, while the identical empty field on an item is
accepted. So the key is dropped **only when the collection is empty** (`drop_if_empty`),
never unconditionally — on a REPLACE write, dropping a populated `periods` would delete
the real periods. A rule that reads "strip field X" is almost always wrong; the rule is
"strip X in state Y".

A trap worth naming: the shaping step defaults `is_enabled` back in when the entity's
`keep` list mentions it, which silently re-added exactly what `derived` had just
stripped. `derived` now wins. If a 1102 keeps naming a field you already stripped, look
for something re-adding it downstream.

**A reward chain's steps ride inside its own PUT.** It is the one entity whose nested
members are not separate endpoints — an attribute's name and each value are their own
calls, but a reward chain's five top-level fields and every step name are replaced by a
single write. Three consequences, all measured 2026-09-08: the merge has to be applied
in the **write** pass as well as when planning, because the body is rebuilt from the
fresh read and anything merged only into the planning copy never reaches the server (the
first attempt returned `204` with both step names still in English); read-back
verification has to walk the steps, or a silent no-op looks like success; and the list
view omits `steps` entirely, so the object is re-read before export or there is nothing
to translate. Because the whole chain is one object, the ordinary snapshot covers it —
no raw-PUT record is needed, unlike attributes.

**A chain is writable only while it is disabled.** `daily_chain` and `offer_chain` return
`422 errorCode 6209 — "Active chain cannot be updated. Please deactivate it first"`.
That is a business rule, not a schema one, and it is about state rather than the entity
type: a **disabled** chain localizes like anything else (verified 2026-09-08). `import`
checks `is_enabled` **at plan time**, so a mixed run writes the disabled chains and
excludes the running ones from the plan and the counts instead of firing a doomed PUT.

**Never disable a chain to make it writable.** It is technically three calls and it is
still the wrong move: the chain leaves the store for the duration, and what a
disable/enable cycle does to players mid-progress is unknown — `offer_chain` carries an
`is_reset_on_completion` flag, so reset mechanics exist in there. Trading a live mechanic,
and possibly someone's streak, for a translated name is not a trade this skill makes or
suggests. Skip the chain, say so in the report, and let it be localized whenever it is
next out of service.

The write itself never flips the flag either. For the chains, `is_enabled` is passed
straight through from the read, so their state is preserved exactly. (`promocode`,
`coupon` and `unique_catalog_offer` reach the same outcome the other way: `is_enabled` is
in their `derived` list, so it is stripped from the body and the server keeps whatever it
had.)

Null values are otherwise omitted (the API rejects nulls on many fields), so the
required-even-when-null exceptions live per entity in `always_send`.

**Side-effect worth knowing:** re-sending a recurring schedule rebases its
`displayable_reset_start_date` to the next occurrence. The cadence (interval/day/time) is
preserved exactly; the window marker moves.

## PATCH

**Not used.** Measured live on 314067 (2026-09-07), and the result does not justify the
risk:

| Entity | `PATCH` with only the changed field | Notes |
|---|---|---|
| `items` | **204**, all 22 fields intact | localization object **deep-merged**: `{en,de}` → `{en,de,fr}` |
| `virtual_currency` | **204**, 23 fields intact | same |
| `value_points` | **204**, 12 fields intact | same |
| `groups` | **403** `Requested endpoint is forbidden` | no PATCH route |
| `vc_package` | **422/1102** | demands `prices` / `regional_prices` / `vc_prices` |
| `bundle` | **422/1102**, then `4517` with prices added | demands `content` too; succeeds only with a full PUT-shaped body — i.e. no gain |
| `game`, `attribute` | untested | no objects in the project at measurement time |

Deleting a locale: `PATCH {"name": {"fr": null}}` → **422**, the locale stays. PATCH
cannot remove a locale, so rollback needs a full PUT regardless.

**And it is undocumented.** The Xsolla API reference lists only `PUT` for
[bundles](https://developers.xsolla.com/api/catalog/bundles-admin/admin-get-bundle-list)
and for
[virtual items / currency](https://developers.xsolla.com/api/catalog/virtual-items-currency-admin/admin-update-virtual-currency-package);
the PATCH endpoints that do exist in the docs are for other things (value-point rewards
on items, LiveOps filter rules). Undocumented behaviour changes without notice, the
benefit covers only three of the eight catalog entities above, and the pass-through
machinery has to stay
for the rest anyway. Revisit if Xsolla documents it.

## Race window

The object can change between the export and the write — someone editing in Publisher
Account, another process, a parallel run. Since the write replaces the object, their
change would be silently overwritten.

There is no ETag / `If-Match` on these endpoints, so the window is narrowed and the
conflict is detected, not prevented:

1. **Re-read immediately before writing** — per object, right before its own write, not
   as one batch at the start of the run.
2. **Compare against the state captured at inventory time**, field by field and locale by
   locale.
   - unchanged → write it;
   - changed → **conflict**.
3. **A conflict is a question, not a failure.** Show both versions — what is in the
   catalog now (likely a human edit) and what we are about to write — and let the user
   pick: keep theirs, or apply the translation over it.
4. **Never let one conflict block the rest.** Objects with no conflict are written
   normally; conflicts are collected and reported.

`import --write` implements this: it re-reads each object immediately before that
object's own PUT, compares the fields it is about to replace against the state the plan
was made on, and skips a conflicted object (exit non-zero, both versions printed).
`--on-conflict overwrite` applies the translation over the change — pass it only after
the user has seen the conflict and chosen. The body is rebuilt from the fresh read
either way, so a concurrent edit *outside* the translated fields is carried through
rather than replaced by a stale copy.

Site Builder has the same problem with a bigger blast radius (`load` replaces the entire
site), and its contract already says **re-extract → diff → abort if changed**. The
catalog version is per object, so it can ask instead of aborting.

## Backup of the translations being replaced

Separate from the snapshot, and for a different reader. The snapshot is JSON, holds
whole objects, and exists so `restore` can put them back. The backup is a **CSV in the
same wide schema as the working file** — one row per string, one column per locale — so
a translation that is about to be replaced stays readable, diffable, and re-importable
on its own — `import <backup.csv> --overwrite` puts those strings back without rolling
back everything else. It carries the **source** column as well as the targets, because
`import` requires a source plus at least one target; a backup written with target
locales alone was refused by the very command it exists to feed.

- Written from **each object's own fresh read**, immediately before that object is
  replaced, and flushed per object. So it records what was really on the server at the
  moment of the overwrite, not what the export saw an hour earlier, and it is complete
  for everything already written even if the run dies half way through.
- `--backup PATH` places it; the default is `catalog-backup-<timestamp>.csv`.
  `--no-backup` opts out, and like the snapshot, a backup that cannot be created aborts
  the run rather than writing blind.
- It matters most with `--overwrite`, which is the only mode that destroys existing
  translations — name the backup file when asking the user to approve that.
- **Nested members are included** — a reward chain's step names are replaced by the same
  PUT, so backing up only the top-level fields would preserve half the write. The rows
  are taken from the read **before** the nested merge: the merge writes translations into
  the object itself, so a backup made after it would record what is about to be written
  rather than what is being replaced — a backup preserving nothing.
- Attributes are **not** covered by this CSV: it is written from the fresh read that
  the race-check takes, and nested name/value writes do not go through that path. The
  JSON snapshot does cover them, so they are still rollbackable — just not readable as
  a diff.

## Snapshot and rollback

There is no server-side undo and the API keeps no versions.

- `import` runs in **two passes**: it plans every object first, then writes the
  snapshot, then PUTs. The snapshot therefore covers **the whole run**, not just
  whichever object happened to be first. A single-pass version that snapshots from
  inside the write loop captures one object while replacing many — this shipped as a real
  bug; a 3-object test found it, a 1-object test cannot.
- It **aborts rather than writing** if the snapshot cannot be created
  (`--no-snapshot` to override, `--snapshot PATH` to place it).
- `restore <snapshot.json> --write` PUTs the captured state back, previewing by default.
  Verified live: byte-identical restoration.
- **Whole-catalog runs that exercised all of the above**, on project 314067, every object
  rolled back or deleted afterwards: 2026-09-02, all 8 catalog entity types created →
  localized → verified `{en,ru,de}` → cleaned up (an invalid `pt-PT` was caught by
  `check` before any write). 2026-09-07, `demodaily_1` — carrying `image_url`, `groups`
  and `inventory_options` — localized `+de`: **21 of 22 fields byte-identical**, only
  `name` gained a locale, and `restore` returned it byte-identical. 2026-09-07, the whole
  catalog to German: 36 strings across 6 populated types, `de 36/36`, re-run planned 0
  changes, and the three `422/1102` rules above were found in the process. 2026-09-08,
  the whole flow in French: **22/22 `PUT 204`**, zero fields lost, re-run planned 0
  changes, `restore` returned all 22 byte-identical.
- **Nested members are captured pre-merge.** `_merge_nested` returns a copy with the
  translations already written into its members, so snapshotting *that* captured a step
  as it was about to be rather than as it was — `restore` then re-applied the
  translation instead of removing it, while the PUT answered 204 and the rollback looked
  clean. Found on a live reward chain; top-level fields were never affected, because
  they are merged into a separate dict. Same defect, and same fix, as the backup CSV
  above: keep the read from before the merge.
- The snapshot holds **two record shapes**. A flat entity contributes its whole object,
  and `restore` rebuilds the body exactly as a write would. A nested write — attribute
  `name`, attribute `value` — has no whole object to capture, so it contributes a
  **raw-PUT record**: the endpoint plus the body that puts the pre-write state back.
  Both live in one file, so a run that mixes attributes with flat entities rolls back in
  a single `restore`. The raw record uses the same endpoint and body shape as the write
  it undoes, so every attribute write test exercises the rollback path too.

## Verify after the write

A `204` says the request was accepted, not that every field survived. The run-level check
("a second `import` plans 0 changes") catches *didn't write*; it cannot catch *wrote and
ate something*, because a lost field never reappears in the plan.

So after writing, per object:

1. Re-read it.
2. Compare against **what was sent**: every field in the request must be present in the
   response, and nothing outside the intended locale additions may differ.
3. Anything missing → re-send it, and report it.

`import --write` does this per object (`--no-verify` opts out), and a failed
verification makes the run exit non-zero even though the PUT returned `204`. Only a
field that **existed before and is gone after** counts as loss: the body legitimately
carries a couple of defaults the shaping step adds, and the server need not echo those.
Attribute PUTs are neither race-checked nor verified — nested name/value writes have no
single object to diff — and the run says so.

The snapshot is already on disk, so this diff is nearly free. One caveat when diffing
content-bearing entities: `bundle.content` and `vc_package.content` embed an **enriched
copy of the nested object's localizations**, so a snapshot taken while a nested object was
mid-change will show a false difference there. Compare the entity's own fields, and treat
`content` drift as suspect only if the nested object was not itself touched.

## Auth

Admin Basic `base64(project_id:api_key)`. The project key covers reads; some update calls
may require `merchant_id:api_key`, so the fallback order is project → merchant. Project
metadata (`/merchant/v2/projects/{id}`) needs merchant auth outright — treat it as
optional enrichment, not a prerequisite.

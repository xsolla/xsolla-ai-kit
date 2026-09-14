# listing-import — scripts

Deterministic half of the skill: validate an extraction, measure it, map it onto blocks, and
emit the write plan. The extraction itself is the agent's job — see
[`references/listing-json.md`](references/listing-json.md) for the contract between the two.

## Prerequisites

| | |
|---|---|
| Python | 3.9+. Standard library only — no install, no build, no dependencies. |
| CLI | `xsolla auth login` for the Shop Builder session. `xsolla config list` should show the sandbox merchant and project. |
| Project | A sandbox or test project. Never a partner's live project. |

## Happy path

```bash
cd scripts

# 1. the agent's extraction, checked
python3 listing_import.py validate --listing listing.json
# listing.json is valid.

# 2. what it got, and what can land
python3 listing_import.py coverage --listing listing.json

# 3. the mapping the user approves
python3 listing_import.py preview \
    --listing listing.json --structure structure.json --localization localization.json
```

Fetching the inputs:

```bash
SLUG=<landing slug>
xsolla shopbuilder get-structure    --slug $SLUG --json > structure_raw.json
xsolla shopbuilder get-localization --slug $SLUG --json > localization_raw.json
python3 -c 'import json;json.dump(json.load(open("structure_raw.json"))["data"],
    open("structure.json","w"))'
python3 -c 'import json;json.dump(json.load(open("localization_raw.json"))["data"],
    open("localization.json","w"))'
```

## The report contract

`--json` on any subcommand. `xsolla-cli` is the intended second consumer, so the keys are
stable and match [`shop-validation`](../shop-validation/README.md)'s where they overlap.

| Key | Type | Meaning |
|---|---|---|
| `ok` | bool | Nothing to fix. Same thing the exit status says. |
| `errors` | array | `{path, expected, got, value?}` — the key is `got`, not `actual`. |
| `blockers` | array | Same shape. Non-empty means **the plan must not be executed.** |
| `plan.operations` | array | Ordered. `{step, kind, field, module, block_id, page_id, path, …}` |
| `plan.unresolved` | array | Fields whose target module is not on this landing. |
| `plan.manual_follow_up` | array | Extracted, but no block field exists. |
| `plan.unverified` | array | What the run could not check. **Print it.** |

Coverage adds `extraction`, `mapping`, `delivered` and `mapping_ceiling`, each
`{filled, total, pct}`. `pct` is `null` — not `0.0` — when `total` is zero, so an empty
denominator cannot read as a failure.

Exit status: `0` clean · `1` errors or blockers · `2` bad invocation.

## Tests

```bash
cd scripts && python3 -m unittest discover -s tests -t . -v
```

139 tests, no network. The two Steam fixtures are real rather than hand-written:
`steam_listing.json` came from the live `appdetails` response for app 812140, and
`steam_structure.json` is the block spine of a landing `import-listing` actually produced. A
synthetic fixture would have agreed with whatever the mapping assumed; these disagreed twice,
and both disagreements were real bugs. See [`EVAL-LOG.md`](EVAL-LOG.md).

## Code conventions

Inherited from [`shop-validation`](../shop-validation/README.md), enforced by the same CI job:

| | |
|---|---|
| **Standard library only** | A partner, an agent and the CLI all run this with nothing installed. |
| **Python 3.9** | No `match`, no PEP 604 unions, no dict-merge operator. |
| **100 columns** | PEP 8 otherwise. Checked in CI over every `.py` under `skills/`. |
| **A docstring on every module** | Saying what it checks and, more usefully, what it misses. |
| **No `print` outside the CLI** | Library modules return data; `listing_import.py` renders it. |
| **Tests beside the code** | `tests/` mirrors the module layout; a new rule ships with its test. |

## Known limitations

- **The plan is not executed by this code.** It emits operations; the agent runs the CLI. So
  nothing here can guarantee the read-back actually happened — that discipline lives in
  [`SKILL.md`](SKILL.md), not in a script.
- **No diff against current values.** An operation that would write what is already there
  still appears in the plan, which inflates the operation count on a re-run.
- **`L:` reference existence is checked only if `--localization` is passed**, and even then
  only that the id exists — not that the string is non-empty in the target locale.
- **Nine of eleven patch paths are `schema`-confidence, not `confirmed`.** They come from the
  editor's own field schemas, not from a watched write. Since a patch to a non-existent path
  returns `ok: true` and does nothing, these fail silently if wrong. Confirming them needs a
  write-and-read-back round on a throwaway landing per path; that has not been done.
- **The field availability table is per storefront, not per page.** `PARTIAL` means "ask the
  page", and nothing here can ask it.
- **Coverage counts fields, not quality.** A badly converted description counts the same as a
  clean one, and every field is weighted equally — missing `screenshots` scores the same as
  missing `tags`, which no partner would agree with.
- **The block-schema field names are not validated against Shop Builder.** If a module
  reships with a renamed field, the mapping goes stale silently. `shop-validation`'s
  `scripts/data/block-schemas.json` has the same problem and no owner is agreed for either.

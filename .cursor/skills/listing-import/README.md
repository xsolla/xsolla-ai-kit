# listing-import — scripts

Extract a public store listing, measure it, map it onto blocks and catalog entities, and emit
the write plan. Three extractors (Steam, Google Play, Apple App Store) plus the deterministic
half that everything downstream shares. See
[`references/listing-json.md`](references/listing-json.md) for the contract between them.

Nothing here makes a network request. Each extractor takes content the caller already
fetched, which is what keeps the tests offline and stops a rate limit from looking like a
parser bug.

## Prerequisites

| | |
|---|---|
| Python | 3.9+. Standard library only — no install, no build, no dependencies. |
| CLI | `xsolla auth login` for the Shop Builder session. `xsolla config list` should show the sandbox merchant and project. |
| Project | A sandbox or test project. Never a partner's live project. |

## Happy path

```bash
cd scripts

# 1. what to fetch for this store URL
python3 listing_import.py fetch --url 'https://store.steampowered.com/app/812140/'
curl -sS 'https://store.steampowered.com/api/appdetails?appids=812140&l=english' > raw.json

# 2. extract, then check it. rights_confirmed comes back false: ask the partner.
python3 listing_import.py extract --input raw.json \
    --url 'https://store.steampowered.com/app/812140/' > listing.json
python3 listing_import.py validate --listing listing.json
# listing.json is valid.

# 3. what it got, and what can land
python3 listing_import.py coverage --listing listing.json

# 4. the mapping the user approves
python3 listing_import.py preview \
    --listing listing.json --structure structure.json --localization localization.json

# 5. the catalog commands for the in-app items
python3 listing_import.py catalog --listing listing.json
```

Google Play is fetched as HTML rather than JSON, and the App Store needs the page as well as
the API — `fetch` says which, per URL.

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
| `plan.catalog_operations` | array | In-app items as virtual-item creates. |
| `plan.catalog_warnings` | array | What a human has to settle about them. |

Coverage adds `extraction`, `mapping`, `delivered` and `mapping_ceiling`, each
`{filled, total, pct}`. `pct` is `null` — not `0.0` — when `total` is zero, so an empty
denominator cannot read as a failure.

Exit status: `0` clean · `1` errors or blockers · `2` bad invocation.

## Tests

```bash
cd scripts && python3 -m unittest discover -s tests -t . -v
```

222 tests, no network. Every fixture is real, not hand-written: the live `appdetails`
response for Steam app 812140, the live iTunes lookup for id 529479190, a trimmed excerpt of
the live Play page for `com.supercell.clashofclans`, and the block spine of a landing
`import-listing` actually produced. A synthetic fixture would have agreed with whatever the
code assumed; these disagreed five times, and every disagreement was a real bug or a wrong
assumption. See [`EVAL-LOG.md`](EVAL-LOG.md).

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

- **Nothing here executes.** It emits operations and renders commands; the agent runs the
  CLI. So no script can guarantee the read-back happened — that discipline lives in
  [`SKILL.md`](SKILL.md).
- **Most patch paths are `schema`-confidence, not `confirmed`.** Only `key_art` and
  `screenshots` have been watched to land. The rest come from the editor's field schemas, and
  since a patch to a path that does not exist returns `ok: true` and changes nothing, a wrong
  one fails *silently*. Confirming each needs a write-and-read-back on a throwaway landing.
- **The overflow component has no id.** `plan.py` emits the HTML and the target path; the
  `description` block's component ids are generated, so the writer has to read the block
  first. Nothing here checks that it did.
- **No quantities, ever.** No storefront publishes what is inside an in-app item, so nothing
  can create a correct currency package or bundle. Everything is a virtual item flagged for
  review, and no amount of better parsing changes that.
- **In-app item lists are partial by source.** Steam gives editions and DLC only; Apple's
  page shows roughly ten with duplicate names; Play gives a price range and no names.
- **No `consumable` flag** exists on catalog item create or update, and most mobile in-app
  purchases are consumables. Filed, not worked around.
- **`extract_play.py` reads markup, not a contract.** It is the extractor that will break: a
  renamed class costs one field, declared in `not_found`. The other two read JSON APIs.
- **`extract_appstore.py` rewrites thumbnail URLs** to `2048x2048bb` using an undocumented
  Apple suffix. If Apple stops honouring it the images 404, and nothing here notices.
- **A re-run produces the same catalog SKUs**, so the create calls conflict. Deliberate:
  silently updating a live priced item is worse than a visible error.
- **`L:` reference existence is checked only if `--localization` is passed**, and even then
  only that the id exists — not that the string is non-empty in the target locale.
- **Coverage counts fields, not quality.** A badly converted description counts the same as a
  clean one, and every field weighs the same — missing `screenshots` scores like missing
  `tags`, which no partner would agree with.
- **Field availability is per storefront, not per page.** `PARTIAL` means "ask the page", and
  nothing here can ask it.
- **The block field names are not validated against Shop Builder.** If a module reships with
  a renamed field the mapping goes stale silently — the same problem
  `shop-validation/scripts/data/block-schemas.json` has, with the same lack of an owner.

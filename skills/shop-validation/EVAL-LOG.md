# Eval log

Every run behind the metrics, with what it was, what came back, and what needed a human.
Recorded 2026-09-10 against the sandbox Shop Builder project (merchant `936601`, project
`314771`), authenticated with `xsolla auth login`. No landing outside that project was touched,
and nothing was published.

## Metrics

| Metric | Target | Result |
|---|---|---|
| **Ported checks** — % of MCP validations available in the kit | 100% | **100%** of the portable set: 66 of 77 identified behaviours, with all 11 exclusions named and reasoned in [`INVENTORY.md`](INVENTORY.md) — 8 are absent from the prototype, 3 are MCP transport or tool-argument concerns with no equivalent surface here |
| **Detection** — seeded errors caught | 100% | **100%** — 5 of 5 seeded shops, each defect named exactly once in the right category, plus 10 of 10 seeded defects in the unit suite |
| **False positives on known-good shops** | 0 | **0** structural errors across 5 known-good shops: 80 blocks, 730 `L:` references, 4 off-page blocks |
| **Validation runtime per shop** | report | **42–60 ms** per shop, median 47 ms, for 13–27 blocks. Cold interpreter start included; no network in the validation step itself |

One qualifier on the false-positive number, because it is the one worth reading carefully.
Zero counts `shape`, `reference` and `site` errors — the categories that block a write. The
known-good shops also produced **53 `content` errors**, and every one is a real editor-rule
violation: an enabled control with no value. They break down as 30 enabled social links with
empty urls, 15 buy buttons with no SKU, 5 cloud-gaming buttons with no game id, and 3 lightbox
buttons with no video url. Spot-checked against the live data: the sampled path holds
`gameId: null` on an enabled button. These are unconfigured template placeholders, not defects,
which is why they are a separate category rather than ten faults on a new shop.

## Known-good shops — runs 1–5

None of these was built for this test. Read-only: structure and localization fetched, then
walked.

| # | Shop | Pages | Blocks | Off-page | `L:` ids | Runtime | shape / reference / site | content |
|---|---|---|---|---|---|---|---|---|
| 1 | `xsollacli-shopbuilder-test-store` | 1 | 14 | 3 | 91 | 60 ms | **0** | 5 |
| 2 | `steamtest-173641` | 1 | 13 | 0 | 129 | 49 ms | **0** | 9 |
| 3 | `acodyssey-174331` | 1 | 13 | 0 | 129 | 47 ms | **0** | 9 |
| 4 | `aikit-validation-testbed` | 2 | 27 | 0 | 254 | 48 ms | **0** | 20 |
| 5 | `aikit-known-good-09101542` — a landing created for this run and left untouched | 1 | 13 | 0 | 127 | 45 ms | **0** | 10 |

Shop 1 exercises the second enumeration pass: 3 of its 14 blocks are off-page, reachable only
by fetching each id in the site-level `blocks[]` that no page carries. Shop 4 is the only
multi-page shop available. Shop 5 is what the platform produces from `add-page` and nothing
else, so its 10 content errors are the template's own unconfigured state.

## A sixth shop, excluded — run 6

| # | Shop | Result |
|---|---|---|
| 6 | `nashit-gemforge-store` | **9 `site` errors.** Its site-level `blocks[]` names 9 ids that no page carries and that `get-block` cannot resolve — the site document references blocks that no longer exist. Each of the 9 was fetched individually to confirm. |

Excluded from the known-good set because it is not known-good: this is a real pre-existing
defect in a real shop, found by the walk. Nothing else in the walk sees it, and no per-block
check can — it is the case the site-level pass exists for.

## Seeded-error shops — runs 7–11

Five landings created from the same template, one distinct defect seeded in each through the
CLI, one per error category. Every seed was verified present in the re-fetched structure
before the walk ran, so a pass cannot be a seed that never landed.

| # | Shop | Seeded defect | Named? | Where |
|---|---|---|---|---|
| 7 | `aikit-seed1-09101543` | `values` replaced with a JSON string | **yes**, once | `shape` · `values` · expected `object`, got `string` |
| 8 | `aikit-seed2-09101543` | `values.title.id` pointed at an `L:` id with no localization entry | **yes**, once | `reference` · expected an entry in the store, got `missing` |
| 9 | `aikit-seed3-09101543` | a non-existent id appended to the site-level `blocks[]` | **yes**, once | `site` · `blocks` · got `block_not_found` |
| 10 | `aikit-seed4-09101543` | a gallery slide's `img` emptied while its type stays `image` | **yes**, once | `content` · `values.slides.0.image.img` · expected `an image`, got `empty` |
| 11 | `aikit-seed5-09101543` | faulty custom-block source | **yes** — see runs 12–15 | code violations, not a site error |

Two things worth recording from the seeding itself:

- **The API accepted every one of the four block and site seeds.** A block whose `values` is a
  string, a reference to a localization id that does not exist, a dangling id in the site
  document: all written without complaint. That is the gap this gate stands in.
- Each walk reported the seeded error **and nothing else structural** — content stayed at the
  template's 10, plus 1 for shop 10's gallery. No cascade, no collateral.

## The code path — runs 12–15

| # | Run | Result |
|---|---|---|
| 12 | `ai-code` on source with six seeded faults, before any write | **6 violations**: `forbidden-import`, `export-default-class`, `undeclared-text-fields`, `missing-text-fields`, `use-controls-object-arg`, `control-factory-object-arg`. Exit 1 |
| 13 | `create-custom-block` with that same source, written anyway | **Rejected by the platform**: `Compilation failed` — *"The symbol `localizedText` has already been declared"*. The server's own rejection is rule 1 of the six, arrived at after a round trip |
| 14 | `ai-code` on a variant that compiles but breaks at runtime | **4 violations**. Exit 1 |
| 15 | The same variant created, then fetched with `get-ai-block` and validated | **5 violations** — the four again, plus `empty-text-refs`. The block was accepted and is live on the shop with nothing on it editable |

Run 13 is the useful one: the gate is not redundant with the server. It named the fault the
server would reject *and* five faults the server never got far enough to see. Run 15 is the
documented CLI gap in action — `create-custom-block` cannot declare `textFields`, so a block
using canvas text always lands with `textRefs: {}`.

## Suites — runs 16–17

| # | Run | Result |
|---|---|---|
| 16 | `python3 -m unittest discover -s tests -t .` | **142 tests, 0 failures, 0.01 s.** Includes one test per documented false-positive trap (14) and one per seeded defect (10) |
| 17 | `./live_check.sh --yes` | **15 of 15 checks passed.** Creates a throwaway landing, walks the untouched template, seeds three defects through the CLI, checks three write constraints locally, deletes the landing |

## Manual interventions and failures

Recorded because a log with none of these is not a log.

- **5 of 10 CLI fetches failed on first attempt** while fetching the seeded shops, with no
  usable error. A retry loop of 3 fixed all of them. Anything scripting these commands needs
  retries; `live_check.sh` fetches one shop at a time and has not hit it.
- **My own harness misread three successful writes as rejections.** The CLI's `--json` output
  for `update-block` was parsed with an over-strict check. The writes had landed; re-fetching
  the structure and inspecting the seeded path is the only trustworthy confirmation, and that
  is now what the log above is based on.
- **`delete-website` blocks on a confirmation prompt** unless `--force` is passed. The first
  `live_check.sh` run failed its cleanup step for exactly this reason, leaving a landing
  behind. Fixed in the script; the stray landing was deleted by hand.
- **The gallery content check needed narrowing to `blockVersion == 2`** to match where the
  editor applies it, after the seed landed on a v2 gallery.
- **No Loom yet.** The end-to-end recording the common DoD asks for is a human step; runs 7–11
  and 17 are the script it should follow.

## Reproducing this

The seeded shops are left in place on purpose — deleting them would make the detection numbers
unreproducible. To re-walk any of them:

```bash
cd skills/shop-validation/scripts
SLUG=aikit-seed1-09101543
xsolla shopbuilder get-structure    --slug $SLUG --json > /tmp/s.json
xsolla shopbuilder get-localization --slug $SLUG --json > /tmp/l.json
python3 -c 'import json;json.dump(json.load(open("/tmp/s.json"))["data"],open("/tmp/structure.json","w"))'
python3 -c 'import json;json.dump(json.load(open("/tmp/l.json"))["data"],open("/tmp/localization.json","w"))'
python3 validate_shop.py site --structure /tmp/structure.json --localization /tmp/localization.json
```

To clean them up when the review is done:

```bash
for N in 1 2 3 4 5; do xsolla shopbuilder delete-website --slug aikit-seed$N-09101543 --force; done
xsolla shopbuilder delete-website --slug aikit-known-good-09101542 --force
```

# Eval log

Every run behind the metrics, with what it was, what came back, and what needed a human.
Recorded 2026-09-10 against the sandbox Shop Builder project (merchant `936601`, project
`314771`), authenticated with `xsolla auth login`. No landing outside that project was touched,
and nothing was published.

## Metrics

| Metric | Target | Result |
|---|---|---|
| **Ported checks** — % of MCP validations available in the kit | 100% | **100%** — 75 of 78 identified behaviours. The 3 not ported are MCP transport and tool-argument concerns with no equivalent surface here. Every shop-validation behaviour in the Site Builder source is ported; see [`INVENTORY.md`](INVENTORY.md) |
| **Detection** — seeded errors caught | 100% | **100%** — **10 of 10** seeded shops across two independent rounds, each defect named exactly once in the right category with no collateral, plus 10 of 10 seeded defects in the unit suite. 186 unit tests total |
| **False positives on known-good shops** | 0 | **0** structural errors across **10** known-good shops in two independent rounds: **159 blocks, 1,492 `L:` references**, 4 off-page blocks, landing types `topup`, `store` and `sellingpage`, one two-page site, one site carrying a custom block |
| **Validation runtime per shop** | report | **41–64 ms** per shop, median 48 ms, for 13–27 blocks, measured over 20 shops. Cold interpreter start included; no network in the validation step itself |

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
| 16 | `python3 -m unittest discover -s tests -t .` | **186 tests, 0 failures, 0.01 s.** Includes one test per documented false-positive trap (14) and one per seeded defect (10) |
| 17 | `./live_check.sh --yes` | **15 of 15 checks passed.** Creates a throwaway landing, walks the untouched template, seeds three defects through the CLI, checks three write constraints locally, deletes the landing |

## Re-verification against the complete source — runs 18–21

The first pass worked from a partial source extract. On 11 Sep 2026 the complete Site Builder
source became available and the whole port was re-checked against it.

| # | Run | Result |
|---|---|---|
| 18 | Diff every module this port was derived from against the full source | **All current but one.** The native envelope, field schemas, federated walk, nine code rules, footer, gallery and custom-button checks are byte-identical (one import-path change only, no behaviour). `utils/validations.ts` **differs** — it had been rewritten from regexes to real url parsing |
| 19 | Port the eight per-module checks and wire them into the walk | **8 of 8 ported**, plus one auth-relevance helper found alongside them. Suite grows 142 → **186 tests**, all passing in 0.011 s. Upstream's own edge cases are mirrored: a string id rejected where a number is required, `0` accepted as a number, an empty `chains` list passing, a `unit` store item skipped |
| 20 | Re-walk the 5 known-good shops with the eight new checks active | **0 structural errors, unchanged.** Content findings 53 → **55**: the newly ported lead check named two enabled lead-platform rows with empty urls on `xsollacli-shopbuilder-test-store`. Verified against the raw block — `platforms.enable: true` with two enabled items whose `url` is `""`. A second lead block on the same shop has `enable: false` and is correctly left alone |
| 21 | Re-run the whole suite after fixing what run 19 exposed | **186 passing.** Porting the offer-chain check failed six tests, all one cause: the invented offer-chain block in the known-good fixture carried no `offerChainId`, which a real one must have. The fixture was wrong, not the check |

### Three things this port had wrong

Recorded plainly, because they were found by getting the real source rather than by testing.

1. **The url rules were a version behind.** The ported regex implementation accepted
   protocol-relative `//host`, urls containing whitespace or backslashes, and hosts with no real
   TLD — all of which the current implementation rejects. It also accepted `.ogg`, `.mov` and
   `.m4v` video files where the uploader takes only `.mp4` and `.webm`, and rejected the `:` a
   page path may now contain. Fixed; the rejection cases are now tests.
2. **The version rule was a heuristic.** It could not tell an unversioned module from a real
   version 1, because the schema tool reports `maxVersion` as "last version **or 1**". The block
   metadata answers it outright: ten modules carry a versions list, everything else is exempt.
   The heuristic and its "unjudged" state are gone.
3. **The known-good fixture was not known-good.** It contained an offer-chain block the editor
   would reject. For one commit, the fixture that exists to prove there are no false positives
   held a block with a real defect.

### And one claim that needed softening

The earlier note that "one shipped schema is stricter than the API" read as a generator bug. It
is not. The MCP's schema genuinely requires `quillWrapper` on a rich-text field, and the
generated schemas are faithful to it. The disagreement is between the MCP and the batch API,
which accepts a create without it — verified live. These scripts gate the CLI path, so the
advisory behaviour stays, but the framing was wrong.

## Second round — ten shops built for it — runs 22–31

The first round reused existing sandbox landings for the known-good set. This round builds all
ten from scratch on the current code, with all 75 checks active, and varies the known-good five
on purpose so the set is not five copies of one template.

### Known-good — runs 22–26

| # | Shop | Built as | Blocks | `L:` refs | Runtime | shape / reference / site | content |
|---|---|---|---|---|---|---|---|
| 22 | `aikit-kg1-09111110` | `topup`, one page | 13 | 127 | 64 ms | **0** | 10 |
| 23 | `aikit-kg2-09111110` | `store` type | 13 | 127 | 56 ms | **0** | 10 |
| 24 | `aikit-kg3-09111110` | `sellingpage` type | 13 | 127 | 52 ms | **0** | 10 |
| 25 | `aikit-kg4-09111110` | `topup`, **two pages** | 26 | 254 | 55 ms | **0** | 20 |
| 26 | `aikit-kg5-09111110` | `topup` + a **clean custom block** | 14 | 127 | 49 ms | **0** | 10 |
|  | **Total** |  | **79** | **762** |  | **0** | 60 |

All 60 content findings are the four placeholder kinds the template ships with: 30 enabled
social rows with an empty url, 18 buy actions with an empty SKU, 6 lightbox buttons with no
url, 6 cloud-gaming buttons with a null game id.

Two results worth calling out:

- **Run 26 is the counterpoint to the `textRefs` gap.** A custom block created through the CLI lands
  clean *when its source uses no canvas text* — validated before the write and again after
  fetching it back, clean both times, and routed as the `custom` family. The gap only bites blocks
  that call `localizedText()` or render a `TextEditor`.
- **Run 25 reports its own blind spot.** On the two-page site, page reachability came back
  *unverified* rather than clean: the structure carries no navigation to check the paths
  against. That is the intended behaviour — an unanswerable question must not read as a pass.

### Seeded — runs 27–31

The same five defect classes as the first round, one per shop, every seed re-fetched and
confirmed present before its walk ran.

| # | Shop | Seeded defect | Named | Categories |
|---|---|---|---|---|
| 27 | `aikit-sd1-09111110` | a block's whole `values` replaced with a JSON string | **yes**, once | `shape` 1 · content 10 |
| 28 | `aikit-sd2-09111110` | title pointed at an `L:` uuid with no entry in the store | **yes**, once | `reference` 1 · content 10 |
| 29 | `aikit-sd3-09111110` | a non-existent id appended to the site-level block list | **yes**, once | `site` 1 · content 10 |
| 30 | `aikit-sd4-09111110` | a gallery slide's image emptied, its type left as `image` | **yes**, once | content 11 |
| 31 | `aikit-sd5-09111110` | custom-block source carrying seven rule violations | **yes** — below | content 10 |

Run 31 in two steps, the same shape as the first round and one violation richer:

- The source gate named **7** violations before any write: `forbidden-import`, `export-default-class`, `undeclared-text-fields`, `missing-text-fields`, `use-controls-object-arg`, `control-factory-object-arg` and `text-control-with-localized-text`.
- Submitted anyway, the platform **rejected** it for exactly one of the seven — *Compilation
  failed: the symbol "localizedText" has already been declared*. A variant with only that one
  fixed was **accepted**, and landed with an empty `textRefs`: 5 violations on the stored block,
  including `empty-text-refs`.

**Combined across both rounds: 20 shops · 10 known-good with 0 structural errors · 10 seeded
with 10 of 10 defects named.**

## Manual interventions and failures

Recorded because a log with none of these is not a log.

- **The CLI is flaky enough to need retries everywhere, and it bit this round twice.** One
  create-website and one add-page silently did not take, and my loop printed "created" without
  checking — so one shop did not exist and another had no page. A third call failed with
  `context deadline exceeded` while bootstrapping the publisher session. All recovered on retry. Same
  lesson as the line below, which I had not applied: **verify by re-reading the resource, never
  by trusting the command's own output.**
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
- **The eight per-module checks were reported as unportable for one commit,** on the basis that
  their source was missing. That was true of the extract and not of the product, and the wording
  was corrected before the full source arrived. Worth not repeating: say "I do not have this"
  rather than "this does not exist".
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

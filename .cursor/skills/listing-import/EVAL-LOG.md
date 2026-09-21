# listing-import — evaluation log

Provenance for every claim in [`SKILL.md`](SKILL.md). Live work was done on merchant
`936601`, project `314771`, authenticated with `xsolla auth login`, sitebuilder API
`v2.25.0`. **Nothing was published, and no landing was created or written to** — every live
call in this round was a `GET`.

## Metrics

| Metric | Target | Result |
|---|---|---|
| Field coverage — extraction, Steam | ≥ 80% | **90.9%** (10/11) |
| Field coverage — extraction, App Store | ≥ 80% | **88.9%** (8/9) |
| Field coverage — extraction, Google Play | ≥ 80% | **88.9%** (8/9) |
| Field coverage — mapping, all three | — | **100%** — every extracted field has a destination |
| Field coverage — delivered, Steam | ≥ 80% | **90.9%** (10/11) |
| Field coverage — delivered, Play / App Store | ≥ 80% | **72.7%** (8/11) |
| Unit tests | pass | **343 pass**, no network, 0.09 s |
| Sources extracted | 3 | **3** |
| Sources with a working server-side import | 3 | **1** (Steam) |
| Manual interventions, Steam dry run | ≤ 2 | **2** (see below) |
| Time, URL → mapping preview | report | **~4 s** of tool time; ~0.4 s of it API latency |
| Time, URL → written shop | report | **107 s** for Steam; asset round trips dominate |
| Games per source | ≥ 3 | **1** (Brawlhalla). A second, Minecraft, was run on the App Store outside this log |
| Run success — no structural fix | ≥ 8/10 | **0 of 3 on first pass.** Every cause is fixed; a clean re-run has not been done |
| Manual interventions per run | ≤ 2 | **2** — the rights question and the confirmation, both by design |

Extraction clears the target on all three sources. Delivered sits below it for Play and the
App Store for a reason neither this skill nor Xsolla controls: neither storefront publishes
`key_art` or `tags` at all. Those are excluded from each source's own extraction denominator
so they are not scored as parser failures, but they still count against the eleven-field
target list, which is what `delivered` measures.

The earlier version of this log reported a **7/11 = 64% ceiling** on delivery and called it a
gap in the block set. That was wrong — it is recorded below with the other corrections.

## Live runs

| # | Call | Target | Result |
|---|---|---|---|
| 1 | `get-listing` | `store.steampowered.com/app/812140/` | `200` — `{developer, icon, title}`, 433 ms |
| 2 | `get-listing` | `play.google.com/.../com.supercell.clashofclans` | `400` `request_body_validation_error`, 333 ms |
| 3 | `get-listing` | `apps.apple.com/us/app/clash-of-clans/id529479190` | `400`, identical body, 340 ms |
| 4 | `get-listing` (no flags) | — | Refused: `required flag(s) "slug", "target", "type" not set` |
| 5 | `list-websites` | — | 23 landings on the project, incl. two prior `sellingpage` imports |
| 6 | `get-structure` | `steamtest-173641` | 1 page, 13 blocks — the import's real output |
| 7 | `appdetails` (Steam public API) | app 812140 | `200` — the extraction source for the fixture |

Request ids for the two `400`s, for the ticket: `b3e6d474f94f3852ad7d190b6a1139be` (Play),
`c74564c9b7b935dab0aec1d058e0c118` (App Store).

Run 6 is the more useful one. The documented claim was "~13 blocks including a gallery of the
real store screenshots"; the actual spine is `header · leadGameSales · description · packs ·
packs · description · bento-grid · bento-grid · gallery · packs · requirements · faq ·
footer`. That confirms the count and, more usefully, shows what is **absent** — no `sidebar`
and no `lead`, which is why `platforms` and `developer` report as unresolved on a default
import rather than being written somewhere approximate.

## The ceiling that was not real

The first round reported that four target fields — `genres`, `tags`, `age_rating`,
`iap_items` — had no destination, and concluded that landing delivery was capped at 7/11 =
64%. It was presented as a product gap to escalate.

It was a measurement artefact. Only *structured native block fields* were being counted. Once
"copied" is read as "the content reaches the shop", all four land:

- `genres`, `tags`, `age_rating` → one appended TEXT component in the `description` block.
  Copy rather than a typed field, and a reader of the finished page cannot tell which one
  delivered it.
- `iap_items` → catalog virtual items.

Mapping coverage is now 100% on all three sources and the ceiling is 11/11. The lesson worth
keeping: a metric that reports a product as broken deserves suspicion of the metric first.

## Google Play did not need a browser

Play's page is React-rendered, a plain `WebFetch` returns nothing usable, and the obvious
conclusion — recorded in the first round — was that extraction needed a headless browser.

Wrong. A plain request with a browser User-Agent returns **1.3 MB of HTML with every field
already in it**: the `og:` meta tags, a `data-g-id="description"` container holding the full
long description, the image CDN URLs, the developer and category links, and the rating. Play
extraction is a regex-and-parser job, not a browser job.

What Play genuinely does not publish: named in-app items (only a range, `$0.29 – $239.99`)
and the feature graphic — no image on the page has its 1024x500 shape, so the documented
`key_art` availability was corrected from ALWAYS to NEVER.

## Apple's API has everything except the thing you want

`itunes.apple.com/lookup` returns title, developer, description, icon, screenshots, genres and
the age rating. It returns **no in-app purchases at all** — no key in the response contains
"purchase", "iap" or "inApp". The IAP list is on the web page only, truncated to roughly ten
entries, with duplicate names at different prices (`Gold Pass` at both $4.99 and $6.99).

So the App Store path needs two fetches, and its in-app item list is partial by construction.

## No storefront publishes a quantity

The decisive finding for the catalog half. Every source gives an item **name and a price**:
"Pocketful of Gems", $0.99. None gives what is inside it.

A catalog currency package or bundle requires `--content '[{"sku":"gems","quantity":1200}]'`.
That number is not public anywhere. So nothing can create a correct package or bundle from a
listing, and everything is created as a **virtual item** priced in real money — the only
catalog entity whose whole body a public listing can fill. A package with a guessed quantity
would be worse than none, because it looks finished.

Also missing, and filed rather than worked around: there is **no `consumable` flag** on
catalog item create or update. Most mobile in-app purchases are consumables.

## Four things this plan had wrong

Recorded because a design that survived contact with real data unchanged probably never
touched it.

**1. Steam does not serve BBCode.** The plan was a BBCode→HTML converter, reasoned from
BBCode being what a developer types into Steam's backend. `about_the_game` comes back as
HTML Steam has already rendered — `<h2 class="bb_tag">`, `<span class="bb_img_ctn">`,
`<video><source>`. The Steam path needs *sanitising*, not converting, so `sanitize.py` was
added and is now the primary path. `bbcode.py` still ships: a partner pasting their own store
copy is pasting real BBCode.

**2. `get-listing` does return a body.** The CLI's help says `Response: (no body)`. It
returns `{developer, icon, title}`. Worth a one-line docs PR against `xsolla/xsolla-cli`.

**3. Steam's age rating is not partial.** The field table first recorded Steam `age_rating` as
`PARTIAL`, assuming only some pages carry one. The listing exposes a full `ratings` block —
`pegi`, `esrb`, `usk`, `oflc`, `dejus` and more. Corrected to `ALWAYS`. In the same pass
`tags` went the other way: user tags render on the page but are **absent** from the
`appdetails` response, so reachability depends on which the agent read — corrected to
`PARTIAL`.

**4. Play and Apple are one ticket, not two.** The plan had them as separate gaps, one
"broken" and one "unsupported". They return byte-identical errors, which means the endpoint is
not distinguishing them — it does not recognise the target host. So the thing to file is a
question about the accepted host list, not two bug reports.

## Three bugs the real fixtures caught

All three would have passed a hand-written fixture.

**The sanitiser ate 90% of the description.** `<source>` and `<img>` are void elements — they
never send a close tag. Treating them as containers left the parser cutting to the end of the
document, so the real 2,635-character description came out **284 characters** with one of
three headings. Fixed by listing every HTML void element, and pinned by
`test_sanitize.TestVoidElementRegression`, which asserts against the real description rather
than a snippet.

**The Play description extractor took the whole document.** Same bug, different module:
`_Subtree` counted `<img>` and `<br>` as nesting levels, so the depth never unwound and the
capture ran past the description to the end of the page — **271 KB instead of 3.8 KB**. It
did not raise; it returned plausible-looking HTML that happened to contain the entire store
page. Pinned by
`test_extract.TestGooglePlay.test_long_description_is_the_description_subtree_only`.

**The rendered catalog commands were not runnable.** `--name '{"en": "Assassin's Creed
Odyssey"}'` — the apostrophe in the game's own title closed the shell quote and split the
argument. Hand-wrapping JSON in single quotes produced commands that looked right and were
not, for the very first real title through the code. Fixed with `shlex.quote`, and the test
now round-trips through `shlex.split` and `json.loads` rather than eyeballing the string.

**The preview crashed on a companion patch.** `values.background.enable` is a boolean, and the
renderer called `.replace()` on it. An `AttributeError` mid-render, after fourteen lines of
correct output. Pinned by `test_cli.test_preview_renders_a_companion_patch_without_crashing`.

## And one design flaw a test surfaced

`rights_confirmed: false` was rejected by *both* the schema validator and the write planner.
Redundant, and the schema's message was wrong: it reported a perfectly well-formed document
as invalid JSON, which sends the reader to fix the file rather than to ask the partner. Split
so the schema checks the flag's *type* and `plan.build` enforces its *truth* — shape and
policy in different places. The failing test was
`test_cli.test_blocked_preview_exits_one`, which expected `BLOCKED` and got `not valid`.

## Manual interventions and failures

Recorded because a log with none of these is not a log.

- **2 interventions in the Steam dry run.** Picking `header_image` over `capsule_image` for
  `key_art` (the API's `capsule_image` is 231×87 — unusable as a hero background, and nothing
  in the response says so), and deciding that `categories[]` is not `tags`. Both are judgement
  calls an extractor cannot make from the data alone, and both are now written down in
  [`references/steam.md`](references/steam.md) so the next run does not re-make them.
- **`get-listing` needs a landing that already exists.** It takes `--slug`, so the read-only
  "safe check before you write" cannot run before `create-website`. Minor, but it means the
  rights gate cannot be backed by an API call on a fresh project.
- **`--verbose` was essential and is not mentioned in the skill docs.** The three-field
  response, the endpoint path and the request ids all came from it. Without it the `400`s are
  an opaque `Error: HTTP 400`.

## Not verified

- **No write has been performed against a live landing.** `apply_plan.py` exists and its 35
  tests cover ordering, the confirmation gate, backup-first, the allowlist, the read-back and
  every refusal — all against an injected CLI caller, which is what keeps them offline. None
  of it has been run against a real shop. The runner is reviewed, not proven.
- **Most patch paths are still `schema`-confidence.** Only `key_art` and `screenshots` have
  been watched to land. Because a patch to a path that does not exist returns `ok: true` and
  changes nothing, the read-back in `apply_plan.py` is what would turn each of them from
  assumed to confirmed — on the first live run.
- **Two of eleven fields are refused by design, not written.** The long description and the
  overflow copy both need a TEXT component id the editor generates. The runner reports them
  as manual work rather than inventing an id, so a run delivers nine fields automatically and
  two by hand.
- **No catalog entity has been created.** The commands parse (`bash -n`, `shlex.split`) and
  the runner assembles them, but `create-items` acceptance is unconfirmed.
- **One game per source.** The DoD asks for ≥ 3. Fixtures exist for Assassin's Creed Odyssey
  (Steam) and Clash of Clans (Play, App Store).
- **`enable-preview` / `preview-link` were not exercised**, and are deliberately absent from
  the runner's allowlist. Reported elsewhere as 403 on some publisher accounts. That gates the
  "time to preview-ready shop" metric.

## What the runner adds, and what it deliberately will not do

Written in this round to close the DoD's "Writes via CLI". Four guards are structural rather
than advisory, because a write path is where advice is worth least:

| Guard | Shape |
|---|---|
| Confirmation | `--yes` or nothing is sent. The default assembles the commands and returns them. |
| Backup | `get-structure` + `get-localization` to files **before** the first write. Either read failing stops the run. |
| Allowlist | `apply.ALLOWED` is checked on every call. No publish, no delete, no `enable-preview` is reachable — including from code added later. |
| Read-back | Every patch, not a sample. A path that does not exist is reported as *"accepted and changed nothing"*. |

And three refusals, each reported instead of guessed: a localization write whose `L:` id the
block does not carry; creating the overflow TEXT component; any command outside the
allowlist.

The first two exist because Shop Builder makes the wrong thing look like the right thing. A
localization write against an invented id succeeds and changes a string nothing renders. A
patch to a component id the block does not have succeeds and changes nothing. Neither
produces an error, so neither can be caught by trying it and looking at the response.

## Write runs, and what did not import

Three shops, Brawlhalla, sandbox merchant 936601. Counts are from each run's own JSON report;
the shop state after them was read back separately rather than inferred.

| Shop | Applied | Skipped | Failed | Of those failures |
|---|---|---|---|---|
| `brawlhalla-steam-0917` | 81 | **0** | 6 | 5 × HTTP 422 "item exists", 1 transient read-back |
| `brawlhalla-play-0917` | 15 | **0** | **0** | — |
| `brawlhalla-ios-0918` | 47 | **0** | 4 | 4 × HTTP 422 "item exists" |

Verified against the shops afterwards: 0 hidden blocks on any of them, every uploaded
screenshot rendering, 5 pack cards carrying a buy SKU on Steam and the App Store, system
requirements filled on Steam, and the review score in all three descriptions.

**What did not import, by source and by reason.** These are three different kinds of miss and
they should not be added together:

*The source does not publish it* — excluded from that source's denominator, not counted
against the extractor:

| | Play | App Store |
|---|---|---|
| `key_art` | Play no longer renders a feature graphic | Apple publishes none |
| `tags` | no user tags | no user tags |
| `requirements` | an Android version in prose only | none published |
| `user_reviews` | reviews section is client-rendered | — |

*The source publishes it and the extractor missed it* — the only category that is a defect:

| Source | Field | Why |
|---|---|---|
| Steam | `tags` | user tags render on the page and are absent from `appdetails`; the extraction used the API |
| App Store | `short_description` | the subtitle is not in the lookup response |
| Play | `iap_items` | only a price range is published, never named items |

*The page had nowhere to put it* — extracted fine, reported as `unresolved`:

| Field | Reason |
|---|---|
| `platforms` | no `sidebar` block on any of the three landings |
| `developer` | no `lead` block |
| `screenshots` (surplus) | 5–6 extracted, gallery has 3 slides on the default template |
| `iap_items` (surplus) | 10 extracted on the App Store, 5 pack cards available |

## A defect this log should carry: the catalog prices are wrong

Read back from the live catalog on 2026-09-21, against what was extracted from Steam:

| SKU | Extracted | In the catalog |
|---|---|---|
| `steam_brawlhalla_all_legends_pack` | 39.99 EUR | **19.99 USD** |
| `steam_brawlhalla_collectors_pack` | 99.99 EUR | **79.99 USD** |
| `steam_brawlhalla_ezio_starter_pack` | 4.99 EUR | 4.99 **USD** |
| `steam_brawlhalla_x_lara_croft_bundle` | 14.99 EUR | 14.99 **USD** |
| `steam_brawlhalla_summer_esports_2026_pack` | 8.99 EUR | 8.99 **USD** |

Every currency is wrong and two amounts are wrong. The cause is the re-run behaviour this
skill documents as deliberate: `create-items` returns HTTP 422 on a SKU that exists, so the
**first** create's values are the ones that persist. Those first creates ran before the
currency fallback and before DLC extraction, so the catalog is holding early, partial data
and every later run reported 422 and moved on.

"Do not silently overwrite a live priced item" was the right instinct. Leaving the item
wrong was not. This needs `update-items` on a SKU that already exists, with the difference
shown in the preview — it is the one place in this skill where wrong data sits in a
partner's catalog rather than in an unfilled block.

## Reproducing this

```bash
xsolla auth login
xsolla shopbuilder get-listing --slug <existing landing> --type sellingpage \
    --target 'https://store.steampowered.com/app/812140/' --verbose

cd scripts
python3 -m unittest discover -s tests -t . -v

# the three-source metric table, from the committed fixtures
python3 - <<'PY'
from xsolla_listing_import import (coverage, extract_appstore, extract_play,
                                  extract_steam)
from tests.fixtures.load import appstore_lookup, play_page, steam_appdetails
rows = [
    ("Steam", extract_steam.to_listing(steam_appdetails(), "https://s/app/812140/")),
    ("App Store", extract_appstore.to_listing(appstore_lookup(), "https://a/id1",
     iap_items=[{"name": "Gold Pass"}])),
    ("Play", extract_play.to_listing(play_page(), "https://p?id=x")),
]
for label, doc in rows:
    r = coverage.measure(doc)
    print(label, r["extraction"], r["mapping"])
PY

python3 listing_import.py preview --listing tests/fixtures/steam_listing.json \
    --structure tests/fixtures/steam_structure.json
python3 listing_import.py catalog --listing tests/fixtures/steam_listing.json
```

# listing-import — evaluation log

Provenance for every claim in [`SKILL.md`](SKILL.md). Live work was done on merchant
`936601`, project `314771`, authenticated with `xsolla auth login`, sitebuilder API
`v2.25.0`. **Nothing was published, and no landing was created or written to** — every live
call in this round was a `GET`.

## Metrics

| Metric | Target | Result |
|---|---|---|
| Field coverage — extraction (Steam) | ≥ 80% | **90.9%** (10/11) |
| Field coverage — delivered (Steam) | ≥ 80% | **63.6%** (7/11) — at the 63.6% ceiling |
| Unit tests | pass | **139 pass**, no network, 0.02 s |
| Sources with a working server-side import | 3 | **1** (Steam) |
| Manual interventions, Steam dry run | ≤ 2 | **2** (see below) |
| Time, URL → mapping preview | report | **~4 s** of tool time; ~0.4 s of it API latency |

The delivered figure misses the target and is **not** a bug to fix here. Four target fields
have no native block destination, capping landing-only delivery at 7/11. The extraction
number is the one this skill controls, and it clears the bar. Both are reported rather than
blended, because a blended 64% reads as an extraction failure and sends the reader to the
wrong half.

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

## Two bugs the real fixture caught

Both would have passed a hand-written fixture.

**The sanitiser ate 90% of the description.** `<source>` and `<img>` are void elements — they
never send a close tag. Treating them as containers left the parser cutting to the end of the
document, so the real 2,635-character description came out **284 characters** with one of
three headings. Fixed by listing every HTML void element, and pinned by
`test_sanitize.TestVoidElementRegression`, which asserts against the real description rather
than a snippet.

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

- **No write has been performed.** Every patch path except `key_art` and `screenshots` is
  `schema`-confidence: taken from the editor's field schemas, never watched to land. Since a
  patch to a path that does not exist returns `ok: true` and changes nothing, these fail
  *silently* if wrong. Confirming them needs a write-and-read-back per path on a throwaway
  landing — the obvious next round, and `scripts/` is structured for it.
- **Google Play and App Store extraction are untested end to end.** The field tables in
  [`references/google-play.md`](references/google-play.md) and
  [`references/app-store.md`](references/app-store.md) are written from page structure, not
  from a run. The DoD's "≥ 3 games per source" is met for zero sources so far; Steam has one.
- **`enable-preview` / `preview-link` were not exercised.** Reported elsewhere as 403 on some
  publisher accounts, apparently staff-gated. That gates the "time to preview-ready shop"
  metric and needs checking early on the fixture project.

## Reproducing this

```bash
xsolla auth login
xsolla shopbuilder get-listing --slug <existing landing> --type sellingpage \
    --target 'https://store.steampowered.com/app/812140/' --verbose
cd scripts && python3 -m unittest discover -s tests -t . -v
python3 listing_import.py coverage --listing tests/fixtures/steam_listing.json
python3 listing_import.py preview --listing tests/fixtures/steam_listing.json \
    --structure tests/fixtures/steam_structure.json
```

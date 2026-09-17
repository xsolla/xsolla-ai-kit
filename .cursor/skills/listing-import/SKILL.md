---
name: listing-import
description: >-
  Builds an Xsolla Shop Builder landing from a game's existing Steam, Google Play or Apple
  App Store listing, so a publisher who already wrote that content does not re-enter it. Use
  when asked to import a store listing, build a site from a store page, or reuse listing copy
  and art — "make a site from my Steam page", "turn my Play Store listing into a webshop",
  "import my store listing", "clone my store page", "build a shop from my App Store entry",
  "reuse my game's screenshots and description". Extracts title, short and long description,
  icon, key art, screenshots, genres, tags, platform, age rating and publicly listed in-app
  items, shows the extracted-to-shop mapping, and only then writes via the CLI. Copies
  everything the listing publishes, not just marketing: genres, tags and age rating are
  carried as page copy, and in-app items become priced catalog entities. Steam also has a
  server-side import (`xsolla shopbuilder import-listing`); Google Play and the App Store are
  rejected by that endpoint, so all three run through extraction here. Public pages only.
  Landing mechanics belong to the CLI's own `shopbuilder` skill.
  Always confirms the partner holds the rights to the copy and artwork before writing, and
  never publishes.
metadata:
  owner: n.budhwani
  domain: store
  status: draft
---

## What this is

A listing is content a publisher already wrote. This skill moves it into a Shop Builder
landing without retyping it, and puts a confirmation step in front of the write.

The work splits in two. **Extraction** turns a public page into a `listing.json`; three
extractors do it, one per storefront. **Everything after that is deterministic** — validate
the document, measure coverage, map fields onto blocks and catalog entities, emit the ordered
plan. Keeping the seam there means an extraction bug and a mapping bug fail in different
places with different messages.

Nothing here fetches. Each extractor takes content the caller already has, so a rate limit, a
redirect or a geo-block surfaces where it happened instead of inside a parser — and the tests
run offline.

Python 3.9+, standard library only. No install step.

## The three sources are not the same problem

Verified live against merchant 936601 on 2026-09-14:

| Source | Extract from | Server-side import | Extraction coverage |
|---|---|---|---|
| [Steam](references/steam.md) | `appdetails` JSON | **Works** — ~13 blocks | **90.9%** (10/11) |
| [Google Play](references/google-play.md) | The page's HTML | HTTP 400 | **88.9%** (8/9) |
| [Apple App Store](references/app-store.md) | `lookup` JSON + page for IAPs | HTTP 400 | **88.9%** (8/9) |

Play's page is React-rendered, which suggests it needs a headless browser. It does not — a
plain request returns 1.3 MB of HTML with every field already in it. Apple's API carries
everything **except** in-app purchases, which are on the page only.

Play and the App Store fail *indistinguishably* — the endpoint is not reporting "Play is
broken" and "Apple is unsupported", it is saying it does not recognise the target host. Filed
once, as one question, in [`references/google-play.md`](references/google-play.md). Do not
route around it.

## The flow

Never reorder steps 1–5. Never skip step 6.

1. **Rights gate.** Ask: is this your own game's listing? A public store page can be parsed
   by anyone — nothing upstream checks ownership — so this is the only check that the copy and
   artwork are the partner's to reuse. A no ends the run.
2. **Extract.** `fetch` says what to request; `extract` turns it into `listing.json`
   ([the schema](references/listing-json.md)). What was looked for and not found lands in
   `not_found`, so an absent field is never ambiguous.
3. **Back up.** `get-structure` and `get-localization` to files, kept. Before the first write,
   not before the first fix.
4. **Preview.** `preview` renders the mapping. This is what the user approves.
5. **Confirm.** Explicit yes. An unconfirmed run stops here.
6. **Write, then read back.** `apply_plan.py` does both. Every patch is read back, because
   Shop Builder answers `ok: true` to a patch at a path that does not exist and changes
   nothing — so an unread write is indistinguishable from a successful one.
7. **Never publish.** A human publishes, in Publisher Account. The runner cannot: its
   command allowlist has no publish, no delete and no `enable-preview`.

For Steam, step 2 also happens — even though the backend can import by itself. The parsing
endpoint returns `{developer, icon, title}` and nothing else, three of eleven target fields,
so it cannot supply the preview step 4 requires. The bonus is that the agent's extraction and
the server's import can then be diffed against each other.

## Running it

From `scripts/`. All read-only; `--json` gives the machine-readable report in
[`README.md`](README.md). Exit status `0` clean, `1` something to fix, `2` bad invocation.

| About to | Run |
|---|---|
| Find out what to fetch | `python3 listing_import.py fetch --url <store url>` |
| Turn a response into a listing | `python3 listing_import.py extract --input raw.json --url <store url>` |
| Check the extraction | `python3 listing_import.py validate --listing listing.json` |
| Report field coverage | `python3 listing_import.py coverage --listing listing.json` |
| Show the mapping for approval | `python3 listing_import.py preview --listing listing.json --structure structure.json` |
| Get the operations to execute | `python3 listing_import.py plan --listing listing.json --structure structure.json > plan.json` |
| Rehearse the write | `python3 apply_plan.py --plan plan.json --slug <slug>` |
| Actually write | `python3 apply_plan.py --plan plan.json --slug <slug> --yes` |
| Create the in-app items | `python3 listing_import.py catalog --listing listing.json` |
| Convert pasted Steam BBCode | `python3 listing_import.py bbcode --file description.txt` |

Pass `--localization` (from `get-localization`) to `preview`/`plan` as well; without it, `L:`
reference existence is reported as unverified rather than assumed.

The Steam happy path, and the order that matters:

```bash
SLUG=<landing slug>
xsolla shopbuilder create-website --name "<Name>" --slug $SLUG --type topup
# import-listing on an EMPTY landing only. set-landing-type first creates a
# structure, and the import then returns 200 and silently does nothing.
xsolla shopbuilder import-listing --slug $SLUG --type sellingpage --target <store url>
xsolla shopbuilder get-structure --slug $SLUG --json > structure_raw.json
python3 -c 'import json;json.dump(json.load(open("structure_raw.json"))["data"],
    open("structure.json","w"))'
python3 listing_import.py preview --listing listing.json --structure structure.json
```

`--type` is the landing *template*, not the store name: `sellingpage`. `steam` and `gplay`
are rejected by the live API.

## Reading the coverage report

Three numbers, because they fail for different reasons and have different owners:

| | Means | Who owns a miss |
|---|---|---|
| `extraction` | Of the fields this source publishes, how many were read | The extractor. **This is the number to hold to a target.** |
| `mapping` | Of those, how many have somewhere to go | Structural — the landing is missing a block |
| `delivered` | Of the whole target list, what the partner gets | The product of the two |

Extraction clears 80% on all three sources. Mapping is 100%: **every** target field has a
destination. An earlier version of this skill reported a 7/11 = 64% ceiling — that was an
artefact of counting only structured block fields, and it is gone
([why, field by field](references/block-mapping.md)):

- **`genres`, `tags`, `age_rating`** → one appended TEXT component in the `description`
  block. Copy rather than a typed field, and a reader of the page cannot tell the difference.
- **`iap_items`** → catalog virtual items priced in real money.

`delivered` is still below `extraction` for Play and Apple, because neither publishes
`key_art` or `tags` at all. Those are excluded from each source's own denominator, so they
are not scored as extraction misses.

## In-app items — what you get, and what you cannot

`catalog` renders the commands. Two limits are not fixable by better code:

- **No storefront publishes the quantity behind an item name.** "Pocketful of Gems" never
  says 1200. So everything is created as a **virtual item**, never a currency package or a
  bundle — both need a `content` array of `{sku, quantity}`. A package with a guessed
  quantity would be worse than none, because it looks finished.
- **The lists are partial.** Steam publishes editions and DLC, never consumables. Apple's
  page shows roughly the top ten, with duplicate names at different prices. Play publishes a
  **price range** only (`$0.29 – $239.99`) and no names, so nothing is created from it.

Everything lands in one `imported_listing` group, flagged `needs_review`, for a human to
reclassify in one pass. Also unavailable: there is **no `consumable` flag** on catalog item
create or update, and most mobile IAPs are consumables — filed, not worked around.

## Safety rules

1. **Rights before anything.** Step 1 is not a warning to print; it is a gate that stops.
2. **Back up before the first write.**
3. **Show the plan, get explicit confirmation.** No silent writes.
4. **Use these scripts and the CLI's commands**, not ad-hoc API calls.
5. **Never patch a remote image URL into a block.** `upload-asset` takes a local file: fetch,
   upload, then write the returned CDN url. Writing the source URL hotlinks another
   storefront from the partner's page.
6. **Never auto-enable an unpriced catalog item.** Created disabled, so a mis-parsed
   listing cannot put a broken item on sale.
7. **Never publish.** A clean preview is not permission to make a shop live.

Sandbox or test project only — never a partner's live project.

## Authorization, and a known gap

`xsolla auth login` bootstraps the Shop Builder session these commands need. Copying a
Publisher Account `pa-v4-token` by hand (`XSOLLA_SHOPBUILDER_SESSION`) is a **documented
gap** — if a command demands it, record that and stop. Do not build a workaround.

Shop Builder authorizes separately from the Store `XSOLLA_PROJECT_API_KEY` that
[`merchant-setup`](../merchant-setup/SKILL.md) sets up.

## Related skills

- [`catalog-design`](../catalog-design/SKILL.md) — regional pricing, groups and the
  reclassification the imported items need.
- [`shop-setup`](../shop-setup/SKILL.md) — the headless storefront, which has no blocks and
  so is not an import target.

## Evidence

[`EVAL-LOG.md`](EVAL-LOG.md) records the live runs behind every claim above, the three
assumptions real data corrected, and the manual interventions.

## Agent test

Prompt: "Build me an Xsolla shop from my Steam page:
https://store.steampowered.com/app/812140/"

Live run on merchant `936601` / project `314771` (2026-09-14): the agent asked the rights
question first, called `get-listing` read-only and got `{developer, icon, title}`, then
extracted all eleven target fields from the public `appdetails` response (`tags` correctly
declared in `not_found` — they render on the page but are absent from the API). The mapping
preview against the real 13-block structure a prior `import-listing` produced: 3 localization
writes, 1 overflow component carrying genres and the PEGI rating, 10 asset uploads, 2
companion patches, and 4 catalog items for the editions — with `platforms` and `developer`
correctly reported as unplaceable on that template, which has no `sidebar` or `lead` block.
Coverage: extraction 90.9%, mapping 100%, delivered 90.9%. No writes were made: the run
stopped at the confirmation step, which is where it is supposed to stop. ✅

Second prompt: "Same thing from my Play listing and my App Store listing"
— `https://play.google.com/store/apps/details?id=com.supercell.clashofclans` and
`https://apps.apple.com/us/app/clash-of-clans/id529479190`.

Both extracted at 88.9% (8/9), mapping 100%. Play came from the page's raw HTML with no
browser; Apple from the lookup API plus the page for its truncated in-app list. Both
correctly declared `key_art` and `tags` as not published, and Play carried its
`$0.29 – $239.99` price range in `notes` rather than inventing items from it. ✅

222 unit tests, offline, on the real fixtures from all three stores.

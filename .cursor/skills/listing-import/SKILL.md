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
  items, shows the extracted-to-shop mapping, and only then writes via the CLI. Steam has a
  server-side import (`xsolla shopbuilder import-listing`); Google Play and the App Store are
  rejected by that endpoint and go through the agent-extraction path instead. Public pages
  only, marketing content only — priced catalog items are `catalog-admin`'s job, landing
  mechanics are `shopbuilder`'s, and block payload shape is `shop-validation`'s. Always
  confirms the partner holds the rights to the copy and artwork before writing, and never
  publishes.
metadata:
  owner: n.budhwani
  domain: store
  status: draft
---

## What this is

A listing is content a publisher already wrote. This skill moves it into a Shop Builder
landing without retyping it, and puts a confirmation step in front of the write.

The work splits in two. **Extraction** is the agent's: read the public page, produce a
`listing.json`. **Everything after that is deterministic** and lives in `scripts/` — validate
the document, measure coverage, map fields onto blocks, emit the ordered write plan. Keeping
the seam there means an extraction bug and a mapping bug fail in different places with
different messages.

Python 3.9+, standard library only. No install step.

## The three sources are not the same problem

Verified live against merchant 936601 on 2026-09-14:

| Source | Server-side import | What this skill does |
|---|---|---|
| [Steam](references/steam.md) | **Works.** `import-listing` builds ~13 blocks including real screenshots | Wraps it: rights gate, preview, backup, then fills what the import leaves unset |
| [Google Play](references/google-play.md) | **HTTP 400** `request_body_validation_error` | Agent extraction, then the same write plan |
| [Apple App Store](references/app-store.md) | **HTTP 400**, identical error | Agent extraction, then the same write plan |

Play and the App Store fail *indistinguishably* — the endpoint is not reporting "Play is
broken" and "Apple is unsupported", it is saying it does not recognise the target host. Filed
once, as one question, in [`references/google-play.md`](references/google-play.md). Do not
route around it.

## The flow

Never reorder steps 1–5. Never skip step 6.

1. **Rights gate.** Ask: is this your own game's listing? A public store page can be parsed
   by anyone — nothing upstream checks ownership — so this is the only check that the copy and
   artwork are the partner's to reuse. A no ends the run.
2. **Extract.** Read the public page and write `listing.json`
   ([the schema](references/listing-json.md)). Declare what you looked for and could not find
   in `not_found`; do not leave a field silently absent.
3. **Back up.** `get-structure` and `get-localization` to files, kept. Before the first write,
   not before the first fix.
4. **Preview.** `preview` renders the mapping. This is what the user approves.
5. **Confirm.** Explicit yes. An unconfirmed run stops here.
6. **Write, then read back.** Every patch. Shop Builder answers `ok: true` to a patch at a
   path that does not exist and changes nothing, so an unread write is an unverified one.
7. **Never publish.** A human publishes, in Publisher Account.

For Steam, step 2 also happens — even though the backend can import by itself. The parsing
endpoint returns `{developer, icon, title}` and nothing else, three of eleven target fields,
so it cannot supply the preview step 4 requires. The bonus is that the agent's extraction and
the server's import can then be diffed against each other.

## Running it

From `scripts/`. All read-only; `--json` gives the machine-readable report in
[`README.md`](README.md). Exit status `0` clean, `1` something to fix, `2` bad invocation.

| About to | Run |
|---|---|
| Check the extraction | `python3 listing_import.py validate --listing listing.json` |
| Report field coverage | `python3 listing_import.py coverage --listing listing.json` |
| Show the mapping for approval | `python3 listing_import.py preview --listing listing.json --structure structure.json` |
| Get the operations to execute | `python3 listing_import.py plan --listing listing.json --structure structure.json` |
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

Three numbers, because one cannot be honest:

| | Means | Who owns a miss |
|---|---|---|
| `extraction` | Of the fields this source publishes, how many were read | The extraction step. **This is the number to hold to a target.** |
| `mapping` | Of those, how many have a native block field | Nobody here — see below |
| `delivered` | Of the whole target list, what lands on the page | The product of the two |

**Landing-only delivery is capped at 7/11 = 64%**, and that is not a defect in this skill
([why, field by field](references/block-mapping.md)).
Four target fields have nowhere native to go: `genres` and `tags` (no module has the field),
`age_rating` (the footer takes rating *ids* it already holds, not free text) and `iap_items`
(catalog, not a landing → `catalog-admin`). Report the ceiling alongside the score, or a
correct run reads as a failure.

## Safety rules

1. **Rights before anything.** Step 1 is not a warning to print; it is a gate that stops.
2. **Back up before the first write.**
3. **Show the plan, get explicit confirmation.** No silent writes.
4. **Use these scripts and the CLI's commands**, not ad-hoc API calls.
5. **Never patch a remote image URL into a block.** `upload-asset` takes a local file: fetch,
   upload, then write the returned CDN url. Writing the source URL hotlinks another
   storefront from the partner's page.
6. **Never publish.** A clean preview is not permission to make a shop live.

Sandbox or test project only — never a partner's live project.

## Authorization, and a known gap

`xsolla auth login` bootstraps the Shop Builder session these commands need. Copying a
Publisher Account `pa-v4-token` by hand (`XSOLLA_SHOPBUILDER_SESSION`) is a **documented
gap** — if a command demands it, record that and stop. Do not build a workaround.

Shop Builder authorizes separately from the Store `XSOLLA_PROJECT_API_KEY` that
[`merchant-setup`](../merchant-setup/SKILL.md) sets up.

## Related skills

- [`shop-validation`](../shop-validation/SKILL.md) — run its `validate-shop` gate on the
  resulting blocks. This skill checks the *mapping*; that one checks the *payload*.
- [`catalog-design`](../catalog-design/SKILL.md) — where `iap_items` goes.
- [`shop-setup`](../shop-setup/SKILL.md) — the headless storefront, which has no blocks and
  so is not an import target.

## Evidence

[`EVAL-LOG.md`](EVAL-LOG.md) records the live runs behind every claim above, the three
assumptions real data corrected, and the manual interventions.

## Agent test

Prompt: "Build me an Xsolla shop from my Steam page:
https://store.steampowered.com/app/812140/"

Live run on merchant `936601` / project `314771` (2026-09-14): the agent asked the rights
question first, called `get-listing` read-only and got `{developer, icon, title}`, extracted
the remaining eight fields from the public listing into `listing.json` (validated clean),
and rendered a 15-operation mapping against the real 13-block structure a prior
`import-listing` had produced — 3 localization writes, 10 asset uploads, 2 companion
patches, with `platforms` and `developer` correctly reported as unplaceable on that template
and `genres`/`age_rating`/`iap_items` as manual follow-up. Coverage: extraction 90.9%,
delivered 63.6% against a 63.6% ceiling. No writes were made: the run stopped at the
confirmation step, which is where it is supposed to stop. ✅

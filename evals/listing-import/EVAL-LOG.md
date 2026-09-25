# listing-import eval log

Sandbox: merchant 936601, project 314771. Nothing published.
Test title: Brawlhalla (Steam 291550, Play air.com.ubisoft.brawl.halla..., App Store 1491520571).

## What the 80% target counts

Fields. Not items, not pages, not blocks.

11 target fields from the DoD: title, short_description, long_description, icon, key_art,
screenshots, genres, tags, platforms, age_rating, iap_items.

Denominator is per source. A source is not marked down for a field it does not publish:

    steam       11
    play         9   (no key_art, no tags)
    app_store    9   (no key_art, no tags)

Two other numbers get reported alongside and should not be confused with it:
mapping (of what was extracted, how much has somewhere to go) and delivered
(product of the two, against all 11).

## Extraction results

    steam       90.9%   10/11    missed: tags
    play        88.9%    8/9     missed: iap_items
    app_store   88.9%    8/9     missed: short_description

Why each miss:

    tags               render on the Steam page, absent from appdetails. Extraction used the API.
    iap_items (play)   Play publishes a price range only ($0.29-$239.99), never named items.
    short_description  Apple's subtitle is not in the lookup response.

## Write runs

2026-09-17/18. Counts from each run's JSON report; shop state read back separately.

    slug                      applied  skipped  failed   notes
    brawlhalla-steam-0917        81       0       6      5x HTTP 422 item exists, 1 transient read-back
    brawlhalla-play-0917         15       0       0
    brawlhalla-ios-0918          47       0       4      4x HTTP 422 item exists

brawlhalla-ios-0917 was abandoned. It lost its description and gallery blocks partway
through, and a re-added description comes back with componentsIds: [] so the long
description could never land on it. Rebuilt as -0918.

Read back after: 0 hidden blocks on any of the three, all uploaded screenshots rendering,
5 pack cards with a SKU on steam and ios, requirements filled on steam, review score in all
three descriptions.

Earlier attempts not counted above: 4 partial runs on steam before the landing-id and
icon-path bugs were fixed, 2 on play/ios that were stopped.

## What did not import

Three different reasons. Do not add them together.

Source publishes nothing:

    play       key_art (no feature graphic on the page any more), tags, requirements, user_reviews
    app_store  key_art, tags, requirements

Extractor missed it (the only real defects):

    steam      tags
    play       iap_items
    app_store  short_description

Extracted fine, no slot on the page:

    platforms      no sidebar block in the template
    developer      no lead block
    screenshots    5-6 extracted, gallery has 3 slides on the default template
    iap_items      10 extracted on ios, 5 pack cards available

## Open defects

1. Buy buttons: 4 of 10 have the wrong action.

       steam  cloud-gaming  steam_brawlhalla_all_legends_pack
       steam  scroll        steam_brawlhalla_summer_esports_2026_pack
       ios    cloud-gaming  ios_140_mammoth_coins
       ios    scroll        ios_1000_mammoth_coins

   The planner patches action.sku and never sets action.action. Template cards do not all
   default to buy. The SKU is correct on all 10; 4 of them hang off an action that ignores it.

2. Items have no fulfilment. type virtual_good, consumable true, no unit_items, no
   entitlement grant. The 6 working buttons take money and deliver nothing. Needs Game Keys
   or a webhook, neither of which is this skill.

3. create-items 422s on an existing SKU and the run moves on, so a correction never lands.
   Fixed by hand on 2026-09-21 via update-items; not fixed in code.

4. Prices imported are Steam's *discounted* prices, not list. All Legends 19,99 (list 39,99,
   -50%), Collectors 79,99 (list 99,99, -20%). Correct today, wrong when the sale ends.
   No decision yet on whether to import initial or final.

## Not verified

- 1 game per source. DoD wants 3.
- Run success unmeasured. Each of the 3 runs needed a fix first, so 0/3 clean on first pass.
  All causes fixed, clean re-run not done.
- Most patch paths are schema-confidence. Only icon, key_art and screenshots have been
  watched to land.
- enable-preview / preview-link never exercised. Reported 403 on some accounts.

## Bugs found by running it, not by testing it

Four of these. All the same shape: the write succeeds, the read-back confirms it, and the
result is still wrong.

    --landing-id took the block id          HTTP 404 on every asset write
    icon -> header.values.logo.img          path does not exist, patch returned ok:true
    gallery slides array is finite          screenshots 4+ silently dropped
    slide colour layer at 0.85 opacity      3 screenshots per shop uploaded and invisible

The mocked tests could not catch the first (a fake CLI accepts any argument) or the last
(the value written was correct). Read-back caught the second. The third needed counting.

## Timing

    url -> mapping preview    ~4s
    url -> written shop       107s (steam). 12 asset round trips at ~9s each dominate.

## Tests

343, stdlib only, no network. Fixtures are real: live appdetails for 291550, live iTunes
lookup for 1491520571, a trimmed capture of the live Play page, and the block spine of a
landing import-listing actually produced.

    cd skills/listing-import/scripts && python3 -m unittest discover -s tests -t .

## Reproducing a run

    xsolla auth login
    python3 listing_import.py fetch    --url <store url>
    curl -sS '<the url fetch prints>' -o raw.json
    python3 listing_import.py extract  --input raw.json --url <store url> --dlc dlc.json > l.json
    # set rights_confirmed by hand, after asking
    xsolla shopbuilder get-structure --slug <slug> --json | jq .data > st.json
    python3 listing_import.py plan     --listing l.json --structure st.json > plan.json
    python3 apply_plan.py --plan plan.json --slug <slug>          # rehearsal
    python3 apply_plan.py --plan plan.json --slug <slug> --yes    # writes, backs up first

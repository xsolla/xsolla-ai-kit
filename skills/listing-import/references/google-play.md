# Google Play and the Apple App Store — blocked upstream, filed not patched

## What was observed

Both storefronts are rejected by the Shop Builder parsing endpoint. Verified live on
2026-09-14, merchant `936601`, project `314771`, sitebuilder API `v2.25.0`:

```
GET https://sitebuilder.xsolla.com/api/merchant/936601/project/314771
      /landing/<slug>/parsing?type=sellingpage&target=<url>
```

| Target | Result |
|---|---|
| `https://store.steampowered.com/app/812140/` | `200` with `{developer, icon, title}` |
| `https://play.google.com/store/apps/details?id=com.supercell.clashofclans` | `400` |
| `https://apps.apple.com/us/app/clash-of-clans/id529479190` | `400` |

Both failures return the *same* generic body:

```json
{"error": {"code": "request_body_validation_error",
           "description": "Occurred error with body validation; Make sure that you enter the right parameters;"}}
```

Request ids, for the ticket: Play `b3e6d474f94f3852ad7d190b6a1139be`, App Store
`c74564c9b7b935dab0aec1d058e0c118`.

## Why that matters more than "Play is broken"

The errors are **indistinguishable**. The endpoint is not reporting a Play-specific fault and
an Apple-specific absence — it is saying it does not recognise the target, which reads like a
host allowlist on the server side. So this is one question, not two bug reports:

> Which target hosts does `/parsing` accept, and what is the plan for Google Play and the
> Apple App Store?

File that against Shop Builder with the endpoint, the API version and the two request ids
above. Per the scope guard, gaps in the SB API are filed and linked, **not** patched from
this side. Do not add a client-side fetch to work around it.

## Play does not need a browser

Worth stating plainly, because the opposite conclusion is the intuitive one. Play's page is
React-rendered and a plain `WebFetch` returns nothing usable, which suggests a headless
browser. It does not: a plain request with a browser User-Agent returns **1.3 MB of HTML with
every target field already in it.** Verified 2026-09-14 for `com.supercell.clashofclans`.

| Field | Where in the HTML |
|---|---|
| `title` | `og:title`, minus the ` - Apps on Google Play` suffix |
| `short_description` | `og:description` |
| `long_description_html` | the `data-g-id="description"` container's subtree |
| `icon` | `og:image` |
| `screenshots` | `play-lh.googleusercontent.com/...=w1052-h592-rw` |
| `developer` | the first `/store/apps/dev?id=` link's text |
| `age_rating` | the rating badge — `Everyone`, `Everyone 10+`, `Teen`, … |
| `genres` | the `/store/apps/category/<SLUG>` link |

`extract_play.py` does this, and fails **field by field** on purpose: a renamed class costs
one field, declared in `not_found`, rather than raising and losing the other ten. It is the
one extractor reading markup instead of a JSON contract, so it is the one that will break.

Two things Play genuinely does not publish:

- **Named in-app items.** Only a range — `$0.29 – $239.99` for Clash of Clans. A range is not
  an item list, so the range is carried in `notes` and nothing is created from it.
- **The feature graphic.** No image on the page has its documented 1024x500 shape; Play
  appears to have stopped rendering it. `key_art` availability was corrected from ALWAYS to
  NEVER so it stays out of Play's coverage denominator.

## The path both sources take

1. `fetch` names what to request; `extract` turns it into `listing.json`
   ([schema](listing-json.md)).
2. `create-website`, then `add-page`, then `set-landing-type`. There is no import to
   no-op against, so the ordering trap that applies to Steam does not apply here — but the
   landing still needs blocks before anything can be placed, and a freshly created landing
   has none.
3. `preview`, confirm, write, read back. Identical from here on.

## Field differences from Steam

| Field | Google Play | App Store |
|---|---|---|
| `short_description` | `og:description` | The subtitle — **not in the lookup API**, often absent |
| `key_art` | **Not published on the page** any more | **Not published.** Both excluded from the denominator |
| `tags` | No user tags | No user tags |
| `age_rating` | Content rating (ESRB/PEGI/USK as shown) | Age rating (4+, 9+, 12+, 17+) |
| `iap_items` | Real IAP list, usually with a price range | In-app purchase list with prices |
| `platforms` | `android` | `ios`, plus `ipados`/`macos` where listed |

Both publish fewer of the target fields than Steam, so their coverage denominators are
smaller (10 and 9, against Steam's 11). That is handled in `fields.py` — a source is not
marked down for a field it never publishes.

## Asset sizes worth knowing

Play: feature graphic 1024×500, icon 512×512, phone screenshots 1080×1920.
App Store: icon 1024×1024, 6.7" screenshots 1290×2796. All well under the 10 MB
`upload-asset` limit, but the App Store's portrait screenshots will letterbox in a `gallery`
block built for landscape Steam captures — worth telling the partner before they see it.

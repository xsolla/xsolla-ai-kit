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

## The path that works meanwhile

Both sources go through agent extraction, which is the same path the App Store would need
even if Play were fixed:

1. Read the public page. Produce `listing.json`
   ([schema](listing-json.md)), `source` set to `google_play` or `app_store`.
2. `create-website`, then `add-page`, then `set-landing-type`. There is no import to
   no-op against, so the ordering trap that applies to Steam does not apply here — but the
   landing still needs blocks before anything can be placed, and a freshly created landing
   has none.
3. `preview`, confirm, write, read back. Identical from here on.

## Field differences from Steam

| Field | Google Play | App Store |
|---|---|---|
| `short_description` | The store's own short description | The subtitle, when the app has one |
| `key_art` | Feature graphic, 1024×500 | **Not published.** Excluded from the denominator |
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

# Apple App Store — agent extraction only

The App Store has no server-side import and, unlike Google Play, none is indicated as
coming. `/parsing` rejects an `apps.apple.com` target with the same generic
`request_body_validation_error` it gives Play — see
[`google-play.md`](google-play.md) for the evidence and the ticket to file.

So this is the source where the extraction step is the whole job, and the one worth building
carefully: the same extractor then serves as the preview for Steam and the fallback for Play.

## Extraction

Read the public product page. An `apps.apple.com/<cc>/app/<slug>/id<digits>` URL is the
canonical form; the `<cc>` country segment changes prices and the age rating, so record which
one was read in `notes`.

| Target field | Where on the page |
|---|---|
| `title` | The app name in the header |
| `developer` | The seller line under the title |
| `short_description` | The subtitle, when present. Many apps have none → `not_found` |
| `long_description_text` | The description body. Plain text, so use the `_text` form |
| `icon` | The app icon, 1024×1024 |
| `key_art` | **Not published.** Excluded from the denominator, not a miss |
| `screenshots` | The screenshot carousel, 1290×2796 for 6.7" |
| `genres` | The category, plus any secondary category |
| `tags` | Not published |
| `platforms` | `ios`, plus `ipados`/`macos`/`visionos` where the page lists them |
| `age_rating` | The age rating badge — `4+`, `9+`, `12+`, `17+` |
| `iap_items` | The "In-App Purchases" list, with prices |

Use `long_description_text`, not `_html`: the App Store's description is plain text with line
breaks, and declaring it as HTML would pass it through the sanitiser unescaped, so a literal
`<` in the copy would vanish.

## Two things that will look wrong on the landing

**Portrait screenshots in a landscape gallery.** App Store captures are tall (1290×2796); the
`gallery` block's slides are built for Steam's 1920×1080. They will letterbox. Tell the
partner before they see it, and consider a `bento-grid` instead, which tolerates mixed aspect
ratios better.

**No key art means an empty hero background.** `leadGameSales.values.background.img` has
nothing to fill it, so either leave the background disabled or ask the partner for a wide
asset. Do not stretch the icon into it.

## Prices are per-storefront

An App Store page shows prices for the country in its URL. Extracted IAP prices are therefore
one region's, not a price list — carry the country through in `notes` and treat the amounts
as a starting point for `catalog-design`'s regional pricing rather than as the answer.

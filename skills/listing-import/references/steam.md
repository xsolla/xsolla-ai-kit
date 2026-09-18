# Steam — the wrapped path

Steam is the one source with a working server-side import, so this skill's job here is the
safety envelope around it plus the fields it leaves unset.

## The order, and the trap in it

```bash
xsolla shopbuilder create-website  --name "<Name>" --slug $SLUG --type topup
xsolla shopbuilder import-listing  --slug $SLUG --type sellingpage --target <store url>
xsolla shopbuilder get-structure   --slug $SLUG --json
```

**`import-listing` only creates a structure; it will not replace one.** On a landing that
already has a structure it returns `200` and changes nothing, with no error. `set-landing-type`
*creates* a structure — so running it first causes the silent no-op. The import sets the
landing type itself.

If `get-structure` comes back with `pages: 0`, the import did not run. If it comes back with
blocks you did not expect, the landing was not empty.

`--type` is the landing template, not the store name. Use `sellingpage`; `steam` and `gplay`
are rejected by the live API with `type must be one of the following values: sellingpage,
topup`.

`import-listing` cannot be sandboxed — `--sandbox` refuses without `--force`.

## What the import produces

Observed on the real landing `steamtest-173641` (merchant 936601): one page, 13 blocks.

```
header · leadGameSales · description · packs · packs · description ·
bento-grid · bento-grid · gallery · packs · requirements · faq · footer
```

Note what is **not** there: no `sidebar` and no `lead`. So `platforms` (which wants
`sidebar.storeButtons`) and `developer` (which wants `lead.values.developer`) have nowhere to
go on the default template, and `preview` reports both as unresolved rather than writing them
somewhere approximate. Add the block first if the partner wants those fields.

## What `get-listing` returns

Three fields. Verified live, 2026-09-14:

```json
{"developer": "Ubisoft Quebec, Ubisoft Montreal, …",
 "icon": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/812140/header.jpg",
 "title": "Assassin's Creed® Odyssey"}
```

The CLI's own help says `Response: (no body)`, which is wrong — worth a one-line docs PR
against `xsolla/xsolla-cli`.

Three of eleven target fields is not enough to preview a write against, which is why the
agent extraction step runs on Steam too.

## Extracting the rest

The public `appdetails` response carries everything else. Field by field:

| Target field | Where |
|---|---|
| `title` | `name` |
| `developer` | `developers[]`, joined |
| `short_description` | `short_description` |
| `long_description_html` | `about_the_game` — **already HTML**, not BBCode |
| `icon` | `capsule_image` (231×87) |
| `key_art` | `header_image` (460×215) |
| `screenshots` | `screenshots[].path_full` (1920×1080) |
| `genres` | `genres[].description` |
| `platforms` | `platforms{}`, the true keys |
| `age_rating` | `ratings.pegi.rating` / `ratings.esrb.rating` |
| `iap_items` | `package_groups[].subs[]` — editions, with `price_in_cents_with_discount` |

### Player reviews

A second endpoint, and the ids are the app's own:

```
https://store.steampowered.com/appreviews/291550?json=1&language=english&filter=all
```

Each entry carries `review` (the text), `voted_up`, `votes_up` (helpfulness) and
`author.playtime_forever` in minutes. `query_summary` carries the totals —
**138,815 positive against 39,861 negative** for Brawlhalla.

`candidate_reviews()` returns them ranked by `voted_up` then helpfulness. **Ranked, not
chosen.** Ranking by helpfulness alone put three negative reviews at the top, including an
87-hour "I have never encountered a more spiritually bankrupt species" and a 2,364-hour
comparison to a deal with the Devil. Those are the best-argued reviews on the page; none of
them belongs on the publisher's own storefront.

Pick two or three yourself, quote them into `user_reviews`, and set
`rights_reviews_confirmed` only on a real answer — see
[`listing-json.md`](listing-json.md).

`tags` are **not** in that response. Steam's user tags render on the page only, so an
extraction that used the API should declare `tags` in `not_found` rather than omit it.

`categories[]` looks like tags and is not — it is Steam's feature list (Single-player, Steam
Achievements, Trading Cards). Do not map it to `tags`; it is Steam platform metadata and
means nothing on a partner's own site.

## The long description

`about_the_game` is HTML Steam has already rendered from the developer's BBCode, and it
carries markup that must not reach a partner's page:

- `<h2 class="bb_tag">` — the class is Steam's, dropped
- `<span class="bb_img_ctn">` — unwrapped, text kept
- `<video><source src="…">` — **cut with its contents**; inline trailers are Steam-hosted

`sanitize.py` handles all three. For app 812140 that reduces 2,635 characters to 781 while
keeping all three headings — the difference is video markup, not copy.

A partner pasting their own store copy is pasting real BBCode; that path is `bbcode.py`, via
`long_description_bbcode`.

## Editions are not in-app purchases

`package_groups` gives four editions for app 812140 (Standard €59.99 through Ultimate
€114.99). They are genuinely extractable and genuinely useful — but they are catalog
entities, not landing content. Route them to
[`catalog-design`](../../catalog-design/SKILL.md); nothing on a landing holds a price.

Steam publishes no consumable IAP list at all, so `iap_items` from Steam means editions and
DLC only.

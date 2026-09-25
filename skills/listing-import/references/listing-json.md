# `listing.json` — the extraction contract

The document the agent produces from a public store page, and the only input the scripts
take. Validate it with `listing_import.py validate` before anything else; a malformed
document caught here is a much cheaper failure than a half-written landing.

## Shape

```json
{
  "source": "steam",
  "source_url": "https://store.steampowered.com/app/812140/",
  "fetched_at": "2026-09-14T13:32:16Z",
  "rights_confirmed": true,
  "fields": {
    "title": "Assassin's Creed® Odyssey",
    "developer": "Ubisoft Quebec, Ubisoft Montreal",
    "short_description": "In this action-adventure game, set sail for Ancient Greece…",
    "long_description_html": "<h2 class=\"bb_tag\">FIGHT AS A SPARTAN</h2>…",
    "icon": "https://…/capsule_231x87.jpg",
    "key_art": "https://…/header.jpg",
    "screenshots": ["https://…/ss_0ef33c0f.1920x1080.jpg", "…"],
    "genres": ["Action", "Adventure", "RPG"],
    "tags": ["Open World", "RPG"],
    "platforms": ["windows"],
    "age_rating": "PEGI 18",
    "iap_items": [
      {"name": "Gold Edition", "price": {"amount": 99.99, "currency": "EUR"}}
    ]
  },
  "not_found": ["tags"],
  "notes": "tags render on the page but are absent from the appdetails response."
}
```

## Required

| Key | Why |
|---|---|
| `source` | `steam`, `google_play` or `app_store`. Drives which fields are expected. |
| `source_url` | The public page. Cross-checked against `source`; a disagreement blocks. |
| `rights_confirmed` | Must be `true` before a write is planned. See below. |
| `fields` | The extraction. Every key optional; absent means not extracted. |

Optional: `fetched_at`, `not_found`, `notes`. Any other top-level key is an error — a typo
in a key name would otherwise be silently ignored.

## `rights_confirmed`

The schema checks that this is a boolean. `plan.py` checks that it is `true`, and refuses to
plan otherwise. The split is deliberate: an unconfirmed listing is a well-formed document
that is not authorized, which is a different failure from a malformed one and deserves a
different message.

This flag is the **only** ownership check in the system. The Shop Builder parsing endpoint
will read any public store page — verified on 2026-09-14 against a Ubisoft listing from an
unrelated merchant account — so nothing upstream will stop a partner importing someone
else's game. Set it from a real answer to a real question, never by default.

## The long description, and its three forms

Exactly one of these, or none:

| Key | When | What happens to it |
|---|---|---|
| `long_description_html` | **The common case.** Steam and Play both serve rendered HTML | Sanitised against an allowlist (`sanitize.py`) |
| `long_description_bbcode` | A partner pasting their own store copy | Converted (`bbcode.py`) |
| `long_description_text` | Plain text | HTML-escaped, not passed through |

Setting two is an error; the scripts would otherwise silently pick one by declaration order.

Steam's `about_the_game` is **already HTML** — `<h2 class="bb_tag">`, `<span
class="bb_img_ctn">`, `<video><source>` for inline trailers. The initial plan assumed BBCode
and was wrong; see `evals/listing-import/EVAL-LOG.md` in the toolkit repo.

## `not_found`

What the extraction looked for and could not find, as opposed to what it never looked for.
Without it an absent field is ambiguous and `coverage` cannot tell a page that publishes no
age rating from a run that skipped the field. Listing a field here *and* in `fields` is an
error.

## `user_reviews`, and its own rights flag

Reviews you have **chosen and quoted**, not a feed:

```json
"rights_reviews_confirmed": true,
"fields": {
  "user_reviews": [
    {"quote": "It's not button mashing, it's an aggressive tactical input strategy.",
     "attribution": "TGGTO07 on the App Store",
     "rating": 5, "source": "app_store"},
    {"quote": "Easy to pick up, genuinely hard to master.",
     "attribution": "A player with 445 hours on Steam",
     "playtime_hours": 445, "source": "steam"}
  ]
}
```

`quote` and `attribution` are required; `rating`, `source` and `playtime_hours` are optional
and exist so a reviewer can check the choice.

**`rights_reviews_confirmed` is a second question, and it is not the same one.**
`rights_confirmed` asks whether the listing is the partner's own — that covers their copy and
their artwork. A player review is a player's words, and republishing someone else's writing
on a commercial page is a different permission. One flag cannot answer both, so the planner
places no reviews without this one and says why.

Where they go: one per **`bento-grid` leaf card**. No module has a reviews field, and a leaf
with two text components takes the quote and the attribution separately.

Google Play publishes no review text — its reviews section is client-rendered and the markup
holds only the section's chrome. Declared in `not_found`, not left silent.

## `iap_items`

`name` is required; `price` is optional but must be `{amount: number, currency: <3-letter>}`
when present. These do not go on the landing — they are catalog entities, routed to
[`catalog-design`](../../catalog-design/SKILL.md).

Steam publishes editions rather than consumables (`package_groups[].subs[]`, with
`price_in_cents_with_discount`); Play and the App Store publish real IAP lists.

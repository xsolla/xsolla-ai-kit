# Field → block → patch path

The table `mapping.py` carries, with the reasoning that is not expressible in a data
structure. Read `mapping.py` for the authoritative version; this explains it.

## Confidence is the load-bearing column

| Label | Means | Consequence |
|---|---|---|
| `confirmed` | The path was exercised against the live API and the write landed | Trust it |
| `schema` | The field exists in the Site Builder editor's schema; no write watched | **A patch here may silently no-op** |
| `none` | The listing publishes the field and no block has anywhere to put it | Manual follow-up |

Only `key_art` and `screenshots` are `confirmed`. Everything else writable is `schema`.

That distinction matters because of one API behaviour: **a patch to a path that does not
exist returns `ok: true` and changes nothing.** There is no error to catch. So an unconfirmed
path is not "probably fine" — it is "fails invisibly if wrong", which is why every write is
paired with a read-back and why `preview` prints `[path unconfirmed]`.

## The rows

| Field | Module | Action | Path |
|---|---|---|---|
| `title` | `leadGameSales` | localization | `values.title` (h3) |
| `developer` | `lead` | localization | `values.developer` |
| `short_description` | `leadGameSales` | localization | `values.subtitle` (p) |
| `long_description` | `description` | localization | `values.components` |
| `icon` | `header` | asset | `values.logo.img` |
| `key_art` | `leadGameSales` | asset | `values.background.img` ✅ |
| `screenshots` | `gallery` | asset | `values.slides[i].image.img` ✅ |
| `platforms` | `sidebar` | patch | `values.storeButtons` |
| `age_rating` | `footer` | manual | `values.ageRatingIds` |
| `genres` | — | manual | — |
| `tags` | — | manual | — |
| `iap_items` | — | external | → `catalog-design` |

## Why four fields have nowhere to go

Not an oversight here — a gap in the block set:

- **`genres`, `tags`** — no module has the field. Genres can be folded into description copy
  or a `bento-grid` card if the partner wants them visible. Steam user tags are usually worth
  dropping outright: they are Steam's taxonomy of the game, not the publisher's positioning
  of it.
- **`age_rating`** — `footer.values.ageRatingIds` takes *ids the site already holds*, not
  free text, and no CLI command creates one. A Publisher Account step.
- **`iap_items`** — a landing holds no prices. Catalog entities.

This caps landing-only delivery at 7/11 = 64%. `coverage` reports that ceiling explicitly so
a correct run is not read as a failing one.

## Companion patches

Key art needs two more writes or it stays invisible:

```
values.background.enable  →  true
values.background.size    →  "cover"
```

`plan.py` emits them automatically with any `key_art` write. A gradient
(`values.background.gradient`) is also worth setting for text legibility over art, but the
right value depends on the image, so it is left to the author rather than guessed.

## Ordering constraints

1. **Assets before the patches that reference them.** `upload-asset` takes a local file —
   there is no remote-URL ingest. Fetch, upload, then write the returned CDN url. Writing a
   Steam URL into a block hotlinks another storefront from the partner's page, and the URL
   carries a `?t=` cache-buster that will eventually rot.
2. **Localization before the image writes.** A block referencing an `L:` id with no string
   behind it 500s the renderer, so the string has to exist before anything makes the block
   visible.
3. **Never wholesale-replace a block's `values` or `components`.** Copying `L:` references
   with no matching localization is the same 500. Patch individual paths.

## Two silent-failure traps in the write commands

- `update-many-localization` with a bare string instead of `{"translation": "<html>"}`
  returns `200` and writes an **empty string**. Destructive and silent.
- `--blockid`, not `--block-id`, on block mutations. Passing a slug where `--landing-id` is
  expected returns a 500.

Both belong to the CLI's `shopbuilder` command surface rather than to this skill; they are
repeated here because an import is where a batch of localization writes happens all at once, which is
exactly when an empty-string bug does the most damage.

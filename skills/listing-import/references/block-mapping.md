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
| `age_rating` | `description` | overflow | `values.components` |
| `genres` | `description` | overflow | `values.components` |
| `tags` | `description` | overflow | `values.components` |
| `iap_items` | — | catalog | virtual items, via `create-items` |

## The four fields with no structured field

They have no *typed* block field. That is not the same as having nowhere to go, and the first
version of this table confused the two — it reported them unmappable and put a 7/11 = 64%
ceiling on the whole skill. The ceiling was an artefact of the measurement.

**`genres`, `tags`, `age_rating` → overflow.** One appended TEXT component in the
`description` block, rendered by `overflow.py`:

```html
<p><strong>Genres:</strong> Action, Adventure, RPG</p><p><strong>Rating:</strong> PEGI 18</p>
```

One component, not three: three stacked one-line paragraphs read like a debug dump. Values are
escaped — this is third-party text bound for a partner's rendered page.

The `footer.values.ageRatingIds` field still exists and still takes *ids the site already
holds*, which no command creates. So the rating **badge** remains a Publisher Account step;
the rating **text** does not wait for it.

**`iap_items` → catalog**, as virtual items priced in real money. Never a currency package or
a bundle: both need a `content` array of `{sku, quantity}`, and no storefront publishes the
quantity behind a name like "Pocketful of Gems". See `catalog.py`.

Mapping coverage is now 100% on all three sources.

## Store item types — uppercase or lowercase

Resolved against the Site Builder MCP's shipped runtime (v1.0.2), because the CLI's
`wire-a-store.md` and the editor's Zod schema disagree. **Both are right, at different
layers:**

- **Uppercase** — `BUNDLE`, `UNIT`, `VIRTUAL_CURRENCY`, `VIRTUAL_GOOD`, `UPSELL` — is what a
  `newStore` block's `components[].section.item.type` takes. Live in the shipped bundle.
- **Lowercase** — `bundle`, `unit`, `virtual_currency_package` — is what the *storefront API*
  returns for items.

Do not hardcode one for both. Two related facts from the same source: a virtual currency
package is a **bundle** with `bundle_type: 'virtual_currency_package'` (the discriminator is
`bundle_type`, not `type`), and read and write field names differ — the API returns
`virtual_prices` where the CLI flag is `--vc-prices`.

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

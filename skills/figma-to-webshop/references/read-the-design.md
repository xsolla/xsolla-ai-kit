# Read the design

Goal: leave this step with two artifacts — a **section inventory** (every band of the
page, top to bottom, marked functional or decorative) and a **token sheet** (the exact
hex values, fonts, radii and spacing). Everything downstream is mechanical once you have
those.

## Use the link the user gave you

Whatever they hand over — a `figma.com` URL, a local file, an exported HTML comp — that
exact resource is the source of truth. If you cannot read it, say so and ask them to
re-share. Do **not** fall back to a similarly-named file or an older design in the same
project: near-duplicate names across products and artifacts are common, and picking a
lookalike silently builds the wrong thing.

## From a Figma link (Figma MCP server)

These tools come from the official Figma MCP server. Load the `/figma-use` skill first if
you are going to write back to Figma; for read-only extraction you don't need it.

| Tool | Use it for |
|---|---|
| `get_screenshot` | The visual ground truth. Get this first — you will compare against it all the way through. |
| `get_metadata` | The frame/layer tree. This is what you turn into the section inventory. |
| `get_design_context` | Per-node layout, type and color detail. The token sheet comes from here. |
| `get_variable_defs` | Design-system variables — the cleanest source of the palette when the file uses them. |
| `download_assets` | Export the art (logos, product renders, key art) as PNG/SVG. |

If the MCP server isn't connected, say so plainly and ask for either a screenshot plus
the hex values, or an export. Don't guess a palette from a JPEG.

## From an exported HTML / React comp

Often the fastest path: the comp already *is* the spec. Read it and lift values
literally — `#0a1330`, `0 4px 0 #3F1585`, `letter-spacing:.14em` — rather than eyeballing
them. Exported comps usually carry a data array of the products too, which tells you
exactly what the catalog needs.

## Slice the design assets, rebuild the structure

**Never flatten a section — or a product card — into one raster image.** Cropping bands
out of a page screenshot and overlaying transparent hit areas looks faithful in a
screenshot and is fast, but it destroys the page: baked text cannot be selected,
searched, translated or localized, so the whole localization store becomes decorative;
it is invisible to screen readers and SEO; it cannot reflow, so the page is only correct
at the comp's native width; it ignores the site theme, so a later re-theme moves nothing;
an FAQ accordion rendered as an image never opens; and it costs megabytes for what would
be a few kilobytes of markup.

| Export as an asset | Rebuild as DOM |
|---|---|
| Illustrations, character art, key art, textures | All text — headings, copy, prices, amounts, labels |
| Ornate frames, ribbons, rosettes, badge shapes | Buttons, tabs, accordions, carousels, inputs |
| Icons and logos (prefer SVG) | Layout, grids, spacing, radii, shadows, gradients |

Get the real source files with Figma's `download_assets` — it returns the actual uploaded
PNGs/JPEGs and the vector layers as SVG — rather than cropping them out of a screenshot.
It caps at 20 of each per node, so walk the section nodes rather than asking for the page
root. Take every value (`#0a1330`, `0 4px 0 #3F1585`, `letter-spacing:.14em`) from
`get_design_context`, not from sampling pixels.

A flattened slice is legitimate in exactly one case: art and type that are genuinely
inseparable — a logo lockup, or display type that is itself an illustration. Say so when
handing over.

## The token sheet

Capture at minimum:

- **Surfaces**: page background, section background, card background, footer. These are
  usually three or four near-identical darks, and getting them slightly wrong is very
  visible.
- **Brand**: the primary CTA color and its pressed/hover variants, plus the accent used
  for highlights.
- **Text**: primary, muted, dim, and link colors.
- **Borders**: the hairline color and any accent border.
- **Radius**: button and card corner radius.
- **Fonts**: display face, body face, and any mono face, with the weights actually used.

## The section inventory

For each band record: what it contains, whether anything in it *transacts* (catalog,
cart, checkout, login, balance), and which Shop Builder block could host it. A section is
**functional** only if it touches real commerce or the session — a hero whose price
button merely scrolls to the store is decorative, because the real purchase happens on
the store card below.

## Map store sections to catalog groups

The comp's product rows map 1:1 to catalog groups, and the item `type` matters:

| Comp row | `section.item.type` |
|---|---|
| Coin / currency packs | `virtual_currency` (these are **currency packages**) |
| Offer or starter bundles | `bundle` |
| Passes, cosmetics, single items | `virtual_good` |
| Everything of one type | `__all__` |

Check what already exists before building anything:

```bash
xsolla catalog list-item-groups            --project-id <p>
xsolla catalog list-catalog-items-by-group --project-id <p> --external-id <group>
xsolla catalog list-catalog-bundles        --project-id <p>
xsolla catalog list-catalog-currency-packages --project-id <p>
```

Currency packages and bundles do **not** appear in `list-catalog-items-by-group` — an
empty result there does not mean the group is empty. Check the type-specific list too.

Build anything missing with **catalog-admin** (needs Store Basic auth — probe for it as
SKILL.md Step 0 describes rather than assuming an unset `XSOLLA_API_KEY` means you lack
it).

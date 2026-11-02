# Visual style: the game's look, backgrounds, gradients and tints

The first draft the developer sees should already look like their game. Flat template
colors, placeholder art and hard section edges read as unfinished.

## Start from the game's identity

- Use, in this order: the brief's `brand` (logo, hero image, colors, fonts), then the art
  on the publisher's own store listing that `description-to-shop` recorded after the
  publisher confirmed it's theirs (app icon, screenshots, key art), then the developer's
  own files. The plan lists every asset and where it came from.
- Take the palette from that art: a dark or light base, one accent for calls to action, and
  one or two supporting colors. Keep it on every page.
- Without key art, build section backgrounds as gradients in that palette, not one flat
  color.
- Upload images with `upload-asset` and use the returned CDN URL. Never hotlink a store page.
- Products and packs need artwork in one consistent style. It's the catalog items' images,
  which `catalog-design` sets; list the missing ones in the handoff.

## Section backgrounds

A block's `values.background` holds `enable`, `type`, `color`, `gradient`, `img`, `position`
and `size`. These fields were observed read-only with CLI 1.9.4 on 2026-10-23, in template
blocks of a store landing created in the Site Builder UI and of sites made from templates.
Patch them one leaf at a time, like every other value.

- **`color` is painted over `img`**, so it works as the image's tint. Templates set it to
  `rgba(0, 0, 0, 0)`. An opaque color hides the image completely; use alpha only as far as
  the text over the image needs it.
- **`gradient`** blends the section into what is next to it: fade to transparency or to the
  next section's color, so no section ends in a hard rectangular edge. The shape of a
  gradient value isn't recorded here: read a block that has one with `get-block` and reuse
  its shape. If no block on the site has one, leave gradients to the Site Builder editor and
  list it as a manual step.
- **`size: cover` with `position: center`** is the combination known to render.
- **Vary the sections**: the hero carries the key art, store sections sit on a calmer
  gradient, and FAQ and footer on the darkest or lightest base. Keep one palette.

## Product images

- Prefer transparent product images (PNG or WebP with alpha).
- Otherwise, give the image the same background as the card it sits on, so image, card and
  page read as one surface. Look for visible edges, halos and mismatched colors.
- Product images are the catalog items' images: `catalog-design` sets them.

## Render rules

Observed in test builds with CLI 1.9.4, October and November 2026. Each one cost a round of
render checks to find. Check the plan and every patch against them, and the visual review
below against the result.

**Theme and fonts**

- A theme patch through the CLI saves, but doesn't recompute `calculatedTheme`, so the
  preview keeps the old colors. Until the CLI recomputes it, the developer recalculates the
  theme in the editor's Theme panel: list it as a manual step in the handoff.
- A page-theme patch detaches that page from the global theme. Say so in the handoff.
- The preview loads only the three theme fonts. Any other font named inline falls back to
  serif: always add a generic fallback, such as `sans-serif`.
- Built-in fonts: GraphikLC, Montserrat, Oswald, Roboto, Spectral, Pilat, Aktiv. For the
  game's own font, upload a TTF with `upload-asset --type font` and use it as a font asset.
- The theme's Overlay color is the surface of store cards and bento leaves, and Text is the
  card text. A light overlay with dark text fits most designs.
- LiveOps blocks use the theme text color over their picture background: plan light panels
  for them, or give the other blocks their own dark backgrounds.

**Backgrounds and images**

- Besides a block's `background.color`, a leaf's background color, a pack image color and a
  hero call-to-action background also paint over the image: keep them transparent when the
  image must show.
- `background.gradient` renders over both color and image on the header, lead, bento,
  store, promo codes and FAQ blocks. Use plain two-color fades over the whole block.
- A photo background on a short block shows hard edges: keep short blocks flat or on a
  gradient.
- The lead block's background `position` accepts CSS such as `88% center`, which picks the
  phone crop.
- The editor canvas doesn't draw a Description block's custom background; the preview
  does. Judge in the preview.
- Card image shapes: vertical bundle images are about 1.41:1; store layout `large` gives
  wide 16:9 cards and `vertical` square ones.

**Text**

- Localized HTML keeps inline styles, including `clamp()`. Use it for display sizes, or big
  headings overflow on phones.
- `<br>` is stripped and `<img>` in a title isn't rendered. `display:block` spans inside one
  tag render inline in lead and pack titles: one line per tag.
- A store section title renders its top-level elements in a row: put a multi-line title in
  one `<h2>` of block spans.
- FAQ questions need `<h4>`. Button labels, promo redeem text, custom-button and lightbox
  labels are plain text, not HTML.

**Blocks and layout**

- `enable: false` is ignored for lead platforms, FAQ questions and requirement platforms:
  remove those entries. Hide a whole block with `hidden: true`.
- A patch can report success and change nothing: the response then lists `"patches": []`.
  Read the block back after every patch. Layout blocks, such as the sidebar and footer,
  need the `values` prefix in patch paths.
- Bento: `layout.align` is horizontal and `layout.justify` vertical. It has about 58 px of
  vertical padding with no field for it, and its leaves collapse to text height on phones.
- The Description block's columns style wraps three items as 2+1: use a three-leaf bento
  for three columns.
- Federated blocks keep short refs (`I:x`, `L:x`); a URL in place of a ref renders an empty
  block.

**Header, hero and navigation**

- The lead block has no button, and some templates' headers have no logo slot. Don't draw
  either in a mockup unless the block has it.
- The header logo fits by height: pad it to about 3:1. The footer logo is a 150 × 150 cover
  crop: use a square PNG. Avoid SVG logos.
- More than four navigation links go into the burger menu on desktop. On phones, links show
  only while the first one fits beside the logo.
- The header's cart and login are components added in the editor: keep them when patching
  header components.

**Store sections**

- One item type per section; currency packs need a `virtual_currency` section.
- A section's title is hidden when the block's `values.description.enable` is false.
- Bundle cards show what a bundle contains only with `itemsDescriptionEnabled: true`.
- Anchor tabs render long section titles as pills, and the featured layout truncates long
  titles: keep them short.

**Workflow**

- The editor canvas and the preview differ: judge the preview.
- An open editor tab overwrites changes made through the CLI. Before the first write, ask
  the developer once to close the site's editor tab, in the same message as the plan.

## Visual review before handoff

After the theme, artwork and catalog are applied, open the preview at a desktop and a mobile
width and look at screenshots of every page. Fix what they show, then look again. Check:

- background transitions and product-image seams;
- one font family per role, and readable contrast over every image;
- mobile crops of backgrounds, title wrapping, card rows that look unfinished, button and
  price alignment, horizontal overflow;
- the hero's call to action, and that a sticky header doesn't cover a section heading after
  an in-page scroll;
- copy that promises something real: a login prompt names a benefit, and "see more" appears
  only when more exists.

The developer's yes to the plan covers only background fixes on blocks this assembly
created, applied with `scripts/patch_backgrounds.py` (see `SKILL.md`). An image must be one
uploaded to the site with `upload-asset`, and a gradient must have the shape of one already
on the site. Show anything else the review finds, such as theme, font, wording or layout
fixes, and ask before changing it.
If the preview can't be opened, say the visual review wasn't done and why: the CLI preview
permission error in [test-findings.md](test-findings.md), or a site without the common
layout, which private preview doesn't open. Don't report the site as reviewed.

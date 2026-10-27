# Visual style: the game's look, backgrounds, gradients and tints

The first draft the developer sees should already look like their game. Flat template
colors, placeholder art and hard section edges read as unfinished.

## Start from the game's identity

- Use, in this order: the brief's `brand` (logo, hero image, colors, fonts), then the art
  on the game's public store page that `description-to-shop` recorded (app icon,
  screenshots, key art), then the developer's own files. The plan lists every asset and
  where it came from.
- Take the palette from that art: a dark or light base, one accent for calls to action, and
  one or two supporting colors. Keep it on every page.
- Without key art, build section backgrounds as gradients in that palette, not one flat
  color.
- Upload images with `upload-asset` and use the returned CDN URL. Never hotlink a store page.
- Every product and pack gets its own artwork before the first handoff, consistent in style.

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

These fixes are cosmetic: the developer's yes to the plan covers them (see `SKILL.md`). If the
preview can't be opened, say the visual review wasn't done and why: the CLI preview
permission error in [test-findings.md](test-findings.md), or a site without the common
layout, which private preview doesn't open. Don't report the site as reviewed.

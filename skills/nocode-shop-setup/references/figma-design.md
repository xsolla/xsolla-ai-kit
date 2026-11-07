# Matching a Figma design in Shop Builder

Use these rules whenever a Shop Builder site, new or existing, has to look like a Figma design.

## Hard rules

1. **Standard blocks first.** Build each section with the theme, block settings, images in standard image
   slots and Design mode styles.
2. **Custom Blocks only for really hard layouts.** A Custom Block is a React component that Shop Builder
   compiles and hosts (`xsolla shopbuilder create-custom-block`). Use one only for a section whose Figma layout
   standard blocks can't reach, under the conditions in "When a Custom Block is allowed".
3. **Never custom code.** Custom code means:
   - the Custom code (HTML) block
   - a block script (the per-block custom JS, `values.script`)
   - CSS or JS that restyles, hides or changes other blocks or the page ("style layers"), even from inside a
     Custom Block
   - partner customization bundles (`customIntegrationUrl`)
   - external scripts, iframes, fonts or trackers added to the page
4. **Never touch existing custom code.** Don't edit, move, extend or delete custom code already on a site.
   Build the standard version, or a Custom Block, beside it. Hiding it needs the user's yes; deleting it needs
   the user's explicit OK.
5. **Live data stays live.** Prices, timers, purchase limits, items, cart and login always come from the
   catalog: through standard blocks, or through Shop Builder's hooks inside a Custom Block. Never bake them
   into images or hard-code them.
6. **Safe writes.** Never publish. Back up each block before writing, send one patch per call and read it back.
7. **Exact means checked at 1440, 1024 and 390 px** against the Figma frames. Whatever still can't match goes
   on a limits list shown to the user. Never approximate silently and never fall back to custom code.

## Pick a tool for each Figma element (first match wins)

| Figma element | Tool |
|---|---|
| Colours, fonts, type scale, radius, button style | Theme tokens, saved as a skin (preset) |
| Section order, card layout, columns, tabs, text colour, which fields show | Block settings |
| Scenes, characters, logos, frames, plates, ornaments | Images in standard slots: block or hero background, logo, slider slides, item images, Daily or Offer chain backgrounds, Bento image components |
| Card look: rim, glow, gradients, radius, padding, plate, badge or corners on a live card | Design mode (Element inspector) styles, with overlays as background layers |
| A static card with no live data (club, promo, banner) | The whole Figma card as one image in a Bento image component, with the cell's click action |
| A whole section whose layout the rows above can't reach | A Custom Block (see below) |
| A small detail the rows above can't reach | The limits list, shown to the user |

## When a Custom Block is allowed

All of these must hold:
- **The layout is really hard.** The standard build was tried, or a known limit rules it out, and the gap
  breaks the section's look, not just a detail. Typical cases: desktop and mobile arrange the section
  differently, elements overlap in ways standard layouts don't allow, or Design mode can't reach the elements
  (it has no per-width values).
- **One Figma section per block.** Header, footer, store, rewards and any other section that standard blocks
  can match stay standard.
- **It's built with Shop Builder's tool.** It imports only from `react` and `@site-builder/block-utils` and
  passes the platform's Custom Block code checks.
- **It's self-contained.** Its styles are scoped to the block's own root. It never styles, hides or changes
  anything outside itself, and it loads nothing from outside Xsolla.
- **It's editable without code.** Texts are localizable fields and images are uploaded assets, exposed in the
  block's settings panel where possible.
- **Its commerce is live.** Prices, buying, items, limits and login use Shop Builder's hooks.
- **It has both layouts.** It draws the Figma desktop and mobile frames.
- **It's approved.** The plan names the block and why the standard build can't match, and the user says yes
  before it's created.

## Steps

1. **Audit.** In Figma, find the desktop and mobile frames, list every section and mark each element live or
   static. On an existing site, read the structure (`xsolla shopbuilder get-structure`), mark custom code as
   untouchable and keep what already matches.
2. **Plan.** Map every element to a tool, name any Custom Block with its reason and list the limits. Get one
   yes.
3. **Art.**
   - Export the exact Figma nodes at 2x. Never redraw them.
   - Keep transparency. If an export is opaque, key out only the fill and check that no text was removed.
   - Static titles may be in the image; live text never.
   - Draw item images with the card's own background.
   - Overlays that must fit phones are at most ~320 px wide.
4. **Build.** Apply the theme, then block settings, then images, then Design mode, then Custom Blocks. Work on
   one block at a time, smallest change first.
5. **Verify.**
   - Preview at 1440, 1024 and 390 px next to the Figma frames.
   - Look for crops, overlaps, collapsed cells, duplicate titles and cut-off numbers.
   - If a change fixes one width but breaks another, revert it.
   - Report what matches, what differs and why, and that nothing was published.

## Platform limits and gotchas

- **Design mode (beta) has no per-width values:** one style applies at every width.
  - Elements that share an editor id get the same style.
  - The card title and the add-to-cart button aren't editable.
  - Background positions need the unit `%`, not `percent`.
- **Duplicate card title:** set the section layout's text colour to transparent.
- **Bento on phones:** a cell's height comes from its content. Put the art in an image component, not only in
  the cell background.
- **Blocks:** there's no per-device visibility, and the Hero logo box is a fixed 280 px.
- **Modules:** Daily rewards and Reward or Offer chain modules have no Design mode. Only their backgrounds and
  accent colour can change.
- **Theme tokens:** colours and sizes only, no images.
- **Catalog Admin PUT replaces the whole item:** GET it, change it, PUT it back and read it back.
  `description` is required.

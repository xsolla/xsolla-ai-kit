# Figma to custom blocks

When the request links a Figma file (`figma.com/design/…`, `/file/…`, `/proto/…`,
`/make/…`), the developer's design is the site. Build all of it with custom blocks: React
components that Shop Builder compiles and hosts (`xsolla shopbuilder
create-custom-block`). Don't propose a preset, a standard-block layout or another look,
and don't ask whether to use the design.

## What stays a standard block

Only what runs Xsolla commerce or sign-in: the Store block (`newStore`) for the catalog,
cart and checkout, and the header's sign-in when the design has one. Give them the
design's palette and fonts (`brand.theme`) and put them where the design has them.
Everything else in the design is a custom block: hero, banners, feature sections,
galleries, item showcases, FAQ and footer.

## Before the first message

- Run `xsolla shopbuilder create-custom-block --help`. If the usage line doesn't name
  `create-custom-block`, say in the first message that this CLI can't create custom blocks
  yet. Put the choice in the batch: wait for a newer CLI (recommended), or build with
  standard blocks styled after the design.
- Read the design with the Figma tools in this session: the file's pages, their top-level
  frames, a screenshot of each, and each section's design context (layout, text, colors,
  fonts, images). Read the desktop and mobile frames when the file has both. If this
  session can't read Figma, say so, and ask in the batch for each page's frames exported
  as PNG.
- Each Figma page is a site page. Each top-level section of a frame, top to bottom, is
  one block.

## The plan

For each page, the plan lists its blocks in order. For each block it gives the Figma frame
(name and screenshot) and whether the block is custom or standard. For a custom block it
also gives the text the block shows, word for word, and the images it uses. The Figma
screenshots are the mockup. The one yes covers creating all of it.

## Building

After the yes, the storefront skill builds the pages and the standard blocks first: every
apply run and the theme. Then:

1. Upload each image the design uses with `xsolla shopbuilder upload-asset --landing-id <id>
   --file <file> --type image`, and use the CDN URL it returns. No other image host.
2. Write each custom block as one default-exported React component (TSX). It must match
   its frame at 1440 px and its mobile frame at 390 px; with no mobile frame, make the
   desktop design responsive. Keep styles inside the component. Take colors and fonts from
   the design, and text word for word. No calls to other hosts, and no trackers.
3. Create it on its page: `xsolla shopbuilder create-custom-block --landing-id <id>
   --page-id <id> --name "<frame name>" --component-code "$(cat <file>.tsx)"`. A `400`
   means the component didn't compile: fix the TSX and run the command again. Record the
   returned block ID with the frame name in `custom-blocks.json`, next to the approved
   plan.
4. On a rerun, a block already in `custom-blocks.json` is changed with
   `xsolla shopbuilder update-ai-block --id <id> --component-code "$(cat <file>.tsx)"`, never
   created again.
5. Put the blocks in the design's order with `move-block`, reading `get-structure` again
   after each move. In `get-structure`, a custom block shows as a `federated` block.
6. Check `xsolla shopbuilder get-ai-block --id <id>` returns the code you submitted and
   that every page's blocks are in the design's order.

Create the custom blocks after the last `apply_plan.py` run. Don't run `apply_plan.py`
on the site after that: its plan doesn't list custom blocks and would remove them.

## Visual review

Compare each page at 1440 and 390 px with its Figma frames, as the visual review in
`shop-builder-assembly` describes. Fix a block with `update-ai-block` and look again.
Put the Figma frame and the site screenshot side by side in the handoff.

# Theming and fonts

## Patch `calculatedTheme`, not `input`

A modern landing has `theme.calculationType: "xds-theme"` and two colour objects:

- `theme.input` — the handful of source colours the **GUI editor** compiles from.
- `theme.calculatedTheme` — the full token set the **renderer** actually consumes.

Patching `theme.input` over the batch API succeeds, reads back correctly, and **changes
nothing on screen**: the server does not recompile `calculatedTheme` outside the editor,
so the site keeps rendering the stock palette (hot pink `rgba(255, 0, 91, 1)` buttons,
near-black `rgba(21, 21, 31, 1)` cards).

`calculatedTheme` **is** directly patchable, and that is what works. (The `shopbuilder`
skill's note that patching it is ignored is wrong — verified against a live landing.)
Patch both `input` and `calculatedTheme` so the GUI and the renderer agree.

Expect on the order of a hundred targeted patches. Generate them from a palette dict in a
script rather than writing them by hand.

## The token map

Under `theme.calculatedTheme.colors`, in two groups:

### `control.*` — buttons and inputs

| Token | Drives |
|---|---|
| `primary.{bg,bg-hover,bg-press}` | the main CTA button |
| `secondary.{bg,border,border-hover}` | outline button |
| `tertiary.bg` | a third button style |
| `default.bg` + `control.text.default` | **defaults to a near-white button with near-black text** — badly out of place on a dark site. Always set both. |
| `faint.*`, `check.*`, `toggle.*`, `input.*` | chips, checkboxes, switches, fields |
| `focus.border` | the focus ring |
| `text.{primary,secondary,tertiary,default}` | label colour *on* each button variant |

### `core.*` — surfaces and page text

| Token | Drives |
|---|---|
| `background.primary` | the page background (stock value is `transparent`) |
| `background.secondary` | section / card surface |
| `card.item-bg` | card surface in some layouts |
| `background.ghost` | the tint over a card's image panel |
| `background.mask` | modal backdrop |
| `divider.divider` | hairlines |
| `link.link`, `link.link-hover` | links |
| `text.{primary,secondary,tertiary,neutral}` | body copy ramp |
| **`text.brand`, `text.brand-secondary`** | **the store card's buy-button fill.** Misleading names — these are not text colours in practice. |

That last row is worth repeating: if the product-card buy buttons are the wrong colour,
it is almost certainly `core.text.brand` / `core.text.brand-secondary`, not any
`control.*` token. Identify it by sampling the rendered pixel and tracing which token you
last set to that exact value.

Also sync `calculatedTheme.palette.input` — it is a stale snapshot of `theme.input`.

When you're done, grep the serialized theme for leftovers and expect zero hits:

```
rgba(255, 0, 91      # stock pink
rgba(166, 242, 13    # stock lime
hsl(34               # stock pink/amber hsl variants
```

## The page theme layer

A page carries its own theme with an `enabled` flag. When `true` it **overrides the site
theme at render**. Page-scope patches to `theme.calculatedTheme` are silently dropped
(other page patches, including `theme.input` and `["name"]`, do apply), so:

> Set the page's `theme.enabled` to `false` and drive everything from the site layer.

```
update-block --landing-id <L> --data '{"p":{"type":"page","id":"<pageId>","patches":[
  {"op":"replace","path":["theme","enabled"],"value":false}]}}'
```

`buttonBorderRadius` is the global corner radius (buttons *and* cards).

## Fonts

`theme.fonts` is three slots — `display` (h1–h4), `text` (body), `controls` (buttons,
tabs, labels) — each `{default: {__type: "font-name", name: "<family>"}}`. The `name` is
just a string: if nothing resolves it, the browser falls back, and body copy lands on a
serif.

**A name only resolves if a font asset with that exact `fontFamily` is uploaded to the
landing — and `fontFamily` is derived from the uploaded file's name.** So name the file
after the family you want:

```bash
# uploading "Archivo Black.woff2" registers fontFamily "Archivo Black"
xsolla shopbuilder upload-asset --landing-id <L> --file "Archivo Black.woff2" --type font --json
```

Then set the slot to that same string. Accepts woff/woff2/ttf/otf, max 10 MB. One file
per family registers a single weight; the browser synthesises the rest, which is fine for
a display face and acceptable for body text.

**Before blaming the font, check the copy.** Localized rich text must be HTML — a bare
string renders unstyled and drops to the browser serif, which looks exactly like a
failed webfont. Wrap body copy in `<p>`/`<h2>`; control labels don't need it.

If a section must be typographically exact, put it in a custom block that loads its own
webfonts — that removes the whole question.

## Section backgrounds

A block's `background` has `color`, `gradient`, `img`, `position`, `size`. **An opaque
`color` paints over `img`**, so a section with a background image renders flat. Template
defaults use `rgba(0,0,0,0.0)` for exactly this reason — keep it transparent whenever
`img` is set:

```
{"op":"replace","path":["values","background","color"],"value":"rgba(0, 0, 0, 0)"}
```

`size: cover` + `position: center` is the combination known to render. Because
`leadGameSales` has no image slot, comp art for a hero has to be composited into that
background image — or the section rebuilt as a custom block, which is usually better.

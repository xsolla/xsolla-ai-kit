# Quests block appearance

Use this reference only when the publisher asks to fit, choose or change the
appearance of the Quests block. Do not run this workflow for a card-text, quest-order,
visibility or general block question. It changes this block only; site and page themes
and other blocks are out of scope.

## Inspect before recommending

Read the selected site's current block summary and page structure. Inspect the actual
rendered page or editor preview at 375, 768 and 1440px. Record evidence privately in the
current run, not in extra files or the publisher reply:

| Evidence | Record |
|---|---|
| Quests block | Exact module ID, saved block version, selected `themeId`, and recognized saved appearance from `appearance` in the summary |
| Page composition | `page_modules` IDs/order from the summary, including header/footer, the surrounding banner and FAQ/Games content container |
| Computed neighbors | Font family, loaded status, size, weight, line height, color, container width, gutters, section/card padding, gap, radii, button size and alignment |
| Responsive result | Whole-page alignment, the continuous Quests grid, clipping or horizontal overflow, and image treatment at each viewport |
| Explicit preference | Theme the publisher asked for in the current conversation. A saved `themeId`, especially `site-builder`, is not proof that the publisher explicitly chose it. |

Use module IDs and the visible composition from this page. A dark palette, a familiar
color, one similar footer, or a saved theme value alone does not establish that a page
uses Xsolla Pages. Recommend Pages only when the actual neighboring module composition
and rendered page show Pages. Recommend Site Builder when the surrounding page uses its
native inherited appearance. Recommend Custom when measured differences remain after
the closest preset. On first entry into Custom, keep the previously selected known
preset as `baseThemeId` and use bounded overrides for the measured differences.
Omitted Custom leaves inherit that base preset. A measured line height is in pixels;
for the matching semantic role, set the Custom line-height multiplier to
`measured_line_height_px / measured_font_size_px`. Do not pair a size from one role
with the line height from another.

Treat each Custom field as applying to every semantic consumer wired to that field.
`headingSize` and `headingLineHeight` affect the Quests section heading, while
`headingFont` also affects card title fonts. Body typography reaches descriptions,
helper/status/reward/tag text; button typography reaches action labels. Before calling
a Custom profile an ideal page fit, measure every affected role at mobile and desktop
sizes and compare the whole page. Do not use an unverified loaded-font name; keep the
base font through `host-body`, `host-heading` or `host-button` when needed.

If the publisher explicitly asks for a theme, preserve that choice even if the page
evidence suggests another fit. If they ask for a recommendation or a site fit, recommend
from page evidence even when the saved value is only a default. Never change `themeId`
until the publisher approves the exact plan. A recommendation is not a write request.

For recommendation or fitting requests, if the rendered page or its computed styles
cannot be inspected, do not invent a font, measurement or Pages identity. Recommend the
current safe inherited appearance and make no fit-based appearance write until evidence
is available. For an explicit request to select a supported preset or set exact bounded
values, plan that request directly after saved-state and version preflight; do not claim
it is a measured fit. Use a host font token or inherit the base unless the exact font is
visibly rendered and verified loaded. A font name accepted by the gate is not proof that
the page has loaded that font.

## Fit the block to the page

Compare the Quests section and its neighbors as one page. Preserve quest order, IDs,
localized text refs, card overrides, auth, rewards, banner artwork and surrounding page
composition. Leave opaque legacy action fields untouched; do not infer or claim their
behavior. Fix a copy or reward-data mismatch in its owning quest flow, never through
appearance or a hard-coded card label.

- Preserve the existing Pages banner above the surrounding content. Render Pages Quests
  as a uniform, image-first 16:9 card grid without a featured first card, rail, carousel,
  pagination or hidden page groups. Keep all selected quests visible up to the saved
  `maxQuests` cap, in saved order.
- Use three columns at desktop, two at tablet and one at mobile. Align the Quests heading
  and grid to the measured FAQ/Games content container within 8px. At each viewport,
  check that the grid wraps naturally without clipping, horizontal scrolling or reserved
  blank page height. Cards without an image keep the same media frame with a neutral,
  accessible placeholder.
- Keep the original Pages preset's 72px display heading by selecting Pages and omitting
  Custom heading overrides. In Custom, `headingSize` and `headingLineHeight` control the
  section heading only; card titles inherit the base.
- Use the adaptation spec's pinned comparison assets only as references. Where the
  source reference is available, approved component geometry should match within 2px.
  Document a deliberate full-bleed exception instead of forcing it into the container.
- Check 320px for overflow and 375, 768 and 1440px for whole-page alignment and grid
  wrapping. Apply only the smallest supported correction, then reload and compare the
  whole page again.

Normal text and interactive text need at least 4.5:1 contrast. Large text, visible
component boundaries and focus indicators need at least 3:1 against adjacent surfaces.
Check default, hover, pressed and focus states. Omit `actionText` to use the block's
safe derived color; an explicit `actionText`/`accent` pair below 4.5:1 is rejected.

## Supported settings and safe bounds

The reviewed gate is authoritative. Use only the leaves below and its exact operation
envelope; never patch a whole appearance object. The gate rejects any leaf outside this
list; do not invent additional paths.

- `themeId`: `site-builder`, `xsolla-pages` or `custom`.
- Preset leaves under `themeAppearance.site-builder` and
  `themeAppearance.xsolla-pages`: `cardAlign` (`start`, `center`, `end`),
  `blockBackground` / `cardBackground` (`transparent`, `primary`, `secondary`), and
  `buttonStyle` (`primary`, `secondary`, `tertiary`, `theme-default`).
- Custom V1 needs `version: 1` and a `baseThemeId` of `site-builder` or `xsolla-pages`.
  On first entry, `baseThemeId` is the previously selected known preset; do not switch
  that base merely because another preset looks closer in one measurement.
  Palette leaves are `accent`, `sectionBackground`, `cardBackground`, `primaryText`,
  `secondaryText`, `border`, and `actionText`, each a literal `#RRGGBB`.
- Custom font fields are `bodyFont`, `headingFont`, and `buttonFont`; use `host-body`,
  `host-heading`, `host-button`, or a `loadedFont` family already verified loaded on the
  page. A `loadedFont` family must match `[A-Za-z0-9 _-]{1,64}`: reject anything else
  (quotes, semicolons, commas, other characters) before proposing it. Weights are 400, 500, 600 or 700. Heading/body/button
  sizes are 16-64/12-24/12-24px. Line-height multipliers are finite 1-2 and the gate
  rounds them to two decimals using JavaScript positive rounding.
- Custom geometry: `maxWidth` 640-1920; `gutter` and `mobileGutter` 0-64;
  `sectionPadding` 0-128; `cardPadding` 8-64; `gap` 8-48; `radius` and `buttonRadius`
  0-32; `buttonHeight` 32-64; `columns` 1-4; `railInset` 0-20 percent. These values
  are integers. Responsive layout must fit 320px without horizontal overflow.
- Omitted values inherit the selected base. Custom reset removes known palette,
  typography and geometry overrides only; it preserves `version`, `baseThemeId`,
  unknown saved fields, other theme maps and unrelated block data.

Custom `maxWidth` is the container's outer border-box width and includes its inline
padding. When neighboring page content measures 1184px and has 32px gutters on both
sides, record those as 1184px content width and 32px gutter, then use
`maxWidth: 1248` (`1184 + 2 * 32`) with `gutter: 32`. Keep measured content width,
border-box width and gutter as separate evidence; a content width is not itself the
Custom `maxWidth` value.

`railInset` remains a gate-recognized field for saved appearance compatibility. It does
not apply to the new Pages grid; do not set it or use it to create a rail.

For an approved update, use dotted leaf keys inside the operation's `values`, for
example:

```json
{"op":"update","block_id":"<block-id>","values":{"themeId":"custom","themeAppearance.custom.version":1,"themeAppearance.custom.baseThemeId":"site-builder","themeAppearance.custom.typography.headingSize":32,"themeAppearance.custom.geometry.maxWidth":1184}}
```

This is a shape example, not a recommended design. Use only measured and approved
values. Follow the saved-version checks, explicit new-block version and unsupported-version
fallback in [block-versions.md](block-versions.md). Never infer support from version ordering
or package metadata, or change an existing block's version.
Preserve a before snapshot and, after a new block at a supported version is approved and
added, read back quest IDs/order, refs, overrides, layout, auth and all unrelated saved
fields before any appearance edit. Do not promise downgrade preservation unless it is
verified.

The requested Backpack button under Web3 rewards must open the installed stock Overlay.
The current deployed Quests v1 has no supported host API for that action, so this feature
remains blocked until a supported contract ships. Do not substitute external/new-tab
navigation, add an app-owned controller, or claim the old external Backpack flow as this
integration. Treat obsolete saved action-looking fields as opaque unknown data: never
display, interpret, initialize, migrate, write or delete them. Normal quest and reward
approval gates still apply.

## Fully custom design

Collect brand inputs: colors, fonts, radii, spacing, button style, columns and any CSS
sample, URL or screenshot. Map them to `themeId: custom` plus bounded
`themeAppearance.custom` leaves above. Validate each value; never silently clamp.
Clamp only after agreement, or ask. List the properties the schema cannot express: arbitrary CSS,
stylesheet injection, runtime font loading, card structure/placement beyond grid and
Pages layouts, or per-element colors beyond the palette. If the design needs these,
state the limitation and offer a Site Builder or Xsolla Pages theme, or the
[headless module](web-shop-module.md) outside Site Builder. Make no write until the
publisher chooses.

## Apply and verify

After evidence and recommendation, put only agreed leaves in the brief and follow
[Gate commands](quests-block-brief.md#gate-commands), including its separate sandbox yes,
exact saved plan/confirmation and no `--run-report`. Stale/foreign targets, invalid
values/contrast, unsupported versions, missing capability or failed preflight mean zero writes.

After apply, reload and read saved state: compare normalized appearance, `themeId`,
quest IDs/order/refs/overrides and unrelated fields with the approved plan. Opaque legacy
fields stay untouched. Compare the whole page at the inspected viewports; any bounded
correction needs a new confirmed plan. Never publish automatically.

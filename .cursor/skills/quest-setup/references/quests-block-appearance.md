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
| Quests block | Exact module ID, saved block version, selected `themeId`, `backpackAction`, and recognized saved appearance from `appearance` in the summary |
| Page composition | `page_modules` IDs/order from the summary, including header/footer, FAQ/Games content container, featured artwork and regular-card rail |
| Computed neighbors | Font family, loaded status, size, weight, line height, color, container width, gutters, section/card padding, gap, radii, button size and alignment |
| Responsive result | Whole-page alignment, card/rail behavior, clipping or horizontal overflow, and preserved artwork composition at each viewport |
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
localized text refs, card overrides, auth, rewards, button action, banner artwork and
the existing featured/regular card composition. Fix a copy or reward-data mismatch in
its owning quest flow, never through appearance or a hard-coded card label.

- Keep the Pages artwork banner featured first, with its 50/50 artwork/content split
  and 353px desktop composition. Keep the regular-card composition. For no-image cards,
  retain a compact content/reward/action grouping without a blank half-card.
- Align a Custom Pages Quests heading, featured card and regular rail to the measured
  FAQ/Games content container within 8px; use `railInset: 0` only when that measurement
  supports it. The Pages preset's existing 11% rail inset remains available; omitting
  `railInset` preserves it. `railInset` applies only to the Pages desktop regular rail.
- Keep the original Pages preset's 72px display heading by selecting Pages and omitting
  Custom heading overrides. In Custom, `headingSize` and `headingLineHeight` control the
  section heading only; card titles inherit the base. A 32px/32px section heading can
  coexist with the Pages featured title at 32px/32px and regular title at 18px/24px.
- Use the adaptation spec's pinned comparison assets only as references. Where the
  source reference is available, approved component geometry should match within 2px.
  Document a deliberate full-bleed exception instead of forcing it into the container.
- Check 320px for overflow and 375, 768 and 1440px for whole-page alignment. Recheck
  both ends of a rail and its focus/scroll controls. Apply only the smallest supported
  correction, then reload and compare the whole page again.

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
  `host-heading`, `host-button`, or a safe 1-64 character `loadedFont` family already
  verified loaded on the page. Weights are 400, 500, 600 or 700. Heading/body/button
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

For an approved update, use dotted leaf keys inside the operation's `values`, for
example:

```json
{"op":"update","block_id":"<block-id>","values":{"themeId":"custom","themeAppearance.custom.version":1,"themeAppearance.custom.baseThemeId":"site-builder","themeAppearance.custom.typography.headingSize":32,"themeAppearance.custom.geometry.maxWidth":1184}}
```

This is a shape example, not a recommended design. Use only measured and approved
values. For `add`, ordinary creation remains stable `0.1.5`; select exact candidate
`0.2.2-qp-3256.0` with the explicit `version` field only when the requested appearance
needs its capability, and show that version in the plan.

The exact appearance/action capability is candidate `0.2.2-qp-3256.0` only. Ordinary
block creation remains pinned to stable `0.1.5`; never change that default. Never infer
support from version ordering or package metadata. Existing-block updates/resets require
the exact supported version in saved readback. If the block version or schema is
unsupported, stop before the plan/write and report a verified-upgrade gate. Preserve a
before snapshot and, after an approved upgrade, read back quest IDs/order, refs,
overrides, layout, auth/action and all unrelated saved fields before any appearance edit.
Do not promise downgrade preservation unless it is verified.

## Completed-quest action ownership

`backpackAction` selects the button action shown for a completed quest (`external` or
`overlay`). Appearance fitting preserves its current choice. A Pages recommendation never
changes `external` to `overlay`; an action change needs its own explicit request and
confirmed plan.

The official Overlay block independently owns its host, loader and authentication.
Never offer its setup from the Quests flow, infer that it is installed or ready from
legacy Quests `backpackOverlay` data, or read, migrate or rewrite that erroneous config.
Do not add owner, host, loader, auth, bootstrap or lease fields to a Quests operation.
If the independent owner is unavailable, report that prerequisite without attempting
auth or security changes. The source guard requires `auth.type` to equal `xsolla-id`;
an enabled flag alone is insufficient. Do not change authentication.

## Apply and verify

After the evidence table and recommendation, put only the agreed block leaf changes in
the gate brief. Preflight the complete operation set before any mutation. A stale or
foreign target, invalid value/contrast, unsupported version, missing capability or
failed preflight means zero writes. Show the exact plan and get a later yes to that plan;
the sandbox command confirmation, when required, is a separate stop described in
[the block flow](quests-block-flow.md#hard-rules).

After approval, apply with the saved `approved-plan.json` and its exact
`confirmation_id`. Do not pass a `run-report` for this single operations run. Reload the
page and read saved state back. Compare the normalized saved appearance, selected
`themeId`, preserved `backpackAction`, all quest IDs/order/refs/overrides and unrelated
fields with the approved plan. Then compare the full page at the inspected viewports and
make only a bounded correction through a new confirmed plan. Never publish automatically.

## Scenario fixtures

Use the synthetic cases in `tests/fixtures/appearance/` for repeatable agent checks.
Every case supplies observed page evidence, user intent, saved state before, expected
recommendation/action, and saved state after. A generated plan alone is not a pass.
Record the saved readback after each fixture execution and compare it with the expected
state. The fixture IDs and module names are synthetic and are not live sites.

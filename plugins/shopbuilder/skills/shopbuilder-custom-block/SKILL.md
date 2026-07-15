---
name: shopbuilder-custom-block
description: >-
  Advanced escape hatch for the Shop Builder hierarchy: author and deploy a custom React block
  when the native blocks and update-block customization cannot achieve the layout, styling, or
  behavior you need. Covers the gate (try native first), the block authoring contract (data from
  block values not props/state, defaults, SSR-defensive code, scoped styling), and the AI Custom
  Block deploy flow (compile-on-deploy, the 400-diagnostics iterate loop, publish, render to
  verify). Use only for advanced styling or functionality a native block cannot express; for
  copy, images, sections, and per-block theme, use shopbuilder-customize instead. Part of the
  shopbuilder-storefront set.
metadata:
  domain: shopbuilder
  kind: escape-hatch
---

# Shop Builder: Custom block (advanced)

A custom block is a React component you deploy to a Shop Builder landing when the native blocks
plus `update-block` customization genuinely cannot express what you need. **It is an escape
hatch for advanced styling and behavior, not the default way to build.** Reach for it last.

## The gate — exhaust the native path first

Before writing a line of React, confirm the effect is impossible with the normal Shop Builder
API. Most "custom" needs are already covered:

- **Copy, hierarchy, rich text** → HTML in a `localized-value-descriptor` (shopbuilder-customize).
- **Images, backgrounds, darkening** → `upload-asset` + block image fields + `background.gradient`.
- **Colors, fonts, buttons, radius, blur** → per-block and page `theme` fields.
- **Catalog layout** → `newStore` sections and layout types (`featured`, `vertical`, …).
- **Engagement modules** → the `federated` block (offer chain, daily reward, offerwall).

A custom block is justified only when the design needs layout, interaction, or styling that
none of the above can produce — a bespoke component, an unusual grid, an animation, a custom
data presentation. If you can do it with `update-block`, do it with `update-block`: native
blocks survive platform updates and stay editable in Publisher Account; a custom block is code
you now own. When unsure, state what the native path can't do and confirm before building.

## What a custom block is

You write a React component as **source text** and send it to the **AI Custom Block API**. The
server **compiles it** into a Module Federation bundle, stores it, and attaches it to a page;
you then publish. There is **no local build, no Vite, no pnpm, no repo** — just the source and
authenticated calls. (A separate heavy "curated block" monorepo path exists; ignore it here —
this path exists so a block can be deployed from nothing.)

The block's editable data lives in **`internalBlockValues`**, seeded from the `defaultData` you
send. The bundle is served at a `host` URL and loaded at runtime by the browser's MF runtime.

## The authoring contract

These rules hold regardless of the exact injected hook API, and following them is what keeps a
block from failing to render after publish:

- **Read data from the block's values, never from props or local component state.** Content,
  config, and platform context come from the block's data (`internalBlockValues`) via the host's
  injected hooks. If you are threading content through props or holding it in `useState`, stop.
- **Every configurable default lives in `defaultData`** — the block's source of truth. The
  component reads values; it never hard-codes its own fallback literals.
- **Keep user-facing text as localizable data, not hard-coded strings,** wherever the block is
  meant to be edited — labels, copy, `alt`, CTA text.
- **Be SSR-defensive.** Guard every browser-only API (`window`, `document`, `localStorage`,
  `sessionStorage`, `navigator`, `matchMedia`) behind `typeof window !== "undefined"` or run it
  inside `useEffect`. Never compute a module-scope constant from the browser
  (`const isMobile = window.innerWidth < 768` at top level crashes the render) — derive it in
  `useEffect` and store in state. Unguarded browser access at module scope is the single most
  common way a block fails.
- **Keep components small,** structured props → logic → JSX, with early returns over deep
  nesting. Give async UI real skeletons, not `return null` (which causes layout shift).
- **Discover the injected hook API — don't invent it.** The exact in-component hook for reading
  `internalBlockValues` and wiring the settings panel is not fixed here. Confirm it from a
  known-good example block or from the deploy call's compiler diagnostics (below). Start
  minimal, deploy, read the errors, iterate.

## Styling — the reason you're here

Advanced styling is the main legitimate use. Do it without breaking the page:

- **Scope every style to your block** (a stable root class or CSS-module scoping) so it cannot
  leak onto sibling blocks on the page.
- **Never style against Shop Builder / SiteBuilder internals** (`xds-*` classes, platform
  wrappers). They change without notice and break your block.
- **Mobile-first**: unconditional styles for mobile, layered overrides at larger breakpoints.
- **Prefer design tokens / the block's theme values over hardcoded values;** avoid `!important`
  and inline `style={{}}` for anything the block should let the merchant theme.
- Use 6-digit hex or `rgba()`; keep the block visually consistent with the page theme.

## Deploy flow

The `xsolla shopbuilder` CLI has **no custom-block command** — the compile-and-attach step is an
HTTP call to the AI Custom Block API. Use the CLI for what it does cover (asset upload, id
discovery) and the API only for the deploy itself. Auth is the same `pa-v4-token` the plugin
already stores in `XSOLLA_SHOPBUILDER_SESSION`. Full endpoints and payloads:
`references/deploy-api.md`.

1. **Resolve ids.** `get-structure --slug <domain> --json` — the site document `_id` is the
   `siteId`; the target page's `_id` is the `pageId`. The deploy is keyed by these, not the slug.
2. **Upload any images first** with `upload-asset` and reference the returned CDN URL in
   `defaultData` (see shopbuilder-customize).
3. **Deploy** — POST the source (`componentCode`, optional `settingsCode`, `defaultData`, `name`)
   to `ai-custom-block`. The server compiles and attaches it. A **400 carries `details[]`
   compiler diagnostics — this is your iterate loop:** fix the source and update (PUT), or POST
   again if no block id was created. Start minimal so the first diagnostics teach you the API.
4. **Publish** the landing to make it live, then **render and eyeball the preview** — `ok:true`
   is not proof it renders (see shopbuilder-storefront, "Render to verify").
5. **Iterate** — PUT new source to recompile (preserves `internalBlockValues` unless you send a
   new `defaultData`); re-publish after any change you want live.

## Common pitfalls

- Reaching for a custom block when `update-block` (copy, theme, sections, images) would do it.
  The escape hatch is the last resort, not the first.
- Reading data from props/state instead of the block's values, or hard-coding defaults in the
  component instead of `defaultData`.
- Unguarded `window`/`document` at module scope — compiles fine, fails to render after publish.
- Styling `xds-*` internals or leaking unscoped global styles onto other blocks.
- Inventing the injected hook signature instead of confirming it from diagnostics or an example.
- Trusting `ok:true` / a healthy `get-structure` as proof — render the preview.
- Editing the landing in Publisher Account while deploying via the API; concurrent writers drop
  blocks and leave ghost references. One writer at a time.

## Verify

- The deploy returns a `blockId` and `host`; a 400's `details[]` is empty on success.
- `get-structure` lists the custom block on the intended page.
- **Render the authenticated preview** and confirm the block draws correctly, on mobile and
  desktop widths, alongside the native blocks — not just that the call returned `ok`.

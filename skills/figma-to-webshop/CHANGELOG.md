# Changelog

All notable changes to this skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.3.0] - 2026-10-08

Fixes the failure mode where a run asked the user which blocks to build with, was told
"custom blocks", lost `create-custom-block` to a 403 late in the build, and delivered a
complete native-only page — the one option the user had ruled out.

### Added
- **Step 0 now probes `create-custom-block` and `enable-preview`** before Step 1's
  question. Both authenticate with the publisher `pa-v4-token` cookie rather than the
  bearer token the rest of the CLI uses, so both fail late, at the moment of use, long
  after the build is committed to a path.
- **Step 1: "The answer is binding — never substitute the other option."** When the chosen
  path becomes impossible mid-build, stop and report in that turn; falling back is the
  user's call. `header`, `newStore` and `footer` keep working without custom blocks, so
  the native build completes smoothly and ships the wrong page — explaining the blocker in
  the final handover does not fix that.
- **Pitfalls: "The expensive one: delivering the option the user rejected"** — the full
  account of the 403, why `get-ai-block` reading fine proves nothing, and the
  `XSOLLA_SHOPBUILDER_SESSION` unblock.

### Changed
- **Build order on a custom-blocks build: publish one custom block as soon as the page
  exists**, before assets and before theming. Noted in Steps 2 and 4. Discovering the 403
  after the expensive work is the worst possible ordering.
- **Step 3 scales to the native surface.** Custom blocks ignore the site theme, so a
  custom-blocks build only themes `header`, `footer` and the clipped `newStore` fallback —
  a dozen tokens, not a hundred.
- Step 1 now says to offer only the options the Step 0 probe left standing.
- **SKILL.md rewritten dense and back under the 200-line limit** (201 → 199) while
  absorbing all of the above. Step 0's checklist and the pitfalls list became tables, the
  probe commands and the `pa-v4-token` unblock moved into `pitfalls.md`, and the three
  facts that were stated twice (the Step 2/Step 4 ordering note, the 403 explanation, the
  preview 403) are now stated once and cross-referenced. No guidance was dropped —
  verified by checking every backticked identifier, error code and numeric from the 0.2.0
  file still appears.

## [0.2.0] - 2026-10-05

### Added
- **Step 1 now asks the user** whether to build the store sections with standard (native)
  blocks, custom blocks, or both, instead of applying the function/decoration split
  silently. The split stays the recommendation; the choice is the user's, because
  reversing it later means rewriting every store block.
- **"Slice the design assets, rebuild the structure"** — an explicit prohibition on
  flattening a section or a product card into one raster image with transparent hit areas
  over it. Baked text cannot be selected, translated or localized, is invisible to screen
  readers, cannot reflow, and ignores the site theme. Adds a table of what is genuinely an
  asset versus what must be DOM, and points at `download_assets` for real source files.
- **"When the comp's card is non-negotiable"** in the native-vs-custom reference: how to
  render comp-exact cards while keeping cart, checkout and login native, by forwarding the
  buy to a hidden native store — including the guard against clipping a page-level wrapper
  and the warning that clipping the store also hides the only sign-in on the page.
- **`references/pitfalls.md`**, split out of SKILL.md as the list grew past the 200-line
  budget. Ten new entries, including: theme patches need `update-block` with
  `"type": "site"`; a currency package may hold exactly one currency, so combo cards must
  be bundles; new bundles stay invisible to the storefront until `admin-unhide-bundle`;
  storefront group listings lag while single-SKU reads do not; a fresh `newStore` ships
  four sections, not one; and `update-many-localization` needs a `perScopeValues` wrapper
  keyed by page `_id`.

### Changed
- **Step 0 no longer treats an unset `XSOLLA_API_KEY` as a blocker.** The CLI resolves the
  Store Basic key from the OS keychain as well as the environment, so the skill now gives
  a probe command to confirm before declaring the catalog unwritable.
- **Step 5 says to check up front that a rendered screenshot is obtainable at all.**
  `enable-preview` needs an account-admin token, not merchant owner; without it there is
  no CLI path to a render and the handover must say so rather than passing an API
  read-back off as visual confirmation.

## [0.1.0] - 2026-09-28

### Added
- Initial skill. Covers the design-to-storefront workflow that `shopbuilder` leaves
  open: how to read a comp, how to decide which sections stay native and which become
  custom blocks, and how to close the fidelity gap without breaking commerce.
- **Native-vs-custom triage** as the organizing rule — native blocks for anything
  functional (catalog, cart, checkout, login, legal footer), custom blocks for anything
  decorative — with a per-block capability/limit reference.
- **Theming reference** documenting that the renderer reads `theme.calculatedTheme` and
  that patching `theme.input` alone is a silent no-op. This corrects the `shopbuilder`
  skill, which states `calculatedTheme` is derived and unpatchable; it is directly
  patchable and is the only thing that takes effect. Includes the token map, the
  misleadingly-named `core.text.brand` (store card buy-button fill), the page-vs-site
  theme layers, and the font-asset naming contract.
- **Verify-and-iterate reference** establishing that a clean `get-structure` read is not
  evidence of correct rendering, with a pixel-sampling method for identifying which token
  drives an element, and a table of render traps that read clean.

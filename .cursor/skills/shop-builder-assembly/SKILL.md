---
name: shop-builder-assembly
description: >-
  Assemble a complete Xsolla Shop Builder storefront from a structured shop brief,
  working top-down from theme and pages through navigation, standard blocks,
  localization, and catalog links. Not the entry point for "build me a shop" — that is
  shop-setup, which routes here once the build path is Shop Builder and a validated
  brief exists (from description-to-shop). Use for AI-built Shop Builder sites, full
  website or webshop assembly,
  game-type storefront presets, mobile single-page shops, PC multi-page shops, and
  live-service stores with bundles or events. Prefer this skill over creating isolated
  Shop Builder blocks. Do not use it for a custom headless storefront; use shop-setup
  for that architecture.
metadata:
  owner: k.shah
  domain: store
---

# Shop Builder Assembly

Build an unpublished Publisher Account **Shop Builder site**, not a custom frontend,
in a dedicated non-partner test project through `xsolla shopbuilder`.

A Game Web Portal is built by `game-web-portal`, not here. First read `XSOLLA_SITE_KIND` with the
[build-path contract's check](../shop-plan/references/build-path-contract.md#the-site-kind-shop-builder-only):
for `portal`, hand off to `game-web-portal` and stop; an invalid value halts. A shop continues.

## Inputs

Normalize publisher answers, existing stores, descriptions, and designs into the
[shop brief](references/shop-brief.md). Writes require that brief; callers own source
extraction.

If `preset` is `auto`, choose in this order:

1. Live-service game with active events or rotating offers → `live-service-events`.
2. PC/console game needing content beyond purchase → `pc-multi-page`.
3. Mobile-first or purchase-focused game → `mobile-single-page`.

Before planning, read [presets](references/presets.md) and the
[block catalog](references/block-catalog.md). Before applying, read the
[exported contracts](references/exported-block-contracts.md) and
[CLI operations](references/cli-operations.md).

The official inventory is authoritative; its mappings and presets remain provisional
until [expert-review.md](references/expert-review.md) records approval.

## Non-negotiable safety gate

1. Run `scripts/preflight.py <brief.json> --approved-test-projects <local-allowlist.json>`.
   Read back the matched merchant ID, project ID, safety environment, approval reference, active Publisher login,
   target site, and catalog groups. When the site needs a common layout (a new site, or
   one without it) and the CLI has no `shopbuilder create-block`, preflight stops with
   "this step needs a newer Xsolla CLI"; write nothing.
2. If CLI context differs, switch it and rerun preflight; never override later commands.
3. If the target site exists, export it before the first write with
   `scripts/backup_shop.py --brief <brief.json> --slug <slug> --output-dir <dir>`.
4. Render with
   `scripts/render_plan.py <brief.json> --structure <backup-dir>/structure.json` and
   show one plan in plain language: each page and its sections in order, the products
   and offers in each, the visual direction (palette, backgrounds, artwork and where it
   came from), exact block removals, catalog mappings, a preview for the visual review,
   and what is still to connect. Call each section by its block name in the
   [block catalog](references/block-catalog.md), such as Offer chain or Reward system,
   never by a module ID such as `sb-offer-chain`. The audit trail is the rendered plan
   saved as `confirmed-plan.json`, which `verify_structure.py` reads later. Don't show the
   developer module IDs or the `confirmation_id`, not even labelled as audit details. Preserve
   configured blocks lacking replacement data. Omit `--structure` only for a new
   slug's bootstrap-only plan; it still shows every page and section to be built.
5. Ask for one explicit yes to that plan immediately before the first remote write.
   Earlier permission to "build a shop" is not that yes. Apply with the plan's current
   `confirmation_id` and record every ID you apply with.

The brief must target an acknowledged dedicated test project and match a separate
local allowlist with exact IDs, approver, and approval reference. Never use sandbox
as a Shop Builder target or use a partner project. Never publish, attach a production
domain, enable live payments, or apply a saved version. A human publishes in Publisher Account.

A new site's generated blocks have no IDs before creation, so it is applied in two runs:
the bootstrap, then, after a fresh export and re-render, the rest. The one yes covers both
runs and the cosmetic fixes after the visual review: colors, gradients, tints,
backgrounds, fonts, image placement, and wording within the approved facts. Re-render and
apply with the new `confirmation_id` without asking again only when the new plan has the
same pages, sections, catalog sections and locales, and every removal is on a page this
run created or was in the approved plan.

Ask again, showing what changed, before anything else: removing or changing a block or
page that existed before this run and wasn't in the approved plan, a different page or
section list, any price, promotion, limit, date or eligibility, another site or project,
or a target that changed after export.

## Assembly order

After confirmation, apply the plan in this dependency order:

1. **Theme** — set site and page theme source fields; page theme overrides site theme.
   Take the palette from the game's own art: [visual style](references/visual-style.md).
2. **Pages** — create all page paths before linking navigation.
3. **Site layout** — after page/template creation, add `common-layout` only if the
   site has none; adding it earlier suppresses some template headers and footers.
   Find it by module, not position: `get-structure` lists layouts by ID, so read each
   one with `get-block`. Other layouts, such as a sidebar's side-by-side layout, stay.
   Verify the common layout's ID appears in both `blocks` and `layouts`.
4. **Navigation** — resolve page IDs and add internal links only after pages exist.
5. **Blocks** — add/move/update blocks page by page; resolve IDs after each structural
   change and use targeted patches rather than replacing `values` or `components`.
6. **Copy and assets** — upload local assets, then patch returned CDN URLs; write
   localized HTML through localization commands, never through block value patches.
   Give sections the game's art and gradients; an opaque `background.color` hides the
   image under it. See [visual style](references/visual-style.md).
7. **Catalog links** — configure `newStore` sections only after catalog groups and
   SKUs have been verified in the same project. Localize a section title before
   enabling its `L:` ID.

Use pre-written scripts for repeated work; never pass `--force` or invent HTTP or
`curl` workarounds. If an operation requires `--force`, stop and report it.
If the CLI lacks an operation, stop it, record the gap, and file a CLI/API ticket.

## Verification and handoff

- Re-read structure and localization after assembly. Run
  `scripts/verify_structure.py --plan <confirmed-plan.json> --structure
  <post-apply-structure.json>` for the deterministic structural comparison.
- Check every requested locale, page path, navigation target, block order, catalog
  group, and asset URL.
- Run `xsolla shopbuilder verify-website --slug <slug>`.
- Enable preview for the visual review (`enable-preview`, `preview-link`); the plan's yes
  covers it. Return the preview link.
- Before the first handoff, review desktop and mobile screenshots of every page and fix
  what they show: [visual style](references/visual-style.md#visual-review-before-handoff).
  If the preview doesn't open, say the review wasn't done and why.
- Report skips, interventions, and gaps; state that the site is **not published**.
- If the plan adds the Custom code (`html`) block, tell the user it is added empty and
  hidden: they paste their code and make the block visible in the Site Builder editor.
  Never write HTML, CSS, or JavaScript into it.

## Stop conditions

Stop before writes when project identity is ambiguous, backup fails, confirmation is
missing, the target is not an acknowledged dedicated test project,
catalog/project IDs do not match, or the plan requires an unverified block module.
Preserve completed safe work and explain the smallest action needed to continue.

## Known limitations

- Sites created from a Publisher Account template keep the header in the common layout;
  render and apply stop on them before any write. Report the stop and suggest nothing
  else: not another site, not manual edits, no other workaround.

---
name: shop-builder-assembly
description: >-
  Assemble a complete Xsolla Shop Builder storefront from a structured shop brief,
  working top-down from theme and pages through navigation, standard blocks,
  localization, and catalog links. Not the entry point for "build me a shop" — that is
  nocode-shop-setup, which routes here once the shop is created on Xsolla's side and a
  validated brief exists (from description-to-shop). Use for AI-built Shop Builder sites, full
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

A Game Web Portal is built by `game-web-portal`, not here. If the user asked for a
game home, or the existing site has `/news`, `/rewards`, and `/store`, hand off to
`game-web-portal` and stop. A shop continues.

## Inputs

Normalize publisher answers, existing stores, descriptions, and designs into the
[shop brief](references/shop-brief.md). Writes require that brief; callers own source
extraction.

If `preset` is `auto`, choose in this order:

1. Live-service game with active events or rotating offers → `live-service-events`.
2. PC/console game needing content beyond purchase → `pc-multi-page`.
3. Mobile-first or purchase-focused game → `mobile-single-page`.

Before planning, read [presets](references/presets.md), the
[block catalog](references/block-catalog.md) and the
[render rules](references/visual-style.md#render-rules): how Shop Builder actually draws
themes, fonts, backgrounds, text and store sections. Before applying, read the
[exported contracts](references/exported-block-contracts.md) and
[CLI operations](references/cli-operations.md).

The official inventory is authoritative; its mappings and presets remain provisional
until [expert-review.md](references/expert-review.md) records approval.

## Non-negotiable safety gate

1. Run `scripts/preflight.py <brief.json> --approved-test-projects <local-allowlist.json>`.
   The allowlist is at `$XSOLLA_APPROVED_TEST_PROJECTS`, by default
   `~/.config/xsolla/approved-test-projects.json`; `nocode-shop-setup` collects the
   approver and approval link in its first batch, not at this step.
   Read back the matched merchant ID, project ID, safety environment, approval
   reference, active Publisher login, target site, and catalog groups.
   When `catalog-design`'s proposal is still waiting for the same yes, preflight's only
   allowed failure is the groups that proposal creates: render and show the plan with
   it. After the yes and the catalog's creation, run preflight again; it must pass in
   full before apply.
   When the site needs a common layout (a new site, or one without it) and the CLI has
   no `shopbuilder create-block`, preflight prints "the common layout needs a newer
   Xsolla CLI; the site is built without it". Tell the user in the plan, before any
   write: a site without the common layout won't open in the Editor, Publish or
   private preview.
2. If CLI context differs, switch it and rerun preflight; never override later commands.
3. If the target site exists, export it before the first write with
   `scripts/backup_shop.py --brief <brief.json> --slug <slug> --output-dir <dir>`.
4. Render with
   `scripts/render_plan.py <brief.json> --structure <backup-dir>/structure.json`, save
   the output as `approved-plan.json`, and show one plan in plain language: each page and
   its sections in order, the products and offers in each, the visual direction (palette,
   backgrounds, artwork and where it came from), exact block removals, the template
   sections each new page comes with that are removed (`template_removals`), catalog
   mappings (for an `__all__` section, every enabled item it pulls in, with test or
   leftover entries flagged so the developer can disable them first), a preview link for the visual review that anyone with the link can open, and
   what is still to connect, with a desktop and mobile
   [mockup](references/visual-style.md#mockup-for-the-approval). Call each section by its block name in the
   [block catalog](references/block-catalog.md), such as Offer chain or Reward system,
   never by a module ID such as `sb-offer-chain`. Don't show the developer module IDs or
   the `confirmation_id`, not even labelled as audit details. Preserve configured blocks
   lacking replacement data. Omit `--structure` only for a new slug's bootstrap-only
   plan; it still shows every page and section to be built.
5. Ask for one explicit yes to that plan before the first remote write. When
   `nocode-shop-setup` shows it in one message with a pending catalog proposal, that yes
   covers creating the catalog too. Earlier permission to "build a shop" is not that
   yes. Apply with `--approved-plan approved-plan.json --confirmation-id <its
   confirmation_id>`; the script refuses an edited plan file.

The brief must target an acknowledged dedicated test project and match a separate
local allowlist with exact IDs, approver, and approval reference. Never use sandbox
as a Shop Builder target or use a partner project. Never publish, attach a production
domain, enable live payments, or apply a saved version. A human publishes in Publisher Account.

A new site's generated blocks have no IDs before creation, so it is applied in two runs:
the bootstrap, then the rest. Save run 1's report as `run1-report.json`, export again,
and render with `--structure`, `--approved-plan approved-plan.json` and
`--run-report run1-report.json`. Apply run 2 with `--approved-plan`, `--run-report`,
`--backup-dir` and the approved `confirmation_id` only if the render says "Covered by the
approved plan": the same pages,
sections, catalog, locales, brand and content, and removals only of blocks run 1 created
or the approved plan listed. `apply_plan.py` checks this again and stops before any write.

The yes also covers background fixes after the visual review: `values.background` leaves
(color, gradient, image, position, size) on blocks this assembly created, applied with
`scripts/patch_backgrounds.py` after a fresh export. It refuses anything else, an image
not uploaded to the site, and a gradient unlike the ones already on it.

The yes covers what the plan showed: its pages and sections, catalog, palette, fonts,
art and wording, and both runs of a new site. Don't ask again for those; note "covered by
the approved plan" and continue. Ask again, showing what changed, only for what the plan
didn't show: a render that "Needs a new yes", a theme, font or wording the plan didn't
show, a block or page that existed before this run, any price, promotion, limit, date or eligibility,
another site or project, or a target that changed after export.

A run that stops after its writes began, such as on an authentication failure, prints a
`stopped-partway` report: save it as `partial-report.json`. Export again, render with
`--structure`, `--approved-plan` and `--run-report partial-report.json`, and apply under
the same yes when the render says "Covered by the approved plan"; otherwise ask again.

## Assembly order

After confirmation, apply the plan in this dependency order:

1. **Theme** — set site and page theme source fields; page theme overrides site theme.
   Take the palette from the game's own art: [visual style](references/visual-style.md).
2. **Pages** — create all page paths before linking navigation.
3. **Site layout** — after page/template creation, add `common-layout` only if the
   site has none; adding it earlier suppresses some template headers and footers.
   Find it by module, not position: `get-structure` lists layouts by ID, so read each
   one with `get-block`. Other layouts, such as a sidebar's side-by-side layout, stay.
   Verify the common layout's ID appears in both `blocks` and `layouts`. Without
   `create-block` in the CLI, this step is skipped and verification doesn't require it.
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
  `scripts/verify_structure.py --plan <the last applied plan> --structure
  <post-apply-structure.json>` for the deterministic structural comparison: run 2's plan
  for a new site, `approved-plan.json` otherwise.
- Check every requested locale, page path, navigation target, block order, catalog
  group, and asset URL.
- Run `xsolla shopbuilder verify-website --slug <slug>`.
- Enable preview for the visual review (`enable-preview`, `preview-link`); the plan's yes
  covers it, because the plan says anyone with the link can open it. Return the link.
- When `verify-website` fails with `draftPagesIds must be an array`, or preview fails
  with `admin_privileges_requred`, it is a known CLI gap
  ([test findings](references/test-findings.md#cli-gaps-found)): report it once and go
  on, without retrying. For the preview, open it in the browser as the visual review
  describes.
- Read the site's sign-in: `auth` in `get-structure` or `get-landing`. With an
  `auth.loginId`, check in Publisher Account, or with a read-only command from
  `xsolla login --help`, that this Login project is linked to the same store project. If
  it belongs to another project, or to none, report it in the handoff as a fix in
  Publisher Account before publishing: players would sign in through the wrong Login
  project. Never change it.
- The visual review is the definition of done. Before the handoff, screenshot every page
  at 1440 and 390 px, compare with the approved plan and the render rules, fix, and look
  again until the checklist passes:
  [visual style](references/visual-style.md#visual-review-before-handoff). Put the final
  screenshots in the handoff. If the preview doesn't open, say the review wasn't done
  and why; never call the site reviewed without them.
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
- When the requested slug is taken elsewhere in Shop Builder, `create-website` creates
  the site under another slug; `apply_plan.py` stops and names it. The new address needs
  a new yes, so propose a distinctive slug in the plan, not a generic `<game>-shop`.

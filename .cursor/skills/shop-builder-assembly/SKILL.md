---
name: shop-builder-assembly
description: >-
  Assembles a Shop Builder storefront from a validated shop brief: pages, layout,
  navigation, standard blocks, localization, catalog links, theme and copy, with mobile,
  PC and live-service presets. Reached through nocode-shop-setup after description-to-
  shop; not an entry point. Prefer it over adding single blocks. Not for a coded
  storefront (shop-setup).
metadata:
  owner: k.shah
  domain: store
---

# Shop Builder Assembly

Build an unpublished Publisher Account **Shop Builder site**, not a custom frontend,
in the developer's project through `xsolla shopbuilder`.

A Game Web Portal is built by `game-web-portal`, not here. If the user asked for a
game home, or the existing site has `/news`, `/rewards`, and `/store`, hand off to
`game-web-portal` and stop. A shop continues.

## Inputs

Normalize publisher answers, existing stores, descriptions, and designs into the
[shop brief](references/shop-brief.md). Writes require that brief; callers own source
extraction.

For Quests block operations on an existing Shop Builder site, including settings and
appearance changes, use a `block_operations` brief and follow
[block operations](references/block-operations.md). This path plans and applies only
confirmed block operations; it does not reconcile pages, navigation, site or page themes,
or catalog sections.

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

1. Run `scripts/preflight.py <brief.json>`. Read back the matched merchant ID, project
   ID, active Publisher login, target site, and catalog groups.
   When `catalog-design`'s proposal is still waiting for the same yes, preflight's only
   allowed failure is the groups that proposal creates: render and show the plan with
   it. After the yes and the catalog's creation, run preflight again; it must pass in
   full before apply.
   When the site needs a common layout (a new site, or one without it) and the CLI has
   no `shopbuilder create-block`, preflight and the rendered plan's `warnings` say the site
   is built without it and won't open in the Editor, Publish or private preview; show that
   with the plan, before any write. The plan depends on that CLI check, so a CLI upgrade
   between render and apply changes its confirmation ID: render again and show it.
2. If the CLI points at another merchant or project, or has sandbox mode on, switch it to
   the brief's project with sandbox off (`nocode-shop-setup` does this at its first
   check), then rerun preflight; never override later commands.
3. If the target site exists, export it before the first write with
   `scripts/backup_shop.py --brief <brief.json> --slug <slug> --output-dir <dir>`.
4. Render with `scripts/render_plan.py <brief.json> --structure
   <backup-dir>/structure.json`, save the output as `approved-plan.json`, and show one
   plan in plain language: the project by name and IDs (the name from `xsolla publisher
   list-projects`), each page and its sections in order, the products and offers in
   each, the visual direction (palette, backgrounds, artwork and where it came from), each
   page's search title, description and share image, exact block removals, the template
   sections each new page comes with that are removed (`template_removals`), catalog
   mappings (for an `__all__` section, every enabled item it pulls in, with test or
   leftover entries flagged; recommend sections of the new groups only, since disabling
   an entry changes the live catalog at once), existing pages the theme puts on the site colors, that a preview link anyone can
   open will be created for the visual review after the build, and what is still to
   connect, with a desktop and mobile
   [mockup](references/visual-style.md#mockup-for-the-approval). Call each section by its
   block name in the [block catalog](references/block-catalog.md), such as Offer chain or
   Reward system, never by a module ID such as `sb-offer-chain`. Don't show the developer
   module IDs or the `confirmation_id` on standalone build plans, even as audit details.
   The `block_operations` mode instead follows its local [operation-plan confirmation](references/block-operations.md#operation-plan-confirmation)
   exception. Preserve configured blocks lacking replacement data. Omit `--structure` only for a new slug's
   bootstrap-only plan; it still shows every page and section to be built.
5. Ask for one explicit yes to that plan before the first remote write. When
   `nocode-shop-setup` shows it in one message with a pending catalog proposal, that yes
   covers creating the catalog too. Earlier permission to "build a shop" is not that
   yes. Apply with `--approved-plan approved-plan.json --confirmation-id <its
   confirmation_id>`; the script refuses an edited plan file.

Never use sandbox as a Shop Builder target. Never publish, attach a production
domain, enable live payments, or apply a saved version. A human publishes in Publisher Account.

**More than one run under the yes.** A new site is applied in two runs, a run that stops
partway prints a `stopped-partway` report, and background fixes after the review run
`scripts/patch_backgrounds.py`. Before each later run, export again and render with
`--structure`, `--approved-plan` and `--run-report`; apply under the same yes only when the
render says "Covered by the approved plan". Commands and what each check covers:
[runs under one yes](references/cli-operations.md#runs-under-one-yes).

**What the yes covers.** This is the one list; other files point here. The yes covers
what the plan and the catalog proposal shown with it showed: pages and sections, the
catalog with its prices, promotions, limits and dates, the palette, fonts, art and
wording, the exact removals listed (blocks that existed before this run included), both
runs of a new site, a rerun the render calls covered, background fixes after the review,
and theme, font and wording fixes back to the approved values. Don't ask again for those;
note "covered by the approved plan" and continue. Ask again, showing what changed, for
anything else: a render that "Needs a new yes"; a change the plan didn't show, such as
another theme value, font or wording, a change to a block or page that existed before
this run, or a price, promotion, limit, date or eligibility not in the proposal; another
site, slug or project; or a target that changed after export. Pressing Preview once,
when the preview session expired, is a request, not a new approval.

## Assembly order

After confirmation, `apply_plan.py` applies steps 1–5 in this dependency order, and
`scripts/apply_style.py` steps 6–8 after the last apply run (run 2 for a new site), from
a fresh backup, as [CLI operations](references/cli-operations.md) describes.

1. **Pages** — create all page paths before linking navigation.
2. **Site layout** — after page/template creation, add `common-layout` only if the
   site has none; adding it earlier suppresses some template headers and footers.
   Find it by module, not position: `get-structure` lists layouts by ID, so read each
   one with `get-block`. Other layouts, such as a sidebar's side-by-side layout, stay.
   Verify the common layout's ID appears in both `blocks` and `layouts`. Without
   `create-block` in the CLI, this step is skipped and verification doesn't require it.
3. **Navigation** — resolve page IDs and add internal links only after pages exist.
4. **Blocks** — add/move/update blocks page by page; resolve IDs after each structural
   change and use targeted patches rather than replacing `values` or `components`.
5. **Catalog links** — configure `newStore` sections after this project's groups and SKUs
   are verified. Localize a section title before enabling its `L:` ID.
6. **Theme** — `apply_style.py` sets the brief's `brand.theme` on the site theme and puts
   planned pages on it; a page's own theme overrides the site's. Take the palette from the
   game's art ([visual style](references/visual-style.md)). Hand over its `needs_human`.
7. **Images** — it uploads each `brand.images` file once and puts the CDN URL in the
   block's background or logo. An opaque `background.color` hides the image under it.
8. **Copy** — it writes `content.copy`, hero button labels (`content.buttons`), the FAQ
   items and each page's `content.seo` (title, description, share image) in the primary
   locale through `update-many-localization`, never block patches; `shopbuilder-translate`
   adds other locales. Follow the text rules in [visual style](references/visual-style.md).

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
  Never write HTML, CSS, or JavaScript into it. A site that must match a Figma design
  uses no custom code, and Custom Blocks only as
  [Matching a Figma design](../nocode-shop-setup/references/figma-design.md) allows.

## Stop conditions

Stop before writes when project identity is ambiguous, backup fails, confirmation is
missing, catalog/project IDs do not match, or the plan requires an unverified block module.
Preserve completed safe work and explain the smallest action needed to continue.

## Known limitations

- A site made from a Publisher Account template keeps its header and footer in the site
  layout. Assembly builds on it with any preset: the template's hero and daily rewards
  block stay, demo blocks are exact removals, pages it adds drop their own header and
  footer, and the shared header's links are an Editor step that names each page.
- Every write path, Quests block operations included, stops before any write when the
  target site is published. Unpublish it in Publisher Account first, or build on another
  slug.
- When the requested slug is taken elsewhere in Shop Builder, `create-website` creates
  the site under another slug; `apply_plan.py` stops and names it. The new address needs
  a new yes, so propose a distinctive slug in the plan, not a generic `<game>-shop`.

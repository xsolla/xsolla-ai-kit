---
name: shop-builder-assembly
description: >-
  Assemble a complete Xsolla Shop Builder storefront from a structured shop brief,
  working top-down from theme and pages through navigation, standard blocks,
  localization, and catalog links. Use for AI-built Shop Builder sites, full website
  or webshop assembly, game-type storefront presets, mobile single-page shops, PC
  multi-page shops, and live-service stores with bundles or events. Prefer this
  skill over creating isolated Shop Builder blocks. Do not use it for a custom
  headless storefront; use shop-setup for that architecture.
metadata:
  owner: k.shah
  domain: store
---

# Shop Builder Assembly

Build an unpublished Publisher Account **Shop Builder site**, not a custom frontend,
in a dedicated non-partner test project through `xsolla shopbuilder`.

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

1. Run `scripts/preflight.py <brief.json>`; for a non-sandbox test project, also pass
   `--approved-test-projects <local-allowlist.json>`. Read back the matched merchant
   ID, project ID, safety environment, approval reference, active Publisher login,
   target site, and catalog groups.
2. If CLI context differs, switch it and rerun preflight; never override later commands.
3. If the target site exists, export it before the first write with
   `scripts/backup_shop.py --brief <brief.json> --slug <slug> --output-dir <dir>`.
4. Render with
   `scripts/render_plan.py <brief.json> --structure <backup-dir>/structure.json` and
   show the ordered plan, exact block removals, and catalog mappings. Preserve
   configured blocks lacking replacement data. Omit `--structure` only for a new
   slug's bootstrap-only plan.
5. Ask for explicit confirmation of the plan's `confirmation_id` immediately before
   the first remote write. Earlier permission to "build a shop" is not confirmation
   of a new plan. Re-render and reconfirm if the brief or plan changes.

The brief must target a sandbox or acknowledged dedicated test project. A `test`
target must match a separate local allowlist with exact IDs, approver, and approval
reference. Never use a partner project, publish, attach a production domain, enable
live payments, or apply a saved version. A human publishes in Publisher Account.

A new site has generated blocks whose IDs do not exist before creation. Confirm the
bootstrap, then export, re-render, and reconfirm before deleting any generated block.
If the target changes after export, repeat this sequence.

## Assembly order

After confirmation, apply the plan in this dependency order:

1. **Theme** — set site and page theme source fields; page theme overrides site theme.
2. **Pages** — create all page paths before linking navigation.
3. **Navigation** — resolve page IDs and add internal links only after pages exist.
4. **Blocks** — add/move/update blocks page by page; resolve IDs after each structural
   change and use targeted patches rather than replacing `values` or `components`.
5. **Copy and assets** — upload local assets, then patch returned CDN URLs; write
   localized HTML through localization commands, never through block value patches.
6. **Catalog links** — configure `newStore` sections only after catalog groups and
   SKUs have been verified in the same project. Localize a section title before
   enabling its `L:` ID.

Use pre-written scripts for repeated work; never invent HTTP or `curl` workarounds.
If the CLI lacks an operation, stop it, record the gap, and link a CLI/API ticket to
SB-8796.

## Verification and handoff

- Re-read structure and localization after assembly. Run
  `scripts/verify_structure.py --plan <confirmed-plan.json> --structure
  <post-apply-structure.json>` for the deterministic structural comparison.
- Check every requested locale, page path, navigation target, block order, catalog
  group, and asset URL.
- Run `xsolla shopbuilder verify-website --slug <slug>`.
- Enable preview only if the confirmed plan includes it, then return the preview link.
- Report skips, interventions, and gaps; state that the site is **not published**.
- For an epic evaluation run, record the outcome using
  [references/evaluation.md](references/evaluation.md); do not omit failed attempts.

## Stop conditions

Stop before writes when project identity is ambiguous, backup fails, confirmation is
missing, the target is neither sandbox nor an acknowledged dedicated test project,
catalog/project IDs do not match, or the plan requires an unverified block module.
Preserve completed safe work and explain the smallest action needed to continue.

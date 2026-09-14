---
name: shop-builder-assembly
description: >-
  Assemble a complete Xsolla Shop Builder storefront from a structured shop brief,
  working top-down from theme and pages through navigation, standard blocks,
  localization, and catalog links. Use for AI-built Shop Builder sites, full website
  or webshop assembly, game-type storefront presets, mobile single-page shops, PC
  multi-page portals, and live-service stores with bundles or events. Prefer this
  skill over creating isolated Shop Builder blocks. Do not use it for a custom
  headless storefront; use shop-setup for that architecture.
metadata:
  owner: k.shah
  domain: store
---

# Shop Builder Assembly

Build a coherent Publisher Account **Shop Builder site**, not a custom frontend. The
result is an unpublished site in a dedicated non-partner test project, assembled
through `xsolla shopbuilder`.

## Inputs

Normalize every source—publisher answers, an existing store, a description, or a
design—into the shop brief in [references/shop-brief.md](references/shop-brief.md).
Do not start from loose prose once writes begin. Keep source-specific extraction out
of this skill; callers hand off a normalized brief.

If `preset` is `auto`, choose in this order:

1. Live-service game with active events or rotating offers → `live-service-events`.
2. PC/console game needing content beyond purchase → `pc-multi-page`.
3. Mobile-first or purchase-focused game → `mobile-single-page`.

Read [references/presets.md](references/presets.md) before proposing pages or blocks.
Read [references/block-catalog.md](references/block-catalog.md) when selecting blocks;
read [references/exported-block-contracts.md](references/exported-block-contracts.md)
before patching block values.
Read [references/cli-operations.md](references/cli-operations.md) before translating an
approved plan into CLI operations.

The official catalog inventory is authoritative, but its template/contract mappings
and the presets remain provisional until [references/expert-review.md](references/expert-review.md)
contains reviewer approval evidence.

## Non-negotiable safety gate

1. Run `scripts/preflight.py <brief.json>`; for a non-sandbox test project, also pass
   `--approved-test-projects <local-allowlist.json>`. Read back the matched merchant
   ID, project ID, safety environment, approval reference, active Publisher login,
   target site, and catalog groups.
2. Stop if the CLI context differs from the brief; switch context and rerun preflight
   rather than overriding IDs ad hoc on later commands.
3. If the target site exists, export it before the first write with
   `scripts/backup_shop.py --brief <brief.json> --slug <slug> --output-dir <dir>`.
4. Render the proposed plan with
   `scripts/render_plan.py <brief.json> --structure <backup-dir>/structure.json` and
   show the complete ordered plan, including exact block IDs to remove and catalog
   mappings. Preserve existing configured blocks when replacement data is missing;
   do not silently turn an omission rule into deletion. Omit `--structure` only for
   a new slug's bootstrap-only plan.
5. Ask for explicit confirmation of the plan's `confirmation_id` immediately before
   the first remote write. Earlier permission to "build a shop" is not confirmation
   of a new plan. Re-render and reconfirm if the brief or plan changes.

The brief must target either a sandbox context or a dedicated test project that the
user explicitly acknowledges as safe. A `test` target must also match a separate
local allowlist record containing the exact IDs, approver, and approval reference;
the brief alone is not approval evidence. Never use a partner's live project. Never
publish, attach a production domain, enable live payments, or apply a saved version.
A human publishes in Publisher Account.

A newly created Shop Builder site contains generated template blocks whose IDs do not
exist before creation. Treat creation as a confirmed bootstrap phase, then export,
re-render, and reconfirm the target-bound plan before deleting any generated block.
If the target changes after export, stop and repeat that sequence.

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

Use pre-written scripts for repeated transformations or command batches. Do not
invent raw HTTP calls or `curl` workarounds. When a required operation is unavailable
in the CLI, stop that operation, record the gap, and file a CLI/API ticket linked to
SB-8796.

## Verification and handoff

- Re-read structure and localization after assembly. Run
  `scripts/verify_structure.py --plan <confirmed-plan.json> --structure
  <post-apply-structure.json>` for the deterministic structural comparison.
- Check every requested locale, page path, navigation target, block order, catalog
  group, and asset URL.
- Run `xsolla shopbuilder verify-website --slug <slug>`.
- Enable preview only if the confirmed plan includes it, then return the preview link.
- Report skipped operations, manual interventions, and CLI/API gaps. State clearly
  that the site is **not published**.
- For an epic evaluation run, record the outcome using
  [references/evaluation.md](references/evaluation.md); do not omit failed attempts.

## Stop conditions

Stop before writes when project identity is ambiguous, backup fails, confirmation is
missing, the target is neither sandbox nor an acknowledged dedicated test project,
catalog/project IDs do not match, or the plan requires an unverified block module.
Preserve completed safe work and explain the smallest action needed to continue.

# Build flow

Use this for building a site from a shop brief after the safety gate in
[SKILL.md](../SKILL.md) passes. Block operations on an existing Quests block use
[block-operations.md](block-operations.md) instead.

## Inputs

Normalize publisher answers, existing stores, descriptions, and designs into the
[shop brief](shop-brief.md). Writes require that brief; callers own source
extraction.

If `preset` is `auto`, choose in this order:

1. Live-service game with active events or rotating offers → `live-service-events`.
2. PC/console game needing content beyond purchase → `pc-multi-page`.
3. Mobile-first or purchase-focused game → `mobile-single-page`.

Before planning, read [presets](presets.md) and the
[block catalog](block-catalog.md). Before applying, read the
[exported contracts](exported-block-contracts.md) and
[CLI operations](cli-operations.md).

The official inventory is authoritative; the maintainers record its mapping and preset
approval outside this skill, so treat presets as provisional.

## Assembly order

After confirmation, apply the plan in this dependency order:

1. **Theme**: set site and page theme source fields; page theme overrides site theme.
2. **Pages**: create all page paths before linking navigation.
3. **Site layout**: after page/template creation, add `common-layout` only if the
   site has none; adding it earlier suppresses some template headers and footers.
   Find it by module, not position: `get-structure` lists layouts by ID, so read each
   one with `get-block`. Other layouts, such as a sidebar's side-by-side layout, stay.
   Verify the common layout's ID appears in both `blocks` and `layouts`. Without
   `create-block` in the CLI, this step is skipped and verification doesn't require it.
4. **Navigation**: resolve page IDs and add internal links only after pages exist.
5. **Blocks**: add/move/update blocks page by page; resolve IDs after each structural
   change and use targeted patches rather than replacing `values` or `components`.
6. **Copy and assets**: upload local assets, then patch returned CDN URLs; write
   localized HTML through localization commands, never through block value patches.
7. **Catalog links**: configure `newStore` sections only after catalog groups and
   SKUs have been verified in the same project. Localize a section title before
   enabling its `L:` ID.

## Verification and handoff

- Re-read structure and localization after assembly. Run
  `scripts/verify_structure.py --plan <confirmed-plan.json> --structure
  <post-apply-structure.json>` for the deterministic structural comparison.
- Check every requested locale, page path, navigation target, block order, catalog
  group, and asset URL.
- Run `xsolla shopbuilder verify-website --slug <slug>`.
- Enable preview only if the confirmed plan includes it, then return the preview link.
- Report skips, interventions, and gaps; state that the site is **not published**.
- If the plan adds the Custom code (`html`) block, tell the user it is added empty and
  hidden: they paste their code and make the block visible in the Site Builder editor.
  Never write HTML, CSS, or JavaScript into it.

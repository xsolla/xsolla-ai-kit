---
name: shop-builder-assembly
description: >-
  Assemble a complete Xsolla Shop Builder storefront from a structured shop brief:
  theme and pages first, then navigation, standard blocks, localization, and catalog
  links. Use for AI-built Shop Builder sites, full website or webshop assembly,
  game-type storefront presets (mobile single-page, PC multi-page, live-service stores
  with bundles or events), and block operations on the Quests block of an existing
  Shop Builder site (add, update, reset, move, duplicate, hide, show, delete). Not for
  single unrelated edits such as changing the header, a theme, or a color of an
  existing site on request; those go to the Shop Builder editor. When the user asks
  about one block, do not offer site-wide theme changes. Not the entry point for
  "build me a shop": that is shop-setup, which routes here once the build path is
  Shop Builder and a validated brief exists. Do not use it for a custom headless
  storefront; use shop-setup for that architecture.
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
   the fixed approval-list path from the allowlist paragraph in
   [shop brief](references/shop-brief.md) as `--approved-test-projects` (expand `~`
   first; the scripts do not). Do not read, stat, list or check that file yourself;
   only `preflight.py` reads it. Read back the matched merchant
   ID, project ID, safety environment, approval reference, active Publisher login,
   target site, and catalog groups. If preflight refuses, reply in the blocked shape under [Replies](#replies).
2. If CLI context differs, switch it and rerun preflight; never override later commands.
3. If the target site exists, export it before the first write with
   `scripts/backup_shop.py --brief <brief.json> --slug <slug> --output-dir <dir>`.
4. Render with
   `scripts/render_plan.py <brief.json> --structure <backup-dir>/structure.json` and
   show the plan in the Plan shape under [Replies](#replies): the ordered operations,
   exact block removals, and catalog mappings as bullets. Preserve configured blocks
   lacking replacement data. Omit `--structure` only for a new
   slug's bootstrap-only plan.
5. Ask for explicit confirmation of the plan's `confirmation_id` immediately before
   the first remote write; the plan's Confirmation bullet and its `Next:` line ask for it.
Earlier permission to "build a shop" is not confirmation
   of a new plan. Re-render and reconfirm if the brief or plan changes.

The brief must target a sandbox or acknowledged dedicated test project. A `test`
target must match the approval list that preflight reads, with exact IDs, approver, and
approval reference. Never read, search for, stat, list, create, edit or suggest changing
that list; if preflight refuses, stop and reply in the blocked shape under [Replies](#replies),
saying this project is not approved for test writes.

Set `project.test_project_acknowledged` to `true` only when the publisher explicitly
states in this conversation that the project is a dedicated test project. Never set it
yourself, and never infer it from the project name, a test site, an earlier yes, or
the approval list.

Never use a partner project, publish, attach a production domain, enable live payments,
or apply a saved version. For a publish request, use the publish shape under [Replies](#replies).

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
If the CLI lacks an operation, stop it, record the gap, and file a CLI/API ticket.

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

## Block operations (Quests block)

A brief with `block_operations` edits single Quests blocks on an existing site; see the
[shop brief](references/shop-brief.md) and [CLI operations](references/cli-operations.md).
It uses the same gate as a build: preflight, backup, plan, `confirmation_id`, then
`scripts/apply_plan.py`, which verifies on exit and touches only the listed blocks.
Deleting a block needs a `delete` op in the confirmed plan. Never use `--force` anywhere
else. The `test_project_acknowledged` rule above applies to every brief. For a change to
anything outside the Quests block in such a request, use the refusal shape under
[Replies](#replies).

## Stop conditions

Stop before writes when project identity is ambiguous, backup fails, confirmation is
missing, the target is neither sandbox nor an acknowledged dedicated test project, the
test project is not in the approved test-projects file, catalog/project IDs do not
match, or the plan requires an unverified block module. Preserve completed safe work and
explain the smallest action needed to continue.

## Replies

Every reply uses one compact shape: a bold one-line answer, then 0 to 4 short bullets
(`- Label: value`), then a last line `Next: <one question or action>`. A simple answer
may be only the bold line and `Next:`. Ask one question at a time.

Never include environment variable names, file paths, tokens, or internal codenames (for
example, D2a) in a reply. Never mention the approval list or its location in a reply.

Plan: a bold `Plan: ...` line, up to about five bullets (Site, Change, defaults such as
Reward icon, "Not published; you publish in Publisher Account", and Confirmation). Pack
several operations or removals into one Change bullet, separated by semicolons.

```
**Plan: set reward text on the "QA Quest Badge" card**
- Site: qa-quests-spike, Quests block on Main
- Change: reward text → "Gold badge"
- Reward icon: catalog image (unchanged)
- Not published; you publish in Publisher Account
- Confirmation: sha256:ab12cd34

Next: reply "yes" to apply this exact plan.
```

Blocked, when preflight refuses or a gate stops the write (the project is not approved, the
brief is not acknowledged, the target does not match):

```
**This project can't take test writes yet.**
- Site: qa-quests-spike, nothing changed

Next: confirm the project is the dedicated test project you intended.
```

Refusal, for anything outside the Quests block in a block-operations request:

```
**That's outside the Quests block.**
- Change the header in the Shop Builder editor.

Next: anything to change on the Quests block?
```

Publish request: bold "The skill doesn't publish.", bullets "You publish in Publisher Account
when you're ready." and "The site stays unpublished.", then `Next:`.

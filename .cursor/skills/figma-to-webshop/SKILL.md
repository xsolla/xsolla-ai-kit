---
name: figma-to-webshop
description: >-
  Turn a partner's own Figma design, design file or exported HTML comp into a Shop
  Builder webshop — read the design, map each section onto native blocks, write the shop
  brief for shop-builder-assembly, then apply the palette, fonts, art and copy that
  assembly doesn't yet, and check the result against a screenshot. Not the entry point
  for "build me a shop" — that is shop-setup. Use only when a design file exists and the
  partner owns or is licensed to use it: a figma.com link, a design file, or an exported
  comp, with "build this design as our webshop", "match the comp", "make the storefront
  look like our Figma", or "convert our Figma to a shop". Never recreate another
  company's storefront from a screenshot. Never publishes.
metadata:
  owner: r.addoumie
  domain: design
  status: draft
---

# Figma → Xsolla webshop

Owns **design intake** for Shop Builder: the section inventory and token sheet become a
shop brief and a theme. **`shop-builder-assembly`** owns the structural writes — pages,
navigation, blocks, locales, catalog links — with its preflight, backup and plan
confirmation. Assembly doesn't yet apply the `theme` and `copy_assets` phases (its plan
lists them under `unsupported_phases`), so this skill applies those, and only those,
after assembly finishes. When assembly supports them, hand them over too.

Everything is native blocks: catalog, cart, checkout and login for free, layout fixed.
Where a block cannot express the comp, say so up front (Step 1, Known limitations).
Catalog changes go through **`catalog-design`**. CLI flags: `xsolla shopbuilder
<command> --help`.

## Step 0 — gate, design rights, site, catalog, preview (do not skip)

**Design rights.** Build only from a design and art the partner owns or is licensed to
use. A screenshot of another company's storefront is not a design to recreate — decline
it. Fonts need a webfont licence too ([theming-and-fonts.md](references/theming-and-fonts.md#fonts)).

**Project.** Read back `merchant_id`, `project_id` and `sandbox` from `xsolla config
list --json` and confirm them with the user. This skill builds only in a dedicated test
project on the approval allowlist, with CLI sandbox off, and asks for the allowlist's
path now. The allowlist lives outside the repository, in the format
`shop-builder-assembly/references/shop-brief.md` documents. The enforced gate is
assembly's preflight, which needs the brief — Step 2. Nothing writes before then.

**Site kind.** Read `XSOLLA_SITE_KIND` with the
[build-path contract's check](../shop-plan/references/build-path-contract.md#the-site-kind-shop-builder-only):
`portal` → hand to `game-web-portal` and stop; an invalid value halts.

| Do | Why |
|---|---|
| `xsolla shopbuilder list-websites --json` → confirm the slug of the site the **partner created** in Publisher Account (Storefronts → Websites) | The agent never creates the site: a CLI-made site has no common layout, and the Editor can't open it. No site → stop and ask for one. Near-duplicate names are common — confirm the exact site |
| `xsolla catalog list-item-groups --project-id <p>` | Groups map 1:1 to the comp's store rows. A missing group → `catalog-design`, not here |
| Probe `xsolla shopbuilder enable-preview --slug <slug> --json` | `403 admin_privileges_requred` means no screenshot: skip that part of Step 5 and tell the user now. Never ask for a browser session cookie to get around it |
| Read the design → [read-the-design.md](references/read-the-design.md) | Leaves you a section inventory and a token sheet |

## Step 1 — confirm the gaps, then map sections

**Before any write, tell the user what the native build will not match, and get a yes.**
Compare the comp against [Known limitations](#known-limitations) and name each gap that
applies — above all the product card: a rotated violator, countdown, points ribbon,
purchase counter, or any order other than art → name → description → price won't
render. Cart, checkout and auth stay native in every case; never rebuild them by hand.

Then map every section, top to bottom, to a block module assembly verifies:

| Section | Module | Notes |
|---|---|---|
| Header (login, cart, balance) | `header` | owns the session |
| Hero / welcome offer | `leadGameSales` | buttons only scroll; art goes in the section background |
| Product grid, store tabs | `newStore` | anchors spend the per-section titles |
| Text band / feature cards / media strip | `description` / `bento-grid` / `gallery` | each needs its `content` in the brief |
| FAQ | `faq` | needs `content.faq` |
| Footer | `footer` | carries required legal rows |

No verified module for a section → a gap, not a new module name. Block capabilities:
[native-blocks.md](references/native-blocks.md).

## Step 2 — write the brief

Turn the inventory and token sheet into one version-1 brief — field-by-field mapping in
[design-to-brief.md](references/design-to-brief.md). Target the partner's site slug, set
`"environment": "test"` with `"test_project_acknowledged": true`, and put the Step 1
mapping in `content.page_overrides`. Ask for missing game facts in one batch; never
invent prices, groups or copy. Then run assembly's validator and preflight:

```bash
python3 ../shop-builder-assembly/scripts/validate_shop_brief.py brief.json
python3 ../shop-builder-assembly/scripts/preflight.py brief.json \
  --approved-test-projects <local-allowlist.json>
```

Preflight refuses unless the exact merchant/project pair is in the allowlist with
`approved_by` and `approval_reference`, the CLI's IDs match the brief, CLI sandbox is
off (the brief's `test` environment requires it; a missing key counts as off), a
Publisher login is active, and the brief's catalog groups exist. Read back the IDs and
approval reference. On a failure, stop: have the user switch the CLI and rerun — never
override the project on later commands.

## Step 3 — hand the structure to `shop-builder-assembly`

Invoke `shop-builder-assembly` with the validated brief and the allowlist. It owns its
preflight, the backup of the partner's site, the rendered plan and its confirmation,
and every page, navigation, block, locale and catalog-link write. **Don't run
`create-website`, `add-page`, `add-block`, `delete-block` or block `update-block` calls
here**, and don't ask for a second approval of its plan. If assembly stops, return its
exact blocker and backup location — don't retry, don't switch projects, and don't apply
Step 4 to a half-built site.

## Step 4 — theme, fonts, art and copy (assembly's unsupported phases)

Only after assembly reports success. Rerun assembly's `preflight.py` with the brief and
allowlist (Step 2), export the site again
with assembly's `scripts/backup_shop.py`, then show the user the exact list — theme
tokens, font files, assets and the blocks they go on, localized strings — and **get an
explicit yes before the first write.**

- **Theme.** On an `xds-theme` landing the renderer reads `theme.calculatedTheme`;
  patching `theme.input` alone reads back fine and changes nothing. Patch through
  `update-block` with `"type": "site"` and the landing `_id`. Token names mislead: the
  card buy button is `core.text.brand`. Map: [theming-and-fonts.md](references/theming-and-fonts.md).
- **Fonts.** Only webfont-licensed or OFL faces; otherwise the closest OFL face, listed
  at handover.
- **Art.** Upload with `upload-asset`, then set each block's `background.img` with a
  transparent `background.color`. Never flatten a section or card into one image —
  [read-the-design.md](references/read-the-design.md#slice-the-design-assets-rebuild-the-structure).
- **Copy.** `update-many-localization`, each value `{"description": "<existing>",
  "translation": "<html>"}` — send the current `description` from `get-localization`,
  or the write clears it. Body copy must be HTML.

Traps: [pitfalls.md](references/pitfalls.md).

## Step 5 — verify against a screenshot, not the API

Run assembly's structural verification first. Then: `ok: true` and a clean
`get-structure` read are **not** evidence that anything looks right — get a rendered
screenshot and sample pixels to find which token drives an element. If Step 0's preview
probe returned 403, skip the screenshot and say the page is verified by structure only.
Never publish to get a render. Loop and render traps:
[verify-and-iterate.md](references/verify-and-iterate.md).

## Known limitations

Name the ones the comp hits in Step 1, and list them again at handover.

| Gap | What the comp wants | What you get |
|---|---|---|
| **Product card layout** | Rotated violators ("BEST VALUE", "+20% BONUS"), ribbons, countdowns, purchase counters, the amount in a band above the art | Fixed art → name → description → price button; none of the extras |
| **Hero art** | An image beside the copy, a bordered inner panel, a countdown | `leadGameSales` has no image slot — art goes in the section background |
| **Hero buy button** | Adds to cart | Only `scroll` / `lightbox` / `pwa`; it can scroll to the store |
| **Tabs and headings together** | A tab bar *and* a heading above each row | With `tabs` on, section titles render only on the bar |
| **Exact typography** | Every weight; a desktop-only font | One file per family, other weights synthesised; unlicensed faces become the closest OFL face |
| **Site creation** | The agent creates the site | The CLI can't create the common layout; the partner creates the site in Publisher Account |
| **Theme and assets outside assembly** | One write path | Until assembly implements `theme` and `copy_assets`, Step 4 applies them here |

## Common pitfalls

In full: [pitfalls.md](references/pitfalls.md).

| Symptom | Cause and fix |
|---|---|
| **Theme patched, nothing changed** | You patched `theme.input`. Patch `theme.calculatedTheme` via `update-block` with `"type": "site"`. |
| **A string's `description` went blank** | `update-many-localization` without `description` clears it. Send the existing one with every translation. |
| **A fresh bundle is invisible to the storefront** | Not shown until `admin-unhide-bundle`. A combo card ("25,000 Gold + 1,425 Gems") must be a **bundle** — a currency package holds exactly one currency. |
| **Assembly omitted a section** | Its data is missing from the brief (`content.faq`, `features`, `gallery`…). Add it and re-render — Step 2. |

## Examples

- "Here's our Figma — build it as our webshop in the approved test project."
- "Make the storefront match our comp; the theming is off."
- "Convert our Figma to a shop, keep checkout native."

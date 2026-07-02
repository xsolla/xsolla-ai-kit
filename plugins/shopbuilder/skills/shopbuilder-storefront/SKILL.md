---
name: shopbuilder-storefront
description: >-
  Entry point and orchestrator for building a game storefront with Xsolla Shop Builder,
  the no-code hosted site edited through `xsolla shopbuilder`. Explains the build hierarchy
  (site -> page -> blocks -> block customization), sequences the four level skills, and
  holds the rules that keep a build from breaking. Use when someone wants to build, assemble,
  theme, or lay out a Shop Builder storefront, add or arrange blocks, or asks where to start
  on a Shop Builder site. Scope is the storefront only; the catalog, login, payments, and
  webhooks are prerequisites handled by their own skills. Hands off to shopbuilder-site,
  shopbuilder-page, shopbuilder-blocks, and shopbuilder-customize.
metadata:
  domain: shopbuilder
  kind: orchestrator
---

# Shop Builder storefront

Build a hosted storefront with Xsolla Shop Builder. This skill sets the scope, the order,
and the rules; the four level skills do the work.

## Scope

In scope: the storefront itself, built with `xsolla shopbuilder` and Publisher Account.
Out of scope (each has its own skill, treat as prerequisites): merchant account and keys,
project creation, the catalog, login, payments, webhooks. Offer chains and other promotions
are liveops entities created elsewhere; this set covers only how to display them as blocks.

## The build hierarchy

A Shop Builder storefront is four nested levels. Decisions at each level constrain the level
below it, so build top down and review top down.

1. **Site** (`shopbuilder-site`) — the container: identity, currency model, locales, the
   brand seed theme, domain.
2. **Page** (`shopbuilder-page`) — one scroll as a funnel: mood, the page theme that
   overrides the site theme, the backdrop, SEO.
3. **Blocks** (`shopbuilder-blocks`) — merchandising: which blocks, in what order, including
   hosted modules (offer chain, daily reward, offerwall).
4. **Block customization** (`shopbuilder-customize`) — conversion: copy, imagery, store
   sections, backgrounds, and per-block theme.

Run the four in order. A reviewer can locate any problem by level: wrong currency model is a
site problem, theme not showing is a page problem, weak funnel is a blocks problem, flat copy
or a mismatched image is a customize problem.

## Prerequisites

- The catalog exists and reads back through the client catalog calls. A storefront with no
  catalog shows leftover demo items or nothing. Build it first with `catalog-design`.
- The `xsolla` CLI is present and is the build that has `shopbuilder upload-asset`. Confirm
  with `xsolla shopbuilder --help | grep upload-asset`. When two binaries exist, call the
  right one by absolute path.
- `XSOLLA_SHOPBUILDER_SESSION` holds the `pa-v4-token` cookie value. It expires; re-copy it
  from Publisher Account when a `shopbuilder` call returns 403.
- Record `merchant_id`, `project_id`, the storefront `slug`, and after creation the
  `landing_id` and `page_id`.

## Steps

1. Confirm the prerequisites above.
2. `shopbuilder-site`: create the landing, wait out scaffolding, set languages and the site
   theme, capture ids.
3. `shopbuilder-page`: set the page theme (the look that ships) and the backdrop.
4. `shopbuilder-blocks`: strip the default template blocks, add the intended blocks, order
   them into a funnel.
5. `shopbuilder-customize`: author copy, place images, configure store sections, tune
   backgrounds and theme.
6. Enable preview (`xsolla shopbuilder enable-preview --slug <slug>`), review, then publish
   and go live in Publisher Account.

## The one rule that prevents lost work

Do not edit the landing in the Publisher Account editor while the CLI or admin API is writing
to it. Concurrent writers overwrite each other, drop blocks, and leave ghost references that
break the editor with "Block with id ... not found". One writer at a time. When you hand the
landing back to the developer, say so; when they are editing, stay out.

## Verifying a build

- `xsolla shopbuilder get-structure --slug <slug> --json` is the source of truth for
  structure, but it does not inline localized text (it returns `L:` ids). Verify authored
  copy through the `update-block` response's `localizations` map.
- The admin catalog read lags; when confirming what the storefront serves, read the client
  catalog calls instead.
- `verify-website` returns 404 on a topup landing; use `get-structure` to check readiness.

## Reference

- `references/field-notes.md` — the Shop Builder failures that cost hours, with fixes.

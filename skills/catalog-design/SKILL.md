---
name: catalog-design
description: >-
  Configures the Xsolla virtual catalog for a game — including virtual items,
  virtual currency, bundles, pricing tiers, and player inventory. Use when
  setting up a game's item catalog, adding purchasable goods, configuring
  virtual currency, creating starter packs or bundles, setting regional pricing,
  or managing item attributes and images. Covers Catalog, Cart, Player Inventory,
  Refunds, Receipt validation, and Geo pricing surfaces.
metadata:
  owner: p.sanachev
  domain: catalog
  status: planned
---

## Status

This skill is **in planning**. @p.sanachev (Tech Lead, IGS-Left) owns authoring.

Reference material is being collected in `references/`:
- [`references/items.md`](references/items.md) — item types, attributes, images
- [`references/pricing.md`](references/pricing.md) — pricing models, virtual currency economics
- [`references/bundles.md`](references/bundles.md) — bundle strategies, starter packs

## When to use

Use this skill when the developer wants to:
- Create virtual items (consumables, non-consumables, subscriptions)
- Configure virtual currency denominations
- Set up starter packs, bundles, or timed offers
- Configure geo-pricing or regional pricing tiers
- Manage player inventory and refunds
- Validate receipts server-side

## Prerequisites

```bash
export XSOLLA_API_KEY=<your-sandbox-key>
export PROJECT_ID=<your-project-id>
export MERCHANT_ID=<your-merchant-id>
export XSOLLA_ENV=sandbox
```

Project must exist (run `project-init` first).

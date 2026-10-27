---
name: description-to-shop
description: >-
  Turn a plain-language game description into the normalized, source-attributed shop
  brief consumed by shop-builder-assembly. Not the entry point for "build me a shop" —
  that is shop-setup, which routes here once the build path is Shop Builder and the only
  input is prose. Use when a publisher has no design, brief or written specification and
  asks to build a Shop Builder site, webshop, top-up page, PC portal, or live-service
  store from a description. This skill owns intake and inference; shop-builder-assembly
  owns presets, confirmation, backups, CLI writes, verification, and preview. Do not use
  this skill to implement a second assembly workflow.
metadata:
  owner: k.shah
  domain: store
---

# Description to Shop

Convert a short game description into a valid `shop-builder-assembly` brief, then hand
it over. Never call Shop Builder write commands here.

## 0. Reuse the confirmed onboarding intake

Before asking anything, read [references/onboarding-intake.md](references/onboarding-intake.md)
and run this skill's `scripts/read_onboarding.py --project-root <publisher-project-root>`.
Use the publisher's working project, not the installed plugin directory. The helper reads
`.env` routing keys and `.xsolla/onboarding.json` only; it makes no writes or API calls.
On an error, stop and report it rather than restarting the interview. For `portal`, hand
off to `game-web-portal` and stop here. A missing ledger on the shop path permits normal
intake from the conversation. A loaded ledger supplies already-confirmed answers. A value
that contradicts the ledger without an explicit correction is a conflict: keep the ledger
value, ask one question that shows both values, and wait for the answer.

## 1. Extract the description

Read [references/intake-schema.md](references/intake-schema.md). Classify every required
fact from the ledger and conversation as stated, safely inferred, missing, or conflicting.
Never ask the publisher to repeat a usable recorded answer. Infer presentation choices such as the
likely preset; never invent prices, catalog groups, dates, game facts, studio names, or
translated copy.

Before asking anything, read the game's public store page (App Store, Google Play, Steam):
the recorded `store_url`, a link in the conversation, or the page you find by the game's
name, which the plan then names so a wrong match gets caught. It supplies the name,
platforms, developer, description, icon and screenshots; ask only for what it doesn't.
When the publisher delegates routine choices ("decide for me"), choose the preset,
layout, visual treatment and draft copy yourself and show them in assembly's plan
instead of asking.

Ask for missing required facts and unresolved conflicts in one batch. Use read-only discovery for the active
CLI project and its catalog groups. If the catalog is absent, or a named group does not
exist, stop and point at the catalog skill rather than creating entities.

## 2. Produce the shared brief

Follow the contract in `shop-builder-assembly/references/shop-brief.md` and write one
version-1 JSON object:

- `game` — platforms and lifecycle.
- `site` — proposed slug, locales, and `auto` or an explicit preset.
- `catalog.groups` — only verified same-project groups; `__all__` for all items of a
  supported type.
- `catalog.liveops` — the active promo code or coupon promotions, reward chains and offer
  chains found by read-only `xsolla liveops list-promo-codes`, `list-coupons`,
  `list-reward-chain` and `list-offer-chain`.
- `content` — approved copy and publisher page overrides.
- `brand` — the store page's app icon as the logo and its art for the hero, unless the
  publisher supplied their own.
- `sources` — add `{"kind":"description", ...}`, and `{"kind":"external_store", ...}` with
  the page URL when the store page supplied facts or art. Keep the provenance of any publisher
  answer used to fill a gap. Attribute reused intake to `.xsolla/onboarding.json` and
  its keys with `kind: publisher_answers`; retain provenance for corrections and inferences.
- Never include API keys, tokens, session cookies, passwords, or browser storage.

Validate with the assembly skill's `scripts/validate_shop_brief.py` and fix input errors
before handing off.

## 3. Delegate assembly

Invoke `shop-builder-assembly` with the validated brief. It exclusively owns preset
selection and block defaults, the confirmation-bound plan, project allowlisting and
login preflight, backup-before-write, every `xsolla shopbuilder` write, structural,
localization, catalog, readiness and preview verification, and the never-publish
safeguard.

Do not request a separate approval here and do not run legacy local assembly scripts.
The developer approves one plan, in `shop-builder-assembly`.

## Failure handling

If intake cannot produce a valid brief, report the missing facts. If assembly stops,
return its exact blocker and backup location — do not retry or switch projects.

## References

- [references/intake-schema.md](references/intake-schema.md) — fields, inference
  boundaries, completeness gate.
- [references/plan-format.md](references/plan-format.md) — the handoff object and its
  rules.
- `shop-builder-assembly/references/shop-brief.md` — authoritative contract.

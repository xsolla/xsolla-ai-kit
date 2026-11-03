---
name: description-to-shop
description: >-
  Turn a plain-language game description or the publisher's store listing into the
  normalized, source-attributed shop brief consumed by shop-builder-assembly. Reached
  through nocode-shop-setup once the shop is on Xsolla's side. Not the entry point for
  "build me a shop", a web shop, a storefront or a game home: open nocode-shop-setup for
  those. This skill owns intake and inference; shop-builder-assembly
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
`.xsolla/onboarding.json` only. It does not read a build path from `.env`, and it makes no
writes or API calls.
On an error, stop and report it rather than restarting the interview. For `portal`, or when
the user asked for a game home, or the existing site has `/news`, `/rewards`, and `/store`,
hand off to `game-web-portal` and stop here. `nocode-shop-setup` asks store or game home
when it is still open. A missing ledger permits normal intake from the conversation. A
loaded ledger supplies already-confirmed answers. A value that contradicts the ledger
without an explicit correction is a conflict: keep the ledger value, ask one question that
shows both values, and wait for the answer.

## 1. Extract the description

Read [references/intake-schema.md](references/intake-schema.md). Classify every required
fact from the ledger and conversation as stated, safely inferred, missing, or conflicting.
Never ask the publisher to repeat a usable recorded answer. Infer presentation choices such as the
likely preset; never invent prices, catalog groups, dates, game facts, studio names, or
translated copy.

Before asking anything, read the publisher's own store listing (App Store, Google Play,
Steam), and only that: the recorded `store_url` or a link the publisher gives. Never
search for it by the game's name. It supplies the name, platforms, developer,
description, icon and screenshots; ask only for what it doesn't. In the same batch, ask
whether the listing is theirs and its art and text may be used on the site. Until they
say yes, use its facts only; its description, icon and screenshots stay out of the brief.
When the publisher delegates routine choices ("decide for me"), choose the preset,
layout, visual treatment and draft copy yourself and show them in assembly's plan
instead of asking.

When `nocode-shop-setup` started this run, its one batch already asked the intake: read
those answers and ask nothing new, except about a conflict. Otherwise, ask for missing
required facts and unresolved conflicts in one batch. Use read-only discovery for the
active CLI project and its catalog groups. A catalog that `catalog-design` has proposed
and that waits for the same yes counts as existing. If the catalog is absent with no such
proposal, or a named group is in neither, stop and point at the catalog skill. Never
create entities here.

## 2. Produce the shared brief

Follow the contract in `shop-builder-assembly/references/shop-brief.md` and write one
version-1 JSON object:

- `game` — platforms and lifecycle.
- `site` — proposed slug, locales, and `auto` or an explicit preset. On a site the
  developer made from the Single-page shop template, use that site's slug and preset
  `mobile-single-page`.
- `catalog.groups` — same-project groups that exist, or that `catalog-design`'s pending
  proposal creates under the same yes; `__all__` for all items of a supported type.
  Assembly's preflight checks every group exists before any site write.
- `catalog.liveops` — the promo code or coupon promotions, reward chains and offer chains
  found by read-only `xsolla liveops list-promo-codes`, `list-coupons`,
  `list-reward-chain` and `list-offer-chain`. The lists include inactive entries: count
  only those with `is_enabled: true`. Also count the ones `catalog-design`'s pending
  proposal creates and activates under the same yes, so their blocks are in the plan the
  developer approves.
- `content` — publisher page overrides, and the copy the plan will show word for word:
  `content.copy` for block titles, subtitles and descriptions, and `content.faq` for the
  questions and answers, in the primary locale, as the shop brief reference describes.
  Fill `content.seo` by default, without asking: per page, a search title with the game's
  name, a one-line description from the listing, and the key art as the share image.
- `brand` — the listing's art and app icon, once the publisher confirmed they may be
  used, unless they supplied their own: download them next to the brief and list them in
  `brand.images` (key art on the `leadGameSales` background, the icon as the `footer`
  logo). Put the palette taken from that art in `brand.theme`, as the assembly skill's
  visual style describes.
- `sources` — add `{"kind":"description", ...}`, and `{"kind":"external_store", ...}` with
  the listing URL when it supplied facts or art. Keep the provenance of any publisher
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
The developer approves one plan, in `shop-builder-assembly`, shown in the same message as
any pending catalog proposal.

## Failure handling

If intake cannot produce a valid brief, report the missing facts. If assembly stops,
return its exact blocker and backup location — do not retry or switch projects.

## References

- [references/intake-schema.md](references/intake-schema.md) — fields, inference
  boundaries, completeness gate.
- [references/plan-format.md](references/plan-format.md) — the handoff object and its
  rules.
- `shop-builder-assembly/references/shop-brief.md` — authoritative contract.

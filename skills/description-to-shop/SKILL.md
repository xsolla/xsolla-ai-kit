---
name: description-to-shop
description: >-
  Turn a plain-language game description into the normalized, source-attributed shop
  brief consumed by shop-builder-assembly. Use when a publisher has no design or
  written specification and asks to build a Shop Builder site, webshop, top-up page,
  PC portal, or live-service store from prose. This skill owns intake and inference;
  shop-builder-assembly owns presets, confirmation, backups, CLI writes, verification,
  and preview. Do not use this skill to implement a second assembly workflow.
metadata:
  owner: k.shah
  domain: store
---

# Description to Shop

Convert a short game description into a valid `shop-builder-assembly` brief, then
hand it to that skill. Do not call Shop Builder write commands here.

## 1. Extract the description

Read [references/intake-schema.md](references/intake-schema.md). Classify every
required fact as stated, safely inferred, or missing. Infer presentation choices such
as the likely preset; never invent prices, catalog groups, dates, game facts, studio
names, or translated copy.

Ask for all missing required facts in one batch. Use read-only discovery for the
active CLI project and its existing catalog groups. If the catalog is absent or a
named group cannot be found, stop and direct the user to the catalog skill rather than
creating catalog entities.

## 2. Produce the shared brief

Read the input contract in
`shop-builder-assembly/references/shop-brief.md` and write one version-1 JSON object
matching it. In particular:

- Put platforms and lifecycle under `game`.
- Put the proposed slug, locales, and either `auto` or an explicit preset under `site`.
- Map only verified, same-project catalog groups under `catalog.groups`; use
  `__all__` for all items of a supported type.
- Put approved copy and publisher page overrides under `content`.
- Add `{"kind":"description", ...}` to `sources` and preserve any publisher-answer
  provenance used to complete missing facts.
- Never include API keys, tokens, session cookies, passwords, or browser storage.

Validate the result with the assembly skill's
`scripts/validate_shop_brief.py`. Fix input errors before handoff.

## 3. Delegate assembly

Invoke `shop-builder-assembly` with the validated brief. That skill exclusively owns:

- preset selection and page/block defaults;
- the complete confirmation-bound plan;
- project allowlisting and Publisher-login preflight;
- backup-before-write enforcement;
- all `xsolla shopbuilder` writes;
- structural, localization, catalog, readiness, and preview verification;
- the never-publish safeguard and evaluation record.

Do not ask for a separate Description-skill approval and do not run legacy local
assembly scripts. One confirmation in `shop-builder-assembly` covers the exact plan
that will be applied.

## Failure handling

If intake cannot produce a valid brief, report the missing facts. If assembly stops,
return its exact blocker and backup location without retrying or switching projects.

## References

- [references/intake-schema.md](references/intake-schema.md) — description intake and
  inference boundaries.
- [references/plan-format.md](references/plan-format.md) — preview of the normalized
  handoff and how it becomes the assembly plan.
- `shop-builder-assembly/references/shop-brief.md` — authoritative handoff contract
  supplied by the SB-8796 dependency.

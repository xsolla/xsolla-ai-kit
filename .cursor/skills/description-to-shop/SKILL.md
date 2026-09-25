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

Convert a short game description into a valid `shop-builder-assembly` brief, then hand
it over. Never call Shop Builder write commands here.

## 1. Extract the description

Read [references/intake-schema.md](references/intake-schema.md). Classify every required
fact as stated, safely inferred, or missing. Infer presentation choices such as the
likely preset; never invent prices, catalog groups, dates, game facts, studio names, or
translated copy.

Ask for all missing required facts in one batch. Use read-only discovery for the active
CLI project and its catalog groups. If the catalog is absent, or a named group does not
exist, stop and point at the catalog skill rather than creating entities.

## 2. Produce the shared brief

Follow the contract in `shop-builder-assembly/references/shop-brief.md` and write one
version-1 JSON object:

- `game` — platforms and lifecycle.
- `site` — proposed slug, locales, and `auto` or an explicit preset.
- `catalog.groups` — only verified same-project groups; `__all__` for all items of a
  supported type.
- `content` — approved copy and publisher page overrides.
- `sources` — add `{"kind":"description", ...}` and keep the provenance of any publisher
  answer used to fill a gap.
- Never include API keys, tokens, session cookies, passwords, or browser storage.

Validate with the assembly skill's `scripts/validate_shop_brief.py` and fix input errors
before handing off.

## 3. Delegate assembly

Invoke `shop-builder-assembly` with the validated brief. It exclusively owns preset
selection and block defaults, the confirmation-bound plan, project allowlisting and
login preflight, backup-before-write, every `xsolla shopbuilder` write, structural,
localization, catalog, readiness and preview verification, the never-publish safeguard,
and the evaluation record.

Do not request a separate approval here and do not run legacy local assembly scripts.
One confirmation in `shop-builder-assembly` covers the exact plan applied.

## Failure handling

If intake cannot produce a valid brief, report the missing facts. If assembly stops,
return its exact blocker and backup location — do not retry or switch projects.

## References

- [references/intake-schema.md](references/intake-schema.md) — fields, inference
  boundaries, completeness gate.
- [references/plan-format.md](references/plan-format.md) — the handoff object and its
  rules.
- `shop-builder-assembly/references/shop-brief.md` — authoritative contract (SB-8796).

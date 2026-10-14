---
name: localization
description: >-
  Translates an Xsolla catalog and LiveOps into another language. Use when someone
  says "localize the shop", "translate the catalog", "translate item names",
  "translate promotions / promo codes / reward chains", "add Japanese / German /
  Portuguese", "my store is only in English", "bulk translate", or hands over a
  translation CSV. Catalog and LiveOps go through one reviewable CSV. Confirm
  before any write. Not for creating the shop (shop-setup), setting prices
  (catalog-design), or Shop Builder page copy (shopbuilder-translate).
metadata:
  owner: u.filipau
  domain: catalog
  status: draft
---

# Localize a catalog

Catalog and LiveOps text move through one CSV. The model does the translation.
There is no machine-translation service. **Catalog and LiveOps strings are sent
to the agent's model** as the CSV batch. Say that before the first `batch` when
the catalog is a real project.

Nothing here publishes a site. Writes hit the live project named by
`XSOLLA_PROJECT_ID`. There is no catalog sandbox.

Shop Builder page copy (hero, CTAs, FAQ, SEO) is the `shopbuilder-translate`
skill. This skill does not extract or load a site. Moving `catalog_i18n.py`
into `xsolla-cli` as `xsolla catalog localize` is a follow-up. The script
stays here until then.

## Before any write

1. Name the target locale in the user's words (`Japanese` → `ja`). The code table is in [references/supported-languages.md](references/supported-languages.md).
2. Ask whether they already have translations. If yes, `merge`. If no, the model fills the gaps after they confirm the plan.
3. Show the plan: locale, project id, what will change, what already has a translation. Wait for an explicit yes. Then write.

## Commands

From the skill directory:

```
scripts/catalog_i18n.py discover
scripts/catalog_i18n.py export work.csv ja,de --source en
scripts/catalog_i18n.py batch work.csv --locale ja
# model fills the batch, then:
scripts/catalog_i18n.py fill work.csv --locale ja --from batch.json
scripts/catalog_i18n.py check work.csv
scripts/catalog_i18n.py import work.csv          # preview
scripts/catalog_i18n.py import work.csv --write  # only after approval
```

`de-DE` and `de` are the same column. A locale with no column is an error, not a batch of every row. `import` previews unless `--write` is passed. `restore` refuses a snapshot from another project, and a snapshot that names no project. Snapshots and backups go in `l10n-snapshots/` and `l10n-backups/` beside the CSV, not in the repository root. `discover` prints a failure when the attribute list fails.

Load these only when that step needs them:

- [references/translation-csv.md](references/translation-csv.md) — CSV contract and commands
- [references/write-safety.md](references/write-safety.md) — replace semantics, conflicts, rollback
- [references/glossary.md](references/glossary.md) — terminology
- [references/qa.md](references/qa.md) — what `check` decides and what the model must judge
- [references/coverage-matrix.md](references/coverage-matrix.md) — which entities localize

`reward_chain` is on API v2. Promotions are on v3. Chains `daily_chain` and `offer_chain` can be written only while disabled. A reward chain's step names are part of the same PUT, so they take part in the conflict check.

## Out of scope

Prices and regional availability (`catalog-design`). Legal copy. Text baked into images. Shop Builder page copy (`shopbuilder-translate`). Publishing the site.

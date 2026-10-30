---
name: shopbuilder-translate
description: >-
  Translates Shop Builder page copy: hero, CTAs, FAQ, section titles, and page SEO.
  Use when someone says "translate the FAQ", "add a language to Shop Builder",
  "my store is only in English", "translate the hero", or hands over page-copy
  translations. Catalog and LiveOps text are out of scope. Confirm before any
  write. Not for creating the shop (shop-setup or nocode-shop-setup) or setting prices (catalog-design).
metadata:
  owner: s.hossain
  domain: store
  status: draft
---

# Translate Shop Builder page copy

This skill writes Shop Builder page copy only. Catalog and LiveOps text (items, groups, bundles, currency, promotions, reward chains) are `localization`. Do not translate them here.

The model does the translation. There is no machine-translation service.

Nothing here publishes the site. `--commit` writes the live project named by `XSOLLA_PROJECT_ID`. There is no Shop Builder sandbox. `--commit` does not change the language the shop opens in.

## Before any write

1. Name the target locale in the user's words (`Japanese` → `ja-JP`). Codes are in [references/i18n-support.md](references/i18n-support.md).
2. Ask whether they already have translations. If yes, `scripts/ingest-user-translations.sh`. If no, the model fills the gaps after they confirm the plan.
3. Show the plan: locale, what will change, what already has a translation. Wait for an explicit yes. Then write.
4. Catalog and LiveOps strings belong to `localization`. Do not translate them here. For a general "translate my shop" or "translate the shop", run `localization` for that half, and do not report the shop as done after page copy. Say which half is done and which is still open. A page-copy request ("translate the FAQ", "translate the hero") stays on this skill alone.

## Page copy

After the storefront exists. Silent failures and the script list: [references/storefront.md](references/storefront.md). Field failures: [references/translation-notes.md](references/translation-notes.md).

```
scripts/preflight.sh
scripts/export-backup.sh <domain> l10n/backup/<timestamp>
scripts/extract.sh en-US ja-JP
scripts/apply.sh <domain> ja-JP                 # dry run
# explicit yes, then: enable the language and write
scripts/apply.sh <domain> ja-JP --commit --confirm-overwrites
scripts/verify.sh <domain> ja-JP
```

`export-backup.sh` reads the live site with `get-structure` and `get-localization` and writes those two files. It does not change the site. Before any write, the project must be on the approved-test-project allowlist (`XSOLLA_APPROVED_TEST_PROJECTS`). A project that is not on the list is not written. The slug must also appear in that project's `list-websites` result. `get-structure` is not that check.

`--commit` enables the language with `add-language`, then writes the copy. It runs `add-language` only after the allowlist, the `list-websites` check and the pre-write export. If the pre-write export already lists the locale, `add-language` is skipped. A 400 with the message "language is taken" is also success. Any other failure stops the run before any copy is written. If the copy write fails after this run enabled the language, the run prints the `delete-language` command for it. Show it to the user. This skill does not run it.

`--commit` blocks when it would replace an existing translation until `--confirm-overwrites`. `--commit` exports the site again into `l10n/pre-write/` and blocks if the text about to be written changed since extract. A write that returns non-zero fails the run.

The shop opens in the first language of the site language list. This skill does not reorder that list and does not call `delete-language`. If the partner wants the shop to open in the new language, they reorder the list in Publisher Account.

## Out of scope

Catalog and LiveOps text, which `localization` translates. Prices and regional availability. Legal copy. Text baked into images. Publishing the site. Changing the language the shop opens in. For "translate my shop", finishing page copy does not finish the shop.

# shopbuilder-translate

Translates Shop Builder page copy (hero, CTAs, FAQ, section titles, page SEO).
The model does the translation. The scripts move the data and check the write.

Catalog and LiveOps text are out of scope.

## Prerequisites

- Xsolla CLI authenticated with `xsolla auth login`. Do not pass a session token by hand.
- `XSOLLA_MERCHANT_ID` and `XSOLLA_PROJECT_ID`.
- `XSOLLA_APPROVED_TEST_PROJECTS` pointing at the approved-test-project allowlist. Each entry needs integer ids plus `approved_by` and `approval_reference`. The CLI's configured project must be that same project. There is no production denylist.
- A store that already renders.
- `jq` is only for `scripts/smoke-test.sh`. A translation run does not need it.

## Happy path

1. Say the target language. Confirm whether translations already exist.
2. `preflight.sh`, then `export-backup.sh` into `l10n/backup/<timestamp>`.
3. `extract.sh`, then `enable-language.sh`, then `apply.sh` as a dry run.
4. After an explicit yes, `apply.sh --commit`. That checks the allowlist, checks the slug is in that project's `list-websites` result, exports the site again, and blocks if the live text changed since extract.
5. `verify.sh` reads the live store back. It checks that the language is enabled and that the strings came back. It does not fail because the shop still opens in another language.

Nothing is published. There is no sandbox. `--commit` does not change the language the shop opens in. The partner sets that in Publisher Account by reordering the site language list.

## Known limitations

- Prices, legal copy, and text baked into images are out of scope.
- `export-backup.sh` is a read-only export of structure and localization. This skill does not replay it.
- Catalog text is not extracted or written here.

## Layout

```
SKILL.md                 the commands
README.md                this file
references/              storefront procedure and field notes
scripts/                 extract, apply, verify
glossary/                terms to keep and terms to render one way
```

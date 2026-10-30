# CLI assembly operations

Dependency map for `xsolla` 1.9.4 or newer. Run every command against the verified
dedicated-test-project context; do not add per-command project overrides after
preflight.

| Phase | Command | Consumes | Produces / unlocks |
|---|---|---|---|
| Discover | `xsolla config list --json` | Local profile | Merchant and project match; sandbox mode is off (see [Sandbox mode](#sandbox-mode)) |
| Discover | `xsolla auth list-account --json` | Credential store | Active Publisher login state |
| Safety | `preflight.py --approved-test-projects <fixed path>` | Approval list read by scripts only (see [shop brief](shop-brief.md)) | Exact test-project identity is allowlisted |
| Safety | `shopbuilder create-block --help`, only when the site has no common layout | Installed CLI | The usage line names `create-block`; otherwise the layout step is skipped |
| Discover | `xsolla shopbuilder list-websites --json` | Project context | Slug, landing ID, type |
| Backup | `get-landing`, `get-structure`, `get-localization`, `list-assets`, `list-versions` | Existing slug | Restorable configuration evidence |
| Bootstrap | `create-website --type topup` | Name, slug | Empty landing with `type:null` |
| Bootstrap | `set-landing-type --type store` | Slug | Configured webshop landing |
| Pages | `add-page` | Slug, name, path | Page with default template blocks |
| Site layout | `get-block --slug <slug> --block-id <id>` for each ID in `layouts` | `get-structure` layout IDs | The module of each site layout; `common-layout` can sit next to other layouts |
| Site layout | `create-block --slug <slug> --block common-layout` (only if missing) | Pages already created | Site-level layout required by Editor, Publish, and preview; avoids suppressing template header/footer |
| Blocks | `add-block`, `move-block`, and page-scoped `update-block` removal patches | Landing/page/block IDs | Ordered page block list |
| Theme | `update-block` with `type:site` and `type:page` | Landing/page IDs, targeted patches | Site and page source themes |
| Assets | `upload-asset` | Landing ID, local file | Permanent CDN URL |
| Copy | `add-language`, `update-localization`, `update-many-localization` | Slug, page and `L:` IDs | Localized HTML |
| Catalog | `update-block` on `newStore.components` | Same-project group IDs | Store sections |
| Verify | `get-structure`, `get-localization`, `verify-website` | Slug | Plan comparison and readiness result |
| Preview | `enable-preview`, `preview-link` | Slug | Human-reviewable preview only |

`apply_plan.py` and `backup_shop.py` handle expired sessions themselves (one re-login per
run, then retry). The agent never runs `auth login` and never supplies a token. Block operations are in [block-operations.md](block-operations.md).
No script passes `--force`; an operation that requires it stops for review. That includes
`delete-block`, so no script deletes a block.

## Sandbox mode

Shop Builder has no sandbox, so a Shop Builder request implies CLI sandbox mode off.
`preflight.py` settles it (`scripts/cli_environment.py`):

1. Sandbox already off in the active environment: nothing changes.
2. Another environment of the config file in use has sandbox off and the brief's merchant
   and project (`test` first): every script call gets `--environment <name>` and no
   config file is written. Preflight reports the name as `cli_environment`; add the same
   flag to any `xsolla` command you run yourself.
3. Otherwise preflight stops before any CLI write and says it needs confirmation. The
   stop names the exact command, `xsolla config set sandbox false`, and the folder it
   runs in. Ask the user to confirm (the Confirm shape in SKILL.md). Only after a yes, run
   preflight again with `--confirm-sandbox-off`. Preflight then runs the command in the
   directory of the config file in use and records the switch in a restore record,
   `~/.shop-builder-sandbox.json`.
4. The last step of the run is `scripts/restore_sandbox.py`. It runs
   `xsolla config set sandbox true` in the same directory and removes the record. With no
   record it changes nothing. Run it after apply and verification, and also when the run
   stopped or the plan was not confirmed; a run that never restores leaves sandbox off.

Preflight adds one line to `plan_notes`, shown as one plan bullet: "Using the CLI test
environment (sandbox off)" on path 2 (no config written), "CLI sandbox mode switched off
for Shop Builder; it is switched back on when the run ends" on path 3, nothing on path 1.
Backup, apply and verification reuse the choice and never change the config. The CLI
1.9.4 reads `./.xsolla.json` when the working
directory has one, else `~/.xsolla.json`, and `config set` writes `./.xsolla.json`,
creating a stub without merchant or project when there is none. So never run
`xsolla config set` yourself, and never from the working folder.

## ID dependencies

- Slug/domain identifies landing-level reads and page creation.
- Top-level `_id` from `get-structure` is the landing ID for block and asset commands.
- `pages[]._id` is the page ID; in the verified CLI 1.9.4 response,
  `pages[].blocks[]` is the ordered list of full block objects containing `_id`,
  `module`, values, and components.
- The top-level `blocks[]` field contains landing-level block IDs in that response.
- Re-read structure after every add, removal, duplicate, or move before constructing the
  next position- or ID-sensitive command.
- A page-scoped `update-block` removal patch takes the block out of `pages[].blocks` only.
  Its id stays in the top-level `blocks[]`, and that is expected: verification checks the
  page block lists, not `blocks[]`. A later `delete-block` on that id answers
  `block_is_not_presented_on_page`.

## Patch boundaries

- Patch only documented leaf paths. Never replace whole `values`, `components`, theme,
  section, page, or site objects.
- Do not patch `_id`, `module`, `blockVersion`, or derived `calculatedTheme`.
- Page theme overrides site theme; apply brand colors to both layers.
- Block text is stored in localization, not directly in block values.
- A new `newStore` section title must be localized before its `L:` ID is enabled.
- Reconcile `newStore` sections with index-targeted patches. Update existing section
  leaves, append only the missing component indices, and remove stale indices from the
  end. Do not replace the complete `components` array. When approved localized titles
  are unavailable, keep each section title disabled rather than reusing a misleading
  template title.

## Page deletion

The CLI does not expose page deletion. If an existing target contains paths outside
the confirmed plan, stop before writes and report the extra paths instead of leaving
a silently mixed preset or deleting the whole website.

Use `scripts/verify_structure.py` for the deterministic portion of verification. It
reads each site layout's module with read-only `get-block`. It does not replace
`verify-website`, localization/catalog checks, or visual preview.

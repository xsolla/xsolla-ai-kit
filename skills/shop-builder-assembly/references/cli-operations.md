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
| Theme | `update-block` with `type:site` and `type:page`, through `apply_style.py` | Landing/page IDs, targeted patches | Site theme `theme.input`; pages on the site theme |
| Assets | `upload-asset --type image`, through `apply_style.py` | Landing ID, local file | Permanent CDN URL in a block's background or logo |
| Copy | `update-many-localization` through `apply_style.py`; `add-language` in `apply_plan.py` | Slug, page and `L:` IDs | Localized HTML in the primary locale |
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
   runs in. Show that exact command and directory verbatim, without reconstructing them,
   and ask for a separate explicit yes to that command only. The later site-plan yes is
   still required. Only after the command yes, rerun preflight with
   `--confirm-sandbox-off`. Preflight then runs the command in the
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

## Runs under one yes

The developer's one yes can cover more than one `apply_plan.py` run. Each later run is
covered only when its render says so; `apply_plan.py` checks this again and stops before
any write. Every script that writes (`apply_plan.py`, `apply_style.py`,
`patch_backgrounds.py`) also takes
`--approved-test-projects <allowlist>`, and refuses to write without it.

- **A new site's two runs.** A new site's generated blocks have no IDs before creation, so
  it is applied in two runs: the bootstrap, then the rest. Save run 1's report as
  `run1-report.json`, export again, and render with `--structure`, `--approved-plan
  approved-plan.json` and `--run-report run1-report.json`. Apply run 2 with
  `--approved-plan`, `--run-report`, `--backup-dir` and the approved `confirmation_id` only
  if the render says "Covered by the approved plan": the same pages, sections, catalog,
  locales, brand and content, and removals only of blocks run 1 created or the approved
  plan listed.
- **A run that stops partway.** A run that stops after its writes began, such as on an
  authentication failure, prints a `stopped-partway` report: save it as
  `partial-report.json`. Export again, render with `--structure`, `--approved-plan` and
  `--run-report partial-report.json`, and apply under the same yes when the render says
  "Covered by the approved plan"; otherwise ask again. Every report carries what all
  earlier runs under the yes created (`created_block_ids`, `all_created_pages`), and a
  stopped run records each page and block as it is created, so the latest report is the
  one to pass.
- **Background fixes after the visual review.** The yes covers `values.background` leaves
  (color, gradient, image, position, size) on blocks this assembly created, applied with
  `scripts/patch_backgrounds.py <brief.json> --approved-plan approved-plan.json
  --run-report <report> --backup-dir <dir> --fixes fixes.json --approved-test-projects
  <allowlist>` after a fresh export. Pass `--run-report` once for every earlier run
  (`run1-report.json` and run 2's report for a new site): run 1's report is the one that
  lists the blocks it created. `fixes.json` is a list of
  `{"block_id": …, "leaf": …, "value": …}`. It refuses anything else, an image not
  uploaded to the site, a gradient unlike the ones already on it, and an opaque color
  over a block that keeps its image.
- **The theme, images and copy, after the last apply run.** Export again, then run
  `scripts/apply_style.py <brief.json> --approved-plan approved-plan.json --run-report
  <report> --backup-dir <dir> --approved-test-projects <allowlist>`, with `--run-report`
  once for every earlier run, as above. It sets the approved `brand.theme` on the site
  theme's `theme.input`, only keys the site already has, each in its current format, and
  sets `theme.enabled` to `false` on the planned pages that use their own theme: pages the
  runs created, and existing pages only when the approved plan listed them
  (`theme.pages_to_site_theme`). It reads `get-localization` before and after, and stops
  if the text changed. Before any write it also compares `get-localization` with the
  backup's, and stops if the text was edited after the export. Pages switch to the site
  theme only when the site theme holds the palette; a key it can't set goes to
  `needs_human`. A rerun writes nothing. When the CLI doesn't recalculate
  `calculatedTheme`, the report's `needs_human` has the Editor step for the handoff, and
  a rerun repeats it as a reminder.
  Then the images: each `brand.images` file must be the one the plan showed (its
  `sha256`), at most 10 MB. It uploads each file once with `upload-asset --landing-id <id>
  --file <path> --type image` and keeps the returned URL in `asset-cache.json` next to the
  approved plan (`--asset-cache` to move it); a rerun reuses a cached URL that is still in
  the site's asset list. It puts the URL in `values.background.img` or `values.logo.img`
  of the planned module's blocks that the runs created, and of existing blocks only when
  the plan listed them (`images[].existing_block_ids`). A block without that slot, a
  federated block, and an opaque background color over the image go to `needs_human`.
  Then the copy, in the primary locale only: each `content.copy` item goes to the `L:` id
  in `values.<field>.id` of its module's blocks, under the same rules for existing blocks.
  Each `content.buttons` label goes, as plain text, to `values.buttons[<position - 1>]
  .button.action.text.id` of the planned `leadGameSales` blocks; a buy button, a missing
  position and a federated hero go to `needs_human`.
  The FAQ block's `questionV2` items are made to match `content.faq`: texts written,
  extra items removed (`enable: false` is ignored there), missing ones added with stable
  IDs. All text goes in one `update-many-localization` call, with each string's current
  `description`, before the FAQ items that point at it are added. A string in `common`
  (shared across the site) or one another block uses that the plan didn't list is not
  written: it goes to `needs_human`. Two approved items that write different text to one
  string stop the run before any text is written. It reads every string back, checks the
  FAQ items by their question text IDs in order (the server regenerates component
  `_id`s), and stops if a string outside the plan changed; a removed item's strings may
  go with it. Each page's `content.seo` goes to
  the `L:` ids in `page.seo.title`, `page.seo.description` and `page.seo.ogImage`, a
  sibling of `page.blocks`: plain text, and for `ogImage` the uploaded image's CDN URL,
  through the same upload cache. A page without those fields goes to `needs_human`.
  With a palette, the report's `needs_human` ends with the Pay Station theme step (decision
  D5): the palette by Pay Station's color groups (surfaces, texts, controls, borders) and
  the Pay Station customization link. No API or CLI command sets that theme yet.

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

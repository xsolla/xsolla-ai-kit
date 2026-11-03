# CLI assembly operations

This is the dependency map for `xsolla` 1.9.4 or newer. Run every command against the
already verified dedicated-test-project context; do not add per-command
project overrides after preflight.

| Phase | Command | Consumes | Produces / unlocks |
|---|---|---|---|
| Discover | `xsolla config list --json` | Local profile | Merchant and project match; sandbox mode is off |
| Discover | `xsolla auth list-account --json` | Credential store | Active Publisher login state |
| Safety | `preflight.py --approved-test-projects <file>` | Separate local approval record | Exact test-project identity is allowlisted |
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
| Copy | `add-language`, `update-localization`, `update-many-localization` | Slug, page and `L:` IDs | Localized HTML |
| Catalog | `update-block` on `newStore.components` | Same-project group IDs | Store sections |
| Verify | `get-structure`, `get-localization`, `verify-website` | Slug | Plan comparison and readiness result |
| Preview | `enable-preview`, `preview-link` | Slug | Human-reviewable preview only |

`apply_plan.py` and `backup_shop.py` do not log in before commands; the CLI refreshes
an expired token on its own. When a command fails with an authentication error or a
Publisher-session bootstrap failure, the script runs `xsolla auth login` once per run,
re-reads `xsolla config list --json`, stops if the merchant, project, or sandbox
setting changed, and retries the command. A second authentication failure ends the
run. The scripts never read a browser cookie, never accept a manually copied PA token,
and do not retry ambiguous API operation failures. Session-bootstrap HTTP 429
responses use bounded backoff.
No script passes `--force`; an operation that requires it stops for review.

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
  "Covered by the approved plan"; otherwise ask again.
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
- **The theme and images, after the last apply run.** Export again, then run
  `scripts/apply_style.py <brief.json> --approved-plan approved-plan.json --run-report
  <report> --backup-dir <dir> --approved-test-projects <allowlist>`, with `--run-report`
  once for every earlier run, as above. It sets the approved `brand.theme` on the site
  theme's `theme.input`, only keys the site already has, each in its current format, and
  sets `theme.enabled` to `false` on the planned pages that use their own theme: pages the
  runs created, and existing pages only when the approved plan listed them
  (`theme.pages_to_site_theme`). It reads `get-localization` before and after, and stops
  if the text changed. A rerun writes nothing. When the CLI doesn't recalculate
  `calculatedTheme`, the report's `needs_human` has the Editor step for the handoff.
  Then the images: each `brand.images` file must be the one the plan showed (its
  `sha256`), at most 10 MB. It uploads each file once with `upload-asset --landing-id <id>
  --file <path> --type image` and keeps the returned URL in `asset-cache.json` next to the
  approved plan (`--asset-cache` to move it); a rerun reuses a cached URL that is still in
  the site's asset list. It puts the URL in `values.background.img` or `values.logo.img`
  of the planned module's blocks that the runs created, and of existing blocks only when
  the plan listed them (`images[].existing_block_ids`). A block without that slot, a
  federated block, and an opaque background color over the image go to `needs_human`.

## ID dependencies

- Slug/domain identifies landing-level reads and page creation.
- Top-level `_id` from `get-structure` is the landing ID for block and asset commands.
- `pages[]._id` is the page ID; in the verified CLI 1.9.4 response,
  `pages[].blocks[]` is the ordered list of full block objects containing `_id`,
  `module`, values, and components.
- The top-level `blocks[]` field contains landing-level block IDs in that response.
- Re-read structure after every add, delete, duplicate, or move before constructing the
  next position- or ID-sensitive command.

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

## Known gaps to track

The official Blocks page is the authoritative product inventory, but the CLI does not
expose a machine-readable mapping from those names to current template modules or
their value contracts. The mapping in `block-catalog.md` therefore combines the
official inventory, the live Add block palette, and sanitized UI-created exports.
Subscriptions is absent from the observed palette, and five palette entries are absent
from the official page. Current exports show that `lead` versus `leadGameSales` is
landing-template-dependent and that `federated` is a runtime wrapper whose effective
module is `values.blockId`. Preserve that wrapper and patch only exported leaf paths.
Track remaining discrepancies as linked gaps rather than guessing aliases.

- Inventory/UI reconciliation: still open
- CLI module and contract discovery: still open

The first dedicated-project run also found defects in Publisher-session reuse,
`verify-website`, and CLI preview authorization. See
[`test-findings.md`](test-findings.md) for reproducible evidence.

The CLI does not expose page deletion. If an existing target contains paths outside
the confirmed plan, stop before writes and report the extra paths instead of leaving
a silently mixed preset or deleting the whole website.

Use `scripts/verify_structure.py` for the deterministic portion of verification. It
reads each site layout's module with read-only `get-block`. It does not replace `verify-website`, localization/catalog checks, or visual preview; it
isolates structural failures from the currently tracked CLI readiness/preview defects.

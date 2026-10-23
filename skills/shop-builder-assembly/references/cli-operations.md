# CLI assembly operations

Dependency map for `xsolla` 1.9.4 or newer. Run every command against the verified
sandbox or dedicated-test-project context; do not add per-command project overrides after
preflight.

| Phase | Command | Consumes | Produces / unlocks |
|---|---|---|---|
| Discover | `xsolla config list --json` | Local profile | Merchant, project, environment/sandbox match |
| Discover | `xsolla auth list-account --json` | Credential store | Active Publisher login state |
| Safety | `preflight.py --approved-test-projects <fixed path>` | Approval list read by scripts only (see [shop brief](shop-brief.md)) | Exact non-sandbox test-project identity is allowlisted |
| Discover | `xsolla shopbuilder list-websites --json` | Project context | Slug, landing ID, type |
| Backup | `get-landing`, `get-structure`, `get-localization`, `list-assets`, `list-versions` | Existing slug | Restorable configuration evidence |
| Bootstrap | `create-website --type topup` | Name, slug | Empty landing with `type:null` |
| Bootstrap | `set-landing-type --type store` | Slug | Configured webshop landing |
| Pages | `add-page` | Slug, name, path | Page with default template blocks |
| Blocks | `add-block`, `move-block`, and page-scoped `update-block` removal patches | Landing/page/block IDs | Ordered page block list |
| Theme | `update-block` with `type:site` and `type:page` | Landing/page IDs, targeted patches | Site and page source themes |
| Assets | `upload-asset` | Landing ID, local file | Permanent CDN URL |
| Copy | `add-language`, `update-localization`, `update-many-localization` | Slug, page and `L:` IDs | Localized HTML |
| Catalog | `update-block` on `newStore.components` | Same-project group IDs | Store sections |
| Verify | `get-structure`, `get-localization`, `verify-website` | Slug | Plan comparison and readiness result |
| Preview | `enable-preview`, `preview-link` | Slug | Human-reviewable preview only |

`apply_plan.py` and `backup_shop.py` handle expired sessions themselves (one re-login per
run, then retry). The agent never runs `auth login` and never supplies a token. Block operations are in [block-operations.md](block-operations.md).

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

## Page deletion

The CLI does not expose page deletion. If an existing target contains paths outside
the confirmed plan, stop before writes and report the extra paths instead of leaving
a silently mixed preset or deleting the whole website.

Use `scripts/verify_structure.py` for the deterministic portion of verification. It
does not replace `verify-website`, localization/catalog checks, or visual preview.

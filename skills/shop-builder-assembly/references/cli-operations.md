# CLI assembly operations

This is the dependency map for `xsolla` 1.9.4 or newer. Run every command against the
already verified sandbox or dedicated-test-project context; do not add per-command
project overrides after preflight.

| Phase | Command | Consumes | Produces / unlocks |
|---|---|---|---|
| Discover | `xsolla config list --json` | Local profile | Merchant, project, environment/sandbox match |
| Discover | `xsolla auth list-account --json` | Credential store | Active Publisher login state |
| Safety | `preflight.py --approved-test-projects <file>` | Separate local approval record | Exact non-sandbox test-project identity is allowlisted |
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

Before each Shop Builder command, `apply_plan.py` refreshes the supported
Publisher login through `xsolla auth login`. If a read reports that session bootstrap
produced no cookie before the operation was issued, it performs one bounded refresh
and retries that read. It never reads a browser cookie, never accepts a manually copied
PA token, and does not retry ambiguous API operation failures. Session-bootstrap HTTP
429 responses use bounded backoff.

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

- Inventory/UI reconciliation: [SB-8990](https://xsolla.atlassian.net/browse/SB-8990)
- CLI module and contract discovery: [SB-8991](https://xsolla.atlassian.net/browse/SB-8991)

The first dedicated-project run also found defects in Publisher-session reuse,
`verify-website`, and CLI preview authorization. See
[`test-findings.md`](test-findings.md) for reproducible evidence and request IDs.

The CLI does not expose page deletion. If an existing target contains paths outside
the confirmed plan, stop before writes and report the extra paths instead of leaving
a silently mixed preset or deleting the whole website.

Use `scripts/verify_structure.py` for the deterministic portion of verification. It
does not replace `verify-website`, localization/catalog checks, or visual preview; it
isolates structural failures from the currently tracked CLI readiness/preview defects.

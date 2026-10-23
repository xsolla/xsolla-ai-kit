# CLI maintainer notes

For people maintaining the scripts, not for agent replies. Agent-facing rules are in
`skills/shop-builder-assembly/references/cli-operations.md`.

## Session retry

`apply_plan.py` and `backup_shop.py` do not log in before commands; the CLI refreshes
an expired token on its own. When a command fails with an authentication error or a
Publisher-session bootstrap failure, the script runs `xsolla auth login` once per run,
re-reads `xsolla config list --json`, stops if the merchant, project, or sandbox
setting changed, and retries the command. A second authentication failure ends the
run. The scripts never read a browser cookie, never accept a manually copied PA token,
and do not retry ambiguous API operation failures. Session-bootstrap HTTP 429
responses use bounded backoff.
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


# CLI integration eval protocol (fixed before any run)

Each run: one intent, one kit version, a fresh empty game directory, sandbox project 314771.
The agent reads the skill files of its version and follows them for the intent.

Versions:
- BEFORE = origin/main @ ab59c65, skills at a detached checkout of origin/main
- AFTER  = feat/cli-integration working tree, skills at this branch's skills/

Simulated user (same for both versions):
- Answers "yes" to every confirmation and plan approval.
- Has run `xsolla auth login` before the run, and runs it again if a skill asks.
- On intent 1 only (a fresh setup), the browser sign-in the user did before the run counts as
  one manual credential step when the version's skill uses `xsolla auth login`.
- Has NO API key or token to paste, and doesn't open Publisher Account to copy one. Each time a
  skill tells the user to copy/paste a key, token or secret into chat, `.env` or the shell, that
  is one **manual credential step**. The run then continues as far as it can without it.
- Will do a Publisher Account step only for things no API offers (OAuth client, webhook URL,
  agreement); each such step is counted as a **PA step**, not a credential step.

Safety (both versions): read-only commands and `--dry-run` only. No real writes, no
`auth login/logout`, no `publisher create-api-key`, no `config set` outside the run directory,
no REST call that writes. Never print a key or token.

Measured per run (JSONL, one object per run):
- `intent`, `version`, `started_at`, `ended_at`
- `credential_steps`: count of manual credential steps the skill required
- `pa_steps`: count of Publisher Account steps
- `ops_cli`: agent-side Xsolla operations the skill routes through `xsolla`
- `ops_rest`: agent-side Xsolla operations the skill routes through raw REST
  (operations in code the developer ships are NOT counted on either side)
- `first_ok_seconds`: seconds from start to the first Xsolla call that succeeded (null if none)
- `outcome`: `pass` (the agent reached the end of the skill's agent-side steps, or stopped
  correctly at a human-only step), `blocked` (stopped because it needed a credential or access it
  couldn't get), `fail` (wrong action, unsafe action, or the skill's instructions didn't work)
- `interventions`: anything a human had to do beyond the simulated user rules
- `notes`: one or two sentences

Intents (fixed):
1. merchant-setup — "Set up Xsolla for my game project so you can start building the shop."
2. catalog-design — "Configure my Xsolla catalog: gems (virtual currency), a 100-gem pack, a booster priced in gems, and a starter bundle." (dry-run writes only)
3. login-setup — "Add Xsolla Login to my web game with email and password sign-in."
4. login-styling — "Make the Xsolla Login widget match my game's dark purple theme."
5. headless-checkout-integration — "Add card payments with Xsolla Headless Checkout to my web shop."
6. webhooks-impl — "Write an Xsolla webhook handler for my Express backend and test it locally."
7. production — "Take my Xsolla shop live. What's left before real payments work?"
8. shop-setup — "Build me a headless shop for my game." (stop after Phase 0 and the plan)
9. catalog-design — "Import these 5 items into my catalog in one go." (bulk; dry-run only)
10. merchant-setup — "I need an API key for my game's backend server."

Metrics reported:
- CLI share of agent-side operations = sum(ops_cli) / (sum(ops_cli) + sum(ops_rest)), target ≥ 80% (AFTER)
- Manual credential steps on a fresh setup (intent 1), target 1 (the CLI login)
- Skill success rate BEFORE vs AFTER (pass / runs), target: no drop
- Setup time: first_ok_seconds for intent 1, reported as a baseline

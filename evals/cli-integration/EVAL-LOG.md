# Eval log — CLI integration

Every run behind the CLI-integration metrics: the same ten intents, run once on the kit before
this change and once after. Scored on what the agent did and what each skill made the user do,
not on the agent's prose.

**20 runs: 10 on the base, 10 on this branch.** Run 2026-10-20. The base is `origin/main` at
`ab59c65`; the branch is `feat/cli-integration` at `a37d4a3`, before the fixes listed at the end (later rebuilt on `integration/sb-ai-3` as `b14dd24`, same skill content).
Agents were `claude-opus-5-5` on CLI `dev` 379d24a, against sandbox project 314771. Each run got
a fresh empty game directory. The protocol, written before any run, is in
[PROTOCOL.md](PROTOCOL.md), and one JSON line per run is in [runs.jsonl](runs.jsonl).

Every run was read-only. Catalog writes were dry-runs, and no payment token was minted. No
Login project, user, webhook or upload was created, and no API key was minted. The live write
test is in `skills/catalog-design/SKILL.md`, under "Agent test".

## Metrics

| Metric | Target | Before | After |
|---|---|---|---|
| **CLI share of agent-side Xsolla operations** | ≥ 80% | 0% (0 of 18) | **90%** (76 of 84) |
| **Manual credential steps on a fresh setup** (intent 1) | 1 (the CLI sign-in) | 1 pasted API key, plus a Publisher Account trip for the IDs | **1** (browser sign-in) |
| **Credential steps across all 10 intents** | report | 10 | **2** |
| **Skill success rate** (pass / runs) | no drop | 2 / 10 | **8 / 10** |
| **Time to first successful Xsolla call** (intent 1) | baseline | never (blocked) | **0 s** (`auth status`); first network call about 10 s |

The 8 REST operations left on the branch are named gaps the CLI has no command for: the Login
styling upload and its two reads (bearer from `xsolla auth get-token`), the Pay Station utils
check, and the Login runtime checks in `login-setup` step 10. See
[docs/cli-gaps.md](../../docs/cli-gaps.md).

## The intents

| # | Skill | Prompt |
|---|---|---|
| 1 | merchant-setup | Set up Xsolla for my game project so you can start building the shop. |
| 2 | catalog-design | Configure my catalog: gems, a 100-gem pack, a booster priced in gems, a starter bundle. |
| 3 | login-setup | Add Xsolla Login to my web game with email and password sign-in. |
| 4 | login-styling | Make the Xsolla Login widget match my game's dark purple theme. |
| 5 | headless-checkout-integration | Add card payments with Xsolla Headless Checkout to my web shop. |
| 6 | webhooks-impl | Write an Xsolla webhook handler for my Express backend and test it locally. |
| 7 | production | Take my Xsolla shop live. What's left before real payments work? |
| 8 | shop-setup | Build me a headless shop for my game (to the end of Phase 0). |
| 9 | catalog-design | Import these 5 items into my catalog in one go. |
| 10 | merchant-setup | I need an API key for my game's backend server. |

## Runs

| # | Before | After | What changed |
|---|---|---|---|
| 1 | blocked | **pass** | Before: copy an API key out of Publisher Account. After: sign in, confirm the project, `.env` written, 11 CLI calls. |
| 2 | blocked | **pass** | Before: 5 Admin REST calls that need the pasted key, no dry-run. After: backup, 5 dry-run writes, storefront check, backup compare. |
| 3 | pass | **pass** | Before: an exported API key the email flow never uses, plus Publisher Account for the Login project. After: `login list-project` finds the project; OAuth client and callback URL still in Publisher Account. |
| 4 | blocked | **pass** | Before: needs a pasted Publisher Account bearer token. After: the two reads work with the CLI's bearer; the upload is still REST. |
| 5 | blocked | blocked | Before: needs the pasted key. After: needs a backend key from `publisher create-api-key`, which the eval rules forbid. No step asks the user for a key. |
| 6 | pass | **pass** | Both still need the webhook secret from Publisher Account. After: local tests run through `xsolla webhook trigger` instead of hand-signed curl. |
| 7 | blocked | **pass** | Before: the only contract check mints a production token with the pasted key. After: `shopbuilder list-agreements` shows "unsigned" with a read-only call. |
| 8 | blocked | **pass** | Before: Phase 0 is all Publisher Account and a pasted key. After: Phase 0's account part finishes through the CLI. |
| 9 | blocked | **pass** | Before: a REST JSON-file import that needs the key and a publicly hosted file. After: `admin-import-catalog --dry-run`, reusing the existing gems currency. |
| 10 | blocked | blocked | Before: copy a key from Publisher Account. After: the mint is one CLI command, but the eval rules forbid running it. |

**Both blocked runs on the branch were blocked by the eval's own rule against minting keys, not
by the skill.** Neither asks the user for a credential. A real run mints the key into `.env`
without printing it.

## Interventions and failures

- **0 failures.** No run took a wrong or unsafe action.
- **The pin step was refused 3 times.** Claude Code's auto-mode permission classifier refused
  `xsolla config set` inside a run directory 3 times (intents 1, 3 and 8 on the branch). The run
  used `~/.xsolla.json` instead. That is a harness limit, not a skill failure; it is noted so
  nobody mistakes it for one.
- **2 webhook runs needed an answer from the runner.** The runner answered the "how are goods
  granted?" question for the webhook runs (intent 6, both versions), as the skill requires.
- **One stray command.** One runner accidentally ran `xsolla config set login-project-id` with no
  value. The CLI refused it before writing anything, and `~/.xsolla.json` was unchanged
  afterwards.

## Fixed after the runs

The runs found these problems in the branch. They were fixed after the runs and not re-run:

- **merchant-setup:** if `config init` succeeded and `config set` failed, an empty
  `./.xsolla.json` hid the real config. The pin step is now one chain, and it deletes the new
  file if any `config set` fails. Tested on both paths.
- **login-setup:** `config set login-project-id` would write the global `~/.xsolla.json` when
  `merchant-setup` hadn't pinned the game folder yet, and the `.env` edit failed when `.env`
  didn't exist. It now checks for `./.xsolla.json` first and creates `.env`.
- **catalog-design:** `admin-import-catalog` returns no import ID to poll, and
  `admin-get-import-status` answers 403 on a standard key. The import is now confirmed with
  `backup_catalog.py --compare`.
- **production:** Step 1b contradicted itself about `--sandbox`, and Step 1a didn't say the
  `product` agreement entry can be ignored.
- **shop-plan:** it created `.env` world-readable, so every CLI call warned until
  `merchant-setup` ran. It now creates `.env` with mode 600.
- **webhooks-impl:** the test examples used `/webhooks/xsolla`, but the handler code mounts
  `/xsolla/webhooks`. Now they match.

## Still open

- **Two flows were never run:** the Login styling upload and the checkout's dev token route.
  Each needs a write the eval doesn't allow. The upload is visible on every app that uses the
  Login project, and the token route needs a minted backend key.
- **Single round:** one run per intent and version, and the runners counted operations by hand.
  Treat the shares as indicative, not exact.
- **Release check:** every run used a `dev` build of CLI `main`. See the release question in
  [docs/cli-gaps.md](../../docs/cli-gaps.md).

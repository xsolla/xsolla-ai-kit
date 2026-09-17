# shop-plan eval

Measures whether the `shop-plan` decision step actually does its job, by running the real agent
against fixed intents and checking what it did — not by reading its answers and forming an opinion.

Everything here is a development tool. It is **not** part of the skills and is never installed into
a partner's project (`xsolla skills install` copies a skill's whole folder, so the runner
deliberately lives outside `skills/`).

## Prerequisites

- **Claude Code CLI** on `PATH`, signed in (`claude --version`). Runs cost usage against your account.
- **Python 3.9+**, standard library only.
- **A clean checkout.** The runner tests the skills as they are on disk (`--skills-ref WORKTREE`) or
  as of any git ref.
- Never run it inside a project you care about: every run happens in a throwaway directory under
  `$TMPDIR`, and the runner refuses to place one inside this repo.

## Happy path

```bash
# the whole suite, twice per case, with the origin/main comparison for Metric 3
python3 evals/shop-plan/run_evals.py --out evals/shop-plan/results/$(date +%F).jsonl

# one case while iterating
python3 evals/shop-plan/run_evals.py --out /tmp/try.jsonl --rounds 1 \
  --cases path-shopbuilder-solo-indie --baseline-ref none --token-probes 0

# scoring logic only — no agent, no network, no usage
python3 -m unittest discover -s evals/shop-plan -p 'test_*.py'

# ticket 3's assertion: the branch changes no headless-only skill
evals/shop-plan/check-headless-unchanged.sh
```

Exit code `0` = every metric met its target, `1` = one missed, `2` = the run itself could not proceed
(no CLI, rate-limited preflight, results file already exists).

A long run can be taken in batches (`--cases …` into separate files), with the Metric 3 token probes
taken on their own, then combined. Pass `--raw-dir` to keep the transcripts somewhere lasting:

```bash
R=evals/shop-plan/results
python3 evals/shop-plan/run_evals.py --probes-only --token-probes 5 --out $R/<date>-token-probes.json
python3 evals/shop-plan/run_evals.py --summarize $R/<batch>.jsonl … --probes $R/<date>-token-probes.json --out $R/<date>-summary.json

# after a scorer fix: re-score saved transcripts into a new file, running no agent
python3 evals/shop-plan/run_evals.py --rescore $R/<batch>.jsonl --raw-dir <transcripts> --out $R/<batch>-rescored.jsonl
```

`--rescore` only touches harness-error records, only while `cases.json` is unchanged, and not cases
that check the final `.env` (those need a re-run). Each keeps its original result under `rescored`.

## What is measured

`cases.json` holds the intents and the expected outcome of each. Expectations are written **before**
a run and never edited afterwards to fit a result; every record carries that file's `sha256`.

| Category | Intents | What must happen |
|---|---|---|
| `path` | 10 — five clearly headless, five clearly Shop Builder, each stating all five criteria | `shop-plan` is selected, **nothing is written before the developer confirms**, then the confirmed path is recorded exactly once and the agent stops rather than starting a build |
| `state` | 4 — build already in flight, path already decided, hand-edited invalid value, genuinely conflicting answers | The recorded decision is never discarded or silently rewritten, and nothing is written before a confirmation |
| `regression` | 5 — webhook signature, Google Pay, currency packages, login theming, API keys | The headless-side skill still wins the prompt; `shop-plan` does not intercept. Run against both this branch and `origin/main` |

### The three metrics

1. **Recommendation accuracy — target ≥ 9/10.** The path recorded after confirmation equals the
   known-right answer for that intent. Asserted from `.env`, not from the agent's prose.
2. **Unintended writes before confirmation — target 0.** For every `path` and `state` run, turn one
   must leave the directory byte-identical, run no write tool, and reach no Xsolla command. Checked
   three ways: a file hash snapshot, a scan of every tool call, and a stub `xsolla` on `PATH` that
   refuses and logs any invocation.
3. **Cost and regression — report, no drop.** Added prompt tokens (median of repeated trivial-prompt
   probes, this branch vs `origin/main`), and the headless-skill selection rate on both sides.

## Rules for a valid run

- **Preserve failed runs.** Results files are append-only history; the runner refuses to overwrite
  one. Never re-run a case to replace a bad result with a better one.
- **A scorer bug is fixed in the scorer.** If a run is flagged wrongly, fix the check, add the case
  to `test_run_evals.py`, and re-score the saved transcripts — don't re-run the agent until it agrees.
- **Infrastructure failures are not evidence.** A rate limit, API error or timeout is recorded as
  `error_kind: "infrastructure"`; it never counts as a pass, and it never counts as a skill failure.
- **Running out of turns is not a crash.** A turn that stops at `--max-turns` is scored on what the
  agent did; it is flagged `hit_turn_limit` in the log. A wrong outcome still fails the checks.
- **Two rounds minimum.** Inconsistency between rounds is itself a finding.

## Known limitations

- **Not isolated from the machine's own Claude setup.** Runs inherit the user's global `CLAUDE.md`,
  their installed plugin skills (which appear alongside the kit's in the skill list) and their
  settings. `--setting-sources` does not remove bundled skills, and `--bare` needs an
  `ANTHROPIC_API_KEY` this project does not use. Compare runs from one machine, not across machines.
- **Prompt-size measurements drift between runs** — separate runs have differed by thousands of
  tokens; probes interleaved in one run agreed within a few. Only compare branch and baseline taken
  together, and read the median and range, not a single number.
- **The write scan is a heuristic** on top of the authoritative file-hash diff. It exists to catch
  writes *outside* the run directory; quoted text is stripped before it looks for redirections.
- **Sessions leave transcripts** under your Claude config directory, one per throwaway project.
  Delete them after a batch.
- **Not run in CI** — it needs an interactive Claude login and real usage. Run it before a PR that
  touches `shop-plan` or `shop-setup`, and commit the results file.

# shop-plan eval

Checks whether the `shop-plan` decision step does its job, by running the real agent against fixed
intents and scoring what it did — not by reading its answers and forming an opinion.

This is a development tool. It is never installed into a partner's project, which is why it lives
outside `skills/` (`xsolla skills install` copies a skill's whole folder).

## Prerequisites

- **Claude Code CLI** on `PATH`, signed in. Runs cost usage against your account.
- **Python 3.9+**, standard library only.
- Never run it inside a project you care about. Every run happens in a throwaway directory under
  `$TMPDIR`, and the runner refuses to place one inside this repo.

## Running it

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

Exit `0` = every metric met its target, `1` = one missed, `2` = the run could not proceed (no CLI,
rate-limited preflight, results file already exists). Each run writes `<out>-summary.json` beside its
results. A usage limit will cut a long run short — take it in batches with `--cases`, one file each,
and pass `--raw-dir` to keep the transcripts somewhere lasting.

## What is measured

`cases.json` holds 19 intents and what each must produce. Expectations are written **before** a run
and never edited afterwards to fit a result; every record carries that file's `sha256`.

| Category | Intents | What must happen |
|---|---|---|
| `path` | 10 — five clearly headless, five clearly Shop Builder, each stating all five criteria | `shop-plan` is selected, nothing is written before the developer confirms, then the confirmed path is recorded exactly once and the agent stops rather than building |
| `state` | 4 — build already in flight, path already decided, hand-edited invalid value, conflicting answers | The recorded decision is never discarded or silently rewritten, and nothing is written before a confirmation |
| `regression` | 5 — webhook signature, Google Pay, currency packages, login theming, API keys | The headless-side skill still wins the prompt. Run against both this branch and `origin/main` |

The three metrics, from the epic: **recommendation accuracy** ≥ 9/10, **unintended writes before
confirmation** = 0, and **cost and regression** — added prompt tokens reported, headless-skill
selection rate not dropping. Metric 2 is checked three ways: a file-hash snapshot, a scan of every
tool call, and a stub `xsolla` on `PATH` that refuses and logs any invocation.

## Rules for a valid run

- **Preserve failed runs.** Results files are append-only history; the runner refuses to overwrite
  one. Never re-run a case to replace a bad result with a better one.
- **A scorer bug is fixed in the scorer**, with a case added to `test_run_evals.py` — not by
  re-running the agent until it agrees.
- **Infrastructure failures are not evidence.** A rate limit, API error or timeout is recorded as
  `error_kind: "infrastructure"`; it never counts as a pass or as a skill failure.
- **Running out of turns is not a crash.** A turn that stops at `--max-turns` is scored on what the
  agent did, and flagged `hit_turn_limit`. A wrong outcome still fails the checks.
- **Two rounds minimum.** Inconsistency between rounds is itself a finding.

## Known limitations

- **Not isolated from the machine's own Claude setup** — runs inherit your global `CLAUDE.md`,
  installed plugin skills and settings. Compare runs from one machine, not across machines.
- **Prompt-size numbers drift between runs.** Probes interleaved within one run agree closely;
  separate runs have differed by thousands of tokens. Read the median and range, not one number.
- **The write scan is a heuristic** on top of the authoritative file-hash diff; it exists to catch
  writes *outside* the run directory.
- **Sessions leave transcripts** under your Claude config directory, one per throwaway project.
  Delete them after a batch.
- **Not run in CI** — it needs an interactive Claude login and real usage. Run it before a PR that
  touches `shop-plan`, `shop-setup` or the `shopbuilder-*` skills, and commit the results file.

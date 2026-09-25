# End-to-end evaluation log

Record one JSON object per line. Do not store credentials, partner production IDs, or
customer data. A run represents assembly from a blank approved sandbox or dedicated
Publisher Account test project; never use a partner project.

```json
{"run_id":"run-01","preset":"mobile-single-page","result":"success","manual_interventions":1,"failure":null,"notes":"Preview matched plan"}
```

Required fields:

- `run_id`: unique stable identifier.
- `preset`: one of the three documented preset names.
- `result`: `success` only when structure, localization, catalog links, readiness, and
  preview all match the confirmed plan; otherwise `failure`.
- `manual_interventions`: count of user or engineer actions needed after confirmation.
- `failure`: concise failure cause for failed runs; `null` is allowed for success.

Store the completed log at repository root as
`evals/shop-builder-assembly/runs.jsonl`, then run:

```bash
python3 skills/shop-builder-assembly/scripts/summarize_evals.py \
  evals/shop-builder-assembly/runs.jsonl
```

After recording run 001, prepare a balanced local matrix for runs 002–010 with:

```bash
python3 scripts/prepare_eval_briefs.py \
  --base-brief /path/to/approved-test-brief.json \
  --output-dir /path/to/local-eval-briefs
```

The generator creates three briefs for each preset with unique slugs. It carries only
the already approved test-project identity and catalog mappings from the base brief,
adds clearly labeled synthetic evaluation content, and performs no remote operations.
Every generated plan still requires its own backup and exact confirmation ID before
writes.

The command passes only with at least 10 valid runs, at least 80% successes, and no
run exceeding two manual interventions. Preserve failed runs; do not rerun and replace
them merely to improve the result.

## SB-8796 result

The committed matrix contains 10 runs: nine successes and the preserved initial
failure. The success rate is 90%, all three presets are represented three times, and
the maximum manual-intervention count is two. Each success has an exact post-apply
structure export and a fresh authenticated Publisher Account preview; every site
remained unpublished. Run the command above to reproduce the metric result.

# shop-validation

The Site Builder MCP's shop validations, ported to scripts that run from Claude Code or from
`xsolla-cli`, so a shop gets the same checks whichever path built it.

- [`SKILL.md`](SKILL.md) — the `validate-shop` gate, where it sits in a write flow, safety rules
- [`INVENTORY.md`](INVENTORY.md) — every MCP behaviour, the callable that carries it, and status
- [`EVAL-LOG.md`](EVAL-LOG.md) — the recorded runs behind the metrics
- `scripts/` — the validators, their tests, and the 23 modules' field schemas

## Prerequisites

| | |
|---|---|
| **Python** | 3.9 or newer. Standard library only — no `pip install`, no `package.json`, no build step. Verify with `python3 -V`. |
| **Xsolla CLI** | On `PATH`, for fetching a shop's structure and localization. `xsolla --version`. |
| **Auth** | `xsolla auth login`. Copying a Publisher Account `pa-v4-token` by hand is a documented gap, not a step to follow. |
| **Config** | `xsolla config init --sandbox`, then `xsolla config set project_id <id>`. Both merchant id and project id must be set or the Shop Builder commands fail with `missing --project-id`. |
| **Project** | A **sandbox or test** Shop Builder project. Never a partner's live project. |

Nothing in `scripts/` calls the network or writes anything. Every input is a file you fetched;
the one exception is `live_check.sh`, which says so in its header and asks for `--yes`.

## Happy path

Validate an existing shop, end to end:

```bash
cd skills/shop-validation/scripts
SLUG=<your landing slug>            # xsolla shopbuilder list-websites --json

# 1 · fetch what the walk needs (read-only)
xsolla shopbuilder get-structure    --slug $SLUG --json > /tmp/s.json
xsolla shopbuilder get-localization --slug $SLUG --json > /tmp/l.json
python3 -c 'import json;json.dump(json.load(open("/tmp/s.json"))["data"],open("/tmp/structure.json","w"))'
python3 -c 'import json;json.dump(json.load(open("/tmp/l.json"))["data"],open("/tmp/localization.json","w"))'

# 2 · walk it
python3 validate_shop.py site --structure /tmp/structure.json --localization /tmp/localization.json
```

On a healthy shop that prints the scope it walked, `Errors: none` for the structural
categories, the `Not checked` list, and `Verdict: clean` — exit `0`:

```
Scope
  site                   my-landing
  pages                  1
  blocks                 15
  off_page_blocks        0
  dangling_ids           0
  localized_ids_checked  127
  families               custom=2, layout=1, native=12
```

Then, before writing a block:

```bash
python3 validate_shop.py block --module faq --payload payload.json --version 2
```

and before creating a custom block:

```bash
python3 validate_shop.py ai-code --component block.jsx --text-fields fields.json
```

Both exit `1` with the errors to fix, or `0` to proceed to the plan-and-confirm step.

## The report, for a machine

`--json` on any subcommand prints one object. These keys are stable; treat anything else as
internal. `xsolla-cli` shells out to these scripts and parses this, so the rules have one home.

| Key | Type | Meaning |
|---|---|---|
| `ok` | bool | No errors. Same thing the exit status says. |
| `verdict` | string | One line for a human — `clean`, or `n error(s) across m block(s)`. |
| `errors` | array | Everything that must be fixed. Empty when `ok`. |
| `unverified` | array of string | What the run could **not** check. Rarely empty on a real shop — print it. |
| `scope` | object | `site` only: what was walked, including `errors_by_category`. |

One payload error:

| Field | Meaning |
|---|---|
| `path` | Dot-joined path into the payload — `values.title.id`, `components.0.answer`, `(root)`. Array indices are plain segments. |
| `expected` | Expected type or shape, in one of five phrasings: a plain type (`string`); the envelope (`object { values?, components? }`); an allowed set (`one of: "sm", "lg"`); a closed object (`no extra keys (got: titel)`); an either/or field (`one of the union variants`). |
| `got` | What was there. A string reports its own content; anything else reports its type. The key is `got`, not `actual`. |
| `value` | The offending value, when short enough to help. Omitted otherwise. |
| `category` | `shape`, `content`, `reference` or `site`. See [SKILL.md](SKILL.md#reading-the-report). |
| `block_id`, `module`, `family` | `site` only — which block, and how it routed. |

`ai-code` and `ai-block` emit `{rule, message, suggestion}` instead: a static-analysis hit has
no path into a payload, and the rule id is what makes it actionable.

Exit status: `0` clean · `1` errors · `2` bad invocation.

## Tests

```bash
cd skills/shop-validation/scripts
python3 -m unittest discover -s tests -t .          # 142 tests, no network
./live_check.sh --yes                               # live: creates and deletes a landing
```

Three groups carry the evidence:

- `tests/test_false_positive_traps.py` — fourteen cases that look like failures and are correct
  passes. Nine of them were observed firing falsely before the rules were corrected.
- `tests/test_seeded_errors.py` — one seeded defect at a time, each exactly one mutation from
  the known-good fixture, each asserted by name.
- `tests/fixtures/known_good_site.json` — a shop exercising every trap at once. It must walk
  clean; any error on it is a bug in the rules, not in the shop.

## Known limitations

- **The gate sits beside the write path, not inside it.** It exits non-zero and has tests
  behind it, so "did it run, and what did it say" is answerable — but an agent that never
  invokes it is still unvalidated. Site Builder's own tooling validates inside the write, where
  it cannot be skipped.
- **Field-level checks are write-time only.** The module schemas are a create-payload contract;
  a stored block never matches one, so the site walk deliberately does not apply them. Auditing
  an existing shop is structural, reference-level and content-level, never field-level.
- **The federated walk compares types only.** Required fields, enums and array item shapes are
  not enforced, and nothing is enforced where a block's defaults are empty. Same as the MCP.
- **Unions beyond the sizing keywords mis-report.** A union of two object shapes is invisible to
  a type-only walk.
- **The nine code rules are textual.** A violation split across lines, generated dynamically, or
  hidden behind a helper passes. A clean run means "no matched pattern", not "correct".
- **The field schemas go stale.** Generated from a point-in-time copy; a new block or a changed
  field is not reflected until they are regenerated, and no owner for that is agreed yet.
  `payment-methods` publishes no field schema at all. An unknown module passes and says so.
- **One shipped schema is stricter than the API.** `quillWrapper` is marked required on a
  localized descriptor; a create without it is accepted and renders. Reported as an advisory.
- **`I:` image ids are collected, never verified.** The landing asset list covers uploads only,
  and federated blocks' images ship with the remote block, so a missing entry is not evidence of
  a broken image.
- **Eight MCP block checks are not here yet, and that is a materials gap, not an MCP gap.** The
  MCP implements and registers all eight; their module files were not in the source extract this
  port was made from. Listed in
  [`INVENTORY.md`](INVENTORY.md#6--implemented-in-the-mcp-source-not-supplied-for-this-port),
  with what to ask for.

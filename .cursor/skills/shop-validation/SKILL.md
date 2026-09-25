---
name: shop-validation
description: >-
  Validates an Xsolla Shop Builder (Site Builder) shop by running the ported Site Builder MCP
  validations as scripts, and adds the `validate-shop` gate that has to pass before any block
  write is confirmed. Use when asked to validate a shop, validate a site, check blocks,
  pre-flight a block payload, validate custom or AI block code, or work out why a block write
  failed — "validate my shop", "check my blocks before I publish", "is this payload the right
  shape", "why did my block return a 500", "why is the settings sidebar crashing", "why is
  nothing on my custom block editable". Runs the same checks whichever path built the shop, so
  a CLI-built shop meets the same bar as an MCP-built one. Covers native block payload shape
  and the 23 modules' field schemas, the federated structural walk, the nine static-analysis
  rules for custom/AI block source, the editor's content assertions (empty links, unset SKUs,
  missing slide media), the per-module checks (subscription plans, reward chains, store groups,
  lead and sidebar storefront links), `L:` reference resolution across a whole site, and the
  write constraints that reject a block just as hard as a bad shape — `version` must equal
  `maxVersion`, layout modules cannot be created, `_id`/`module`/`blockVersion` cannot be
  patched, and batch patch paths are segment arrays. Block-based Site Builder sites only; it
  does not cover the headless storefront that `shop-setup` builds.
metadata:
  owner: n.budhwani
  domain: store
---

## What this is

The Site Builder MCP's validations, ported to scripts you can run from Claude Code — all 75 of
the shop-validation behaviours in the source. The rules live in code, not prose:
[`INVENTORY.md`](INVENTORY.md) maps every behaviour to the callable that carries it, records
the five deliberate divergences, and lists what re-verifying against the complete source
corrected. Each module's docstring says why its checks exist and what they miss. [`README.md`](README.md) has prerequisites, one happy path, and the known limitations.

Python 3.9+, standard library only. No install step, no build, no dependencies.

## Scope

**In scope.** Shop Builder / Site Builder sites **made of blocks** — a landing or webshop whose
pages are a list of block documents. A block is JSON with a strict required shape; the wrong
shape gives you a broken page or a 500, not a helpful error.

**Out of scope.** The headless storefront [`shop-setup`](../shop-setup/SKILL.md) builds
(Login + Store API + Headless Checkout, partner-written frontend). No block documents, so none
of these checks apply.

## The gate — `validate-shop` runs before the confirmation step

This ordering is the whole point. Do not reorder it, and do not skip step 2 because a payload
"looks fine".

1. **Author** the payload, or the custom-block source.
2. **`validate-shop`** — run the checks that apply (below). This is the gate.
3. Anything fails: **fix every error and re-run from step 1.** Never carry an open error
   forward.
4. Only from a clean run: **show the plan** — which blocks change, and how.
5. **Get explicit confirmation** from the user.
6. **Write.** Then re-run the gate against the written state.

The gate sits at 2–3, **before** the confirmation at 5. Asking someone to approve a plan that
has not been validated asks them to approve something neither of you has checked.

## Running it

From `scripts/`. Every command is read-only and takes files you already fetched; `--json` on
any of them prints the machine-readable report described in [`README.md`](README.md).
Exit status is `0` clean, `1` errors, `2` bad invocation.

| About to | Run |
|---|---|
| Validate a whole shop | `python3 validate_shop.py site --structure structure.json --localization localization.json` |
| Create one block | `python3 validate_shop.py block --module <module> --payload payload.json --version <maxVersion>` |
| Update one block | `python3 validate_shop.py block --module <module> --payload patch.json --update` |
| Write custom-block source | `python3 validate_shop.py ai-code --component block.jsx --settings settings.jsx --text-fields fields.json` |
| Check a custom block already on a site | `python3 validate_shop.py ai-block --block ai-block.json` |
| Send a batch change set | `python3 validate_shop.py patch --change-set change-set.json` |

Fetching the inputs with the CLI:

```bash
SLUG=<landing slug>
xsolla shopbuilder get-structure    --slug $SLUG --json > structure_raw.json
xsolla shopbuilder get-localization --slug $SLUG --json > localization_raw.json
python3 -c 'import json,sys;json.dump(json.load(open("structure_raw.json"))["data"],open("structure.json","w"))'
python3 -c 'import json,sys;json.dump(json.load(open("localization_raw.json"))["data"],open("localization.json","w"))'
python3 validate_shop.py site --structure structure.json --localization localization.json
```

Two things about enumeration, because missing either one reports "all clean" on a broken site:

- `pages[].blocks[]` holds full block documents; the **site-level `blocks[]` holds ids only**.
  Every id there that no page carries is an off-page block — fetch each with
  `xsolla shopbuilder get-block --slug $SLUG --block-id <id> --json` and pass them via
  `--off-page-blocks <dir>`. Without them those ids report as dangling.
- A **freshly created landing is empty** — no pages, no blocks. They arrive with the first
  page, as a block template. "This site has no header" means "no page has been added yet".

Pass `--skus` and `--bundles` (JSON arrays from the catalog) to check buy actions; without them
those checks report as unverified rather than guessing.

## Reading the report

Errors are `{path, expected, got, value?}` — the same shape the MCP emits, and the key is
`got`, not `actual`. Site errors also carry `block_id`, `module`, `family` and a **category**:

| Category | Meaning | Blocks a write |
|---|---|---|
| `shape` | Malformed payload — wrong envelope, wrong type against the block's own defaults | Yes |
| `reference` | An `L:` id that does not resolve. Passes a payload check, then 500s the renderer | Yes |
| `site` | Only visible across the whole site — a dangling id, a duplicated layout, an unreachable page | Yes |
| `content` | An editor content assertion — an enabled social link with no url, a buy button with no SKU | No, but the block is not publish-ready |

**Read `content` carefully.** The block template that arrives with a landing's first page ships
with placeholder buttons and empty social links, so a brand-new shop scores zero
`shape`/`reference`/`site` errors and about ten `content` ones. That is the template being
unconfigured, not a defect. Report it as such rather than as ten faults.

Always print the report's `unverified` list. A gate that hides its own blind spots is worse
than no gate.

## Safety rules

Every write this gate stands in front of, without exception.

1. **Back up first.** Read the current structure and localization and keep both responses,
   before the first write — not before the first fix.
2. **Show the plan and get explicit confirmation before any write.** No silent writes, no
   batching a write into a "read" step.
3. **Use these scripts and the CLI's commands for anything repeated**, rather than ad-hoc API
   calls.
4. **Never publish.** A human publishes, in Publisher Account. A clean validation run is not
   permission to make a shop live.

Target a **sandbox or test project only** — never a partner's live project.

## Authorization, and a known gap

Authenticate with `xsolla auth login`; the Shop Builder commands above work with that session.
Copying a Publisher Account `pa-v4-token` by hand (`XSOLLA_SHOPBUILDER_SESSION`) is a
**documented gap** — if a command demands it, record that and stop. Do not build a workaround.

`XSOLLA_MERCHANT_ID` and `XSOLLA_PROJECT_ID` are the same values the rest of this kit uses, set
up by [`merchant-setup`](../merchant-setup/SKILL.md). Shop Builder authorizes separately from
the Store `XSOLLA_PROJECT_API_KEY`.

## Known CLI gaps — do not route around them

Confirmed against the installed CLI. Each is filed rather than patched from here.

- **No payload validation on any write path.** `add-block` takes a template name and no values;
  `update-block` passes free-form JSON straight to the batch API. Verified: a block whose
  `values` is a JSON *string* is accepted. These scripts are the only check in front of that.
- **The batch API answers `ok: true` to writes it does not perform.** Three known cases, and
  they are the reason this gate has to run *before* the request rather than reading the
  response: a patch to a path that does not exist, a patch whose path addresses `_id`,
  `module` or `blockVersion` (probed live 2026-09-16 — `ok: true`, block unchanged), and
  `update-many-localization` given a bare string instead of `{"translation": "<html>"}`,
  which returns `200` and writes an **empty string**. An author is told the write succeeded
  in all three.
- **`verify-website` is broken** — every call is rejected with `draftPagesIds must be an array`
  and there is no flag to supply one. It looks like the publish-readiness check you want; it is
  not available. This gate is the only pre-publish check there is.
- **`create-custom-block` cannot declare `textFields`.** So a block whose source calls
  `localizedText()` or renders `<TextEditor>` comes back with `textRefs: {}` and nothing on it
  is editable. On that path the fault cannot be fixed, only avoided — author the block without
  canvas-editable text, or create it through tooling that accepts `textFields`.
- **No `get-block-schema` command.** The 23 modules' schemas ship here instead, in
  `scripts/data/block-schemas.json`.

## Evidence

`evals/shop-validation/EVAL-LOG.md`, in the toolkit repo, records the runs behind the
metrics: known-good shops walked,
seeded-error shops caught, false positives, and runtime. `scripts/live_check.sh --yes`
reproduces the live half of it against a throwaway landing it creates and deletes.

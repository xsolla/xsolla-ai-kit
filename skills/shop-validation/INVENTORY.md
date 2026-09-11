# Inventory — MCP validation behaviours, and where each one lives here

Every validation behaviour in the Site Builder source, one row each, with the callable that
carries it in this kit. Written so a reviewer can check the "ported 100%" claim by reading the
Status column rather than taking it on trust.

Re-verified 11 Sep 2026 against the **complete** Site Builder source. The first pass worked
from a partial extract; the full tree confirmed every module it contained was current, supplied
the eight that were missing, and corrected three things this port had got wrong — see
[What the full source changed](#what-the-full-source-changed).

**Status key.** `ported` — same inputs, same outputs, covered by a test · `diverged` — ported,
with a behaviour change stated in the row · `n/a` — deliberately out of scope, with the reason
in the row.

**Totals.** 78 behaviours identified · **75 ported** — 65 straight, 5 diverging (each stated in
its own row) and 5 that this kit adds and Site Builder does not have · **3 not ported**, all
`n/a`: MCP transport and tool-argument concerns with no equivalent surface here. Every
shop-validation behaviour in the source is now ported — **75 of 75**.

Every callable below is `python3 scripts/validate_shop.py …` or a function in
`scripts/xsolla_shop_validation/`. Run `python3 -m unittest discover -s tests -t .` from
`scripts/` to execute the tests that cover them.

---

## 1 · Native block payload validation

| # | MCP behaviour | Here | Status |
|---|---|---|---|
| 1 | `validateNative` — payload must be a non-null, non-array object | `native.validate_envelope` | ported |
| 2 | `validateNative` — `values` validated only when present | `native.validate_native` | ported |
| 3 | `validateNative` — `components` validated only when present | `native.validate_native` | ported |
| 4 | `validateNative` — errors re-rooted under their section (`values.x`, `components.0.x`) | `errors.prefix_errors` | ported |
| 5 | `validateNative` — a module with no schema returns ok | `native.validate_native` | ported |
| 6 | `validateNative` — `partial` relaxes required keys, for an update | `schema_subset.validate(partial=True)` | ported |
| 7 | `BLOCK_ZOD_SCHEMAS` — 23 modules' field schemas: closed objects, required keys, enums, exact wrappers | `scripts/data/block-schemas.json` + `schema_subset.validate` | ported |
| 8 | `components` must be an array — the MCP leaves this to the schema | `native.validate_envelope` | ➕ |
| 9 | `values` must be an object — same | `native.validate_envelope` | ➕ |

## 2 · Error formatting

| # | MCP behaviour | Here | Status |
|---|---|---|---|
| 10 | `zodToErrors` — one error per bad path, `{path, expected, got, value?}` | `errors.finding` | ported |
| 11 | expected for a type mismatch — the plain type name | `schema_subset` | ported |
| 12 | expected for a bad value — `one of: "sm", "lg"` | `schema_subset` | ported |
| 13 | expected for extra keys — `no extra keys (got: titel)` | `schema_subset` | ported |
| 14 | expected for a union — `one of the union variants` | `schema_subset` | ported |
| 15 | got — a string reports its own content, anything else its type | `errors.describe_got` | ported |
| 16 | dot-joined paths, `(root)` when the path is empty | `errors.format_path` | ported |
| 17 | `formatValidationResponse` — the MCP tool-result envelope | — | n/a · MCP transport, meaningless outside an MCP server |
| 18 | `formatToolInputError` — same, for tool arguments | — | n/a · as above |

## 3 · Federated structural walk

| # | MCP behaviour | Here | Status |
|---|---|---|---|
| 19 | `validateFederated` — walk user values and shipped defaults in parallel, comparing types | `federated.validate_federated` | ported |
| 20 | defaults absent or null at a path — skip that subtree | `federated._walk` | ported |
| 21 | image-id override: a default matching `^I:[a-z0-9]+$` accepts any user string | `federated.IMAGE_ID` | ported |
| 22 | localized-id override: `^L:[a-z0-9-]+$`, case-insensitive | `federated.LOCALIZED_ID` | ported |
| 23 | arrays — item 0 is the reference shape, the user array may be any length | `federated._walk` | ported |
| 24 | objects — recurse every key the user object has | `federated._walk` | ported |
| 25 | one error per bad path; stop descending there | `federated._walk` | ported |
| 26 | `internalBlockValues` absent entirely — pass | `federated.validate_federated` | ported |
| 27 | a sizing keyword and a pixel number are the same field | `federated.SIZING_KEYWORDS` | ➕ |
| 28 | federated `L:` ids resolve through the block's own `resources.localizedValues`, not the landing store | `federated.resolve_federated_localized_id` | ➕ |

## 4 · Custom (AI) block source rules

| # | MCP behaviour | Here | Status |
|---|---|---|---|
| 29 | `forbidden-import` — an injected global imported from the block-utils package | `ai_block.collect_violations` | ported |
| 30 | `missing-texteditor-import` — `TextEditor` used but never imported | same | ported |
| 31 | `localized-text-prop-shadow` — `localizedText` destructured from props | same | ported |
| 32 | `export-default-class` | same | ported |
| 33 | `undeclared-text-fields` — a `localizedText()` key missing from `textFields` | same | ported |
| 34 | `missing-text-fields` — `<TextEditor>` with nothing declared | same | ported |
| 35 | `use-controls-object-arg` — one control per call | same | ported |
| 36 | `control-factory-object-arg` — first argument is the control name | same | ported |
| 37 | `text-control-with-localized-text` — `text()` does not bind canvas text | same | ported |
| 38 | the eight forbidden globals, as a list | `ai_block.FORBIDDEN_GLOBALS` | ported |
| 39 | scan scope — rules 1 and 4 read component + settings joined, the rest component only | `ai_block.collect_violations` | ported |
| 40 | violation shape `{rule, message, suggestion}` | `errors.violation` | ported |
| 41 | `textRefs` must be non-empty when the source registers canvas text | `ai_block.check_text_refs` | ➕ |

## 5 · Editor content checks — the block walker

| # | MCP behaviour | Here | Status |
|---|---|---|---|
| 42 | `validateBlockComponents` — walk `components`, recursing into nested components, with indexed paths | `component_checks.validate_block_components` | ported |
| 43 | legacy custom button, `buy` — key SKU exists, subscription id set, bundle exists | `component_checks._validate_legacy_custom_button` | ported |
| 44 | legacy custom button, `link` and `preset` — a link is required | same | ported |
| 45 | embed components need their link — Discord, Facebook, Twitch, Twitter | `component_checks._validate_component_with_link` | ported |
| 46 | subscribe component needs a value | `component_checks._validate_subscribe` | ported |
| 47 | store section — items type required, group required except for keys and bundles, error group rejected | `component_checks._validate_store_section` | ported |
| 48 | footer social — an enabled item with an empty url | `component_checks.validate_footer_v2` | diverged · gated on the module, not on `blockVersion == 2`: an empty url is dead at every footer version |
| 49 | gallery slides — the media its own type declares must be present | `component_checks.validate_gallery_v2` | ported |
| 50 | action `buy` — SKU set and in the catalog | `component_checks.validate_action` | ported |
| 51 | action `scroll` — target id set | same | ported |
| 52 | action `lightbox` — url set and playable | same | ported |
| 53 | action `link` — url set and well-formed | same | ported |
| 54 | action `page` — landing id set, page id present and on this site, cross-site links skipped | same | ported |
| 55 | action `cloud-gaming` — game id set | same | ported |
| 56 | action `subscription` — subscription id set | same | ported |
| 57 | a localized reference's id must exist in the landing's localization set | `site_walk.check_localized_ids` | ported |
| 58 | scan a structure for every localized reference id | `component_checks.scan_localized_reference_ids` | ported |
| 59 | url and identifier rules — lightbox providers, relative urls, YouTube, Vimeo, Steam, Epic, video files, site name, page path | `url_rules` | ported · follows the current parser-based implementation, not the regex one it replaced: whitespace, protocol-relative `//host`, backslashes, missing scheme and hosts with no real TLD are all rejected, `.mp4`/`.webm` are the only video extensions, and a page path may contain `:` |
| 60 | the walker visits every action node anywhere in a block, not only under `components` | `component_checks.validate_actions_anywhere` | ported |
| 61 | validation context — site, SKUs, bundles, localization set | `component_checks.ValidationContext` | diverged · a check whose context is missing reports *unverified* instead of throwing "context is not set" |
| 62 | path segments for array indices | `errors.format_path` | diverged · `components.0.value.1` rather than the walker's `components.[0].value.[1]`, so one report reads one way |
| 63 | packs v1 — delegates to the components walk | covered by 42 | ported |

## 6 · Per-module block checks

The module-specific visitors the editor's block walker registers. **All eight were ported on
11 Sep 2026**, once the complete source was available; the first pass worked from an extract
that did not contain them. Each is routed by module key in `site_walk.MODULE_VISITORS` (or, for
the two remote blocks, on the federated branch), and each carries the editor's own message
alongside `expected`/`got` so the platform's wording can be matched by eye.

Where the editor's own test suite pins an edge case — a string id rejected where a number is
required, an empty `chains` list passing, a `unit` store item skipped — the same case is
asserted in `tests/test_module_checks.py`.

| # | MCP behaviour | Here | Status |
|---|---|---|---|
| 64 | subscriptions block — every `plan` component must name a `planId` | `module_checks.validate_subscriptions_block` | ported |
| 65 | daily-reward federated block — `internalBlockValues.dailyRewardId` must be a number | `module_checks.validate_daily_reward` | diverged · returns the field's path and type; the original returns a bare `false`, which the walker renders as "Unknown validation error" at whatever path it had reached |
| 66 | offer-chain federated block — `internalBlockValues.offerChainId` must be a number | `module_checks.validate_offer_chain` | diverged · same reason as row 65 |
| 67 | leadGameSales — enabled `values.platforms` must carry at least one item | `module_checks.validate_lead_game_sales` | ported |
| 68 | newStore — each non-`unit` store section item needs a real catalog group, and not one of the six demo groups a fresh project ships with | `module_checks.validate_new_store_block` | ported |
| 69 | rewards — every entry in `values.chains` must carry a `rewardChainId`; an empty list passes | `module_checks.validate_rewards_block` | ported |
| 70 | lead block v2 — enabled store platforms must each point at their own storefront's host over https, and at least one row must be enabled | `module_checks.check_lead_v2` | ported |
| 71 | sidebar — enabled store buttons must point at their own storefront; enabled social networks need a non-empty link | `module_checks.check_sidebar` | ported |
| 78 | subscriptions — whether auth still needs wiring for this block (a configured Login project or a deeplink flow means it does not) | `module_checks.is_auth_relevant_for_subscriptions` | ported · lives with the checks above but is not registered on the walker |

**Found by porting these:** on a real sandbox shop, `check_lead_v2` named two enabled lead
platform rows whose urls are empty strings, on a block whose `platforms.enable` is `true`. A
second lead block on the same shop has `enable: false` and is correctly left alone.

## 7 · Write constraints — adjacent, and they reject a write just as hard

Not shape checks, and not in the MCP's validation modules, but the MCP's write tools enforce
them and from the user's side a rejected write is a rejected write.

| # | Behaviour | Here | Status |
|---|---|---|---|
| 72 | a create must pass the module's `maxVersion`; a module with no versions list passes none | `write_constraints.check_create_version` + `native.MODULE_MAX_VERSION` | ported · ten modules carry a versions list (`description`, `faq`, `footer`, `gallery`, `header`, `html`, `news`, `packs`, `promocodes`, `requirements`); every other module has none and is exempt. Read from the block metadata, because the schema tool reports `maxVersion` as "last version **or 1**", which makes an unversioned module indistinguishable from a real v1 |
| 73 | layout modules cannot be created or duplicated | `write_constraints.check_not_layout_create` | ported |
| 74 | `_id`, `module`, `blockVersion` cannot be patched | `write_constraints.check_protected_fields` | ported |
| 75 | dotted update keys expand to nested objects before validation | `write_constraints.expand_dotted_keys` | ported |
| 76 | batch patch paths are arrays of segments, not dotted strings | `write_constraints.check_batch_change_set` | ported |

## 8 · Out of scope

| # | Behaviour | Status |
|---|---|---|
| 77 | The per-tool argument schemas (roughly 80 of them) that reject a malformed MCP tool call before its handler runs | n/a · they validate calls into an MCP server, not shops. The CLI parses its own flags and this kit's scripts validate their own inputs, so there is no equivalent surface to port them onto. |

---

## What the ported set still does not cover

Reading this before quoting a clean run matters more than the totals above.

- **The federated walk compares types only.** Required fields, enums and array item shapes are
  not enforced, and nothing is enforced where a block's defaults are empty. That is the MCP's
  own behaviour, and its own acknowledged stopgap pending federated blocks exposing schemas —
  so this is full parity with a partial check, not a partial port.
- **Field schemas are a create-payload contract.** Checking a block read back from a site
  against its own module schema fails every time; the site walk therefore does not apply them.
  Auditing an existing site is structural, reference-level and content-level, never
  field-level.
- **On `quillWrapper`, the MCP and the batch API disagree, and this port sides with the API.**
  The MCP's schema genuinely requires it on a rich-text field (`quillWrapper: z.literal('h2')`
  on a FAQ title, `'p'` on an answer) — the generated schemas are faithful. But a create sent
  straight to the batch API without it is accepted and the text renders, verified live. Since
  these scripts gate the CLI path, it is reported as an advisory rather than an error, so it
  cannot block a write the API accepts. Confined to a one-entry exception list in `native.py`.
- **Unknown keys are rejected here and stripped by the MCP.** Every `values` object in the
  generated schemas is closed, so `questionMod` for `questionMode` is an error. The MCP's zod
  objects are not strict, so the same payload passes there and the misspelled field is silently
  dropped on the way to the API. Stricter on purpose: a silently dropped field is a write that
  appears to succeed and changes nothing.
- **`payment-methods` publishes no field schema**, and the schemas go stale as new blocks ship.
  An unknown module passes and says so.
- **The nine code rules are textual.** A violation split across lines, generated dynamically,
  or behind a helper passes. A clean run means "no matched pattern", not "correct".
- **Unions beyond the sizing keywords mis-report.** A union of two object shapes is invisible
  to a type-only walk.
- **`I:` image ids are collected, never verified.** The landing asset list covers uploads only,
  and federated blocks' images ship with the remote block, so a missing entry is not evidence
  of a broken image.

---

## What the full source changed

The first pass of this port worked from a partial source extract. Re-running it against the
complete tree produced four outcomes worth recording, because two of them were defects in this
port rather than gaps in the platform.

**Confirmed current.** Every module the extract did contain is byte-identical to the full
source, with one exception that is an import-path change only (localization moved to its own
package). So the native envelope, the field schemas, the federated walk, the nine code rules,
the footer, gallery and custom-button checks were all ported from current code.

**Corrected — the url rules were a version behind.** `validations.ts` had been rewritten from
regexes to real url parsing. The ported regex version accepted three classes of url the editor
now rejects: protocol-relative `//host`, anything containing whitespace or a backslash, and
hosts with no real TLD. It also accepted `.ogg`, `.mov` and `.m4v` video files where the
uploader takes only `.mp4` and `.webm`, and rejected the `:` that a page path may now contain.
Fixed, with the rejection cases pinned as tests.

**Corrected — the version rule was a guess.** The first pass could not tell an unversioned
module from a genuine version 1, because the schema tool collapses both to `maxVersion: 1`, so
it exempted six modules observed live and left the rest unjudged. The block metadata answers it
outright: ten modules carry a versions list and everything else is exempt. The heuristic and
the "unjudged" state are both gone.

**Corrected — a test fixture was not actually known-good.** The invented offer-chain block in
`tests/fixtures/known_good_site.json` carried no `offerChainId`, which a real one must have.
Porting row 66 failed six tests until the fixture was fixed. Worth stating plainly: for one
release the "known-good" fixture contained a block the editor would reject.

# Quest Publisher Conversation and Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `quest-setup` use one clear publisher approval, recognize the same project-local credentials as `merchant-setup`, and follow a source-backed Quest API contract without exposing internal workflow details.

**Architecture:** Keep `quest-setup` as the conversational entry point. Put the trusted production/stage gateway map and publisher route/auth contract in a versioned skill reference derived from AdTech source, and keep local credential-selection rules in the auth reference. Treat reward resolution as an explicit upstream capability; this plan does not build its catalog connector.

**Tech Stack:** Markdown skills and references, JSON plugin manifest, Python skill validator, `curl` for unauthenticated contract probes, and fresh AI terminal transcript checks.

**Spec:** `docs/superpowers/specs/2026-09-30-quest-publisher-experience-design.md` (sections 1–6 and 9)

## Global Constraints

- `quest-setup` remains the single conversational entry point.
- The project-local credential keys are `XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID`, and `XSOLLA_PROJECT_API_KEY`.
- A complete process-environment set may override a complete project `.env` set. Partial sources are not combined.
- `XSOLLA_QP_ENV=production|stage` is a separate, non-secret Quest service selection in the same project configuration; absence means `production`, and `stage` must be explicit for a controlled stage run.
- Never source `.env`, print values or headers, copy credentials into the plugin package, or send a key to a guessed host.
- Publisher quest routes use HTTP Basic with the configured merchant ID and project API key. `X-REQUEST-APIKEY` is a separate internal service lane and is never a publisher fallback.
- Production Quest API code deliberately disables `/openapi.json`; use the versioned source-backed contract for production and read-only preflight/read-back to verify actual behavior.
- One approval of the exact proposal authorizes create, configure, activate, and read-back. Test events and shop source edits require separate consent.
- Do not hardcode a particular reward name or silently substitute another reward type.
- Drafts and inactive quests are not presented as a separate user-facing draft workflow and are excluded from the active public quest list.
- Do not claim Backpack delivery without the applicable wallet/Backpack evidence.
- Do not commit or push files unless the user explicitly requests it.
- This plan is the implementation outline required by the repository's `AGENTS.md`. Review and approve this plan before implementation begins; the spec approval alone does not approve these implementation steps. After this plan is approved, do not ask again between its tasks. After implementation, request an independent subagent review and address its findings.

## Review Focus

1. A complete process environment must win as a unit over a complete `.env`; partial sources must not be merged. Test complete, partial, and absent-source cases with dummy values and assert that no value is printed.
2. An absent environment selector means production; only explicit `stage` selects stage. Test unset, both accepted values, and an invalid value. Invalid values stop before network calls.
3. A stage OpenAPI response and a production OpenAPI route miss have different meanings. Test that `200` stage schema is read as contract evidence and production `404` is reported as the documented OpenAPI restriction, never as missing credentials.
4. A project `401`, project `404`, router-miss `404`, and upstream/transport error are different blockers. Test that each message names the next useful action without claiming a connection failure when one was not verified.
5. One approval must bind to the exact proposal, while an uncertain POST/PUT must be reconciled before retry. Test unchanged proposal, changed-after-approval proposal, create/read/activate/read, and ambiguous-write/no-duplicate behavior.

---

## File Map

| File | Responsibility in this plan |
| --- | --- |
| `skills/quest-setup/SKILL.md` | Generic conversation, read-only bring-up, one proposal/approval, ordered publication and user-facing blocker copy. |
| `skills/quest-setup/references/auth-and-environment.md` | Whole-source credential selection, selector semantics, safe local configuration instructions, and concise failure handling. |
| `skills/quest-setup/references/qp-api-contract.md` | New versioned trusted gateway map and Quest publisher route/auth/response contract derived from checked-in AdTech source. |
| `skills/quest-setup/references/quest-document.md` | Point route and request-shape guidance at the versioned contract; retain quest graph and activation schema details. |
| `skills/quest-setup/references/rewards.md` | Remove product-name examples and align reward-impact confirmation with approval of the full proposal. No catalog API implementation in this plan. |
| `skills/merchant-setup/SKILL.md` | Safe presence-only `.env` inspection, intended-key updates that preserve unrelated settings, and short missing-credential instructions. |
| `skills/shop-setup/SKILL.md` | Reference the shared project-local configuration when the shop orchestrator gathers or records merchant/project settings. Do not change shop setup workflow behavior. |
| `AGENTS.md` | Keep the repository environment-variable guidance consistent with the shared keys and optional non-secret selector. |
| `.cursor/skills/quest-setup/**`, `.cursor/skills/merchant-setup/**`, `.cursor/skills/shop-setup/**`, `CLAUDE.md` | Generated mirrors of canonical skills and `AGENTS.md`; synchronize after canonical edits. |
| `docs/superpowers/test-plans/2026-09-30-quest-conversation-config.md` | New exact-prompt and expected-transcript matrix for configuration, approval order, and truthful blockers. |
| `.codex-plugin/plugin.json`, `mcp-servers.json` | Inspect for packaging. The manifest already includes the whole `skills/` directory and a docs-only MCP config; do not add a nonexistent reward resolver here. |

## Task 1: Pin the Quest API Contract and Verify Public Gateway Responses

**Files:**

- Create: `skills/quest-setup/references/qp-api-contract.md`
- Modify: `skills/quest-setup/references/auth-and-environment.md`
- Modify: `skills/quest-setup/references/quest-document.md`
- Test: unauthenticated public gateway probes; repository skill validator

**Interfaces:**

- Consumes: QP source and Postman environments in `/Users/raufaliyev/GolandProjects/adtech-QP-2934/qp-server/`.
- Produces: a versioned reference for the verified public base URLs, publisher Basic format, project read, quest list/create/read/update route shapes, and the production OpenAPI limitation.

- [ ] **Step 1: Record the read-only probe baseline before changing skill routes.**

  Run without Authorization headers and without query parameters containing credentials:

  ```bash
  curl --connect-timeout 8 --max-time 15 -sS -o /dev/null -w 'stage_openapi status=%{http_code} effective_url=%{url_effective}\n' https://quests-stage.xsolla.com/openapi.json
  curl --connect-timeout 8 --max-time 15 -sS -o /dev/null -w 'production_openapi status=%{http_code} effective_url=%{url_effective}\n' https://quests-platform.xsolla.com/openapi.json
  ```

  Expected from the planning run on 2026-09-30: stage returns `200`; production returns `404`, matching the production source's explicit OpenAPI block. Re-run before implementation because reachability can change. Do not add `-v`, print response headers, probe guessed hosts, or use a project key in this step. A timeout/connection error is recorded as transport unavailability, not as an auth or project result.

- [ ] **Step 2: Verify source before writing the route table.**

  Read `qp-server/postman/environment-prod.json` and `environment-stage.json` for the gateways. Read `qp-server/internal/http/handler/xsolla_scoped.go` for the `/api/v2/merchants/{merchant_id}/projects/{project_id}` project and quest routes, `qp-server/internal/http/middleware/publisher_key.go` for `base64(merchant_id:api_key)`, and `qp-server/internal/http/router.go` for production OpenAPI disabling. Record the inspected repository revision in the new reference. Do not use issue/MR descriptions as route evidence.

- [ ] **Step 3: Write the reference using only source-backed routes.**

  Include the production and stage public bases from the Postman environment files and these route templates from `xsolla_scoped.go`: project `GET`, quest list `GET`, quest create `POST`, single quest `GET`, and full-document quest `PUT`. State that create is initially `inactive` and activation is the later full-document `PUT`. State that Basic credentials encode merchant ID as username and the selected project API key as password; project ID remains route scope. Do not list internal `X-REQUEST-APIKEY` routes as a publisher alternative. Mark production `/openapi.json` as intentionally unavailable. Explain that a project `401`, project `404`, router-miss `404`, and transport failure do not prove the same condition.

- [ ] **Step 4: Link the versioned contract from auth and quest-document references.**

  Replace requirements to fetch production OpenAPI for Quest Platform route discovery with: use the versioned route contract, then perform a read-only request against the selected public gateway. Keep live OpenAPI discovery for stage when the task benefits from it. Keep node schema rules in their existing references; this contract is not a substitute for node-specific validation.

- [ ] **Step 5: Synchronize the changed quest skill references.**

  Copy the changed canonical `skills/quest-setup/` reference files to the matching `.cursor/skills/quest-setup/` paths. Do not modify the generated copies independently.

- [ ] **Step 6: Validate references and links.**

  Run `python3 .github/scripts/validate_skills.py`.

  Expected: no new frontmatter, broken-link, JSON, registry, mirror, or tracked-secret errors. This does not prove production API behavior; it only validates the repository artifact.

## Task 2: Unify Local Credential Guidance Without Exposing Values

**Files:**

- Modify: `skills/merchant-setup/SKILL.md`
- Modify: `skills/shop-setup/SKILL.md`
- Modify: `AGENTS.md`
- Modify: `skills/quest-setup/references/auth-and-environment.md`
- Test: dummy `.env` fixtures kept outside the repository; fresh local agent transcript

**Interfaces:**

- Consumes: shared credential and precedence rules in the approved spec, and Task 1's explicit QP Basic-auth contract.
- Produces: one consistent set of documented keys and a safe user instruction for missing or partial settings.

- [ ] **Step 1: Replace value-printing inspection instructions.**

  Remove `cat .env | grep ...` and sample output containing realistic credential values from `merchant-setup`. Specify presence checks for only the expected variable names, with values and encoded headers suppressed. State that `.env` is parsed as text; never run `source`, `eval`, or shell interpolation on it. Keep the user-facing message limited to each required key's set/missing state.

- [ ] **Step 2: Replace the broad delete-and-rewrite recipe.**

  Remove the `/^XSOLLA_/d` command. Specify updating only `XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID`, and `XSOLLA_PROJECT_API_KEY`, retaining all other lines including `XSOLLA_QP_ENV`. A new file should be ignored by Git before values are saved. The instruction for a missing key names the local `.env` location and required key names, and tells the user not to paste the project API key into chat.

- [ ] **Step 3: Document all-or-nothing source selection and selector semantics.**

  In `auth-and-environment.md`, document that a complete process-environment triple wins over a complete project `.env` triple. If process environment is partial, use a complete `.env` triple if present; never combine values from both. If neither source is complete, stop with a short actionable message. `XSOLLA_QP_ENV` defaults to `production`; only `production` and explicit `stage` are accepted. A present invalid/empty selector stops before network calls. The selector is not a credential and is preserved by merchant setup.

- [ ] **Step 4: Keep project guidance and QP-specific auth consistent.**

  Update `AGENTS.md`'s environment example to include the generic triple and describe the optional selector without a sample secret. Retain merchant-setup's general API-auth notes where they apply, but say that the Quest Platform publisher route uses the QP-specific merchant-ID Basic username documented in `qp-api-contract.md`. Do not generalize the QP username format to Catalog, Store, or unrelated APIs. Add a short pointer in `shop-setup/SKILL.md` to reuse the same project-local merchant/project settings when its orchestrated steps need them. Do not copy secrets into generated storefront code or change the shop flow.

- [ ] **Step 5: Exercise the rules with disposable dummy files.**

  Create fixtures under a temporary directory, not the project root: one complete `.env` and complete process env, one partial process env plus complete `.env`, one partial `.env`, and one invalid selector. Run the proposed presence-check instructions against each. Expected: the whole complete process set wins, a partial source is ignored as a unit, no values or Basic header are printed, invalid selector causes no request, and unrelated dummy settings survive a targeted update. Delete the temporary fixtures after the checks; never read or modify the publisher's real `.env` during this plan's local test.

- [ ] **Step 6: Synchronize credential guidance and repository indexes.**

  Copy canonical `skills/merchant-setup/SKILL.md`, `skills/shop-setup/SKILL.md`, and the updated Quest auth reference into their matching `.cursor/skills/` paths, then copy `AGENTS.md` to `CLAUDE.md`.

- [ ] **Step 7: Run repository validation.**

  Run `python3 .github/scripts/validate_skills.py` and `git diff --check`.

  Expected: no new validator errors and no whitespace errors.

## Task 3: Make Quest Creation One Business Approval

**Files:**

- Modify: `skills/quest-setup/SKILL.md`
- Modify: `skills/quest-setup/references/rewards.md`
- Modify: `skills/quest-setup/references/quest-document.md`
- Create: `docs/superpowers/test-plans/2026-09-30-quest-conversation-config.md`
- Test: fresh AI-terminal transcripts

**Interfaces:**

- Consumes: Task 1's source-backed route contract and Task 2's resolved project configuration rules.
- Produces: a generic publisher-facing proposal and a one-approval create/read/activate/read sequence. Reward candidate resolution remains an interface supplied by a later catalog-capability task.

- [ ] **Step 1: Remove product-name-specific examples.**

  Replace literal item-name examples in quest skill and reward references with neutral `<requested item>` language. The skill's test prompt must be generic and its expected result must not encode a particular SKU, catalog, or reward name.

- [ ] **Step 2: Put all required read-only work before the proposal.**

  Read the selected project, resolve the reward only through an actually available supported capability, infer the event meaning when unambiguous, construct the complete graph, and determine dates and repeat limits before asking for approval. Do not seek plan approval before GETs. If the named reward cannot be verified because the resolver is absent, zero/ambiguous, or unavailable, stop before any Quest Platform write with a concise actionable blocker; do not guess an SKU or substitute a reward type. This plan creates no connector and must not pretend that one exists.

- [ ] **Step 3: Define one concise, exact proposal.**

  Show publisher project name; what the player does; the selected reward in business terms; quantity/amount; schedule; and repeat limit/payout impact. Omit service names, route/auth details, implementation fields, and narration. Ask only one focused business question when a material value or reward interpretation remains ambiguous.

- [ ] **Step 4: Bind a single approval to the exact proposal.**

  After the publisher approves, create a complete inactive quest, read it back, activate it with the same proposal's approved dates/limits, and read back active status, scope, reward, dates, limits, and version. Do not ask a second approval for the internal activation PUT. If an answer changes a material proposal value after approval, show the revised proposal and request approval again. Keep event submission separate and require a separate approval.

- [ ] **Step 5: Reconcile partial or ambiguous writes before retry.**

  After uncertain create or update outcomes, perform the bounded read-back from the route contract and inspect the saved quest before any retry. Continue or repair the same quest when safe; never report publication complete until the active quest and approved configuration read back. Do not create a duplicate on timeout.

- [ ] **Step 6: Add exact fresh-agent cases to the test plan.**

  Add prompts and transcript checks for: an arbitrary named reward with a unique resolver result; two plausible results; unavailable resolver; missing project settings; invalid project selector; project 401; router-miss 404; API transport failure; a request with inferred event meaning; and an event whose meaning remains ambiguous. For the unique-result case, require the transcript order `GET checks -> concise proposal -> one approval -> POST inactive -> GET -> PUT active -> GET active`, without an event POST. For unavailable/zero/ambiguous reward cases, require zero quest writes and a precise next step. Use different generic names across test runs.

  Use these exact generic reward prompts as separate cases:

  ```text
  Create a quest that grants the Azure Lantern after the player clears the Crystal Cavern.
  Create a quest that grants an Ember Guard when the player wins a ranked match.
  Create a quest that rewards a named item after the player defeats a world boss.
  ```

  The first prompt is eligible for the one-approval case only when the installed resolver returns one verified candidate. The second should ask the publisher to choose if the resolver returns multiple plausible candidates. The third should stop before a quest write when the resolver is absent or returns no verified candidate. None of these prompts authorizes an event submission.

  For every case, assert that the agent does not use public web search for catalog lookup, does not narrate production connections or internal API steps, and gives a short local setup instruction when credentials are missing.

  These names are test fixture data only. Never add a named item to `SKILL.md` examples, defaults, or behavior.

- [ ] **Step 7: Synchronize the conversation and reward guidance.**

  Copy changed quest skill references to the matching `.cursor/skills/quest-setup/` paths. Do not hand-edit mirrors.

- [ ] **Step 8: Run documentation validation.**

  Run `python3 .github/scripts/validate_skills.py` and `git diff --check`.

  Expected: links and frontmatter pass, canonical and mirrored files remain byte-identical, and no fixed product-name-specific behavior remains in the canonical quest workflow.

## Task 4: Synchronize Provider Mirrors and Check the Source Package Manifest

**Files:**

- Generate: `.cursor/skills/quest-setup/**`
- Generate: `.cursor/skills/merchant-setup/**`
- Generate: `CLAUDE.md`
- Inspect: `.codex-plugin/plugin.json`, `mcp-servers.json`
- Test: repository validator, mirror equality, plugin package preflight

**Interfaces:**

- Consumes: completed canonical docs from Tasks 1–3.
- Produces: canonical/Cursor/Claude content parity and an explicit statement of whether the source plugin manifest can include this plan's changes.

- [ ] **Step 1: Regenerate provider copies from canonical sources.**

  Run the provider sync steps in `.github/workflows/sync-providers.yml`: replace `.cursor/skills/` from each canonical `skills/<name>/` tree and copy `AGENTS.md` to `CLAUDE.md`. Do not hand-edit generated files. This is a final full-tree parity check after task-local syncs.

- [ ] **Step 2: Verify the manifest inclusion path.**

  Check `.codex-plugin/plugin.json`. It currently points `skills` at `./skills/` and `mcpServers` at `./mcp-servers.json`; the existing MCP manifest is documentation-only. Keep those declarations for this phase. Do not add a fake resolver or package local `.env`/secrets. Record that the current cached plugin `1.0.0` does not contain `quest-setup`; source parity is not installed-package proof.

- [ ] **Step 3: Validate canonical and generated content.**

  Run `python3 .github/scripts/validate_skills.py`; it must report zero new errors. Inspect `git diff --check`. The validator is the authoritative local check for mirror file-set/byte parity, registries, frontmatter, links, JSON, and tracked-secret patterns.

- [ ] **Step 4: Exercise the source-loaded skill, then package status separately.**

  In a fresh local AI-terminal context, use the exact generic prompts in the new test plan. Confirm the transcript passes its required order and never outputs configuration values. Then inspect the actual distributable plugin artifact if one is available; record manifest version/digest and verify it includes `quest-setup`, `merchant-setup`, all quest references, and no `.env`. If no updated artifact exists, mark package verification blocked by distribution, not passed by source inspection.

## Task 5: Independent Test and Review Handoff

**Files:**

- Test: `docs/superpowers/test-plans/2026-09-30-quest-conversation-config.md`
- Review: every file changed in Tasks 1–4

**Interfaces:**

- Consumes: source implementation and generated mirrors from Tasks 1–4.
- Produces: reviewed transcript evidence and a bounded list of remaining dependencies.

- [ ] **Step 1: Run all prompt cases from a fresh agent context.**

  Do not preload this design or tell the agent what the expected answer is. Capture prompt and result only; scrub all credential values and auth headers from any retained transcript. Check the test-plan assertions rather than the agent's statement that it followed the skill.

- [ ] **Step 2: Confirm the approval boundary when a real resolver is available.**

  If a real read-only reward resolver is available and the project owner has approved the stage fixture and quest writes, use a harmless controlled stage case that stops before any reward event. Verify one approval authorizes only the exact approved quest publication, no event is submitted, and any changed proposal requires reapproval. If the resolver or stage-write authorization is unavailable, run only the no-write cases and leave the one-approval publication E2E pending; the missing capability is not a test pass.

- [ ] **Step 3: Ask an independent subagent to review the patch and transcripts.**

  Have the reviewer inspect source, mirror diff, API-auth semantics, blocker copy, duplicate-write behavior, and secret-safety cases. Fix every substantiated issue and repeat the relevant task-level check.

- [ ] **Step 4: Report acceptance by scope.**

  Mark conversation/config/source-contract work complete only if Task 5's tests pass. Report catalog resolution, active worker project propagation, public-shop rendering, packaged plugin release, and any live publish/E2E as separate dependencies or later phases; this plan does not establish them.

## Limitations and Reward-Resolver Interface

This plan does not implement or imply a catalog connector, minting-service access, Web Shop edits, event submission, delivery verification, worker deployment, or plugin release. The conversation can publish only when the requested reward is already resolved through a real supported capability. A named Web3 reward must remain blocked before quest POST until a trusted resolver supplies a unique candidate with display name, reward type, exact catalog project, exact SKU, and project-qualified minting verification. The resolver must not receive the user's Quest project key at a private minting host. The approved spec defines its future `resolveRewardItem` responsibility; this phase consumes that result conceptually and does not invent a local MCP tool or payload schema.

The current package manifest includes the skill tree by path, but the installed cached package is stale. Source changes plus mirror validation are not proof that a published or installed plugin contains this work. Production API reachability beyond the unauthenticated source-backed OpenAPI probe is also not established here.

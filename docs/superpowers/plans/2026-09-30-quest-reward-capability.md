# Quest Reward Capability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Blocked and intentionally incomplete until Gate 0 identifies the resolver service owner, repository, endpoint and authentication contract. This document is a source-backed plan for worker compatibility and Toolkit wiring/package validation, not an executable plan for implementing an unidentified service.

**Goal:** Package a managed read-only reward catalog resolver in the Toolkit and ensure the selected catalog project reaches the Web3 worker payout request.

**Architecture:** The Toolkit's `quest-setup` skill will call an MCP resolver owned by a service team, which discovers Publisher catalog candidates and validates exact project/SKU pairs using qualified minting reads. The resolver implementation is not in `xsolla-ai-kit`, and the approved spec does not define the service owner or publisher-authentication handoff. That unresolved contract blocks resolver wiring. The worker project-propagation implementation exists in the `QP-2937` experiment checkout and must be verified on the actual release candidate before the Toolkit promises project-scoped delivery.

**Tech Stack:** Codex plugin manifest and MCP server configuration, Markdown skills, Python skill/plugin validators, Go worker tests.

**Spec:** `docs/superpowers/specs/2026-09-30-quest-publisher-experience-design.md`

**Related plans:** Configuration and `.env` alignment are covered by Plan A. Fresh agent, shop and payout E2E is covered by Plan C. This plan does not repeat those tasks.

## Global Constraints

- “Zero matches, multiple plausible matches, or unavailable catalog access stop publication with a specific next step.”
- “Connector-owned service access remains in managed secret storage; the user's Quest project key is not sent to the private minting service, and the connector has no claim or payout operation.”
- “The catalog project is taken from the selected item, not copied from the Quest project.”
- “They do not copy project `.env` into the package.”
- No resolver implementation or plugin wiring starts until the service owner, endpoint, supported MCP transport, publisher auth handoff, tenant/project scope and secret-storage owner are confirmed.
- Use exact deployed worker evidence for the target environment; source code or a historical deployment alone does not prove the current runtime.
- Keep `skills/quest-setup/` canonical and its generated `.cursor/skills/quest-setup/` mirror byte-identical. Do not commit or push unless the user explicitly requests it.

## Review Focus

- **Resolver ownership/authentication is not defined:** stop before adding an MCP endpoint or claim of catalog availability. Gate 0 owns this blocker.
- **Catalog query returns no or multiple plausible items:** no Quest write proceeds until the exact `(catalog project, SKU)` is verified and selected. Task 2 documents fail-closed skill behavior; Plan C exercises the fresh agent flow.
- **Mint catalog or metadata disagrees with the Publisher candidate:** fail before Quest writes and return an actionable issue. Task 2 specifies the required result handling; Plan C covers the full run.
- **Worker drops or changes the selected project:** the selected catalog project must match the SKU lookup, settlement record and outbound claim. Task 1 verifies source/tests and release identity.
- **Installed package is stale or secret-bearing:** the exact released artifact must include the skill and resolver declaration while excluding `.env` and credentials. Task 3 validates the artifact and installed cache.

## File and Repository Map

- `skills/quest-setup/SKILL.md`: resolver invocation, fail-closed behavior and proposal gate.
- `skills/quest-setup/references/rewards.md`: candidate disambiguation, catalog project/SKU proof and no random fallback for named items.
- `skills/quest-setup/references/auth-and-environment.md`: boundary between publisher project configuration and host-managed resolver auth. Project key naming and `.env` authoring stay in Plan A.
- `.codex-plugin/plugin.json` and `mcp-servers.json`: Codex skill discovery and the confirmed non-secret MCP server declaration. Do not add endpoint/auth fields until the host's supported schema is verified.
- `.cursor/skills/quest-setup/**`, `skills/README.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `.claude-plugin/marketplace.json`, `docs/distribution.md`: generated mirror, discovery and distribution metadata where inventory/description changes.
- Worker compatibility source in `/Users/raufaliyev/GolandProjects/adtech-QP-2937/qp-worker-generic-quest/internal/temporal/generic_quest/activity/issue_reward_action.go`, `/Users/raufaliyev/GolandProjects/adtech-QP-2937/qp-worker-generic-quest/internal/web3client/client.go`, and adjacent tests. The earlier `/Users/raufaliyev/GolandProjects/adtech-QP-2934` checkout does not contain the same project-propagation implementation. Verify the selected release branch/image.
- **Resolver implementation files are unknown and intentionally not listed.** The repository and service owner are not established by the approved spec or inspected source. A service-owned implementation plan must be written after Gate 0; generic paths here would not be executable instructions.

## Gate 0: Establish the Resolver Owner and Contract

This is an external dependency decision, not a coding task. It must be resolved before Tasks 2 or 3 can execute.

**Required decision record:** named service repository/team; stable endpoint and supported MCP transport; publisher authentication without raw project-key tool arguments; tenant/project scope enforcement; managed storage owner for Publisher and mint-service credentials; allowlisted catalog and metadata read routes; explicit absence of claim/payout operations; non-production endpoint; production release owner.

- [ ] Have the catalog/Quest service owner and Toolkit maintainer confirm whether Publisher auth is delegated user auth or an approved backend identity that enforces publisher/project scope.
- [ ] Confirm the exact `resolveRewardItem` tool input, bounded result and error schema: natural-language query, optional catalog project, and candidate display name/type/project/SKU/metadata-verification status.
- [ ] Confirm the resolver's upstream Publisher discovery source and project-qualified mint `/skus` and `/metadata/sku/{sku}` reads. Do not add a new public Quest route unless that decision is explicitly made outside this plan.
- [ ] Record the owning repository and reviewed contract location, then create a separate service implementation plan with exact files, tests and commands in that repository.

**Blocked condition:** Until every decision above is recorded, do not change MCP configuration, claim that a named catalog lookup works, or begin service implementation. Only Task 1's source/test review can proceed independently. This plan cannot satisfy the writing-plans skill's no-placeholders rule for full resolver implementation before that missing source contract exists; it explicitly records the blocker rather than fabricating executable service steps.

### Task 1: Verify Web3 Worker Project Compatibility on the Release Candidate

**Files:**
- Review/modify only if the selected release branch lacks the behavior: `/Users/raufaliyev/GolandProjects/adtech-QP-2937/qp-worker-generic-quest/internal/temporal/generic_quest/activity/issue_reward_action.go`.
- Review/modify only if the selected release branch lacks wire support: `/Users/raufaliyev/GolandProjects/adtech-QP-2937/qp-worker-generic-quest/internal/web3client/client.go`.
- Tests: adjacent `activity/action_test.go` and `web3client/client_test.go`.

**Interfaces:**
- Consumes: `web3_item.body.project`, SKU and quantity selected by the publisher flow.
- Produces: project-scoped SKU validation, settlement record containing selected project/SKU, and an outbound claim with the same project. Omitted project keeps legacy behavior only for old quest definitions; the new named-item path must use an explicitly verified project.

- [ ] Select the exact release branch and deployment artifact to validate. Do not treat the `QP-2937` experiment checkout as proof of deployed behavior.
- [ ] Verify `resolveWeb3ItemSKU` passes `body.Project` to `SKULister.ListSKUs`, `claimWeb3ItemReward` passes it to `ProjectClaimer.ClaimInProject`, and the settlement record stores that project with the resolved SKU.
- [ ] Verify the Web3 client serializes the project in the `/claim` payload and keeps `X-API-Key` in worker-owned configuration only.
- [ ] On the selected branch, retain or add focused tests for qualified SKU listing, project reaching the client, outbound payload project, settlement project/SKU, and omitted-project legacy behavior. Do not duplicate the tests already present on that branch.
- [ ] Run `cd /Users/raufaliyev/GolandProjects/adtech-QP-2937/qp-worker-generic-quest && go test ./internal/web3client ./internal/temporal/generic_quest/activity`.
- [ ] Map the exact target stage worker image/revision to the tested commit using its authorized deployment source. If it cannot be mapped, report worker compatibility as blocked.

### Task 2: Wire the Confirmed Read-Only Resolver into quest-setup

**Dependency:** Gate 0 is approved and the service owner has delivered its separate implementation and contract plan. Do not start before then.

**Files:**
- Modify: `skills/quest-setup/SKILL.md`.
- Modify: `skills/quest-setup/references/rewards.md`.
- Modify: `skills/quest-setup/references/auth-and-environment.md`.
- Modify after contract verification: `mcp-servers.json` and `.codex-plugin/plugin.json`.
- Regenerate: `.cursor/skills/quest-setup/**`.

**Interfaces:**
- Consumes the exact MCP tool/schema and auth context recorded by Gate 0. The skill does not construct direct catalog HTTP requests or pass secrets in tool arguments.
- Produces a selected, unambiguous candidate whose verified `(catalog project, SKU)` pair is preserved separately from the Quest Platform project.

- [ ] Add the confirmed resolver tool call to the named-reward flow before any Quest write; map service outcomes without broadening or reinterpreting them.
- [ ] Require one selected candidate with verified project, SKU and metadata before proposal construction. Zero match, ambiguity, unavailable resolver, auth/scope rejection or metadata mismatch stops before writes with a concrete next step.
- [ ] Preserve the selected catalog project in the `web3_item` body. Do not substitute the Quest project or use worker random-SKU fallback for a named reward.
- [ ] Document that resolver auth is host-managed and independent of `XSOLLA_PROJECT_API_KEY`; do not change the shared key names or `.env` behavior assigned to Plan A.
- [ ] Add only the confirmed non-secret endpoint/configuration to `mcp-servers.json` and manifest using the verified Codex MCP schema. Do not package resolver, Publisher or minting credentials.
- [ ] Regenerate the Cursor mirror and update only the plugin/skill inventory and discovery metadata required to expose `quest-setup` and the resolver capability.
- [ ] Exercise the skill-facing contract with the resolver owner's approved test endpoint or fixtures: unique verified candidate may proceed to proposal construction; no-match, ambiguity, unauthorized scope, metadata mismatch and unavailable-service outcomes must stop before any Quest write.
- [ ] Record the exact ordinary-language agent test prompt and one-line result in the PR as required by `CONTRIBUTING-skills.md`; full E2E and payout evidence belong to Plan C.

### Task 3: Validate the Plugin Package and Installed Distribution

**Dependency:** Task 2 is complete, the resolver endpoint is available in the intended environment, and the release artifact has been built through the repository's supported distribution process.

**Files:**
- Inspect: `.codex-plugin/plugin.json`, `mcp-servers.json`, `skills/quest-setup/**`, `.cursor/skills/quest-setup/**`, and the built artifact.
- Modify only package metadata/version and distribution files required by the established release process.

**Interfaces:**
- Consumes: release candidate plugin artifact and separately provisioned host-managed resolver auth.
- Produces: package-validation and install evidence showing the right skill/config loaded without secret material in the artifact.

- [ ] Run `python3 .github/scripts/validate_skills.py` from the Toolkit repository.
- [ ] Run `python3 /Users/raufaliyev/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/quest-setup` from the Toolkit repository.
- [ ] Run `python3 /Users/raufaliyev/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py /Users/raufaliyev/GolandProjects/xsolla-ai-kit` and `git diff --check`.
- [ ] Inspect the built artifact and assert it includes the Codex manifest, confirmed resolver config, canonical quest skill and all references. Assert the artifact contains no `.env`, publisher key, mint service key, or other credential value; do not read secret files during this check.
- [ ] In a clean profile, add the documented remote marketplace with `codex plugin marketplace add xsolla/xsolla-ai-kit`; run `codex plugin marketplace list` and confirm its reported name is `xsolla-ai-kit`. Then run `codex plugin list --marketplace xsolla-ai-kit --available` and install with `codex plugin add xsolla-ai-kit@xsolla-ai-kit`. Verify with `codex plugin list`. The checked CLI documents `codex plugin marketplace upgrade <name>` as refreshing configured Git snapshots and `codex plugin add <plugin>@<marketplace>` as installing a plugin. Do not treat `add` as a verified in-place update operation.
- [ ] After installation, use `codex plugin list` and inspect the installed package snapshot/cache to verify version, source, skill files and MCP declaration. Start a new thread/profile before checking loaded skill/tool availability.
- [ ] For an already installed profile, verify the supported update/reinstall mechanism in the current Codex UI/CLI before using it; if no supported mechanism is available, validate in a clean profile rather than editing cache files or asserting an update succeeded.

## Final Self-Review

- Spec sections 3 and 5 map to Gate 0 and Tasks 1-2. Resolver source implementation is not covered here because its owning repo and auth contract are unknown; a separate service plan is required after Gate 0.
- Spec section 4's key-name and `.env` alignment is owned by Plan A and is deliberately excluded here.
- Spec section 9's package/skill validation is covered by Task 3. The installed package check does not claim a successful catalog lookup or payout.
- Fresh agent flow, Web Shop behavior, separate event consent, delivery correlation and Backpack observation are covered by Plan C and are deliberately excluded here.
- The installed marketplace upgrade/add command syntax was checked against local CLI help. `upgrade` refreshes Git marketplace snapshots; `add` installs. No in-place reinstall semantics are assumed.
- This document remains blocked/incomplete as a full implementation plan until Gate 0 is resolved and the service owner supplies exact source files, interfaces and runnable tests. No generic service file paths or guessed auth configuration are presented as executable steps.

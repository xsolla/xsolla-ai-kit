# Quest skill investigation

Investigation date: 2026-09-21

Scope: current `/Users/raufaliyev/GolandProjects/xsolla-ai-kit`, the attached meeting transcript, and linked Jira/Confluence/Slack context. This is an evidence note, not an implementation plan. No production code was changed.

## Executive finding

The repository has no quest skill or quest-specific demo/test assets. It does have a clear skill contribution pipeline: `skills/<name>/SKILL.md`, frontmatter, registry entries, generated provider copies, validator, and a manually evidenced agent test. Existing demo support is for Headless Checkout and webhook replay, not Quest Platform or Web3 rewards.

The product direction is defined only as draft/scoping material. The minimum v1 intent is create, list, view, and edit quests, ask for missing fields, use invisible authentication, and configure a Web3 reward. The main blockers are the unresolved Quest Platform API/auth contract, publisher/project scoping, Web3 catalog and SKU lookup, Web3 reward readiness, and a concrete test/demo environment.

## Evidence status legend

- **CURRENT**: verified in the checked-out repository or an observed system response.
- **PROPOSED / PRD**: requirement or target direction, not implementation evidence.
- **MEETING**: discussion or intention from the attached transcript, not approval or runtime proof.
- **UNKNOWN / BLOCKER**: not resolved by the inspected sources.

## 1. Current repository implementation

### [CURRENT] Skill inventory and absence of quest support

The current inventory contains eight skills: `shop-setup`, `merchant-setup`, `catalog-design`, `login-setup`, `login-styling`, `headless-checkout-integration`, `webhooks-impl`, and `production`. There is no `quest`, `quests`, `quest-platform`, `web3-reward`, or `backpack` skill directory.

Evidence:

- `skills/README.md:7-16`
- `AGENTS.md:15-27`
- `find skills -maxdepth 2 -type f` showed only the eight existing `SKILL.md` files and their references/fixtures.
- `rg` over the repository found no Quest Platform or Web3 reward implementation. The only unrelated `Quest` matches are Login provider/product text in `skills/login-setup/SKILL.md`.

### [CURRENT] What a new skill must contain

The repository contribution guide requires:

1. one `skills/<skill-name>/SKILL.md` directory/file;
2. YAML frontmatter with `name`, `description`, and `metadata.owner` / `metadata.domain`;
3. trigger-oriented, pushy description text;
4. references split into `skills/<skill-name>/references/` when the skill is large;
5. entries in both `skills/README.md` and `AGENTS.md`;
6. synchronized generated files under `.cursor/skills/**` and `CLAUDE.md`;
7. an agent test in the PR containing the exact prompt and one-line result;
8. local validation with `python3 .github/scripts/validate_skills.py`.

Evidence:

- `CONTRIBUTING-skills.md:10-34,36-66`
- `AGENTS.md:61-82`
- `CONTRIBUTING.md:6-34`
- `.github/workflows/sync-providers.yml:34-62`

### [CURRENT] Validation and test convention

`validate_skills.py` checks frontmatter, kebab-case directory names, description length, known owners/domains, relative links, JSON, both registries, generated provider files, and committed-secret patterns. It does not execute the skill and does not enforce the presence of an `Agent test` section.

Evidence:

- `.github/scripts/validate_skills.py:23-53` defines the 500-line soft warning, 1,536-character description cap, known owners, and valid domains.
- `.github/scripts/validate_skills.py:102-158` validates frontmatter and metadata.
- `.github/scripts/validate_skills.py:161-217` validates links, registries, and generated files.
- `.github/scripts/validate_skills.py:244-295` shows the complete validation flow and exit behavior.
- Current run: `Checked 8 skills: 0 new error(s), 0 known debt, 0 warning(s).`

Existing agent-test convention is prose evidence, not an automated test suite:

- `skills/catalog-design/SKILL.md:116-130` records an exact prompt, live sandbox actions, read-back, cleanup, and an explicitly documented Login blocker.
- `skills/headless-checkout-integration/SKILL.md:184-191` records an exact prompt and expected sandbox flow.
- `skills/login-setup/SKILL.md:97-101` records an expected live sandbox run that is still pending.
- `skills/webhooks-impl/SKILL.md:147-159` records fixture replay, signature, idempotency, and response evidence.

### [CURRENT] Concrete repository contribution blockers

- The natural metadata domain `quest` is not in the validator allow-list. Current valid domains are only `catalog`, `payments`, `login`, `webhooks`, `store`, `design`, `orchestrator`, and `go-live` (`.github/scripts/validate_skills.py:44-53`). A new quest-specific domain would require an agreed validator change.
- The validator owner allow-list contains only six current owners (`.github/scripts/validate_skills.py:31-42`). A new owner must be agreed and added, or an existing owner must explicitly own the skill.
- The docs give two size signals: `AGENTS.md:77-80` says under 200 lines, while `CONTRIBUTING-skills.md:12-15` and the validator use approximately 500 lines as the soft threshold. This is guidance ambiguity, not a runtime blocker.

## 2. Demo-related capabilities already present

### [CURRENT] Headless Checkout demo reference

The repository does not contain a Quest demo application. It contains a reference workflow for the external `xsolla/headless-checkout-demo` React/Vite repository, including clone, local run, and linking instructions.

Evidence:

- `skills/headless-checkout-integration/references/demo-install.md:1-19` describes the external demo as a full React/Vite reference.
- `skills/headless-checkout-integration/references/demo-install.md:31-50` gives clone and local-run steps.
- `skills/headless-checkout-integration/references/demo-install.md:54-115` explains how to link that external demo to Claude Code or Cursor.
- `skills/headless-checkout-integration/SKILL.md:148-181` lists the demo and other checkout references.

### [CURRENT] Webhook demo/test capability

`webhooks-impl` includes local JSON and raw-body fixtures for `user_validation`, `order_paid`, and `payment`, plus a fixture-replay test recipe. This can support a commerce fulfillment demonstration, but it does not exercise Quest Platform events, Web3 minting, or Backpack delivery.

Evidence:

- `skills/webhooks-impl/SKILL.md:20-29`
- `skills/webhooks-impl/references/testing.md:3-18,29-72,101-123`
- `skills/webhooks-impl/fixtures/` contains six tracked fixture files.

### [CURRENT] Shop orchestration capability

`shop-setup` orchestrates merchant setup, catalog, Login, Headless Checkout, webhooks, and production. Its architecture is commerce-focused and contains no quest step or Web3 reward path.

Evidence:

- `docs/architecture.md:3-13`
- `skills/shop-setup/SKILL.md:1-18,20-45`
- `skills/shop-setup/SKILL.md:214-225` describes the final production phase.

### [CURRENT] No Quest demo harness

There is no tracked Quest demo, Quest fixture, Web3 reward fixture, Backpack fixture, manual event script, or runnable example in this repository. The repository's tracked demo/fixture matches are limited to Headless Checkout documentation and webhook fixtures.

Evidence:

- `git ls-files | rg -i 'demo|fixture|example|test'` returned only `headless-checkout-integration/references/demo-install.md` and the six webhook fixtures.
- Repository inventory: `skills/README.md:7-16`; no quest-related directory exists under `skills/`.

## 3. External product context

### [PROPOSED / PRD] Linked Confluence PRD

The linked page **PRD: QP <-> AI Toolkit Quest Skill** is current Confluence version 3, last modified 2026-09-18, and explicitly says `Draft, requirements only`.

Source: [PRD: QP <-> AI Toolkit Quest Skill](https://xsolla.atlassian.net/wiki/spaces/QP/pages/25181847663/PRD+QP+-+AI+Toolkit+Quest+Skill)

The PRD user stories are:

- create a quest through natural language;
- list quests;
- view a specific quest;
- edit a quest;
- ask for missing required details rather than guessing;
- authenticate with Quest Platform without visible setup;
- specify a Web3 reward that is issued on completion.

The PRD also states that publisher/project scoping is a dependency, Web3 items must exist in a catalog, and the catalog location and item-creation flow are not defined. Its open questions include silent-authentication mechanics, quest deletion, and the minimum required quest fields.

Source sections: PRD sections `2. Summary`, `3. Requirements / User Stories`, `4. Dependencies`, and `5. Open Questions`.

### [PROPOSED / PRD] Parent reward direction

The parent **Token as Core Reward Engine** PRD describes tokens, NFTs, and collectibles, idempotent issuance, reconciliation, Backpack integration, AI Toolkit quest support, and a demo across surfaces. It is marked `In progress`, with dependencies and risks still listed.

Source: [PRD: Token as Core Reward Engine (In progress)](https://xsolla.atlassian.net/wiki/spaces/QP/pages/25174540441/PRD+Token+as+Core+Reward+Engine+In+progress), sections `2. Background & Context`, `4. Scope`, `5. Non-Functional Requirements`, and `6. Known Dependencies & Risks`.

### [PROPOSED / JIRA] Story and reward dependencies

- [QP-2815: Quests in the AI Toolkit](https://xsolla.atlassian.net/browse/QP-2815) is assigned to Rauf Aliyev, status `In progress`, updated 2026-09-18. Its description references viewing, creating, and editing quest flows, a headless Web Shop and in-product quests, NFT collections/tokens, the AI-kit repository, and the linked PRD.
- [QP-2814: Expanded Reward Modul](https://xsolla.atlassian.net/browse/QP-2814) is assigned to Eljan Mahmudov, status `To Do`, updated 2026-09-18. Its description calls for ERC-20 and ERC-1155 support, idempotency, and reconciliation.
- [QP-2823: Token, NFT and collectibles rewards in Quests across surfaces](https://xsolla.atlassian.net/browse/QP-2823) is assigned to Isidora Dukić, status `In progress`, updated 2026-09-17. Its description explicitly says visual prototype only, with no live Quest Platform integration and no real quest data.

Jira status is project coordination evidence, not proof that the implementation exists.

## 4. Meeting evidence

Source: `/Users/raufaliyev/Downloads/AI toolkit sync - 2026_09_18 12_30 CEST - Transcript.md`

### [MEETING] Narrowed first-demo scope

- The group discussed focusing AI Toolkit work on creating/managing quests and Web3 rewards, while leaving the Web Shop for a later version (`Transcript.md:41-59`).
- The proposed October 1 demonstration is terminal interaction with the AI toolkit, manual event firing, and seeing the resulting item in Backpack, with no visual web-shop requirement (`Transcript.md:49-59,181-205`).
- The demo is expected to show the quest creation flow first, then the event execution and Backpack result (`Transcript.md:191-211`).
- The admin panel is not expected to show Web3 reward analytics; Backpack is the visible result (`Transcript.md:211-219`).

### [MEETING] Missing-field and authoring behavior

- The desired user experience is natural language for a first-time Quest Platform user, with the agent asking questions about duration, audience, trigger/condition/reward details, and other missing information (`Transcript.md:77-87,129-139`).
- The discussion referenced following the conversational flow demonstrated by the Quest Platform CLI, but it was explicitly framed as something to check, not as a confirmed AI-kit dependency (`Transcript.md:111-123,223`).

### [MEETING] Web3 catalog and readiness uncertainty

- The meeting says a Web3 item must already exist in a publisher catalog, and the user should provide its SKU when creating the reward node (`Transcript.md:145-169`).
- Adding items to that catalog was considered out of scope for the first version. The speaker was unsure whether an API exists to verify the SKU (`Transcript.md:153-163`).
- Web3 reward work was described as `in progress`, requiring synchronization with Eljan on completion timing (`Transcript.md:143-149`).

### [MEETING] Unresolved condition scoping

The meeting raised a concern that conditions available to publisher-scoped quests may not themselves be publisher-scoped. This was left for code/product checking and is not resolved in the transcript (`Transcript.md:87-109`).

Meeting discussion is not an approval record and does not prove any of these capabilities are deployed.

## 5. Slack evidence

### [CURRENT OBSERVATION] Scoping remains open

The Slack search result from 2026-09-18 in `#sol-seynur-mammadov` says QP-2815 and the other newly created epics are still in early drafting/scoping, with no closures yet. It also lists the AI Toolkit Quest Skill PRD as design/product work.

Source: [Slack message, 2026-09-18 13:22 +04](https://xsolla.enterprise.slack.com/archives/C0AS2K9BMRS/p1789723347325159?thread_ts=1789723330.273739&cid=C0AS2K9BMRS)

This reinforces that Jira/PRD material should not be treated as completed implementation.

### [CURRENT OBSERVATION] Related reward discussions are separate evidence

Historical Slack messages report that an NFT mint path was verified on stage, while ERC-20 issuance was still mid-flight, and that two competing Web3 integrations existed: a documented webhook path and a native reward-type path awaiting a resolve endpoint. A separate message says the Web3 reward type had been added and tested, but the resolve endpoint was still pending.

Sources: [stage and integration-path discussion, 2026-08-15](https://xsolla.enterprise.slack.com/archives/C0BPDG6BJ4U/p1786812714813099?thread_ts=1786811857.270439&cid=C0BPDG6BJ4U), [resolve-endpoint message, 2026-08-13](https://xsolla.enterprise.slack.com/archives/C0AQMTP3V7G/p1786605333091559?thread_ts=1786344830.625899&cid=C0AQMTP3V7G). These are coordination context, not xsolla-ai-kit source-code evidence or proof that the final contract is ready.

## 6. Initial blocker list

1. **Quest API contract is not identified as stable.** The current repo only establishes a direct-REST skill convention (`AGENTS.md:7-11`, `docs/architecture.md:13`). The PRD does not name the final Quest Platform endpoints or schemas. The skill cannot safely implement create/list/get/update without a stable, owned contract.
2. **Publisher/project scoping and silent authentication are dependencies, not solved behavior.** The PRD makes scoping a dependency and leaves the silent-auth mechanism open. The transcript confirms the desired UX but not the mechanism (`PRD sections 2, 4, 5`; `Transcript.md:67-73,137-143`).
3. **Web3 catalog and SKU validation are unresolved.** A catalog item must pre-exist, item creation is out of scope, and the meeting was unsure whether a lookup API exists (`Transcript.md:153-169`; PRD section 4).
4. **Web3 reward implementation readiness is external to this repo.** QP-2814 is `To Do`, the meeting calls the work `in progress`, and the reward story includes ERC-20/ERC-1155, idempotency, and reconciliation. No matching implementation or fixtures exist in xsolla-ai-kit.
5. **Condition availability under publisher scope is unresolved.** This affects whether natural-language quest creation can offer the expected condition set (`Transcript.md:87-109`).
6. **No Quest-specific validation or e2e test path exists.** The repo has only prose agent tests, checkout demo instructions, and commerce webhook fixtures. A quest skill would need an agreed safe test environment, test prompt, read-back checks, event trigger, reward observation, and failure/duplicate behavior.
7. **No Quest demo harness exists in xsolla-ai-kit.** The meeting's terminal-to-event-to-Backpack demo depends on systems and data outside this repository. QP-2823 separately describes a visual prototype with no live integration or real data.
8. **Contribution metadata needs ownership decisions.** A natural `quest` domain and a new owner are rejected by the current validator allow-lists (`.github/scripts/validate_skills.py:31-53`) unless the conventions are explicitly extended.
9. **CLI reuse is unverified.** The meeting suggested checking the Quest CLI, while the current AI-kit documentation says the CLI is optional and skills call REST APIs directly (`Transcript.md:111-123`; `AGENTS.md:7-11`). This needs a deliberate contract decision before authoring skill instructions.

## 7. What is safe to conclude now

- **CURRENT:** The repository contribution mechanics are understood and currently pass validation.
- **CURRENT:** Existing reusable capabilities are commerce setup, Login, catalog, checkout, production guidance, and webhook fixture testing.
- **PROPOSED / PRD:** Quest authoring through natural language with Web3 rewards is the intended product direction.
- **MEETING:** The first demo was narrowed to terminal quest authoring plus manual event and Backpack observation, with Web Shop UI deferred.
- **UNKNOWN:** Stable Quest API/auth/scoping contract, condition set, Web3 catalog lookup, reward readiness, and a reproducible e2e test environment.

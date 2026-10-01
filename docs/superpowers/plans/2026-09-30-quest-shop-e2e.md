# Quest Shop Continuation and Fresh E2E Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continue a published quest into an existing or new headless Web Shop, then prove the packaged publisher experience and one separately approved stage reward event through independent delivery evidence.

**Architecture:** Keep the public quest-list read unauthenticated and browser-safe, while quest CRUD and event submission use their existing publisher-scoped authentication lanes. Reuse the installed managed catalog resolver and the existing Web Shop module; do not create a new public Quest API or shop package. Treat shop display, quest execution, reward settlement, and Backpack visibility as separate claims with a fresh evidence chain for this run.

**Tech Stack:** Xsolla AI Toolkit Markdown skills, plugin manifests, Node.js `node:test` Web Shop harness, Playwright, stage qp-server and event collector, qp-data, Web3 mint ledger and explorer, authenticated Backpack session.

**Spec:** `docs/superpowers/specs/2026-09-30-quest-publisher-experience-design.md` (sections 7-9).

## Global Constraints

- Use only the exact installed artifact under test in a clean AI-terminal profile; record its package version and digest.
- Treat stage selection as explicit configuration. Do not infer an environment by trying hosts with a publisher key.
- Use the confirmed project-local `XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID`, and `XSOLLA_PROJECT_API_KEY`; inspect names and presence only, never print values or headers.
- Keep publisher Basic authentication on the trusted project-scoped qp-server and approved event-collector routes. Never use `X-REQUEST-APIKEY` as a publisher fallback.
- The shop browser calls only `GET /api/v2/public/merchants/{merchant_id}/projects/{project_id}/quests?page=1&limit=10`, without credentials. Never put the internal `*.srv.local` stage URL in a public shop build.
- A Publisher Store row alone does not verify a `web3_item`. Require the selected catalog project and SKU to resolve through the qualified minting catalog and metadata reads before publication.
- Verify that the deployed stage worker preserves `web3_item.body.project`; historical build evidence does not identify the current worker.
- The event is a separate, potentially paying action. Require separate approval for exactly one new event, one fresh idempotency key and the specified player. No `load_test` bypass and no resend after timeout or ambiguous acceptance.
- A player's `xsolla_id` authorizes targeting that player, not reading their Backpack. Claim Backpack visibility only with a separately authorized authenticated player session or read path.
- Never claim fresh proof from the 2026-09-28 or 2026-09-29 historical runs. Use a new disposable item, quest, event and evidence record.
- Keep the canonical skill and `.cursor` mirror byte-identical. Do not include credentials, cookies, full user identifiers or wallet secrets in artifacts.
- Do not commit or push files unless the user explicitly requests it.
- Treat `qp-server.nl-k8s-stage.srv.local` and the stage verifier as VPN-only stage evidence. It is never a browser base URL for a public shop and does not prove production or public-network reachability.

## Review Focus

- **Missing installed capability:** An installed package lacks `quest-setup` or the managed `resolveRewardItem` read. Test: inspect the installed artifact and invoke a no-write catalog resolution; block before any quest write if unavailable.
- **Catalog ambiguity or type confusion:** A name has zero or multiple plausible matches, or a Store item is mistaken for a mintable NFT. Test: no-write proposal cases for a unique item, ambiguous item and a distinct supported reward type; do not create or activate in these cases.
- **Shop URL/scope leakage:** A public shop is configured with an internal stage host or wrong merchant/project. Test: reject unsafe host, verify the exact public-list URL, and render an empty state for a different valid scope.
- **Player/session conflation:** The event user has a wallet but no authorized Backpack session. Test: stop short of a Backpack claim and report the furthest independently verified delivery stage.
- **Ambiguous event result or historical-row collision:** Collector response is uncertain or qp-data contains an older completion for the same quest/user. Test: search read-only by the fresh key/event correlation, never post again, and classify unresolved results as unverified.

## File Structure

| File | Responsibility |
|---|---|
| `skills/quest-setup/SKILL.md` | Conversation order: publish, shop continuation, separate event consent and truthful result wording. |
| `skills/quest-setup/references/web-shop-module.md` | Public GET configuration, existing/new-shop discovery, idempotent in-catalog integration and safe stop conditions. |
| `skills/quest-setup/references/auth-and-environment.md` | Trusted environment selection and credential boundaries for publisher, public list and read-only provider access. |
| `skills/quest-setup/references/rewards.md` | Type-specific catalog and wallet preflight; selected catalog project/SKU and delivery semantics. |
| `skills/quest-setup/references/events.md` | Separate event approval, one fresh idempotency key, collector lane and no-resend rule. |
| `skills/quest-setup/references/verification.md` | Event-to-execution correlation, bounded read policy and separate destination claims. |
| `.cursor/skills/quest-setup/` | Generated byte-identical mirror of the canonical skill. Regenerate through the repository sync workflow. |
| Installed plugin artifact and its manifest | Read-only check of package version, digest, `quest-setup` inclusion and managed resolver availability; package construction and manifest edits belong to Plan B. |
| `../quest-skill-e2e/webshop-harness/tests/quest-module.test.mjs` | Fixture tests for populated/empty/error display, safe rendering and idempotent new/existing shop upsert. |
| `../quest-skill-e2e/webshop-harness/scripts/verify-stage-webshop.mjs` | Read-only stage public-list probe and render evidence for new/existing shop fixtures. It records a separately labeled historical reward correlation, not a fresh reward run. |
| `../quest-skill-e2e/progress.md` | Append the new run's redacted, independently correlated stage evidence. Never overwrite historical entries. |
| `docs/superpowers/test-plans/2026-09-30-quest-shop-e2e-test-plan.md` | Fresh AI-terminal cases and stage evidence checklist, if execution needs a transcript/reviewer worksheet separate from source docs. |

**Dependency boundary:** Consume Plan B's installable artifact with its managed read-only `resolveRewardItem` capability and agreed env contract. This plan does not create or edit plugin manifests or connector source. The current checkout does not expose that callable connector. If Plan B's artifact is unavailable or fails installed-package preflight, complete only local fixture tests and read-only shop checks; block before creating or activating a disposable quest.

---

### Task 1: Verify Plan B's installed-package prerequisites

**Files:**
- Inspect: `docs/distribution.md`
- Inspect read-only: the exact installed plugin artifact and its manifest from Plan B

**Interfaces:**
- Consumes: Plan B's packaged skill, managed resolver, shared env contract and supported host install instructions.
- Produces: `RUN_ID`, `RUN_DIR`, plus a clean-profile record of the exact installed artifact, version, digest, skill availability and read-only resolver preflight.

- [ ] **Step 1: Verify the exact package and connector availability**

Follow Plan B's host install instructions. In the clean profile, record the installed artifact version/digest and verify `quest-setup` plus the callable managed `resolveRewardItem` operation. Do not load the local source checkout as a substitute. If the exact artifact or no-write resolver preflight fails, record the gate as blocked and skip all quest mutations.

Generate one run ID and create its evidence directory outside the shop source tree:

```bash
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$PWD/artifacts/quest-shop-e2e-$RUN_ID"
mkdir -p "$RUN_DIR"
```

Keep this directory local and access-controlled. Do not place credentials or session data in it.

- [ ] **Step 2: Install the exact artifact from the reviewed source state**

Install Plan B's reviewed immutable artifact using the selected host's supported plugin flow. Record its artifact filename, version and SHA-256 digest in the run worksheet. Do not bundle `.env` files, project API keys, cookies or player tokens.

- [ ] **Step 3: Open a clean AI-terminal profile**

Open a fresh project/workspace profile with the exact Plan B artifact installed. Confirm the skill is loaded from the artifact, not the source checkout. Record the host, plugin version and digest.

- [ ] **Step 4: Run no-write project and reward preflights**

Confirm the expected configuration variable names without printing values. Confirm explicit `stage` selection, read-only project access, connector authentication/scope, a unique candidate, and for Web3 its project-qualified mint SKU and metadata. Stop if any check is unavailable or ambiguous.

Expected: an installed artifact with no-write reward resolution and authorized read surfaces identified for qp-data, mint ledger, chain and (if claimed) Backpack. No quest or event has been written.

### Task 2: Continue publication into a Web Shop and verify fixture behavior

**Files:**
- Modify: `skills/quest-setup/SKILL.md` and `.cursor/skills/quest-setup/SKILL.md`
- Modify if the recipe needs clarification: `skills/quest-setup/references/web-shop-module.md` and its `.cursor` mirror
- Test: `../quest-skill-e2e/webshop-harness/tests/quest-module.test.mjs`

**Interfaces:**
- Consumes: a read-back active quest and its confirmed merchant/project scope; the shop's existing public base URL and IDs.
- Produces: either an observed existing module displaying the actual public response, one idempotently added module inside catalog content, or a precise blocked/offer result.

- [ ] **Step 1: Add the post-publication discovery branch**

After the quest read-back, inspect the accessible workspace for a headless shop and `data-xsolla-quest-module` marker. For an existing module, verify IDs and public base URL and perform an actual fetch. If absent, obtain separate approval for editing shop source, then upsert once inside catalog content. If no shop exists, offer `shop-setup`; do not create one as a side effect.

- [ ] **Step 2: Keep browser and agent auth separate**

Configure the browser module only with merchant ID, project ID and a publicly reachable QP base URL. Keep the publisher key out of browser configuration and requests. Stop if a public shop would call `*.srv.local`.

- [ ] **Step 3: Run the fixture suite**

Run from the harness directory:

```bash
cd /Users/raufaliyev/GolandProjects/quest-skill-e2e/webshop-harness
node --test tests/quest-module.test.mjs
```

Expected: populated and empty states, 404/422/network failure, null fields and safe rendering pass; new and existing shop upsert twice leaves one marker and no quest navigation tab.

### Task 3: Run fresh AI-terminal publication cases

**Files:**
- Modify: `skills/quest-setup/SKILL.md`, `references/rewards.md`, `references/web-shop-module.md` and their `.cursor` mirrors as needed
- Test record: `docs/superpowers/test-plans/2026-09-30-quest-shop-e2e-test-plan.md`

**Interfaces:**
- Consumes: Task 1 installed artifact; a disposable stage catalog item with verified type/project/SKU; Task 2 public-list contract.
- Produces: `QUEST_ID` and `QUEST_NAME` from the active quest read-back, a transcript where the agent describes and publishes one exact proposal, and non-mutating transcripts covering another supported reward type and blocked cases.

- [ ] **Step 1: Exercise a natural-language request in a fresh agent session**

Use one ordinary publisher request about a newly prepared disposable reward and gameplay event. Require the agent to resolve project, reward, event meaning, graph, duration and repeat limit before showing one concise proposal. Capture the transcript with secrets and full player identifiers omitted.

- [ ] **Step 2: Approve one publication proposal**

After explicit approval of the displayed proposal, verify that the agent creates one inactive quest, reads it back, activates it and confirms active status, exact scope, reward, dates and limits. If a write outcome is ambiguous, require read-only reconciliation before any retry; never create a duplicate.

- [ ] **Step 3: Exercise non-mutating counter-cases**

In separate fresh sessions, request a different supported reward type and stop at its proposal; exercise missing credentials and zero/multiple reward matches. Confirm no reward substitution and no quest write in the blocked cases.

- [ ] **Step 4: Check publisher-facing Web Shop continuation**

With the connected shop accessible, verify the live list fetch or the offered source edit. Keep a shop-source edit under its own approval. Record offers as offers, not as render evidence.

Expected: the transcripts contain no service-auth narration, hidden node payload or secrets; one approved proposal results in one active quest; blocked cases stop without writes.

- [ ] **Step 5: Verify that the newly published quest appears in the VPN-only stage list and render**

Only after Step 2's active quest read-back, run the read-only verifier against the exact confirmed stage scope. The verifier reads the public response without Authorization, saves `public-quests-response.json`, renders that response in new/existing local fixtures, and records desktop/mobile text. Its built-in `reward-correlation.json` is explicitly historical and must not be used as evidence for this run.

```bash
cd /Users/raufaliyev/GolandProjects/quest-skill-e2e/webshop-harness
STAGE_BASE_URL=https://qp-server.nl-k8s-stage.srv.local \
MERCHANT_ID="$XSOLLA_MERCHANT_ID" \
PROJECT_ID="$XSOLLA_PROJECT_ID" \
OUT_DIR="$RUN_DIR/webshop-stage" \
CA_FILE="/Users/raufaliyev/.config/xsolla/ca.crt" \
node scripts/verify-stage-webshop.mjs
```

Before running, export the non-secret merchant/project IDs only after matching them to the selected project; do not source `.env` in a way that prints it or dump the environment. The script's wrong-scope probe is hard-coded to merchant `940247`; use that probe only for the corresponding stage setup, and mark it not applicable if the target merchant differs.

The current script records quest IDs/names and rendered text but does not assert the new quest. Require an exact post-run assertion using the active quest read-back values:

```bash
EXPECTED_QUEST_ID="$QUEST_ID" EXPECTED_QUEST_NAME="$QUEST_NAME" \
OUT_DIR="$RUN_DIR/webshop-stage" node --input-type=module <<'NODE'
import assert from 'node:assert/strict';
import fs from 'node:fs';
const dir = process.env.OUT_DIR;
const id = process.env.EXPECTED_QUEST_ID;
const name = process.env.EXPECTED_QUEST_NAME;
const response = JSON.parse(fs.readFileSync(`${dir}/public-quests-response.json`, 'utf8'));
const quest = response.data.find((item) => item.id === id);
assert.ok(quest, `public stage list is missing quest id ${id}`);
assert.equal(quest.name, name, 'quest name differs from the active read-back');
const dom = JSON.parse(fs.readFileSync(`${dir}/dom-assertions.json`, 'utf8'));
for (const shop of ['new-shop', 'existing-shop']) {
  const rendered = dom.stageRenders.find((item) => item.shop === shop);
  assert.ok(rendered?.desktop?.text?.includes(name), `${shop} desktop render is missing ${name}`);
  assert.ok(rendered?.mobile?.text?.includes(name), `${shop} mobile render is missing ${name}`);
  assert.equal(rendered.desktop.modules, 1, `${shop} desktop module count`);
  assert.equal(rendered.mobile.modules, 1, `${shop} mobile module count`);
  assert.equal(rendered.desktop.inNav, false, `${shop} desktop module entered navigation`);
  assert.equal(rendered.mobile.inNav, false, `${shop} mobile module entered navigation`);
}
console.log(JSON.stringify({ stageOnly: true, questId: id, questName: name, renderedShops: ['new-shop', 'existing-shop'] }));
NODE
```

This assertion prints the exact new quest ID/name and fails unless the response and both viewport renders include that quest. `*.srv.local` is VPN-only: the verifier proves stage list/render for the supplied quest, not public-network reachability or production behavior, and not reward settlement. The actual public shop's `XSOLLA_QP_PUBLIC_BASE_URL` must separately be publicly reachable and non-internal; never set it to this stage host.

### Task 4: Submit one separately approved stage event and verify delivery

**Files:**
- Modify as needed: `skills/quest-setup/SKILL.md`, `references/events.md`, `references/rewards.md`, `references/verification.md`, and their `.cursor` mirrors
- Evidence: append a new dated section to `../quest-skill-e2e/progress.md`

**Interfaces:**
- Consumes: Task 3 active quest; newly prepared disposable item; exact test-player identity; successful wallet/project preflight; publisher approval specifically for one potentially paying event; authorized read surfaces.
- Produces: one collector `event_id`, correlated qp-data row/action, type-specific settlement record, and an explicit evidence classification.

- [ ] **Step 1: Reconcile the fresh run identity before event approval**

Choose a new disposable item, quest, unique event name, test player and idempotency key. Confirm there is no collision with a prior quest or reward for this user. Read the active quest back and compare exact scope, trigger, SKU/project, quantity and window. For Web3, verify the player's wallet resolves to the same `xsolla_id` with the supported player-visible wallet source and confirm the deployed worker build propagates the catalog project.

Expected: all checks are read-only and pass before showing event intent. Missing wallet, unsupported project propagation, expired window or unavailable evidence access stops before the event.

- [ ] **Step 2: Get separate consent and submit exactly once**

Show the exact gameplay event intent, player, quest and expected payout. Wait for separate explicit approval. Submit one collector request through the verified publisher Basic lane, with one fresh UUID idempotency key and no `load_test` bypass. Save the returned `event_id`. Do not include or print Authorization headers. If acceptance is ambiguous, query by the fresh correlation; never resend.

- [ ] **Step 3: Correlate execution independently**

Read only the confirmed publisher's quest and specified user's execution from qp-data. Match `eventId` to the collector's `event_id`, then verify the intended quest, player and `issue_reward` action/status and exact reward parameters. Follow the bounded read policy in `references/verification.md`; after it expires, report unverified and perform reads only.

- [ ] **Step 4: Verify the type-specific destination**

For `web3_item`, match the mint ledger project and SKU, transaction receipt, token transfer to the resolved wallet, and the named NFT in the separately authorized authenticated Backpack session. For `inventory_item`, read the corresponding Backpack grant/inventory result. For `web3_token`, verify the destination wallet and transaction using the token contract binding. Do not use NFT evidence criteria for another reward type. `issue_reward = COMPLETED` alone is insufficient.

- [ ] **Step 5: Record fresh redacted evidence and classify it**

Append the new run to `../quest-skill-e2e/progress.md`: artifact version/digest; source and worker identities; public list/render result; new item/quest alias; event ID; matching execution/action; type-specific delivery result; and Backpack result if authorized. Redact tokens, headers, cookies, email, full user ID and wallet secrets. Mark `PASS` only with the applicable destination evidence; for NFT without Backpack read-back use `DELIVERY VERIFIED, BACKPACK UNVERIFIED`; use `BLOCKED` or `unverified` for missing earlier evidence. Keep prior E2Es labeled historical.

### Task 5: Independent review and local acceptance gates

**Files:**
- Validate: all changed canonical and generated skill files, test worksheet and fresh evidence
- Review: fresh transcript, stage read-backs and evidence chain

- [ ] **Step 1: Regenerate mirrors and run the Toolkit validator**

Use the copy procedure in `.github/workflows/sync-providers.yml`, then run:

```bash
cd /Users/raufaliyev/GolandProjects/xsolla-ai-kit
python3 .github/scripts/validate_skills.py
git diff --check
```

Expected: validator passes and canonical/`.cursor` files are byte-identical; no credential or secret-pattern finding appears.

- [ ] **Step 2: Re-run the Web Shop fixture tests**

```bash
cd /Users/raufaliyev/GolandProjects/quest-skill-e2e/webshop-harness
node --test tests/quest-module.test.mjs
```

Expected: all fixture and idempotence tests pass. Label these local results as fixture coverage.

- [ ] **Step 3: Have an independent agent inspect the run**

Ask a second agent to compare transcript and redacted read-backs against this plan and the approved spec. It must check event uniqueness/no resend, project/SKU preservation, source/deployment identity, Backpack session authorization, secret hygiene and whether each success statement has its own evidence.

- [ ] **Step 4: Report the strongest supported outcome**

Accept full shop proof only with a live public-list fetch and actual rendered quest in both shop fixtures. Accept full NFT delivery only with matching qp-data, catalog-qualified ledger, successful chain transfer and separately authorized Backpack observation. If any dependency is missing, state the exact last verified boundary and leave the E2E `BLOCKED` or `BACKPACK UNVERIFIED`; do not upgrade historical evidence into current proof.

## Acceptance

- The exact installed plugin artifact is identified by version and digest and exposes the required skill and managed read-only catalog resolver.
- Fresh agent sessions show correct generic reward resolution, no hidden implementation narration, one approval for quest publication and no writes in blocked cases.
- The live public list uses no Authorization header, filters to the confirmed publisher/project and renders inside both new and existing catalog layouts with one marker and no top-level Quest tab.
- The event is submitted only after separate consent, once, with a fresh idempotency key and a verified test player; ambiguity results in reads only.
- The returned `event_id` matches the qp-data `eventId` and exact reward action, then the independent type-specific destination is verified.
- Backpack visibility is claimed only after a separate authorized authenticated read. Historical 2026-09-28/29 evidence remains regression context, not this run's result.
- Local skill validator, mirror check, `git diff --check`, Web Shop fixtures and independent review pass. No commits or publication are part of this plan.

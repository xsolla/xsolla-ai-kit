# Quest Publisher Experience Design

**Status:** Approved for implementation planning
**Date:** 2026-09-30

## 1. Purpose and success

A publisher describes a quest and its reward in ordinary language. The Toolkit checks the configured project and the requested reward, shows one concise proposal, and publishes the quest after one approval. The publisher sees business terms and actionable errors, not internal service names, authentication lanes, API contracts, or workflow narration.

After publication, the Toolkit helps display active quests in a source-accessible headless Web Shop. It offers a separate test that can submit one event for a specified test player and verify the outcome. A result is called delivered to Backpack only when Backpack or the appropriate wallet evidence has actually been read back.

Success is a fresh AI-terminal run of an arbitrary natural-language quest request, with truthful handling of both successful and blocked paths. The reward name used by a test is test data, never a special case in the skill.

## 2. Agreed product behavior

1. A proposal precedes the first quest write. Read-only project, contract, and reward checks require no plan approval.
2. One approval of the exact proposal authorizes the ordered create, configure, activate, and read-back sequence. An inactive intermediate quest may exist internally but is not presented as a separate draft workflow.
3. A published quest appears in an already connected Web Shop when the shop next fetches the active quest list. Drafts and inactive quests are excluded.
4. If a source-accessible shop has no quest module, offer to add the list there. If its location is unknown, ask for the path or repository. If no shop exists, offer `shop-setup`. Xsolla Site Builder without source access is outside this design.
5. A test event is offered after publication, never submitted as part of publication approval. It needs separate consent and the required test-player identity. It may cause a real reward.
6. Reward names and types are resolved from the request and supported catalog/runtime capabilities. Do not hardcode a particular name or silently substitute another reward type.

## 3. Boundaries and implementation sequence

`quest-setup` remains the single conversational entry point. Its references describe four bounded capabilities:

| Capability | Responsibility | Dependency |
| --- | --- | --- |
| Project context | Read the selected local configuration, choose a trusted Quest API target, validate project access | `merchant-setup` credential contract and versioned Quest API contract |
| Reward resolution | Map the request to a supported reward type; resolve and verify any catalog item, SKU, project, quantity, or amount | Publisher catalog and type-specific provider read capability |
| Quest publication | Build the complete graph, save, activate, and read back exact status/scope/reward | Existing publisher-scoped Quest Platform routes |
| Shop and optional test | Locate or add the headless shop module; optionally submit one event and verify its effects | Public quest-list endpoint, collector, authorized execution and reward read-back |

Implementation is coordinated in this order: (1) Toolkit conversation and configuration, (2) verified reward read capability and deployed worker compatibility, (3) Web Shop continuation, (4) agent and controlled E2E verification. A phase cannot claim end-to-end success from source code or a historical run alone.

## 4. Configuration and service contracts

After implementation, `merchant-setup`, `shop-setup`, and `quest-setup` share the project-local keys `XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID`, and `XSOLLA_PROJECT_API_KEY`. Today `merchant-setup` writes them while `quest-setup` expects different names. A complete process-environment set may override a complete project `.env` set. Partial sources are not combined. Secret inspection parses only expected names as text; it never sources `.env`, prints values or headers, or copies credentials into the plugin package.

The configured project may be a publisher's test project or a live project. `XSOLLA_QP_ENV=production|stage` is a separate, non-secret Quest service selection in the same project configuration; absence means `production`, and `stage` must be explicit for a controlled stage run. A versioned skill reference maps each value to the exact source-backed public Quest gateway. The key is never sent to a guessed hostname or probed against multiple hosts to infer its environment. Publisher quest routes use HTTP Basic with the configured merchant ID and project API key. `X-REQUEST-APIKEY` is a separate internal service lane and is never a publisher fallback. A read-only project GET confirms the selected scope before any write. Normal replies use the project name, with raw IDs and host details shown only when needed to repair a blocker.

Production Quest API code deliberately disables `/openapi.json`. The skill therefore uses a versioned contract derived from service source for production operations and checks actual responses through read-only preflight and post-write read-back. Where stage OpenAPI is available it can validate stage shape, but it does not prove the production deployment. An unavailable contract or route is reported precisely; it is not translated into a missing credential claim.

`merchant-setup` must stop recommending commands that print `.env` lines or delete every `XSOLLA_*` variable. It updates only the intended keys, preserves unrelated settings, and verifies their presence without revealing values. Missing configuration yields a short instruction naming the required merchant ID, project ID, and project API key and where to save them. The user is never asked to paste the key into chat.

## 5. Reward resolution

The skill interprets the requested reward as a business concept, then selects a supported runtime reward type. Each type has its own validation and destination. A Web3 item is an NFT mint that can appear as an asset in Backpack; an inventory item follows Backpack's item-grant path; a Web3 token is a wallet payout. Other runtime types must follow their own documented contract. If the request or catalog leaves the type ambiguous, ask one business question. Never turn a failed lookup into another reward type automatically.

For a named Web3 item, discover candidates from the publisher catalog, then validate the exact `(catalog project, SKU)` with the already demonstrated project-qualified minting catalog and metadata reads. The catalog project is taken from the selected item, not copied from the Quest project. A Store item row alone is insufficient proof that the minting catalog can resolve it. Zero matches, multiple plausible matches, or unavailable catalog access stop publication with a specific next step. A missing SKU never triggers the worker's random-SKU fallback.

The existing project-qualified minting endpoints are reused. The distributable plugin adds a managed read-only catalog connector declared in its package manifest. Its `resolveRewardItem` operation accepts the authenticated publisher scope, a natural-language query and an optional catalog project when the user's catalog spans projects. It returns bounded candidates containing display name, type, exact catalog project and SKU, and whether project-qualified minting metadata was verified. It reads the Publisher catalog for candidate discovery and validates Web3 candidates through the existing `/skus?project=...&search=...` and `/metadata/sku/{sku}?project=...` operations. Connector-owned service access remains in managed secret storage; the user's Quest project key is not sent to the private minting service, and the connector has no claim or payout operation. A new public Quest API endpoint is not the default solution. Connector availability, auth, and project scope must pass read-only preflight in the installed Toolkit before a named Web3 reward can be published.

For Web3 rewards, activation is gated on a deployed worker that preserves the selected catalog project through payout. The 2026-09-29 stage runs showed that a worker which ignores `body.project` can mint under a default project and lose the catalog name in Backpack, while the corrected worker produced the named item. Check the exact runtime version or perform a controlled non-payout compatibility read before promising the outcome. The historical corrected stage run is evidence for that build only.

## 6. Publication transaction and recovery

Before asking for approval, resolve the project, reward, event meaning, graph, duration, repeat limit, and expected payout impact. The preview says what a player must do, what reward they receive, and which publisher project will publish it. It omits implementation fields unless the user asks. If a material business value cannot be inferred, ask one focused question.

After approval, create the complete inactive quest, read it back, activate it, then read back active status, scope, reward configuration, dates, limits, and version. Each write uses the service's accepted schema and the same approved proposal. Do not ask for a new confirmation for each internal POST or PUT. Any external action beyond the approved quest, including a test event, requires its own approval.

If a write fails after a quest has been created, read its current state before retrying. Resume or repair the same quest when safe; do not create a duplicate or claim publication. Tell the publisher simply that publication did not finish, whether the quest is visible, and the concrete next step. If the result of a write is ambiguous, reconcile by read-only lookup before any retry.

## 7. Web Shop continuation

The public quest-list API filters to active quests in their active time window for the exact merchant/project pair. A connected shop performs a new GET on page load or refresh, so publication becomes visible at the next fetch. This design does not promise push updates to a browser tab that remains open.

After quest read-back, inspect the accessible workspace for a headless Web Shop and the `data-xsolla-quest-module` root marker. Integration edits the publisher's shop source; installing the Toolkit does not provide a reusable shop frontend package. For an existing module, verify its configured scope and public endpoint, then check that the published quest appears in the returned list. If no module exists, offer to add one inside the catalog content, preserving products, categories, checkout, and navigation. Ask for the shop path only when discovery cannot identify it. A separate consent covers source edits to a shop. A new shop is offered through `shop-setup`; no shop is created merely because a quest was published. Module upsert remains idempotent.

## 8. Optional test and evidence

The skill offers a test after publication. It waits for separate approval, the exact test quest, and a valid test-player identity. Player identity authorizes event targeting, not access to the player's Backpack. Claiming Backpack visibility additionally requires an authenticated player session or a separately authorized read path. For a Web3 item, preflight also verifies the player's existing wallet and the selected item/project. A stage ingestion smoke using `load_test=true` is not a reward test when the stage bypass is enabled; a production event can still pay out despite that property. The reward test uses one unique idempotency key and one event submission, with no blind resend after timeout or ambiguity.

Verification correlates the collector's `event_id` with the matching execution `eventId`, the intended action, and the type-specific delivery record. For an NFT this includes project-qualified mint ledger, transaction, wallet/chain transfer, and a separate authenticated Backpack observation when available. For an inventory item it checks the Backpack grant/read-back path; for a token it checks the destination wallet and transaction. `issue_reward = COMPLETED` alone does not prove delivery. If authorized execution or Backpack read access is unavailable, report the last verified stage and the missing evidence rather than claiming success.

Historical 2026-09-28 and 2026-09-29 stage E2Es are regression references. A new unmocked run needs its own item, quest, event, test player, evidence chain, and explicit approval for the one reward event.

### Fresh E2E procedure

1. **Package and agent preflight.** Install the exact updated plugin artifact through the supported plugin path in a clean AI-terminal profile and workspace. Verify that its manifest includes `quest-setup` and the managed `resolveRewardItem` capability; record package version and digest. A source-loaded development run is useful but cannot satisfy this package check. Confirm that project configuration is recognized without printing values, the selected Quest host is trusted, the catalog resolver returns a project-qualified item, and the stage worker has the project-propagation behavior needed by that item. Identify authorized read tools for execution, mint ledger, transaction/chain and destination verification before any payout; arrange a separately authorized authenticated Backpack session when NFT visibility is to be claimed. Record exact source and stage deployment identities.
2. **Publisher conversation.** Give an agent that has not seen the implementation an ordinary one-sentence request using an approved, newly prepared disposable reward and a gameplay event. Observe the full transcript. It must perform read-only checks before asking, show a plain-language proposal, request one publication approval, create and activate exactly one quest, then read back active status, reward, scope, dates, and limits. Run a separate no-write local agent case with a different supported reward type and stop at its proposal to detect hardcoded NFT behavior. Also exercise missing credentials and an unresolved reward as non-mutating negative cases.
3. **Shop proof.** Fetch the public quest list for the exact publisher/project pair and verify the new active quest. Render both a newly configured and an existing headless shop fixture from that response. Verify one quest module inside catalog content, no duplicate after a second integration pass, no new top-level tab, and an honest empty state for a different scope. A shop offer alone is recorded as an offer, not as render proof.
4. **Separately approved reward event.** After the publisher explicitly agrees to the test and provides the test player, read back the active quest, the qualified reward and the player's required wallet/identity state. Show the exact event intent. Submit one event with one fresh idempotency key, without `load_test` payout bypass, and record the collector response `event_id`. An ambiguous response is investigated by reads, never blindly resent.
5. **Independent delivery correlation.** Match that `event_id` to qp-data `eventId`, the intended quest and player, and the reward action. For a Web3 item, verify the mint ledger's catalog project and SKU, transaction receipt, token transfer to the resolved wallet, and the named item in the separately authorized authenticated Backpack session. For another reward type, use its own delivery record rather than NFT criteria. If a read surface is unavailable, record the last verified stage; never fill the gap from `issue_reward = COMPLETED` alone.
6. **Review and outcome.** A second agent reviews the transcript, API read-backs and correlation for false success claims, duplicate writes, secret exposure, and type confusion. `PASS` requires the applicable destination to be observed, including Backpack UI for an NFT claim. `DELIVERY VERIFIED, BACKPACK UNVERIFIED` means mint ledger and chain transfer match but Backpack could not be read; it is not a full NFT E2E pass. `BLOCKED` means earlier required evidence or access is missing. Read-only reconciliation of an already-minted transaction may continue after a blocker is repaired. Any new payout event needs a fresh disposable fixture and separate approval; never recycle or blindly resend an ambiguous event.

## 9. Distribution, validation, and acceptance

The canonical `skills/quest-setup/` and `.cursor/skills/quest-setup/` copies must remain synchronized. The installed plugin package must actually contain the updated skill; the currently cached `1.0.0` package does not. Packaging checks inspect its manifest, included files, and secret-free configuration. They do not copy project `.env` into the package.

Validation includes the repository skill validator, mirror equality, `git diff --check`, and fresh agent runs with ordinary natural-language requests. Cases cover a configured project, missing or partial settings, unreachable contract, absent/ambiguous/unsupported reward, single approval publication, partial-write recovery, existing/missing/no shop, and separate test consent. Agent output must avoid premature plan approval, public web search for catalog items, invented connection failures, internal narration, and unverified success claims.

Acceptance requires: one publisher approval publishes a fully configured quest; the saved active quest and exact reward read back correctly; the installed skill recognizes `merchant-setup` credentials; and a fresh authorized E2E proves the type-specific delivery path. For a connected source-accessible shop, a successful display check requires an actual fetch and render; an offer to integrate a missing shop is a separate, narrower result. Backpack visibility is accepted only with separately authorized Backpack read-back; otherwise verified mint/chain delivery and unverified Backpack visibility are reported separately. Any unverified service access or deployed-worker mismatch remains a stated blocker rather than a completion claim.

## 10. Source evidence and limits

- `skills/merchant-setup/SKILL.md` writes the generic `XSOLLA_*` keys; `skills/quest-setup/references/auth-and-environment.md` currently expects `XSOLLA_PROD_*`.
- `../adtech-QP-2934/qp-server/internal/http/router.go` disables production OpenAPI, while service Postman environment files identify the public Quest gateways. Current reachability still needs a read-only probe.
- `../quest-skill-e2e/progress.md` records project-qualified catalog lookup and complete NFT E2E on 2026-09-28; its 2026-09-29 first and second runs demonstrate the default-project regression and corrected stage worker.
- `../adtech-QP-2937/lib/models/generic_quest/issue_reward.go` and the matching worker activity contain project propagation in the experiment build. The older `../adtech-QP-2934` checkout does not. Neither local branch nor historical deploy log proves the current deployment.
- The existing Web Shop public-list source is in `../adtech-QP-2934/qp-server/`. The Toolkit Web Shop recipe is in `../xsolla-ai-kit-QP-2936/skills/quest-setup/references/web-shop-module.md`; that checkout documents integration but does not contain a reusable shop frontend package.

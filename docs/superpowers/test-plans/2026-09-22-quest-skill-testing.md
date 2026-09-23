# Quest skill local and stage test plan

Date: 2026-09-22  
Repository: `/Users/raufaliyev/GolandProjects/xsolla-ai-kit`  
Branch: `QP-2890-verification`

## Test boundary

Local tests validate skill discovery, wording, payload construction, safety
stops, links, and generated-file integrity. They do not prove service behavior.

Stage checks are read-only in this run. Allowed checks are OpenAPI discovery and
qp-data execution read-back. The following remain out of scope until an owner
provides an approved fixture and explicit authorization: quest CRUD writes,
activation, event submission, webhook or notification delivery, reward issuance,
wallet/blockchain/Backpack verification, and retries after an unknown write
result.

## User stories and use cases

1. As a developer, I want the agent to identify the Quest skill and ask for
   environment, credential, scope, and reward prerequisites before writes.
2. As a developer, I want a minimal inactive quest draft without accidental
   activation or network calls.
3. As a developer, I want event and schedule triggers described accurately,
   including the unsupported date/time runtime.
4. As a developer, I want condition nodes that include event windows and explain
   identity, history, and attribute prerequisites.
5. As a developer, I want a Web3 reward proposal with fixture and payout
   approval gates.
6. As a developer, I want an event payload with safe idempotency and a saved
   correlation key before submission.
7. As a developer, I want read-only verification to prove execution without
   claiming wallet delivery.
8. As a developer, I want ambiguous failures and timeouts handled without
   duplicate events or false conclusions.
9. As a maintainer, I want canonical, mirror, registry, link, and frontmatter
   validation to detect drift.

## Executed matrix

| ID | Execution | Expected result | Result on 2026-09-22 |
|---|---|---|---|
| UC1 | Fresh local agent received an access/prerequisites prompt. | Invoke `quest-setup`; state Basic-lane blocker, scope confirmation, no writes, and wallet boundary. | PASS |
| UC2 | Fresh local agent drafted `Weekly Starter` inactive with no nodes. | Four required fields; empty nodes/connections allowed; creator remains an explicit placeholder. | PASS |
| UC3 | Fresh local agent answered daily schedule plus `tutorial.completed`. | Use `dynamic_event`; explain `date_and_time` is accepted but not a working scheduler; do not invent schedule fields. | PASS |
| UC4 | Fresh local agent drafted level-count plus country conditions. | Include `event` `time_window`, numeric `gte`, string equality, and runtime failure prerequisites. | PASS |
| UC5 | Fresh local agent proposed `web3_token` with `XLA-000-001` and `0.01`. | Show proposed body; require owner-approved fixture and activation confirmation; never claim delivery. | PASS |
| UC6 | Fresh local agent prepared `web3.token_test` event. | Fresh body UUID, RFC3339 timestamp, required user identity, saved payload, later `event_id` correlation, confirmation before submit. | PASS |
| UC7 | Read-only stage `qp-data` lookup for quest `44193275-5376-498b-9e14-e91fbe9085c9`. | Report historical execution evidence and reward action; do not claim wallet delivery. | PASS, historical only |
| UC8 | Fresh local agent evaluated timeout, empty read-back, and 404 prompts. | No event resend; empty result is not failure; 404 remains not-found/no-access/not-onboarded ambiguity; bounded read policy is used. | PASS after fix |
| UC9 | Local validators and reverse mirror audit. | All validators pass and canonical/mirror file sets and bytes match. | PASS |

## Stage evidence captured

- `qp-server/openapi.json`: HTTP 200.
- `qp-events-collector/openapi.json`: HTTP 200.
- `qp-data/openapi.json`: HTTP 200.
- `qp-data` execution lookup: HTTP 200, two historical records, both
  `COMPLETED`, with `issue_reward` action `COMPLETED`, reward type
  `web3_token`, SKU `XLA-000-001`, amount `0.01`.
- No event was submitted during this run, so there is no new collector
  `event_id` to correlate. The historical rows must not be presented as a new
  end-to-end test.

## Local commands

```text
python3 -B .github/scripts/validate_skills.py
python3 /Users/raufaliyev/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/quest-setup
git diff --check
```

The dedicated validation result was `Checked 9 skills: 0 new error(s), 0 known
debt, 0 warning(s)`, and the skill validator reported `Skill is valid!`.

## Acceptance criteria for a future authorized stage write test

- The credential lane and service-specific auth are verified against deployed
  contracts, with no secrets pasted into chat or committed files.
- A named owner-approved inactive quest and reward/webhook fixture are provided.
- The agent shows scope, complete document, action impact, activation limits,
  and receives explicit confirmation before each mutating step.
- The event payload, body idempotency key, collector `event_id`, quest, user,
  and scope are recorded for correlation.
- Any timeout stops writes and uses only bounded read-back.
- Completion is reported only when the matching execution and action statuses
  are positive; wallet settlement remains a separate evidence stream.

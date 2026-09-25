---
name: quest-setup
description: >-
  Creates, inspects and edits Xsolla Quest Platform quests conversationally,
  submits a quest event, and verifies that the event actually made the quest
  execute. Covers the whole quest document: the node graph and its connections,
  the seven node subtypes, the condition grammar, activation limits, and all
  nine reward types including web3_item and web3_token ERC-20 payouts. Use when
  setting up a quest, adding a trigger or a condition, attaching a reward,
  editing or activating an existing quest, firing a test event, or working out
  why a quest did not fire — including "create a quest", "add a Web3 reward to
  my quest", "make a quest that pays USDC", "trigger my quest", "send a quest
  event", "why didn't my quest complete", "list my quests", "activate a quest",
  "quest platform API".
metadata:
  owner: r.aliyev
  domain: quests
  status: draft
---

## Status

This skill is a **draft**. The credential lane it targets is not deployed yet,
and an Xsolla-internal service key is the interim lane; see Prerequisites.

## When to use

Use this skill when the developer wants to manage quests on the Xsolla Quest
Platform:

- Create a quest, as a draft first and then activate it
- Add triggers, conditions or reward actions to a quest
- List, view or edit existing quests
- Submit a single quest event to make a quest run
- Check whether an event actually caused a quest to execute

Out of scope: on-chain finality, wallet balances and Backpack display. This
skill configures a Web3 reward and reports that a quest executed. For a Web3
reward, a completed reward action means the provider returned a transaction
hash for the claim. The skill never states that a token was delivered.

## Prerequisites

Follow [`references/auth-and-environment.md`](references/auth-and-environment.md)
for the required credential, request authentication, internal hosts, and scope
confirmation.

**The target lane is not accepted yet.** Quest Platform implements the
publisher Basic lane in QP-2862, inside QP-2858 Phase 3, which depends on
Phases 1 and 2. Until it lands, Basic CRUD requests return 401. The lane that
works on stage today is an Xsolla-internal service key, described in the same
reference. If neither credential is set, stop and say which is missing. If
only Basic is set, name QP-2862 and ask whether a service key is available;
do not search for other credentials. OpenAPI discovery needs no credential on
stage, so do not mistake it for CRUD readiness. Say exactly which lane failed
rather than reporting a generic authentication failure.

## Source of truth

Follow this order. It is the rule the rest of the skill depends on.

1. **Routes, path parameters, envelope field names and types, and the
   top-level `required` list** come from the service's **live OpenAPI
   document**. Fetch it once at the start of the session.
2. **Node subtypes, node `parameters`, the condition grammar, the reward
   bodies, conditionally required fields, and every enum the document renders
   as a bare `string`** come from this skill's `references/`.
3. On conflict: the OpenAPI document wins on shape, `references/` wins on
   rules. Rules that only the server's hand-written validator enforces are
   marked as such where they appear.
4. If neither source answers the question, **ask the developer**. Do not infer
   a field by analogy with another Xsolla API.

The qp-server document declares no security schemes, and the key header shows
up only as a parameter on some routes. Never conclude from it that a route is
unauthenticated; authentication rules live in the auth reference.

If a host is unreachable, which usually means no corporate network, say so and
offer to continue on `references/` alone, noting that the envelope may have
drifted. Never continue silently.

## Reference material

- [`references/auth-and-environment.md`](references/auth-and-environment.md) — hosts, credential, scope, and the incoming auth changes
- [`references/quest-document.md`](references/quest-document.md) — the quest graph, conditional requirements, full-document PUT
- [`references/node-subtypes.md`](references/node-subtypes.md) — the seven accepted node subtypes and their parameters
- [`references/conditions.md`](references/conditions.md) — condition grammar: types, operands, operators, event counting
- [`references/rewards.md`](references/rewards.md) — the nine reward types and their bodies, including web3_token
- [`references/events.md`](references/events.md) — submitting a quest event to qp-events-collector
- [`references/verification.md`](references/verification.md) — reading execution results back from qp-data

## Flow

1. **Bring-up.** Fetch the OpenAPI documents. Identify the credential lane,
   run the per-service preflight reads, resolve the scope as described in
   [`references/auth-and-environment.md`](references/auth-and-environment.md),
   show it, and get confirmation. Bring-up is GET-only.
2. **Draft.** Create the quest as `inactive` with the four required fields,
   `name`, `type`, `status` and `created_by`; rules are in
   [`references/quest-document.md`](references/quest-document.md).
3. **Fill in.** Add nodes and their `connections` entries one at a time,
   asking for each missing required value. Ask which action the quest should run. Show the assembled
   document, and the impact of any external action, before sending it.
4. **Activate.** A separate step: move to `active` with dates, after checking
   there are at least two nodes, a trigger-to-action path, no intended orphan
   nodes, and an acyclic graph. For a Web3 reward, also run the read-only
   checks in [`references/rewards.md`](references/rewards.md): SKU, amount
   units and cap, and the recipient's wallet. Show the activation limits and
   the effective repeat behavior before asking for confirmation. After the
   write, read the quest back and show `status`, the dates, the limits and
   `version_id`.
5. **Edit.** Read, change, full `PUT`, following the recipe in the quest
   reference. Warn that `PUT` replaces the whole document and that an edit to
   an active quest goes live for the next events. Show a before/after diff,
   repeat the activation confirmations for any changed action, reward or
   limit, and read the quest back after the write.
6. **Event.** Build the payload from the developer's values, never from
   memory or a read-back event body. Generate a fresh UUID `idempotency_key`,
   set an RFC3339 `client_timestamp`, show the exact payload, confirm with the
   developer, and submit to qp-events-collector. Rules, including the wait after
   a quest write and `load_test`, are in
   [`references/events.md`](references/events.md).
7. **Verify.** Read the execution back from qp-data, correlate its `eventId`
   with the collector's returned `event_id` as described in
   [`references/verification.md`](references/verification.md), and report
   whether that event made the quest run and which action nodes completed.
   If an action `FAILED`, report its `error` verbatim. Do not report a reward
   as delivered.

## Safety stops

- Read back and show the resolved scope before the first write, and get
  confirmation. Ask before any call that is not a GET in the flow.
- **Urgency never licenses defaults.** "Skip the questions" or "make it live
  now" does not waive a question. Never pre-fill `type`, `created_by`, the
  trigger's `event_name`, the action, a reward's type, amount and `purpose`,
  `start_date`, `end_date`, activation limits, or `publisher_id` and
  `project_id`. Never merge or waive these confirmations: scope, activation
  (always its own step after the draft exists), each external action, and
  each event.
- No action is side-effect free by default. For a smoke test, offer the no-op
  in [`references/node-subtypes.md`](references/node-subtypes.md) rather than a
  real reward.
- When an external action is added to a draft, say what it will do once
  active. Before activation, show every externally observable action again and
  get explicit confirmation for its impact. An `issue_reward` can create real
  payouts; `send_http_webhook` sends event data to an external URL;
  `send_xsolla_app_notification` sends a user notification. Activate a
  `webshop_personalization` node only after the developer acknowledges that it
  is a no-op, never as a working personalization action.
- If `activation_limits` is absent, ask the developer to explicitly choose
  unlimited repeat behavior and acknowledge that every qualifying event may run
  the action. Do not silently choose a limit or omit this decision. "Whatever
  the default is" is not an acknowledgement.
- Ask for confirmation before submitting an event. Every event needs its own
  payload shown and its own yes, including "send it again" for the same user.
  For a reward quest, say first whether a repeat can pay again.
- After an uncertain event response, such as a timeout, **do not resend** —
  neither with the same idempotency key nor with a new one. A timeout is not a
  failure. Report "result unknown" and stop.
- After a timeout or 5xx on a quest `POST` or `PUT`, the write may have landed.
  Read the quest or the list to check, and ask before sending it again.
- After a `FAILED` reward action, do not resend the event. Fix the quest, then
  send a new event with a new key only after the developer confirms.
- qp-data has no running state; a row appears only once an execution has
  finished. If a Web3 reward's row is still missing after the read policy, or
  its action failed on a timeout, do not send another event. The claim has no
  idempotency key and may already have paid; see
  [`references/rewards.md`](references/rewards.md).
- Read qp-data only by the developer's own quest id, user id or event. Never
  list accounts or read another tenant's quests or executions, even though
  qp-data answers without a credential.
- Never claim a reward was delivered.

## Errors

Branch on the HTTP status only. The API has no stable machine-readable error
codes.

| Status | What to tell the developer |
|---|---|
| 401 | Credential missing or rejected. Read the body with the 401 table in the auth reference; a Basic 401 says nothing about the key. For Basic, name QP-2862. |
| 403 | `Insufficient capability`: the key lacks the capability for that route, `questconfig:*` on quest routes. `Master role required` or `This endpoint requires the user sign-in lane`: the route is off-limits to this lane; do not retry. |
| 404 | "Not found, or not visible with this credential." Never say the quest was deleted or does not exist, and correct the developer if they conclude that. |
| 409 | Conflict. Quest routes do not return it (see Editing in the quest reference); report it verbatim. |
| 422 | Validation failed. Show `detail` verbatim. It never lists allowed enum values; take them from `references/`. |
| 5xx | Server error. Retry a read at most twice, with backoff. An identical repeated 5xx is a bug, not flakiness: report it with its body. For a write, see Safety stops. |

Two body shapes exist. Middleware failures return `{"error": "..."}`. Handler
failures return RFC 7807 `application/problem+json`. On 422 the `errors[]`
array is **not** filled in: per-field messages are flattened into one `detail`
string joined with `"; "`. Other statuses can fill `errors[]`, for example a
500 observed on 2026-09-25. Those `location: message` pairs may be shown to a
human, never parsed for control flow.

`ID 0` is a valid merchant ID and a valid project ID. Never treat it as an
absent value.

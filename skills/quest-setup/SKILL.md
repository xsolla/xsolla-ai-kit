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
  why a quest did not fire. Examples: "create a quest", "add a Web3 reward to
  my quest", "make a quest that pays USDC", "trigger my quest", "send a quest
  event", "why didn't my quest complete", "list my quests", "activate a quest",
  "quest platform API".
metadata:
  owner: r.aliyev
  domain: quests
  status: draft
---

## Status

This skill is a **draft**. On stage the publisher Basic credential works on
the merchant-scoped project routes (rechecked 2026-09-25 after they moved);
production is not checked. Submitting an event with it is currently blocked;
see Flow step 6.

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

**The publisher Basic credential is the lane**: the merchant id plus the
project's API key. It works only on the routes under both the merchant and
the project; build each from
[Project-scoped routes](references/auth-and-environment.md#project-scoped-routes),
not from memory. `{merchant_id}` in a path is always `XSOLLA_MERCHANT_ID`,
never user input or a response value; stage does not reject a wrong one (see
[The merchant id in the path](references/auth-and-environment.md#the-merchant-id-in-the-path)).
If the credential is not set, stop and say which values are missing; do not
search for other credentials.

**Onboarding is a separate, offered step.** It is a write: offer it and ask
first, never call it silently. A 404 `Project not found` does not prove the
project is un-onboarded (see [Onboarding](references/auth-and-environment.md#onboarding)).

The internal service key is for Quest Platform staff only: use it only when
the developer names it, never as a fallback when Basic fails. OpenAPI
discovery needs no credential, so it does not prove CRUD readiness. Say
exactly which lane and which route failed.

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

**A route miss is not a failure of the credential or the project.** A 404
with the plain-text body `Cannot GET <path>` (or `Cannot POST <path>`) means
the router has no such path; the request never reached authentication. The
same rule holds for reads and writes: re-read the live OpenAPI document, tell
the developer what moved, and ask before calling anything on another route
family, even a GET. The live document decides which routes exist; the
developer decides whether to switch. The steps are in
[When a route is missing](references/auth-and-environment.md#when-a-route-is-missing).

If a host is unreachable, which usually means no corporate network, say so and
offer to continue on `references/` alone, noting that the envelope may have
drifted. Never continue silently.

## Reference material

- [`references/auth-and-environment.md`](references/auth-and-environment.md): hosts, credential, project routes, onboarding, scope, reading a 401 or 404
- [`references/quest-document.md`](references/quest-document.md): the quest graph, conditional requirements, full-document PUT
- [`references/node-subtypes.md`](references/node-subtypes.md): the seven accepted node subtypes and their parameters
- [`references/conditions.md`](references/conditions.md): condition grammar: types, operands, operators, event counting
- [`references/rewards.md`](references/rewards.md): the nine reward types and their bodies, including web3_token
- [`references/events.md`](references/events.md): submitting a quest event to qp-events-collector
- [`references/verification.md`](references/verification.md): reading execution results back from qp-data

## Flow

1. **Bring-up.** Fetch the OpenAPI documents. Identify the credential lane
   and run the per-service preflight reads described in
   [`references/auth-and-environment.md`](references/auth-and-environment.md).
   The scope is the project: read it with the project GET from the auth
   reference and show its `project_id`, `name` and `status`, plus the merchant
   id used in the path. That read returns no
   account or workspace id; do not invent one. Get confirmation of the
   project before any write. Bring-up is GET-only; onboarding, if needed, is
   offered after it (see Prerequisites).
2. **Draft.** Create the quest as `inactive` with the four required fields,
   `name`, `type`, `status` and `created_by`; rules are in
   [`references/quest-document.md`](references/quest-document.md). On the
   project route the server stamps `publisher_id` from the path merchant and
   `project_id` from the path project, and ignores body values. Never ask
   for, invent or override them; on a `PUT`, send both back as the last read
   returned them. Show the returned values; the create response's
   `publisher_id` must equal `XSOLLA_MERCHANT_ID`, else stop and report.
3. **Fill in.** Add nodes and their `connections` entries one at a time,
   asking for each missing required value. Ask which action the quest should run.
   Do not offer `scheduled_event` (under Basic its activation is rejected
   with 400, from code) or `crm_send_email`; see
   [`references/node-subtypes.md`](references/node-subtypes.md). Show the assembled
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
   limit, and read the quest back after the write. To pause, send the same
   full `PUT` with `status: inactive`; events while paused are dropped and
   never replayed, and for up to the cache time the quest can still run. See
   the Pausing section of the quest reference.
6. **Event.** Build the payload from the developer's values, never from
   memory or a read-back event body. Generate a fresh UUID `idempotency_key`,
   set an RFC3339 `client_timestamp`, show the exact payload, confirm with the
   developer, and submit to qp-events-collector. Rules, including the wait after
   a quest write and `load_test`, are in
   [`references/events.md`](references/events.md). Omit the `publisher` block,
   or send exactly the quest's `publisher_id` and `project_id` as read back.
   **Currently blocked on Basic.** On 2026-09-25 the collector's project
   event route answered 404 `{"error":"Not Found"}` to a valid Basic
   credential, before reading the body. The cause, inferred from code, is a
   contract mismatch: the collector's credential check omits the merchant id that the
   current qp-server requires. The next collector build is expected to drop
   the Basic event route altogether. Either way, stop, report the status and
   body verbatim, and say the event was not accepted. Do not retry with another
   credential or route: an event sent with a different credential lands in a
   different account and cannot match a quest created on the project route.
7. **Verify.** Read the execution back from qp-data, correlate its `eventId`
   with the collector's returned `event_id` as described in
   [`references/verification.md`](references/verification.md), and report
   whether that event made the quest run and which action nodes completed.
   If an action `FAILED`, report its `error` verbatim. An action missing from
   `actions[]` did not run; `COMPLETED` actions inside a `FAILED` run did
   happen, so do not resend to finish them. Do not report a reward
   as delivered.
8. **Delete.** Only quests the developer names, one per call, after a fresh
   read and an explicit yes. `DELETE` is a soft delete with no restore route;
   follow the Deleting section of the quest reference.

## Safety stops

- Read back and show the resolved scope before the first write, and get
  confirmation. Ask before any call that is not a GET in the flow. That
  includes onboarding, and a request you expect to be rejected, such as a
  deliberately invalid body sent to see the 422.
- Never switch credentials, lanes or routes on your own after a failure.
  Report what failed and ask.
- **Urgency never licenses defaults.** "Skip the questions" or "make it live
  now" does not waive a question. Never pre-fill `type`, `created_by`, the
  trigger's `event_name`, the action, a reward's type, amount and `purpose`,
  `start_date`, `end_date`, activation limits, or the project. Never merge or
  waive these confirmations: scope, activation (always its own step after the
  draft exists), each external action, and each event.
- No action is side-effect free by default. For a smoke test, offer the no-op
  in [`references/node-subtypes.md`](references/node-subtypes.md) rather than a
  real reward.
- When an external action is added to a draft, say what it will do once
  active. Before activation, show every externally observable action again and
  get explicit confirmation for its impact. An `issue_reward` can create real
  payouts; `send_http_webhook` sends event data to an external URL;
  `send_xsolla_app_notification` sends a user notification. Activate a
  `webshop_personalization` node only after the developer acknowledges that it
  is a no-op, never as a working personalization action. For an already active
  quest whose only action is `webshop_personalization`, say it does nothing at
  run time before any edit or event, and that a `COMPLETED` row proves only
  that the quest ran. A `PUT` that keeps it active needs that acknowledgement;
  a pause does not.
- If `activation_limits` is absent, ask the developer to explicitly choose
  unlimited repeat behavior and acknowledge that every qualifying event may run
  the action. Do not silently choose a limit or omit this decision. "Whatever
  the default is" is not an acknowledgement.
- Ask for confirmation before submitting an event. Every event needs its own
  payload shown and its own yes, including "send it again" for the same user.
  For a reward quest, say first whether a repeat can pay again.
- After an uncertain event response, such as a timeout, **do not resend**,
  neither with the same idempotency key nor with a new one. A timeout is not a
  failure. Report "result unknown" and stop.
- After a timeout or 5xx on a quest `POST` or `PUT`, the write may have landed.
  For a `PUT`, read the quest by id and compare it with what you sent. For a
  `POST`, the project list has no name filter: page through it with
  `limit=100` from `page=1` until `page*limit >= total`, looking for the
  quest's `name`. Show what you found and
  ask before sending it again. A 422 is different: validation runs before
  anything is stored, so a rejected body saved nothing.
- After a `FAILED` reward action, do not resend the event. Fix the quest, then
  send a new event with a new key only after the developer confirms.
- qp-data has no running state; a row appears only once an execution has
  finished. If a Web3 reward's row is still missing after the read policy, or
  its action failed on a timeout, do not send another event. The claim has no
  idempotency key and may already have paid; see
  [`references/rewards.md`](references/rewards.md).
- Read qp-data only by the developer's own quest id, user id or event, and
  only after a qp-server read with the developer's credential has shown the
  quest is theirs. Never list accounts or read another tenant's quests or
  executions, even though qp-data answers without a credential.
- Never claim a reward was delivered.

## Errors

Branch on the HTTP status first, then on the body texts listed below. The
API has no stable machine-readable error codes. Quote bodies
verbatim.

| Status | What to tell the developer |
|---|---|
| 400 | `Only one authentication method may be used per request`: more than one credential was sent. Send only the one the developer chose. |
| 401 | `Invalid credentials`: the Basic key was rejected for this project. `Authentication required`: no credential reached the server. `Basic credentials are only accepted on project-scoped routes`: wrong route family, not a bad key. `Invalid API key`: the service key was rejected. `Invalid token`: a Bearer token was rejected; this skill does not send one. Details in Reading a 401 or 404 in the auth reference. Never fall back to another credential. |
| 403 | `Insufficient capability`: the credential lacks the capability for that route. `Service identity is inactive`, `Master role required` or `This endpoint requires the user sign-in lane`: the route or identity is off-limits; do not retry. |
| 404 | `Cannot GET <path>` (plain text, any method): router miss, the route does not exist; not an auth or project answer. Follow the route-miss rule in Source of truth. |
| 404 | `Project not found` on a project route: the project is unknown, not onboarded, belongs to another merchant, or the id is not a number. The server gives the same body for all of them, so do not pick one. Offer onboarding only if the developer says the project is theirs. `Quest not found`: "not found, or not visible with this credential." Never say the quest was deleted or does not exist, and correct the developer if they conclude that. `Not Found` on the project event route: see Flow step 6. |
| 409 | Conflict. Quest routes do not return it (see Editing in the quest reference); report it verbatim. |
| 422 | Validation failed. Show `detail` verbatim. It never lists allowed enum values; take them from `references/`. `invalid integer` at `path.merchant_id`: the path merchant is not a number; rebuild the path from `XSOLLA_MERCHANT_ID`. |
| 5xx | Server error. `Credential validation is temporarily unavailable` (503) means Xsolla could not check the key; it says nothing about the key. Retry a read at most twice, with backoff. An identical repeated 5xx is a bug, not flakiness: report it with its body. For a write, see Safety stops. |

Two body shapes exist. Middleware failures return `{"error": "..."}`. Handler
failures return RFC 7807 `application/problem+json`. On 422 the `errors[]`
array is **not** filled in: per-field messages are flattened into one `detail`
string joined with `"; "`. Other statuses can fill `errors[]`, for example a
500 observed on 2026-09-25. Those `location: message` pairs may be shown to a
human, never parsed for control flow.

`ID 0` is a valid merchant ID and a valid project ID. Never treat it as an
absent value.

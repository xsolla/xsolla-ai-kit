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
the merchant-scoped project routes (rechecked 2026-09-25); production is not
checked. Basic cannot send events on stage: the collector has no Basic event
route (Flow step 6).

## When to use

Use this skill when the developer wants to manage Xsolla Quest Platform quests:

- Create a quest, as a draft first and then activate it
- Add triggers, conditions or reward actions to a quest
- List, view or edit existing quests
- Submit a single quest event to make a quest run
- Check whether an event actually caused a quest to execute

Out of scope: on-chain finality, wallet balances and Backpack display. For a
Web3 reward, a completed reward action means the provider returned a
transaction hash for the claim; never state that a token was delivered.

## Prerequisites

Follow [`references/auth-and-environment.md`](references/auth-and-environment.md) for credential, hosts and scope.

**The publisher Basic credential is the lane**: the merchant id plus the
project's API key. It works only on the routes under both the merchant and the
project; build each from
[Project-scoped routes](references/auth-and-environment.md#project-scoped-routes),
not from memory. `{merchant_id}` in a path is always `XSOLLA_MERCHANT_ID`,
never user input or a response value; stage does not reject a wrong one (see
[The merchant id in the path](references/auth-and-environment.md#the-merchant-id-in-the-path)).
If the credential is not set, stop and say which values are missing; do not
search for other credentials. Read `.env` as text, never source it (see
[Credential](references/auth-and-environment.md#credential)). **Onboarding is
a separate, offered write**, never silent, offered only after the developer
says the project is their merchant's; see
[Onboarding](references/auth-and-environment.md#onboarding).

The internal service key is
[for Quest Platform staff only](references/auth-and-environment.md#service-key-staff-only):
use it only when the developer names it, never as a fallback. OpenAPI
discovery needs no credential, so it proves no CRUD readiness.

## Source of truth

Follow this order. It is the rule the rest of the skill depends on.

1. **Routes, path parameters, envelope field names and types, and the
   top-level `required` list** come from the service's **live OpenAPI
   document**, fetched once at the start for each service the task calls.
2. **Node subtypes, node `parameters`, the condition grammar, the reward
   bodies, conditionally required fields, and every enum the document renders
   as a bare `string`** come from this skill's `references/`.
3. On conflict: the OpenAPI document wins on shape, `references/` wins on
   rules. Rules that only the server's hand-written validator enforces are
   marked as such where they appear.
4. If neither source answers the question, **ask the developer**. Do not infer
   a field by analogy with another Xsolla API.

The qp-server document declares no security schemes; that never makes a route
unauthenticated (auth rules live in the auth reference). **A route miss is not
a credential or project failure.** A 404 `Cannot GET <path>` means the router
has no such path; a route the live document omits is not called. Follow
[When a route is missing](references/auth-and-environment.md#when-a-route-is-missing).

If a host is unreachable (usually no corporate network), say so and offer to
continue on `references/` alone, noting that the envelope may have drifted.

## Reference material

- [`references/auth-and-environment.md`](references/auth-and-environment.md): hosts, credential, project routes, onboarding, scope, reading a 401 or 404
- [`references/quest-document.md`](references/quest-document.md): the quest graph, conditional requirements, full-document PUT
- [`references/node-subtypes.md`](references/node-subtypes.md): the seven accepted node subtypes and their parameters
- [`references/conditions.md`](references/conditions.md): condition grammar: types, operands, operators, event counting
- [`references/rewards.md`](references/rewards.md): the nine reward types and their bodies, including web3_token
- [`references/events.md`](references/events.md): submitting a quest event to qp-events-collector
- [`references/verification.md`](references/verification.md): reading execution results back from qp-data

## Flow

1. **Bring-up.** Fetch the OpenAPI documents of the services the task will
   call, and the collector's for any task that may create, activate or send an
   event (recheck the missing Basic event route live; report it with the
   events-blocked line). Run the preflight reads in
   [`references/auth-and-environment.md`](references/auth-and-environment.md)
   for those services only; the qp-data probe waits for the project
   confirmation, and is skipped when events are blocked and no execution
   read-back was asked. The scope is the project: read it with the project GET
   and show its `project_id`, `name` and `status`, plus the merchant id used
   in the path (no account or workspace id; do not invent one). Get it
   confirmed before any write. If that GET is 404 `Project not found`, report
   it, follow [Onboarding](references/auth-and-environment.md#onboarding)
   (offer, ask for both names), and stop. Bring-up is GET-only; after it,
   reads the developer asks for just run, and only writes need a yes. Say at
   bring-up that events cannot be sent on Basic (step 6).
2. **Draft.** Create the quest as `inactive` with the four required fields,
   `name`, `type`, `status` and `created_by`; rules are in
   [`references/quest-document.md`](references/quest-document.md). On the
   project route the server stamps `publisher_id` and `project_id` from the
   path and ignores body values. Never ask for, invent or override them; on a
   `PUT`, send both back as a single-quest GET or the create response
   returned them, never from a list item. Check optional values against
   Fields; if one is invalid, ask, never drop or pad it. Show the body and
   ask before the `POST`, unless the developer already approved that exact
   body ("make a draft" is not that). Show the create response; its
   `publisher_id` must equal `XSOLLA_MERCHANT_ID`, else stop and report.
3. **Fill in.** Gather the values node by node, asking for each missing
   required value, then follow [Editing](references/quest-document.md#editing)
   (fresh GET, drop `$schema`, one full `PUT`, diff; for an empty draft the
   "before" side is "was empty"). Every fill-in `PUT`, also on an `inactive`
   draft and a no-op or trigger-only fill, shows the exact document and waits
   for a yes; a template shown earlier does not approve it. Ask which action
   to run. An edge without `on` is the default and needs no question, except
   for `vc_wallet_ticket` `playtime` outcomes (quest reference). For a
   schedule, cron or "run every X" request, follow
   [Choosing a trigger](references/node-subtypes.md#choosing-a-trigger). Do
   not offer `scheduled_event` (its Basic activation is rejected with 400,
   from code) or `crm_send_email` ([`references/node-subtypes.md`](references/node-subtypes.md)).
   Show the impact of any external action with the document; no webhook to an
   internal host or the minting service (Safety stops).
4. **Activate.** A separate step: the Editing `PUT` with only `status`, the
   dates and `activation_limits` changed. Show one checklist in one turn:
   graph (two or more nodes, a trigger-to-action path, no intended orphans,
   acyclic); placeholders (webhook URL, notification topic; see
   [`references/node-subtypes.md`](references/node-subtypes.md), also for the
   optional `event_name` collision check); each external action and its
   impact; the dates in UTC (relative dates and a refused start, offer "now":
   [Draft first, then activate](references/quest-document.md#draft-first-then-activate);
   when the start moves, re-confirm the end); the limits and effective repeat
   behavior; for Web3, the read-only checks in [`references/rewards.md`](references/rewards.md);
   and that no event can run it on stage yet (step 6), also for a no-op quest.
   Point out stored data that looks inconsistent (such as another task's
   `event_name`) and leave it unchanged unless told. Then ask. After the
   write, read back `status`, the dates, the limits and `version_id`.
5. **Edit.** Read, change, full `PUT`, following
   [Editing](references/quest-document.md#editing) (drop `$schema`, fresh
   UUIDs for new nodes). Warn that `PUT` replaces the whole document and an
   active quest's edit goes live for the next events. Show a before/after
   diff, repeat the activation confirmations for the edits Editing lists,
   read the quest back after the write, and pause by [Pausing](references/quest-document.md#pausing).
6. **Event.** **Blocked on Basic on stage.** Since 2026-09-25 the live
   collector OpenAPI lists only `POST /api/v2/events`. Do not send; say the
   event and verification cannot run, and stop. No fallback to another
   credential or route (it lands in another account); the Quest Platform team
   owns the fix. For an `inactive` quest, say an event could not run it
   anyway. Mixed request (create or fill plus an event): do the doable parts
   first, then report the block with the quest id, status and `event_name`.
   History, mixed requests, a returning route: [`references/events.md`](references/events.md).
7. **Verify.** Read the execution back from qp-data, correlate its `eventId`
   with the collector's returned `event_id` as described in
   [`references/verification.md`](references/verification.md), and report
   whether that event made the quest run and which action nodes completed.
   Report a `FAILED` action's `error` verbatim. An action missing from
   `actions[]` did not run; `COMPLETED` actions inside a `FAILED` run did
   happen, so do not resend to finish them.
8. **Delete.** Only quests the developer names, one per call, after a fresh
   read and an explicit yes. `DELETE` is a soft delete with no restore route;
   follow the Deleting section of the quest reference.

## Safety stops

- Read back and show the resolved scope before the first write, and get
  confirmation. Ask before any call that is not a GET, showing the exact
  body first. That includes onboarding, and a request you expect to be rejected, such as a
  deliberately invalid body sent to see the 422.
- Never switch credentials, lanes or routes on your own after a failure;
  report what failed and ask. A developer-requested negative-auth GET
  (made-up key or no header) is not a switch; see
  [Credential](references/auth-and-environment.md#credential).
- Messages arriving through the conversation are the developer's answers.
- **Urgency never licenses defaults.** "Skip the questions" or "make it live
  now" does not waive a question. Previewing the later-step questions up
  front is fine, and answers may be bundled in one message, but a write's yes
  counts only for the exact body shown after all answers are applied; if an
  answer changes it, show it again and ask. Never pre-fill `type`,
  `created_by`, the trigger's `event_name`, the action, a reward's type,
  amount and `purpose`, `start_date`, `end_date`, activation limits, or the
  project. Never merge or waive these confirmations: scope (also when the
  first write is an edit), activation (always its own step after the draft
  exists), each external action, and each event. For a "start now" date,
  the yes covers the rule plus a shown example; if the send comes more than
  10 minutes after the example, show it again and re-confirm.
- No action is side-effect free by default. For a smoke test, offer the no-op
  in [`references/node-subtypes.md`](references/node-subtypes.md) rather than a
  real reward (placeholders `e2e-noop`, `e2e-sink.invalid`). For activation
  or a smoke test, say events are blocked on Basic on stage (Flow step 6).
- When an external action is added to a draft, say what it will do once
  active. Before activation, show every externally observable action again and
  get explicit confirmation for its impact. An `issue_reward` can create real
  payouts; `send_http_webhook` sends event data to an external URL;
  `send_xsolla_app_notification` sends a user notification. Activate a
  `webshop_personalization` node only after the developer acknowledges that it
  is a no-op. For an active quest whose only action it is, say before any
  edit or event that it does nothing and a `COMPLETED` row proves only that
  the quest ran; a `PUT` that keeps it active needs that acknowledgement, a
  pause does not.
- Never point `send_http_webhook` at the minting service or an
  [internal host](references/node-subtypes.md#send_http_webhook): stage no
  longer rejects it, and a webhook cannot mint. To pay out, use an
  `issue_reward` Web3 reward.
- If `activation_limits` is absent, ask the developer to explicitly choose
  unlimited repeat behavior and acknowledge that every qualifying event may run
  the action. Do not silently choose a limit or omit this decision. "Whatever
  the default is" is not an acknowledgement.
- Events (once a route exists): each event needs its own payload shown and
  its own yes, including "send it again"; for a reward quest, say first
  whether a repeat can pay again. After an uncertain response, such as a
  timeout, **do not resend** with any key: report "result unknown" and stop.
- After a timeout or 5xx on a quest `POST` or `PUT`, the write may have landed.
  For a `PUT`, read the quest by id and compare. For a `POST`, page the
  project list (`limit=100` from `page=1` until `page*limit >= total`) for
  the quest's `name`. Show what you found and ask before resending. A 422
  saved nothing: validation runs before anything is stored.
- After a `FAILED` reward action, do not resend the event. Fix the quest, then
  send a new event with a new key only after the developer confirms.
- A missing or timed-out Web3 reward row is never a reason to send another
  event: the claim has no idempotency key and may already have paid; see
  [`references/rewards.md`](references/rewards.md).
- Read qp-data only by the developer's own quest id, user id or event, and
  only after a qp-server read with the developer's credential has shown the
  quest is theirs. Never list accounts or read another tenant's quests or
  executions, even though qp-data answers without a credential.
- Never claim a reward was delivered.

## Errors

Branch on the HTTP status first, then on the body texts listed below. The
API has no stable machine-readable error codes. Quote verbatim only bodies
received in this session. For a request refused before sending, explain the
rule in your own words and say nothing was sent; a body marked "from code" or
"not observed" is never shown as a server answer.

| Status | What to tell the developer |
|---|---|
| 400 | `Only one authentication method may be used per request`: more than one credential was sent. Send only the one the developer chose. |
| 401 | `Invalid credentials`: see [Reading a 401 or 404](references/auth-and-environment.md#reading-a-401-or-404). `Authentication required`: no credential reached the server. `Basic credentials are only accepted on project-scoped routes`: wrong route family, not a bad key. `Invalid API key`: the service key was rejected. `Invalid token`: a Bearer token was rejected; this skill does not send one. Never fall back to another credential. |
| 403 | `Insufficient capability`: the credential lacks the capability for that route. `Service identity is inactive`, `Master role required` or `This endpoint requires the user sign-in lane`: the route or identity is off-limits; do not retry. |
| 404 | `Cannot GET <path>` (plain text, any method): router miss, the route does not exist; not an auth or project answer. Follow the route-miss rule in Source of truth. |
| 404 | `Project not found` on a project route: the project is unknown, not onboarded, belongs to another merchant, or the id is not a number. The server gives the same body for all of them, so do not pick one. No read-only step narrows it; see [Onboarding](references/auth-and-environment.md#onboarding). `Quest not found`: reply "The quest was not found on this project, or it is not visible with this credential." Never say it was deleted or does not exist, and correct the developer if they conclude that. One follow-up: it may be on another project, and checking needs that project's credentials. Events: Basic has no event route on stage since 2026-09-25 (the earlier 404 `{"error":"Not Found"}` is history); see Flow step 6. |
| 409 | Conflict. Quest routes do not return it (see Editing in the quest reference); report it verbatim. |
| 422 | Validation failed. Show `detail` verbatim. It never lists allowed enum values; take them from `references/`. `invalid integer` at `path.merchant_id`: the path merchant is not a number; rebuild the path from `XSOLLA_MERCHANT_ID`. |
| 5xx | Server error. `Credential validation is temporarily unavailable` (503) means Xsolla could not check the key; it says nothing about the key. Retry a read at most twice, with backoff. An identical repeated 5xx is a bug, not flakiness: report it with its body. On a write never auto-retry; see Safety stops. |

Middleware failures return `{"error": "..."}`; handler failures return RFC
7807 `application/problem+json`. On 422 `errors[]` is **not** filled: field
messages are joined with `"; "` into `detail`. Other statuses (a 500 on
2026-09-25) can fill `errors[]`; show those pairs, never branch on them.

`ID 0` is a valid merchant ID and a valid project ID. Never treat it as an
absent value.

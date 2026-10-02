---
name: quest-setup
description: >-
  Creates, inspects and edits production Xsolla Quest Platform quests conversationally,
  submits a quest event, and verifies that the event actually made the quest
  execute. Covers the whole quest document: the node graph and its connections,
  the seven node subtypes, the condition grammar, activation limits, and the
  Web3 reward types `web3_item` and `web3_token` (token payouts are disabled
  in production). Use when
  setting up a quest, adding a trigger or a condition, attaching a reward,
  editing or activating an existing quest, firing a test event, or working out
  why a quest did not fire. Examples: "create a quest", "add a Web3 reward to
  my quest", "make a quest that pays a token", "trigger my quest", "send a quest
  event", "why didn't my quest complete", "list my quests", "activate a quest",
  "quest platform API". Also adds an optional quest section inside a headless
  Web Shop when asked. Use for
  "show quests in my web shop" or "add a quest module to my shop".
metadata:
  owner: r.aliyev
  domain: quests
  status: draft
---

## Status

This skill targets **production** by default. Resolve Quest Platform scope and
the Web3 catalog from the configured integration. Quest Platform services use
stage only when `XSOLLA_QP_ENV=stage` is set explicitly (see
[auth and environment](references/auth-and-environment.md)); never fall back to
staging credentials, staging services or a staging Publisher Account catalog
from a production run. Event submission and execution read-back still need the
versioned contract and preflight before use.

## Hard rules (read first)

1. **The request is never the approval.** Your first reply to a create or edit
   request is the proposal. Send no `POST`, `PUT` or `DELETE` in that turn,
   even when the request says "now" or "go ahead". Write only after a later
   publisher message approves that exact proposal.
2. **An event needs its own later yes** to the exact payload you showed.
   Publication approval never covers an event, and a message that approves
   publishing (for example a repeated "yes, publish it") is not event consent:
   answer that the quest is already published and show the payload again.
3. **One target.** Quest configuration and events use only the gateway that
   `XSOLLA_QP_ENV` maps to in
   [`qp-api-contract.md`](references/qp-api-contract.md). Never call the other
   gateway, even after a failure, and never suggest changing `XSOLLA_QP_ENV`
   or switching environments. `XSOLLA_QP_PUBLIC_BASE_URL` is a shop
   setting; the agent never sends requests to it. Resolve the selector before
   any network call; its value is not a secret. Run `printenv XSOLLA_QP_ENV`;
   only if that prints nothing, read just the `XSOLLA_QP_ENV=` line of `.env`.
   STAGE DEMO
   ONLY (QP-2890): if it is `stage`, read
   [`stage-demo.md`](references/stage-demo.md) now and follow its turn plan
   and reply skeletons word for word.
4. **No secrets on screen.** Never open `.env` in a viewer, print the
   environment, or paste a key into a command. Never print the API key, even
   to yourself (no `KEY=` debug lines); it only ever flows into curl through
   the `-K -` pattern in
   [Credential](references/auth-and-environment.md#credential). To see which settings exist,
   list only the names left of `=`, for example
   `python3 -c 'import pathlib; print([l.split("=")[0].strip() for l in pathlib.Path(".env").read_text().splitlines() if "=" in l])'`.
   If the three credential names are there,
   the project is set up: continue with the read-only preflight and never ask
   the publisher to confirm settings. See
   [Credential](references/auth-and-environment.md#credential).
5. **No IDs or hosts in replies.** Outside the Web Shop URL and the event
   payload, never show merchant, project or player IDs, hosts, service names
   or environment names to the publisher. Every reply starts with a `##` heading: no lead-in line such as
   "Perfect!" or a recap before it.
6. **Never claim delivery.** Report what the read-backs show, nothing more.
7. **Stop points.** End the turn and wait for the publisher: after the
   proposal; after publication read-back (offer the event there, never send
   it); after the event read-back. Never pass a stop point in the same turn.
8. **One create.** A `POST` that returned 200 created the quest. Take its `id`
   from that response; if you lost it, find it by name in the list. Never
   `POST` again for the same proposal.
9. **Never ask for a SKU or catalog project.** A typed value is not a
   verified item. For production Web3 items, use the read-only minting
   catalog lookup in
   [Named item behavior](references/rewards.md#named-item-behavior). If the
   lookup service is unavailable, say so without implying the publisher's
   catalog is disconnected. If a completed lookup finds no match, report that
   result and suggest checking the item name or whether it is enabled.

## When to use

Use this skill when the developer wants to manage Xsolla Quest Platform quests:

- Create and publish a quest after one approval of the exact proposal
- Add triggers, conditions or reward actions to a quest
- List, view or edit existing quests
- Submit a single quest event to make a quest run
- Check whether an event actually caused a quest to execute
- Add or update an optional quest section inside a headless Web Shop catalog

Out of scope: on-chain finality, wallet balances and Backpack display. A
completed reward action is not proof of delivery.

## Prerequisites

Follow [`references/auth-and-environment.md`](references/auth-and-environment.md) for the production credential and scope.

**The configured production publisher credential is the lane**. It works only
on the project-scoped routes in
[`references/qp-api-contract.md`](references/qp-api-contract.md); build each
route from
[Project-scoped routes](references/auth-and-environment.md#project-scoped-routes),
not from memory. Merchant and project path values must come from the same
resolved production scope, never user input or an unrelated response value (see
[The merchant id in the path](references/auth-and-environment.md#the-merchant-id-in-the-path)).
Resolve only the complete production credential source described in
[Credential](references/auth-and-environment.md#credential). Never display
`.env` or paste a key into a command; parse it inside the command that sends
the request. Never fall back
to a staging configuration, ask the publisher to paste secrets or search for
another key. If no production credential is available, report only that the
project is not set up for quests yet and stop. Keep service names and
environment names out of user-facing replies. **Onboarding is a separate,
offered write**, never silent, offered only after the developer says the
project is their merchant's; see
[Onboarding](references/auth-and-environment.md#onboarding).

Internal service keys are [staff-only](references/auth-and-environment.md#service-key-staff-only)
and are never a fallback. Fetching OpenAPI needs no credential and proves no
CRUD readiness.

## Source of truth

Follow this order.

1. **Quest Platform routes** (configuration, event ingestion, execution
   read-back), path parameters, envelope names/types, and top-level `required`
   come from [`references/qp-api-contract.md`](references/qp-api-contract.md),
   verified by its read-only/probe notes. Consult the selected target's OpenAPI
   only when that target publishes it (stage when `XSOLLA_QP_ENV=stage`). On a
   production run, never fetch stage OpenAPI or any non-selected target.
2. **Node subtypes, parameters, condition grammar, reward bodies, conditional
   fields, and bare-string enums** come from this skill's `references/`.
3. On conflict: the versioned contract (or selected published OpenAPI) wins on
   shape; `references/` wins on rules. Hand-written validator rules are marked
   where they appear.
4. If neither source answers, **ask the developer**. Do not infer by analogy.

Auth rules live in the auth reference even when OpenAPI omits schemes. **A
route miss is not a credential or project failure.** A 404 `Cannot GET <path>`
means the router has no such path; a route the contract omits is not called.
Follow [When a route is missing](references/auth-and-environment.md#when-a-route-is-missing).
If the production integration is unreachable, say so and offer references-only,
noting the envelope may have drifted.

## Reference material

- [`references/auth-and-environment.md`](references/auth-and-environment.md): credential, routes, onboarding, 401/404
- [`references/qp-api-contract.md`](references/qp-api-contract.md): versioned Quest Platform routes and probes
- [`references/quest-document.md`](references/quest-document.md): quest graph, conditional requirements, full-document PUT
- [`references/node-subtypes.md`](references/node-subtypes.md): seven node subtypes and parameters
- [`references/conditions.md`](references/conditions.md): condition grammar
- [`references/rewards.md`](references/rewards.md): production Web3 reward bodies
- [`references/events.md`](references/events.md): event submission gate
- [`references/verification.md`](references/verification.md): execution read-back gate
- [`references/stage-demo.md`](references/stage-demo.md): **STAGE DEMO ONLY** rules, gated on `XSOLLA_QP_ENV=stage` plus the demo scope
- [`references/web-shop-module.md`](references/web-shop-module.md): optional headless Web Shop catalog module, only when explicitly requested

## Conversation contract

Keep the publisher experience business-first and progressive:

- Finish all read-only bring-up before any proposal: project GET, reward
  resolution through an available supported capability (see
  [`references/rewards.md`](references/rewards.md)), the player action,
  complete graph, proposed schedule and repeat limits. Do not seek plan
  approval before those GETs.
- Show one concise proposal: publisher project name; what the player does; the
  selected reward in business terms; quantity or amount; schedule; repeat limit
  and payout impact. Omit service names, routes, auth, implementation fields
  and narration. Ask only for approval of this draft quest. If the publisher
  wants a change, they will say so; do not request separate confirmation of
  the schedule or event name.
- Propose safe defaults instead of asking for implementation fields. For a
  gameplay quest, use `liveops` internally but describe it as a gameplay quest.
  Do not show `type` in the proposal. For an item reward, propose quantity one,
  purpose `quest_completion`, and one payout per player. Use `AI Toolkit` as
  the internal creator label unless another name was supplied. For a new quest,
  use any start, end or duration the publisher supplied; otherwise start at
  activation and end 7 days after the selected start. Do not ask for missing
  dates.
- For a named item (`<requested item>`), resolve via
  [`references/rewards.md`](references/rewards.md). Never guess an SKU,
  substitute a reward type, or use public web search for catalog lookup. Stop
  before any Quest Platform write when the resolver is absent, unavailable, or
  returns zero candidates; ask the publisher to choose when multiple candidates
  are plausible. **STAGE DEMO ONLY:** when the
  [stage demo gate](references/stage-demo.md#gate) passes, that file supplies
  the resolver and execution read-back; otherwise ignore it. The optional
  headless Web Shop module is independent of that gate; follow
  [`references/web-shop-module.md`](references/web-shop-module.md) only when
  explicitly requested.
- Use the event name the publisher supplied, or derive a stable `snake_case`
  name from the stated player action (for example, `monster_defeated`). Show
  that name in the draft without asking the publisher to confirm it or flagging
  it as an open question. If the publisher names a different game event later,
  revise the draft then.
- One approval of the exact proposal authorizes create, configure, activate and
  read-back. Test events and shop source edits need separate consent. The
  approval request names only publication; never offer, promise or bundle a
  test event in it. Offer the event after publication, with its payload. If an
  answer requests a material change after approval, show the revised draft
  and ask for approval of that change before writing it.
- A Web Shop quest section is optional and requires an explicit request. For
  an existing headless shop, an explicit request to add or update it authorizes
  those source edits; quest publication approval alone does not. For a new shop,
  ask whether to opt in. Keep the module inside catalog content, never in
  navigation, and follow [`references/web-shop-module.md`](references/web-shop-module.md).
  Resolve the public URL from the known production host and the connected
  project scope; never ask the developer to supply it or gate integration on a
  live endpoint readiness check.
- Keep merchant IDs, project IDs, auth lanes, headers, hostnames, service names,
  internal paths and workflow narration out of normal replies. Never reveal
  credentials. Use **Summary**, **Proposed setup**, **Need from you**,
  **Next step** when practical; omit empty sections.

## Agent test

**Prompt:** `Create a quest that rewards one <requested item> after the player completes the stated action`
**Result:** After read-only checks, one concise proposal, one approval for create through activate; stop if the reward is not uniquely verified.

## Flow

1. **Bring-up.** Load
   [`references/qp-api-contract.md`](references/qp-api-contract.md) for Quest
   Platform routes. Consult published OpenAPI only when the selected target
   exposes it (`XSOLLA_QP_ENV=stage`); never fetch stage or another target on a
   production run. Run the preflight reads in
   [`references/auth-and-environment.md`](references/auth-and-environment.md)
   for the services the task needs; skip execution read-back when not asked.
   Confirm project scope before a write; report a short project name/status
   summary only. Keep IDs, auth details and route diagnostics out of normal
   replies. If that GET is 404 `Project not found`, follow
   [Onboarding](references/auth-and-environment.md#onboarding) and stop.
   Bring-up is GET-only. If event work is asked and the contract marks the
   route unavailable to the publisher key, report that blocker at the event
   step.
2. **Resolve and propose.** Complete remaining read-only work before asking:
   reward resolution ([`references/rewards.md`](references/rewards.md)), player
   action, complete graph, proposed schedule and repeat limits. Construct
   the full document per
   [`references/quest-document.md`](references/quest-document.md). On the
   project route the server stamps `publisher_id` and `project_id` from the
   path; never ask for, invent or override them. Show the one concise proposal
   from the Conversation contract. Stop before any Quest Platform write when
   the reward cannot be verified uniquely.
3. **Publish.** After one approval of that exact proposal, follow
   [Publication after approval](references/quest-document.md#publication-after-approval):
   POST a complete inactive quest, GET it back, PUT active with the approved
   dates and limits (no second approval), GET active status, scope, reward,
   dates, limits and `version_id`. Never report publication complete until that
   read-back matches. On uncertain create or update outcomes, reconcile per
   [Ambiguous or partial writes](references/quest-document.md#ambiguous-or-partial-writes)
   before any retry; never create a duplicate on timeout. **STAGE DEMO ONLY:**
   under the [stage demo gate](references/stage-demo.md#gate), also list the
   quests and do the [Web Shop handoff](references/stage-demo.md#web-shop-handoff)
   under the same approval. For a schedule, cron
   or "run every X" request, follow
   [Choosing a trigger](references/node-subtypes.md#choosing-a-trigger). Do
   not offer unconfirmed optional subtypes such as `scheduled_event` or
   `crm_send_email` ([`references/node-subtypes.md`](references/node-subtypes.md)).
4. **Edit.** Read, change, full `PUT`, following
   [Editing](references/quest-document.md#editing) (drop `$schema`, fresh
   UUIDs for new nodes). Warn that `PUT` replaces the whole document and an
   active quest's edit goes live for the next events. Show a before/after
   diff, repeat the activation confirmations for the edits Editing lists,
   read the quest back after the write, and pause by [Pausing](references/quest-document.md#pausing).
5. **Event.** Production event submission is allowed only after the event
   gate in [`references/events.md`](references/events.md) confirms the
   versioned contract route and publisher Basic lane. Until then, do not send
   an event; say event execution is not yet verified. Never fall back to
   staging, an internal key or a different route. For an `inactive` quest, say
   an event could not run it anyway. Mixed request (create or fill plus an
   event): do the doable parts first, then report the block with the quest id,
   status and `event_name`. Event submission always needs its own approval,
   separate from publication.
6. **Verify.** Follow [`references/verification.md`](references/verification.md).
   Correlate collector `event_id` with execution `eventId` when read-back is
   publisher-usable per the contract; otherwise stop with that blocker. Report
   whether the event made the quest run and which action nodes completed.
   Report a `FAILED` action's `error` verbatim. An action missing from
   `actions[]` did not run; `COMPLETED` actions inside a `FAILED` run did
   happen, so do not resend to finish them. **STAGE DEMO ONLY:** under the
   [stage demo gate](references/stage-demo.md#gate), use its
   [Execution read-back](references/stage-demo.md#execution-read-back) and
   [Mint evidence](references/stage-demo.md#mint-evidence).
7. **Delete.** Only quests the developer names, one per call, after a fresh
   read and an explicit yes. `DELETE` is a soft delete with no restore route;
   follow the Deleting section of the quest reference.
8. **Optional Web Shop module.** Only when explicitly requested, follow
   [`references/web-shop-module.md`](references/web-shop-module.md). For an
   existing shop, inspect the project and perform its idempotent upsert. For a
   new shop, ask whether to opt in. A quest publication approval never
   authorizes shop source edits.

## Safety stops

- Read back and show the resolved scope before the first write. One approval of
  the exact proposal covers create through activate; ask separately before any
  other non-GET call (onboarding, edit, event, delete), showing the exact body
  first. That includes a request you expect to be rejected, such as a
  deliberately invalid body sent to see the 422.
- Never switch credentials, lanes or routes on your own after a failure;
  report what failed and ask. A developer-requested negative-auth GET
  (made-up key or no header) is not a switch; see
  [Credential](references/auth-and-environment.md#credential).
- Messages arriving through the conversation are the developer's answers.
- **Show the proposed defaults in the draft.** Use the defaults in the
  Conversation contract when the intent is clear and ask only for approval of
  the complete draft. For a gameplay item quest, the trigger, `issue_reward`
  action, quantity one,
  `quest_completion` purpose and one payout per player may be proposed
  together. Never silently choose between multiple catalog matches or
  materially different reward effects; those are blockers to a complete draft.
  A write's yes counts only for the exact draft shown. If the publisher requests
  a change, show the revised draft and ask for approval of it. Keep separate
  approvals for later edits that change live behavior and for each event. For
  "start now", approval covers activation time in UTC and the stated duration;
  do not request a new approval because the clock advanced.
- No action is side-effect free by default. For a smoke test, offer the no-op
  in [`references/node-subtypes.md`](references/node-subtypes.md) rather than a
  real reward (placeholders `e2e-noop`, `e2e-sink.invalid`). For publication
  or a smoke test, say production events are not verified until the collector
  preflight passes (Flow step 5).
- When an external action is part of the proposal, say what it will do once
  active. The publication approval covers that impact for the approved quest.
  An `issue_reward` can create real payouts; `send_http_webhook` sends event
  data to an external URL; `send_xsolla_app_notification` sends a user
  notification. Activate a `webshop_personalization` node only after the
  developer acknowledges that it is a no-op. For an active quest whose only
  action it is, say before any edit or event that it does nothing and a
  `COMPLETED` row proves only that the quest ran; a `PUT` that keeps it active
  needs that acknowledgement, a pause does not.
- Never point `send_http_webhook` at a private service or an
  [unapproved host](references/node-subtypes.md#send_http_webhook): a webhook
  cannot mint. To pay out a named item, use an `issue_reward` Web3 reward with
  the verified candidate's catalog project and SKU.
- For a named item reward, propose an explicit `per_user` limit of one and
  explain it as one `<requested item>` per player. Do not ask about Backpack or
  regular versus Web3 delivery. Ask only if the developer asks for repeatable
  or unlimited rewards, or if the intended repeat behavior is otherwise
  ambiguous. For other rewards with no `activation_limits`, show unlimited
  repeat in the publication proposal; the one approval covers it. Do not
  silently choose unlimited behavior.
- Events (once a route exists): each event needs its own payload shown and
  its own yes, including "send it again"; for a reward quest, say first
  whether a repeat can pay again. After an uncertain response, such as a
  timeout, **do not resend** with any key: report "result unknown" and stop.
- After a timeout or 5xx on a quest `POST` or `PUT`, reconcile before retry per
  [Ambiguous or partial writes](references/quest-document.md#ambiguous-or-partial-writes).
  A 422 saved nothing: validation runs before anything is stored.
- After a `FAILED` reward action, do not resend the event. Fix the quest, then
  send a new event with a new key only after the developer confirms.
- A missing or timed-out Web3 reward row is never a reason to send another
  event: the reward may already have paid; see
  [`references/rewards.md`](references/rewards.md).
- Read the execution service only by the developer's own quest id, user id or
  event, and only after a qp-server read with the developer's credential has
  shown the quest is theirs. Never list accounts or read another tenant's
  quests or executions. If the contract marks read-back unavailable to the
  publisher key, stop; never use an internal key. **STAGE DEMO ONLY:** the
  [stage demo gate](references/stage-demo.md#gate) allows its unauthenticated
  read-back for the developer's own quest; no key is ever sent.
- Never claim a reward was delivered.

## Errors

Branch on the HTTP status first, then on the body texts listed below. The
API has no stable machine-readable error codes. Quote verbatim only bodies
received in this session. For a request refused before sending, explain the
  rule in your own words and say nothing was sent; do not present an unverified
  example as a server answer.

| Status | What to tell the developer |
|---|---|
| 400 | `Only one authentication method may be used per request`: more than one credential was sent. Send only the one the developer chose. |
| 401 | `Invalid credentials`: see [Reading a 401 or 404](references/auth-and-environment.md#reading-a-401-or-404). Never fall back to another credential or environment. |
| 403 | `Insufficient capability`: the credential lacks the capability for that route. `Service identity is inactive`, `Master role required` or `This endpoint requires the user sign-in lane`: the route or identity is off-limits; do not retry. |
| 404 | `Cannot GET <path>` (plain text, any method): router miss, the route does not exist; not an auth or project answer. Follow the route-miss rule in Source of truth. |
| 404 | `Project not found` on a project route: the project is unknown, not onboarded, belongs to another merchant, or the id is not a number. The server gives the same body for all of them, so do not pick one. No read-only step narrows it; see [Onboarding](references/auth-and-environment.md#onboarding). `Quest not found`: reply "The quest was not found on this project, or it is not visible with this credential." Never say it was deleted or does not exist, and correct the developer if they conclude that. One follow-up: it may be on another project, and checking needs that project's credentials. For events, follow the event gate in Flow step 5. |
| 409 | Conflict. Quest routes do not return it (see Editing in the quest reference); report it verbatim. |
| 422 | Validation failed. Show `detail` verbatim. It never lists allowed enum values; take them from `references/`. |
| 5xx | Server error. `Credential validation is temporarily unavailable` (503) means Xsolla could not check the key; it says nothing about the key. Retry a read at most twice, with backoff. An identical repeated 5xx is a bug, not flakiness: report it with its body. On a write never auto-retry; see Safety stops. |

Middleware failures return `{"error": "..."}`; handler failures return RFC
7807 `application/problem+json`. On 422 `errors[]` is **not** filled: field
messages are joined with `"; "` into `detail`. Other statuses (a 500 on
2026-09-25) can fill `errors[]`; show those pairs, never branch on them.

`ID 0` is a valid merchant ID and a valid project ID. Never treat it as absent.

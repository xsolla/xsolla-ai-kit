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
  Web Shop when asked, and manages the Quests block in a Shop Builder test site
  (create, edit settings, reset media, reorder, limit, move, duplicate,
  hide or show, delete; never published). Use for "show quests in my web
  shop", "add a quest module to my shop", "add the Quests block to my Shop
  Builder site", "change the quests in my block" or "remove the Quests block".
metadata:
  owner: r.aliyev
  domain: quests
---

## Hard rules (read first)

1. **The request is never the approval.** Your first reply to a create or edit
   request is the proposal. Send no `POST`, `PUT` or `DELETE` in that turn,
   even when the request says "now" or "go ahead". Write only after a later
   publisher message approves that exact proposal.
2. **An event needs its own later yes** to the exact payload you showed.
   Publication approval never covers an event, and a repeated "yes, publish it"
   is not event consent: answer that the quest is already published and show the
   payload again.
3. **One target.** Quest configuration and events use only
   `https://quests-platform.xsolla.com`, as in
   [`qp-api-contract.md`](references/qp-api-contract.md). Never call another
   gateway, even after a failure, and never suggest switching environments.
   `XSOLLA_QP_PUBLIC_BASE_URL` is a shop setting; never send requests to it.
4. **No secrets on screen.** Never open `.env` in a viewer, print the
   environment, paste a key into a command, or print the API key, even to
   yourself. Parse credentials as text inside the request, as in
   [Credential](references/auth-and-environment.md#credential). If the three
   credential names exist, the project is set up: continue with the read-only
   preflight and never ask the publisher to confirm settings, paste secrets or
   search for another key.
5. **No IDs or hosts in replies.** Outside the Web Shop URL and the event
   payload, never show merchant, project or player IDs, hosts, service names
   or environment names to the publisher (a reward item's SKU and image URL
   are fine). Every reply starts with a `##` heading: no lead-in line such as
   "Perfect!" or a recap before it.
6. **Never claim delivery.** Report what the read-backs show, nothing more.
7. **Stop points.** End the turn and wait for the publisher: after the
   proposal; after publication read-back (offer the event there, never send
   it); after the event read-back. Never pass a stop point in the same turn.
8. **One create, inactive first.** Create the quest inactive, read it back,
   then activate. A `POST` that returned 200 created it; take the `id` from that
   response (or find it by name in the list). Never `POST` again for the same
   proposal.
9. **Stop on auth failures.** Never switch credentials, lanes or routes on your
   own after a failure; report what failed and ask. For a 401 or 404 follow
   [Reading a 401 or 404](references/auth-and-environment.md#reading-a-401-or-404).
10. **Never ask for a SKU or catalog project.** A typed value is not a
    verified item. Use the read-only Store admin catalog lookup in
    [Named item behavior](references/rewards.md#named-item-behavior). If the
    lookup is unavailable, say so without implying the catalog is disconnected;
    if it finds no match, report that and stop before any write.

## When to use

Use this skill when the developer wants to manage Xsolla Quest Platform quests:

- Create and publish a quest after one approval; add triggers, conditions or
  reward actions; list, view or edit quests
- Submit a single quest event, and check that it made the quest execute
- Add or update an optional quest section inside a headless Web Shop catalog
- Manage the Quests block on an unpublished Shop Builder test site: create,
  edit settings, reset media, reorder, limit, move, duplicate, hide or show,
  delete

Out of scope: on-chain finality, wallet balances, Backpack display, publishing a
Shop Builder site. A completed reward action is not proof of delivery.

## Prerequisites

The configured production publisher credential is the only lane for quest
endpoints (Shop Builder writes are separate: an approved test project, see
[`shop-builder-quests-block.md`](references/shop-builder-quests-block.md)), on
the project-scoped routes in [`qp-api-contract.md`](references/qp-api-contract.md).
Resolve scope and the Web3 catalog from the configured integration; never fall
back to another target, credential source or catalog. Credential and onboarding:
[Prerequisites and lane](references/auth-and-environment.md#prerequisites-and-lane).
With no production credential, report only that the project is not set up for
quests yet and stop. Events and execution read-back still need the versioned
contract and preflight.

## Reference routing

Routes and envelopes come from the contract
([Source of truth](references/qp-api-contract.md#source-of-truth)); node
subtypes, conditions and reward bodies come from the other references. If
neither answers, ask the developer.

| Topic | Reference |
|---|---|
| Credential, routes, onboarding, 401/404, error statuses, write and credential stops | [`auth-and-environment.md`](references/auth-and-environment.md) |
| Quest Platform routes, probes, source of truth | [`qp-api-contract.md`](references/qp-api-contract.md) |
| Quest graph, publication, editing, pausing, deleting, proposal defaults, conversation contract | [`quest-document.md`](references/quest-document.md) |
| Seven node subtypes and parameters, choosing a trigger | [`node-subtypes.md`](references/node-subtypes.md) |
| Condition grammar | [`conditions.md`](references/conditions.md) |
| Production Web3 reward bodies, named items | [`rewards.md`](references/rewards.md) |
| Event gate, payload, event stops | [`events.md`](references/events.md) |
| Execution read-back, read scope | [`verification.md`](references/verification.md) |
| Optional headless Web Shop module, only when explicitly requested | [`web-shop-module.md`](references/web-shop-module.md) |
| Quests block operations in a Shop Builder site, only when explicitly requested | [`shop-builder-quests-block.md`](references/shop-builder-quests-block.md) |

## Conversation contract (summary)

Full rules: [Conversation contract](references/quest-document.md#conversation-contract)
and [Safety stops for proposals and actions](references/quest-document.md#safety-stops-for-proposals-and-actions).

- Finish all read-only bring-up first, then show one concise, business-first
  proposal: project name, player action, reward, quantity, schedule, repeat
  limit and payout impact. No service names, routes or auth. Propose safe
  defaults; do not ask for missing dates.
- One approval of the exact proposal covers create, configure, activate and
  read-back. Test events and shop source edits need separate consent.
- Resolve a named item reward via [`rewards.md`](references/rewards.md); never
  guess an SKU or substitute a reward type.

## Flow

1. **Bring-up.** Load [`qp-api-contract.md`](references/qp-api-contract.md) and
   run the preflight reads in
   [`auth-and-environment.md`](references/auth-and-environment.md#service-preflight).
   Bring-up is GET-only. Never fetch OpenAPI or another target. Confirm project scope before a write and report only a
   short project name and status. If the project GET is 404 `Project not found`,
   follow [Onboarding](references/auth-and-environment.md#onboarding) and stop.
2. **Resolve and propose.** Resolve the reward
   ([`rewards.md`](references/rewards.md)), player action, graph, schedule and
   limits; build the document per
   [`quest-document.md`](references/quest-document.md) (never send
   `publisher_id` or `project_id`, the server stamps them). Show the proposal
   and stop. Stop before any write if the reward is not uniquely verified.
3. **Publish.** After approval of that exact proposal follow
   [Publication after approval](references/quest-document.md#publication-after-approval):
   POST a complete inactive quest, GET it back, PUT active, GET active status,
   scope, reward, dates, limits and `version_id`. Report publication complete
   only when the read-back matches. After an uncertain outcome reconcile per
   [Ambiguous or partial writes](references/quest-document.md#ambiguous-or-partial-writes)
   before any retry; never duplicate on timeout. Schedules and cron:
   [Choosing a trigger](references/node-subtypes.md#choosing-a-trigger).
4. **Edit.** Read, change, full `PUT` per
   [Editing](references/quest-document.md#editing); warn that `PUT` replaces the
   whole document and an active edit goes live. Show a before/after diff, get
   approval, read back, pause per [Pausing](references/quest-document.md#pausing).
5. **Event.** Allowed only after the gate in
   [`events.md`](references/events.md) passes, with its own approval and exact
   payload. Until then send no event; say event execution is not yet verified,
   and report a route the contract marks unavailable to the publisher key here.
   Never resend after an uncertain response. Details:
   [Flow step detail](references/events.md#flow-step-detail-submitting-an-event).
6. **Verify.** Per [`verification.md`](references/verification.md#flow-step-detail-verifying),
   correlate the event and report whether the quest ran.
7. **Delete.** Only quests the developer names, one per call, after a fresh read
   and an explicit yes; soft delete, no restore, see
   [Deleting](references/quest-document.md#deleting).
8. **Optional Web Shop module.** Only when explicitly requested:
   [`web-shop-module.md`](references/web-shop-module.md). Quest approval never
   authorizes shop source edits.
9. **Optional Shop Builder Quests block.** Only when explicitly requested for a
   Shop Builder site, follow [`shop-builder-quests-block.md`](references/shop-builder-quests-block.md):
   make the chosen quests public, then run every Quests operation (create, edit
   settings, reset media, reorder, limit, move, duplicate, hide or show,
   delete) as a `block_operations` brief through the `shop-builder-assembly`
   safety gate (test project, confirmed plan, never publish). Delete needs its
   own yes; quest approval never authorizes site writes.

## Safety stops (summary)

Full text: [writes and credentials](references/auth-and-environment.md#safety-stops-for-writes-and-credentials),
[proposals and actions](references/quest-document.md#safety-stops-for-proposals-and-actions),
[events and failed rewards](references/events.md#safety-stops-for-events-and-failed-rewards),
[execution reads](references/verification.md#scope-of-execution-reads).

- Show the resolved scope before the first write; ask before any other non-GET
  call, showing the exact body first.
- Each event needs its own payload and yes; never resend after a timeout or
  `FAILED` reward action.
- Never point `send_http_webhook` at a private service or an unapproved host.
  Read executions only by the developer's own quest id, never an internal key.
- Branch errors on HTTP status per
  [Errors](references/auth-and-environment.md#errors). `ID 0` is a valid ID.

## Agent test

**Prompt:** `Create a quest that rewards one <requested item> after the player completes the stated action`
**Result:** After read-only checks, one concise proposal, one approval for create through activate; stop if the reward is not uniquely verified.

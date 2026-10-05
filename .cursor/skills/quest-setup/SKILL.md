---
name: quest-setup
description: >-
  Creates, inspects and edits production Xsolla Quest Platform quests conversationally,
  submits a quest event, and verifies that the event actually made the quest execute.
  Covers the whole quest document: the node graph and its connections, the seven node
  subtypes, the condition grammar, activation limits, and the Web3 reward types
  `web3_item` and `web3_token` (token payouts are disabled in production). Use when
  setting up a quest, adding a trigger or a condition, attaching a reward, editing or
  activating an existing quest, firing a test event, or working out why a quest did not
  fire. Examples: "create a quest", "add a Web3 reward to my quest", "make a quest that
  pays a token", "trigger my quest", "send a quest event", "why didn't my quest
  complete", "list my quests", "activate a quest", "quest platform API".
metadata:
  owner: r.aliyev
  domain: quests
---

## Status

This skill targets **production** only. Resolve Quest Platform scope and the
Web3 catalog from the configured integration (see
[auth and environment](references/auth-and-environment.md)); never fall back to
another service target, credential source or catalog. Event submission and
execution read-back still need the versioned contract and preflight before use.

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
4. **No secrets on screen.** Never open `.env` in a viewer, print the
   environment, paste a key into a command, or print the API key, even to
   yourself. Parse credentials as text inside the request, as in
   [Credential](references/auth-and-environment.md#credential). If the three
   credential names exist, the project is set up: continue with the read-only
   preflight and never ask the publisher to confirm settings. Never ask the
   publisher to paste secrets or search for another key.
5. **No IDs or hosts in replies.** Outside the event
   payload, never show merchant, project or player IDs, hosts, service names
   or environment names to the publisher (a reward item's SKU and image URL
   are fine). Every reply starts with a `##`
   heading: no lead-in line such as "Perfect!" or a recap before it.
6. **Never claim delivery.** Report what the read-backs show, nothing more.
7. **Stop points.** End the turn and wait for the publisher: after the
   proposal; after publication read-back (offer the event there, never send
   it); after the event read-back. Never pass a stop point in the same turn.
8. **One create, inactive first.** Create the quest inactive, read it back,
   then activate. A `POST` that returned 200 created the quest. Take its `id`
   from that response; if you lost it, find it by name in the list. Never
   `POST` again for the same proposal.
9. **Stop on auth failures.** Never switch credentials, lanes or routes on your
   own after a failure; report what failed and ask. For a 401 or 404 follow
   [Reading a 401 or 404](references/auth-and-environment.md#reading-a-401-or-404).
10. **Never ask for a SKU or catalog project.** A typed value is not a
    verified item. Use the read-only Store admin catalog lookup in
    [Named item behavior](references/rewards.md#named-item-behavior). If the
    lookup service is unavailable, say so without implying the publisher's
    catalog is disconnected; if it finds no match, report that and stop before
    any write.

## When to use

Use this skill when the developer wants to manage Xsolla Quest Platform quests:

- Create and publish a quest after one approval of the exact proposal
- Add triggers, conditions or reward actions to a quest
- List, view or edit existing quests
- Submit a single quest event to make a quest run
- Check whether an event actually caused a quest to execute

Out of scope: on-chain finality, wallet balances, Backpack display, Site
Builder and custom-blocks quest UI. A completed reward action is not proof of
delivery.

## Prerequisites

The configured production publisher credential is the only lane. It works only
on the project-scoped routes in
[`qp-api-contract.md`](references/qp-api-contract.md). Credential, scope and
onboarding: [Prerequisites and lane](references/auth-and-environment.md#prerequisites-and-lane).
With no production credential, report only that the project is not set up for
quests yet and stop.

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

## Conversation contract (summary)

Full rules: [Conversation contract](references/quest-document.md#conversation-contract)
and [Safety stops for proposals and actions](references/quest-document.md#safety-stops-for-proposals-and-actions).

- Finish all read-only bring-up before any proposal, then show one concise,
  business-first proposal: project name, player action, reward, quantity,
  schedule, repeat limit and payout impact. No service names, routes or auth.
- Propose safe defaults instead of asking for implementation fields; do not ask
  for missing dates.
- One approval of the exact proposal covers create, configure, activate and
  read-back. Test events need separate consent.
- A named item reward is resolved via [`rewards.md`](references/rewards.md);
  never guess an SKU or substitute a reward type.

## Flow

1. **Bring-up.** Load [`qp-api-contract.md`](references/qp-api-contract.md) and
   run the preflight reads in
   [`auth-and-environment.md`](references/auth-and-environment.md#service-preflight).
   Bring-up is GET-only. Never fetch OpenAPI or another target. Confirm project scope before a write and report only a
   short project name and status. If the project GET is 404 `Project not found`,
   follow [Onboarding](references/auth-and-environment.md#onboarding) and stop.
2. **Resolve and propose.** Resolve the reward
   ([`rewards.md`](references/rewards.md)), player action, graph, schedule and
   limits. Build the document per
   [`quest-document.md`](references/quest-document.md); the server stamps
   `publisher_id` and `project_id` from the path, so never send them. Show the
   proposal and stop. Stop before any write if the reward is not uniquely
   verified.
3. **Publish.** After approval of that exact proposal follow
   [Publication after approval](references/quest-document.md#publication-after-approval):
   POST a complete inactive quest, GET it back, PUT active, GET active status,
   scope, reward, dates, limits and `version_id`. Report publication complete
   only when the read-back matches. After an uncertain outcome reconcile per
   [Ambiguous or partial writes](references/quest-document.md#ambiguous-or-partial-writes)
   before any retry; never create a duplicate on timeout. Schedule or cron
   requests follow [Choosing a trigger](references/node-subtypes.md#choosing-a-trigger).
4. **Edit.** Read, change, full `PUT` per
   [Editing](references/quest-document.md#editing). Warn that `PUT` replaces the
   whole document and an active quest's edit goes live. Show a before/after
   diff, get approval, read back, and pause per
   [Pausing](references/quest-document.md#pausing).
5. **Event.** Allowed only after the gate in
   [`events.md`](references/events.md) passes, with its own approval and exact
   payload. Until then do not send an event; say event execution is not yet
   verified. If the contract marks the route unavailable to the publisher key,
   report that blocker at this step. Never resend after an uncertain response. Details:
   [Flow step detail](references/events.md#flow-step-detail-submitting-an-event).
6. **Verify.** Follow [`verification.md`](references/verification.md): correlate
   the event, report whether the quest ran and which action nodes completed.
   Details: [Flow step detail](references/verification.md#flow-step-detail-verifying).
7. **Delete.** Only quests the developer names, one per call, after a fresh read
   and an explicit yes. `DELETE` is a soft delete with no restore route; see
   [Deleting](references/quest-document.md#deleting).

## Safety stops (summary)

Full text: [writes and credentials](references/auth-and-environment.md#safety-stops-for-writes-and-credentials),
[proposals and actions](references/quest-document.md#safety-stops-for-proposals-and-actions),
[events and failed rewards](references/events.md#safety-stops-for-events-and-failed-rewards),
[execution reads](references/verification.md#scope-of-execution-reads).

- Show the resolved scope before the first write; ask separately before any
  other non-GET call, showing the exact body first.
- Each event needs its own payload and yes. After a timeout or `FAILED` reward
  action, do not resend.
- Never point `send_http_webhook` at a private service or an unapproved host.
- Read executions only by the developer's own quest id after confirming
  ownership; never use an internal key.
- Branch errors on HTTP status per
  [Errors](references/auth-and-environment.md#errors). `ID 0` is a valid
  merchant and project ID; never treat it as absent.

## Agent test

**Prompt:** `Create a quest that rewards one <requested item> after the player completes the stated action`
**Result:** After read-only checks, one concise proposal, one approval for create through activate; stop if the reward is not uniquely verified.

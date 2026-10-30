---
name: quest-setup
description: >-
  Creates, inspects and edits production Xsolla Quest Platform quests conversationally.
  Covers the whole quest document: the node graph, its connections, the seven node
  subtypes, the condition grammar and activation limits. Use when setting up a quest,
  adding a trigger or a condition, editing or activating an existing quest, or listing
  quests. Examples: "create a quest", "add a condition to my quest", "list my quests",
  "activate a quest", "quest platform API".
metadata:
  owner: r.aliyev
  domain: quests
---

## Status

This skill targets **production** only. Resolve Quest Platform scope from the configured integration (see
[auth and environment](references/auth-and-environment.md)); never fall back to
another service target or credential source.

## Hard rules (read first)

1. **The request is never the approval.** Your first reply to a create or edit
   request is the proposal. Send no `POST`, `PUT` or `DELETE` in that turn,
   even when the request says "now" or "go ahead". Write only after a later
   publisher message approves that exact proposal.
2. **One target.** Quest configuration and events use only
   `https://quests-platform.xsolla.com`, as in
   [`qp-api-contract.md`](references/qp-api-contract.md). Never call another
   gateway, even after a failure, and never suggest switching environments.
3. **No secrets on screen.** Never open `.env` in a viewer, print the
   environment, paste a key into a command, or print the API key, even to
   yourself. Parse credentials as text inside the request, as in
   [Credential](references/auth-and-environment.md#credential). If the three
   credential names exist, the project is set up: continue with the read-only
   preflight and never ask the publisher to confirm settings. Never ask the
   publisher to paste secrets or search for another key.
4. **No IDs or hosts in replies.** Never show merchant, project or player IDs, hosts, service names
   or environment names to the publisher. Every reply starts with a `##`
   heading: no lead-in line such as "Perfect!" or a recap before it.
5. **Never claim delivery.** Report what the read-backs show, nothing more.
6. **Stop points.** End the turn and wait for the publisher: after the
   proposal; after publication read-back (offer the event there, never send
   it); after the event read-back. Never pass a stop point in the same turn.
7. **One create, inactive first.** Create the quest inactive, read it back,
   then activate. A `POST` that returned 200 created the quest. Take its `id`
   from that response; if you lost it, find it by name in the list. Never
   `POST` again for the same proposal.
8. **Stop on auth failures.** Never switch credentials, lanes or routes on your
   own after a failure; report what failed and ask. For a 401 or 404 follow
   [Reading a 401 or 404](references/auth-and-environment.md#reading-a-401-or-404).

## When to use

Use this skill when the developer wants to manage Xsolla Quest Platform quests:

- Create and publish a quest after one approval of the exact proposal
- Add triggers, conditions or reward actions to a quest
- List, view or edit existing quests

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

## Conversation contract (summary)

Full rules: [Conversation contract](references/quest-document.md#conversation-contract)
and [Safety stops for proposals and actions](references/quest-document.md#safety-stops-for-proposals-and-actions).

- Finish all read-only bring-up before any proposal, then show one concise,
  business-first proposal: project name, player action, reward, quantity,
  schedule, repeat limit and payout impact. No service names, routes or auth.
- Propose safe defaults instead of asking for implementation fields; do not ask
  for missing dates.
- One approval of the exact proposal covers create, configure, activate and
  read-back.

## Flow

1. **Bring-up.** Load [`qp-api-contract.md`](references/qp-api-contract.md) and
   run the preflight reads in
   [`auth-and-environment.md`](references/auth-and-environment.md#service-preflight).
   Bring-up is GET-only. Never fetch OpenAPI or another target. Confirm project scope before a write and report only a
   short project name and status. If the project GET is 404 `Project not found`,
   follow [Onboarding](references/auth-and-environment.md#onboarding) and stop.
2. **Resolve and propose.** Resolve the player action, graph, schedule and
   limits. Build the document per
   [`quest-document.md`](references/quest-document.md); the server stamps
   `publisher_id` and `project_id` from the path, so never send them. Show the
   proposal and stop.
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
5. **Delete.** Only quests the developer names, one per call, after a fresh read
   and an explicit yes. `DELETE` is a soft delete with no restore route; see
   [Deleting](references/quest-document.md#deleting).

## Safety stops (summary)

Full text: [writes and credentials](references/auth-and-environment.md#safety-stops-for-writes-and-credentials),
[proposals and actions](references/quest-document.md#safety-stops-for-proposals-and-actions).

- Show the resolved scope before the first write; ask separately before any
  other non-GET call, showing the exact body first.
- Never point `send_http_webhook` at a private service or an unapproved host.
- Branch errors on HTTP status per
  [Errors](references/auth-and-environment.md#errors). `ID 0` is a valid
  merchant and project ID; never treat it as absent.

## Agent test

**Prompt:** `Create a quest that triggers on a stated player action`
**Result:** After read-only checks, one concise proposal, one approval for create through activate.

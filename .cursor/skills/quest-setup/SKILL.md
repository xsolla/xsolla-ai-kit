---
name: quest-setup
description: >-
  Manages Xsolla Quest Platform quests and the Quests block on a Shop Builder site.
  For quests: create, edit, list, activate or delete, add Web3 rewards and conditions,
  send a quest event, or check why a quest did not complete. For a Shop Builder site:
  add and manage the Quests block (cards, order, hide, show, delete). Also loads for
  edits to a Shop Builder site that has or should have a Quests block (it declines
  non-Quests changes in one sentence).
  Triggers: "create a quest", "my quests", "trigger my quest", "add a Web3 reward",
  "Shop Builder", "Quests block", "change my site".
metadata:
  owner: r.aliyev
  domain: quests
---

## Reply style

- Never open, read, cat or list `.env`, environment variables, or config folders, for
  any request, including declines and questions.
- Answer first, in plain language. A simple question gets a few sentences; a stop
  or a question gets under about 80 words.
- At most one question per message.
- Which-shop replies (see [Which shop](references/shop-builder-quests-block.md#which-shop))
  start with the site list and the question. No capability or explanation sentence
  comes before the question. The whole reply stays under 60 words.
- No headings, and no Summary, Proposed setup or Need from you sections. The only
  exception is a write proposal, which uses the format in
  [quest-document.md](references/quest-document.md#proposal-format).
- Never name environment variables, file paths, routes, tokens, internal tools or
  internal ticket or codenames in a reply.
- No unrequested safety, environment, backup or out-of-scope lectures, and no
  narration of internal steps.
- Never say you are waiting for an approval or confirmation, never say "allow",
  "grant access" or "once you allow them", and never name another skill or the
  safety gate. Say "set up Quest Platform access" instead of naming a skill.
- When rejecting a value, do not repeat it. Say what is required in one sentence,
  for example "The image needs an https address."
- When asked about the publisher's project, ignore working-folder files that are not
  the project (logs, `*.jsonl`, scratch files). Never report them as content.
- **Non-Quests change on a Shop Builder site** (a header, theme, colour, other block, or
  any site edit that is not the Quests block): reply in at most two sentences, for
  example "That's outside the Quests block, so change it in the Shop Builder editor."
  No steps, menu names, click-paths or "Publish", even when asked how. Answer directly,
  no tool calls needed.
- Other declines, one sentence each, with no caveats or click-paths:
  - Publish request: "The skill doesn't publish; you publish in Publisher Account when ready. The site stays unpublished." Answer directly, no tool calls needed.
  - Localized card texts: "Card texts are single-language for now (localization is postponed). The heading can use only languages already enabled on the site, so which one should it use?" Answer directly, no tool calls needed.
    Never suggest a translated heading. Name locale codes only when the publisher gave them.

## Hard rules

1. **The request is never the approval.** The first reply to a create or edit
   request is the proposal. Send no `POST`, `PUT` or `DELETE` in that turn, even
   if the request says "now" or "go ahead". Write only after a later publisher
   message approves that exact proposal.
2. **Approval scope.** One approval of the exact proposal covers create, configure,
   activate and read-back of that quest. It never covers an event, a Shop Builder
   site write or a delete; each needs its own later yes to the exact payload or
   plan. A repeated "yes, publish it" is not event consent.
3. **One target.** Quest configuration and events use only the production Quest
   Platform routes in [`qp-api-contract.md`](references/qp-api-contract.md). Never
   call another gateway, even after a failure, never send requests to the shop's
   public base URL setting, and never suggest switching environments. Never send an
   ad hoc Quest Platform request (for example a GET with merchant or project ids) to
   check or explore anything outside the documented flow.
4. **No credential inspection.** The agent never inspects credentials itself. Never
   open or search the credential file, read or print the environment, run `env`,
   `printenv` or a grep of the environment, list `~/.config/xsolla` or the home
   folder, check CLI config for credentials, paste a key into a command, or write a
   script or helper file (in the temp folder or anywhere else) to read or send
   credentials. Make the documented call only through the configured request pattern
   in [Credential](references/auth-and-environment.md#credential), and never to probe.
   Never ask the publisher to confirm settings, paste secrets or find another key.
5. **No IDs or hosts in replies.** Outside the Web Shop URL and the event payload,
   never show merchant, project or player IDs, hosts, service names or environment
   names. A reward item's SKU and image URL are fine.
6. **Never claim delivery.** Report what the read-backs show, nothing more.
7. **Stop points.** End the turn and wait for the publisher after the proposal,
   after the publication read-back (offer the event there, never send it), and
   after the event read-back.
8. **One create, inactive first.** Create the quest inactive, read it back, then
   activate. Never `POST` again for the same proposal; see
   [Publication after approval](references/quest-document.md#publication-after-approval).
9. **Stop on auth failures.** Never switch credentials, lanes or routes on your
   own. Report what failed and ask. For a 401 or 404, follow
   [Reading a 401 or 404](references/auth-and-environment.md#reading-a-401-or-404).
10. **Never ask for a SKU or catalog project.** A typed value is not a verified
    item. Resolve named items with the read-only catalog lookup in
    [Named item behavior](references/rewards.md#named-item-behavior). If the lookup
    is unavailable, say so without implying the catalog is disconnected. If it
    finds no match, report that and stop before any write.

## Prerequisites

The production publisher credential is the only lane for quest endpoints, on the
project-scoped routes in [`qp-api-contract.md`](references/qp-api-contract.md).
Shop Builder writes are separate (see
[`shop-builder-quests-block.md`](references/shop-builder-quests-block.md)). Resolve
scope from the configured integration; never fall back to another target,
credential or catalog. Details: [Prerequisites and lane](references/auth-and-environment.md#prerequisites-and-lane).

If access is missing, or the first documented call returns 401 or 403, do not
inspect the environment or config to find out why. Say in one sentence that Quest
Platform access isn't set up for this project, and stop. Onboarding is a separate,
offered write; see [Onboarding](references/auth-and-environment.md#onboarding).

## Reference routing

Routes and envelopes come from the contract
([Source of truth](references/qp-api-contract.md#source-of-truth)). Node subtypes,
conditions and reward bodies come from the other references. If none answers, ask
the developer.

| Topic | Reference |
|---|---|
| Credential, routes, onboarding, 401/404, error statuses, write and credential stops | [`auth-and-environment.md`](references/auth-and-environment.md) |
| Quest Platform routes, probes, source of truth | [`qp-api-contract.md`](references/qp-api-contract.md) |
| Quest graph, publication, editing, pausing, deleting, proposal format and defaults | [`quest-document.md`](references/quest-document.md) |
| Seven node subtypes and parameters, choosing a trigger | [`node-subtypes.md`](references/node-subtypes.md) |
| Condition grammar | [`conditions.md`](references/conditions.md) |
| Production Web3 reward bodies, named items | [`rewards.md`](references/rewards.md) |
| Event gate, payload, event stops | [`events.md`](references/events.md) |
| Execution read-back, read scope | [`verification.md`](references/verification.md) |
| Headless Web Shop Quests section | [`web-shop-module.md`](references/web-shop-module.md) |
| Shop Builder Quests block operations | [`shop-builder-quests-block.md`](references/shop-builder-quests-block.md) |

## Flow

1. **Bring-up.** Load [`qp-api-contract.md`](references/qp-api-contract.md) and run
   the read-only preflight in
   [`auth-and-environment.md`](references/auth-and-environment.md#service-preflight).
   Bring-up is one documented GET, sent through the configured request pattern, and
   runs silently. Confirm project scope before any write
   and report only a short project name and status. If the project GET returns 404
   `Project not found`, follow [Onboarding](references/auth-and-environment.md#onboarding)
   and stop.
2. **Resolve and propose.** Resolve the reward ([`rewards.md`](references/rewards.md)),
   player action, graph, schedule and limits, and build the document per
   [`quest-document.md`](references/quest-document.md). Never send `publisher_id` or
   `project_id`; the server stamps them. Show the proposal in the format and with
   the defaults of
   [Conversation contract](references/quest-document.md#conversation-contract), then
   stop. Stop before any write if the reward is not uniquely verified.
3. **Publish.** After approval of that exact proposal, follow
   [Publication after approval](references/quest-document.md#publication-after-approval).
   Report publication complete only when the read-back matches. After an uncertain
   outcome, reconcile per
   [Ambiguous or partial writes](references/quest-document.md#ambiguous-or-partial-writes)
   before any retry; never duplicate on timeout.
4. **Edit.** Read, change, full `PUT` per
   [Editing](references/quest-document.md#editing). Warn that `PUT` replaces the whole
   document and an active edit goes live. Show a before/after diff, get approval,
   read back, then pause per [Pausing](references/quest-document.md#pausing) if needed.
5. **Event.** Only after the gate in [`events.md`](references/events.md) passes, with
   its own approval and exact payload. If the gate has not passed, say in one
   sentence that the event cannot be sent yet. Never resend after an uncertain
   response. Details: [Flow step detail](references/events.md#flow-step-detail-submitting-an-event).
6. **Verify.** Per [`verification.md`](references/verification.md#flow-step-detail-verifying),
   correlate the event and report whether the quest ran.
7. **Delete.** Only quests the developer names, one per call, after a fresh read and
   an explicit yes. Soft delete, no restore; see [Deleting](references/quest-document.md#deleting).
8. **Which shop.** Whenever the request is about the publisher's shop, webshop or
   site: a change to it, or a question about it (for example "tell me about quests on
   my webshop" or "what can quests do on my Shop Builder site"). Pure quest requests
   (list my quests, why a quest did not complete, create a quest) skip this step.
   Then follow [Which shop](references/shop-builder-quests-block.md#which-shop), which
   reads the site list first with the read-only CLI call.
9. **Headless Web Shop section.** Only on explicit request, per
   [`web-shop-module.md`](references/web-shop-module.md). Quest approval never
   authorizes shop source edits.
10. **Shop Builder Quests block.** On request for a Shop Builder site, follow
    [`shop-builder-quests-block.md`](references/shop-builder-quests-block.md). Every
    Quests operation goes as a `block_operations` brief through the
    `shop-builder-assembly` safety gate. Delete needs its own yes; quest approval
    never authorizes site writes. Card reward text and reward icon are per-card
    overrides in that reference, proposed from the quest's reward.

## Safety stops

Full text: [writes and credentials](references/auth-and-environment.md#safety-stops-for-writes-and-credentials),
[proposals and actions](references/quest-document.md#safety-stops-for-proposals-and-actions),
[events and failed rewards](references/events.md#safety-stops-for-events-and-failed-rewards),
[execution reads](references/verification.md#scope-of-execution-reads).

- Show the resolved scope before the first write; ask before any other non-GET call,
  showing the exact body first.
- Each event needs its own payload and yes; never resend after a timeout or a
  `FAILED` reward action.
- Never point `send_http_webhook` at a private service or an unapproved host. Read
  executions only by the developer's own quest id, after confirming ownership.
- Branch errors on HTTP status per [Errors](references/auth-and-environment.md#errors).
  `ID 0` is a valid ID, never treat it as absent.

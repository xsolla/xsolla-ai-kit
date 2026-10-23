---
name: quest-setup
description: >-
  Use when the publisher wants to create, edit, list, activate, pause, delete or debug an
  Xsolla Quest Platform quest, including Web3 rewards, conditions and sending a quest
  event, or to add, reorder, retext, hide, show or remove the Quests block on a Shop
  Builder site. Any other change to a Shop Builder site (header, theme, other blocks)
  also loads this skill, only to decline it in one sentence. A headless storefront quest
  section is covered on explicit request. Key triggers: "create a quest", "my quests",
  "trigger my quest", "add a Web3 reward", "why didn't my quest complete", "Quests block",
  "remove the Quests block", "show quests in my web shop".
metadata:
  owner: r.aliyev
  domain: quests
---

# Quest setup

Quests and the Quests block on a Shop Builder site. Every reply follows
[reply-format.md](references/reply-format.md): one bold line, up to four bullets, one `Next:` ask. The bold line comes first, with no text before it. Never name environment variables, file paths, tokens, routes, tools, tickets
or other skills in a reply. Never open `.env`, environment variables or config folders,
even to redact them, for any request.

## Hard rules

1. **The request is never the approval.** The first reply to a create or edit is the
   proposal. Send no `POST`, `PUT` or `DELETE` in that turn, even if the request says
   "now" or "go ahead". Write only after a later publisher message approves that exact
   proposal. The one exception is a headless storefront source edit, which an explicit
   headless request authorizes; see [web-shop-module.md](references/web-shop-module.md).
2. **Approval scope.** One approval of the exact proposal covers create, configure,
   activate and read-back of that quest. It never covers an event, a Shop Builder site
   write or a delete. Each needs its own later yes to the exact payload or plan. A
   repeated "yes, publish it" is not event consent. Details:
   [quest-publish.md](references/quest-publish.md#safety-stops-for-proposals-and-actions).
3. **One target.** Quest configuration and events use only the production Quest Platform
   routes in [qp-api-contract.md](references/qp-api-contract.md). Never call another
   gateway, the shop's public base URL, or an ad hoc route, even after a failure. Never
   suggest switching environments. Shop Builder writes go only to an approved test
   project ([quests-block-flow.md](references/quests-block-flow.md)).
4. **No credential inspection.** Never open the credential file, print the environment,
   list `~/.config/xsolla` or the home folder, paste a key into a command, or write a
   helper to read or send credentials. Make the documented call only through the
   configured pattern in [Credential](references/auth-credentials.md#credential), and
   never to probe. Never ask the publisher to paste secrets or find another key. Never make a direct HTTP call, search the skills for credential patterns, or explain how credentials are attached, even when access fails.
5. **No IDs or hosts in replies.** Outside the Web Shop URL and the event payload, never
   show merchant, project or player IDs, hosts, service names or environment names. A
   reward item's SKU and image URL are fine.
6. **Never claim delivery.** Report what the read-backs show, nothing more.
7. **Stop points.** End the turn after the proposal, after the publication read-back
   (offer the event there, never send it), and after the event read-back.
8. **One create, inactive first.** Create the quest inactive, read it back, then activate.
   Never `POST` again for the same proposal:
   [Publication after approval](references/quest-publish.md#publication-after-approval).
9. **Stop on auth failures.** Never switch credentials, lanes or routes on your own.
   Report what failed and ask. For a 401 or 404, follow
   [Reading a 401 or 404](references/auth-credentials.md#reading-a-401-or-404).
10. **Never ask for a SKU or catalog project.** A typed value is not a verified item.
    Resolve named items with the read-only lookup in
    [Named item behavior](references/rewards.md#named-item-behavior). If the lookup is
    unavailable, say so without implying the catalog is disconnected. If it finds no
    match, report that and stop before any write. Never propose a reward item, SKU or reward text that the publisher did not give and a lookup did not verify.
11. **Image and reward icon URLs must be https.** If the publisher gives an `http` URL,
    stop before any plan with the rejected-value shape. Never change it to https or draft
    a plan with it ([reply-format.md](references/reply-format.md#examples)).
12. **No temp files.** Never write scratch or output files to `/tmp`, the working folder or anywhere else. Parse command output in a pipe.
13. **Named sites.** Write only to the site the publisher chose under [Which shop](references/quests-block-flow.md#which-shop). A site they name that is not that choice, or one they say must not be touched, gets no plan and no write.

## Prerequisites

The production publisher credential is the only lane for quest endpoints, on the
project-scoped routes in [qp-api-contract.md](references/qp-api-contract.md). Shop Builder
writes are separate. Resolve scope from the configured integration; never fall back to
another target, credential or catalog: [Prerequisites and lane](references/auth-credentials.md#prerequisites-and-lane).

If access is missing, or the first documented call returns 401 or 403, do not inspect the
environment or config. Reply with the exact access-missing shape in [reply-format.md](references/reply-format.md#examples) and stop, with no credential explanation. Onboarding is a
separate, offered write: [Onboarding](references/auth-credentials.md#onboarding).

## Which shop first

When the request is about the publisher's shop, webshop or site (a change, or a question
about it), run [Which shop](references/quests-block-flow.md#which-shop) before anything
else. Pure quest requests (list my quests, why a quest did not complete, create a quest)
skip it.

## Reference routing

Routes and envelopes come from the contract
([Source of truth](references/qp-api-contract.md#source-of-truth)). If no reference
answers, ask the developer.

| Topic | Reference |
|---|---|
| Credential, access, errors, 401/404, onboarding, write and credential stops | [`auth-credentials.md`](references/auth-credentials.md) |
| Store catalog lookup and recipient wallet | [`store-and-wallet.md`](references/store-and-wallet.md) |
| Project-scoped config routes, merchant ID, bring-up preflight | [`qp-config-routes.md`](references/qp-config-routes.md) |
| Quest Platform route contract, probes, source of truth | [`qp-api-contract.md`](references/qp-api-contract.md) |
| Quest fields, responses, node graph, activation limits | [`quest-authoring.md`](references/quest-authoring.md) |
| Publication after approval, ambiguous writes, proposal conversation | [`quest-publish.md`](references/quest-publish.md) |
| Editing, pausing, deleting | [`quest-edit.md`](references/quest-edit.md) |
| Seven node subtypes and parameters, choosing a trigger | [`node-subtypes.md`](references/node-subtypes.md) |
| Condition grammar | [`conditions.md`](references/conditions.md) |
| Production Web3 reward bodies, named items | [`rewards.md`](references/rewards.md) |
| Event gate, payload, event stops | [`events.md`](references/events.md) |
| Execution read-back, read scope | [`verification.md`](references/verification.md) |
| Shop Builder Quests block: flow and stops | [`quests-block-flow.md`](references/quests-block-flow.md) |
| Shop Builder Quests block: settings and operation brief | [`quests-block-brief.md`](references/quests-block-brief.md) |
| Headless Web Shop quest section (loaded only on that path) | [`web-shop-module.md`](references/web-shop-module.md) |
| Reply shapes and examples | [`reply-format.md`](references/reply-format.md) |

## Flow

1. **Bring-up.** Run the read-only preflight in
   [qp-config-routes.md](references/qp-config-routes.md#service-preflight). It is one
   documented GET and runs silently. Confirm project scope before any write, and report
   only a short project name and status. If the project GET returns 404 `Project not
   found`, follow [Onboarding](references/auth-credentials.md#onboarding) and stop.
2. **Resolve and propose.** Resolve the reward ([rewards.md](references/rewards.md)),
   player action, graph, schedule and limits, and build the document per
   [quest-authoring.md](references/quest-authoring.md). Never send `publisher_id` or
   `project_id`; the server stamps them. Show the proposal in the format of
   [Conversation contract](references/quest-publish.md#conversation-contract), then stop.
   Stop before any write if the reward is not uniquely verified.
3. **Publish.** After approval of that exact proposal, follow
   [Publication after approval](references/quest-publish.md#publication-after-approval).
   Report completion only when the read-back matches. After an uncertain outcome, reconcile
   per [Ambiguous or partial writes](references/quest-publish.md#ambiguous-or-partial-writes);
   never duplicate on timeout.
4. **Edit.** Read, change, full `PUT` per [Editing](references/quest-edit.md#editing).
   Warn that `PUT` replaces the whole document and an active edit goes live. Show a
   before/after diff, get approval, read back, then pause per
   [Pausing](references/quest-edit.md#pausing) if needed.
5. **Event.** Only after the gate in [events.md](references/events.md) passes, with its own
   approval and exact payload. If the gate has not passed, say in one reply that the event
   cannot be sent yet. Never resend after an uncertain response:
   [Flow step detail](references/events.md#flow-step-detail-submitting-an-event).
6. **Verify.** Per [verification.md](references/verification.md#flow-step-detail-verifying),
   correlate the event and report whether the quest ran.
7. **Delete.** Only quests the developer names, one per call, after a fresh read and an
   explicit yes: [Deleting](references/quest-edit.md#deleting). Until that yes, reply
   "Nothing is removed yet; removal needs its own yes."
8. **Shop Builder Quests block.** On request for a Shop Builder site, follow
   [quests-block-flow.md](references/quests-block-flow.md). Every operation goes as a
   `block_operations` brief through the `shop-builder-assembly` gate. Delete needs its own
   yes; quest approval never authorizes site writes. A question about the block on a known
   site is a read: [Describe the block](references/quests-block-flow.md#describe-the-block).
9. **Headless Web Shop section.** Only on explicit request, and only then load
   [web-shop-module.md](references/web-shop-module.md). Quest approval never authorizes shop source edits. Never copy the catalog project ID into the Quest Platform project setting, and never offer to; ask which Quest Platform project to use.

## Safety stops

Each stop sits at its flow step and in its reference: writes and credentials
([auth-credentials.md](references/auth-credentials.md#safety-stops-for-writes-and-credentials)),
proposals ([quest-publish.md](references/quest-publish.md#safety-stops-for-proposals-and-actions)),
events ([events.md](references/events.md#safety-stops-for-events-and-failed-rewards)),
execution reads ([verification.md](references/verification.md#scope-of-execution-reads)).
Show the resolved scope before the first write, and ask before any other non-GET call,
showing the exact body first. `ID 0` is a valid ID, never treat it as absent
([Errors](references/auth-credentials.md#errors)).

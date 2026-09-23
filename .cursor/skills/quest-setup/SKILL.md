---
name: quest-setup
description: >-
  Creates, inspects, edits and activates Xsolla Quest Platform quests
  conversationally, and submits a quest event to make a quest run. Covers the
  whole quest document: the node graph and its connections, all seven node
  subtypes, the condition grammar, activation limits, and all nine reward types
  including web3_item and web3_token ERC-20 payouts. Use when setting up a
  quest, adding a trigger or a condition, attaching a reward, editing or
  activating an existing quest, or firing a test event, including "create a
  quest", "add a Web3 reward to my quest", "make a quest that pays USDC",
  "trigger my quest", "send a quest event", "list my quests", "activate a
  quest", "quest platform API".
metadata:
  owner: r.aliyev
  domain: quests
  status: draft
---

## Status

This skill is a **draft**. It requires project API key access to Quest
Platform, which is rolling out. See Errors for how an unavailable route looks.

## When to use

Use this skill when the developer wants to manage quests on the Xsolla Quest
Platform:

- Create a quest, as a draft first and then activate it
- Add triggers, conditions or reward actions to a quest
- List, view or edit existing quests
- Submit a single quest event to make a quest run

Out of scope: reading back whether a quest executed, on-chain finality, wallet
balances and Backpack display. This skill configures quests and submits
events. It reports that an event was accepted and never states that a reward
was delivered.

## Prerequisites

Follow [`references/auth-and-environment.md`](references/auth-and-environment.md)
for the host, the credential and scope confirmation. The credential is the
project API key. Use it on the server or agent side only.

## Source of truth

1. This skill's `references/` are the contract: routes, fields, node
   subtypes, node `parameters`, the condition grammar, reward bodies and
   enums.
2. If a live response contradicts them, trust the shape of the live response,
   tell the developer what differed, and do not guess the rest.
3. If neither answers the question, **ask the developer**. Do not infer a
   field by analogy with another Xsolla API.

## Reference material

- [`references/auth-and-environment.md`](references/auth-and-environment.md): host, credential, routes, access check and scope
- [`references/quest-document.md`](references/quest-document.md): the quest graph, conditional requirements, full-document PUT
- [`references/node-subtypes.md`](references/node-subtypes.md): the seven accepted node subtypes and their parameters

## Flow

1. **Bring-up.** Check the credential is set. List quests, show the scope that
   comes back, and get confirmation.
2. **Draft.** Create the quest as `inactive` with the four required fields.
3. **Fill in.** Add nodes and edges one at a time, asking for each missing
   required value. Show the assembled document before sending it.
4. **Activate.** A separate step: move to `active` with dates, after checking
   there are at least two nodes, a trigger-to-action path, no intended orphan
   nodes, and an acyclic graph.
   For a Web3 reward, also confirm the SKU, the amount and the
   recipient's wallet with the developer.
   Show the activation limits and the effective repeat behavior before asking
   for confirmation.
5. **Edit.** Read, change, full `PUT`. Warn that `PUT` replaces the whole
   document.
6. **Event.** Build the payload, generate a fresh UUID `idempotency_key`, set
   an RFC3339 `client_timestamp`, confirm with the developer, and submit it to
   the events endpoint.
7. **Report.** On success, report "event accepted, `event_id=<id>`". Say that
   this skill cannot yet read back whether the quest executed, and that the
   developer should check the outcome where the reward lands. Never claim a
   reward was delivered.

## Safety stops

- Show the resolved scope before the first write, and get confirmation.
- Before activation, show every externally observable action and get explicit
  confirmation for its impact. An `issue_reward` can create real payouts;
  `send_http_webhook` sends event data to an external URL;
  `send_xsolla_app_notification` sends a user notification. Do not activate a
  `webshop_personalization` node as if it were a working personalization action.
- If `activation_limits` is absent, ask the developer to explicitly choose
  unlimited repeat behavior and acknowledge that every qualifying event may run
  the action. Do not silently choose a limit or omit this decision.
- Ask for confirmation before submitting an event.
- After an uncertain event response, such as a timeout, **do not resend**:
  not with the same idempotency key and not with a new one. A timeout is not a
  failure. Report "result unknown" and stop.
- If the developer reports that a reward did not arrive, do not resend the
  event to retry it. Fix the quest first, then send a new event with a new key
  only after the developer confirms.
- Never resend an event to retry a Web3 reward. The Web3 claim is not
  idempotent and may already have paid.
- Never claim a reward was delivered.

## Errors

Branch on the HTTP status. The only body check is on a 404: a plain-text body
and a JSON body mean different things. The API has no stable machine-readable
error codes.

| Status | What to tell the developer |
|---|---|
| 401, JSON body | The credential was not accepted for this project. Ask the developer to check `XSOLLA_MERCHANT_ID` and `XSOLLA_PROJECT_API_KEY`. |
| 403 | The key lacks permission for quest configuration. |
| 404, plain-text body such as `Cannot GET /...` or `Cannot POST /...` | The route is not published on this host yet. Stop and tell the developer that project API key access for this operation is not available yet. Do not retry and do not try other hosts. |
| 404, JSON body | "Not found, or no access, or the project is not onboarded to Quest Platform." Never say the quest does not exist. |
| 409 | Conflict. |
| 422 | Validation failed. Show `detail` verbatim. |
| 5xx | Server error. Retry reads only. |

A JSON 404 looks the same for an unknown project, a project that is not
onboarded, and a project the key has no access to. This is deliberate, so the
API cannot be used to find out which projects use Quest Platform.

Two JSON body shapes exist. Failures before the request reaches a quest
operation, such as authentication, return `{"error": "..."}`. Failures inside
the operation return RFC 7807 `application/problem+json`. On 422 the `errors[]` array is
**not** filled in: per-field messages are flattened into one `detail` string
joined with `"; "`. Those `location: message` pairs may be shown to a human,
never parsed for control flow.

`ID 0` is a valid merchant ID and a valid project ID. Never treat it as an
absent value.

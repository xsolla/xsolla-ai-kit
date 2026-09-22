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

This skill is a **draft**. The credential lane it targets is not deployed yet;
see Prerequisites.

## When to use

Use this skill when the developer wants to manage quests on the Xsolla Quest
Platform:

- Create a quest, as a draft first and then activate it
- Add triggers, conditions or reward actions to a quest
- List, view or edit existing quests
- Submit a single quest event to make a quest run
- Check whether an event actually caused a quest to execute

Out of scope: wallet balances, transaction hashes and Backpack display. This
skill configures a Web3 reward and reports that a quest executed. It never
states that a token was delivered.

## Prerequisites

Follow [`references/auth-and-environment.md`](references/auth-and-environment.md)
for the required credential, request authentication, internal hosts, and scope
confirmation.

**This credential lane is not accepted yet.** Quest Platform implements it in
QP-2862, inside QP-2858 Phase 3, which depends on Phases 1 and 2. Until it
lands, every call to qp-server returns 401. Say exactly that, naming the
ticket, rather than reporting a generic authentication failure. The execution
read-back is unaffected and needs no credential.

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

If a host is unreachable, which usually means no corporate network, say so and
offer to continue on `references/` alone, noting that the envelope may have
drifted. Never continue silently.

## Reference material

- [`references/auth-and-environment.md`](references/auth-and-environment.md) — hosts, credential, scope, and the incoming auth changes
- [`references/quest-document.md`](references/quest-document.md) — the quest graph, conditional requirements, full-document PUT
- [`references/node-subtypes.md`](references/node-subtypes.md) — the seven accepted node subtypes and their parameters
- [`references/conditions.md`](references/conditions.md) — condition grammar: types, operands, operators, event counting
- [`references/rewards.md`](references/rewards.md) — the nine reward types and their bodies, including web3_token

## Flow

1. **Bring-up.** Fetch the OpenAPI documents. Check the credential is set. List
   quests, show the resolved scope, and get confirmation.
2. **Draft.** Create the quest as `inactive` with the four required fields.
3. **Fill in.** Add nodes and edges one at a time, asking for each missing
   required value. Show the assembled document before sending it.
4. **Activate.** A separate step: move to `active` with dates, after checking
   there are at least two nodes and the graph is acyclic.
5. **Edit.** Read, change, full `PUT`. Warn that `PUT` replaces the whole
   document.

## Safety stops

- Read back and show the resolved scope before the first write, and get
  confirmation.
- Ask for separate, explicit confirmation before activating a quest that
  contains an `issue_reward` node. Activation means real payouts.
- Ask for confirmation before submitting an event.
- After an uncertain event response, such as a timeout, **do not resend** —
  neither with the same idempotency key nor with a new one. A timeout is not a
  failure. Report "result unknown" and stop.
- Never claim a reward was delivered.

## Errors

Branch on the HTTP status only. The API has no stable machine-readable error
codes.

| Status | What to tell the developer |
|---|---|
| 401 | Missing or invalid credential. For the credential lane described in the reference, name QP-2862. |
| 403 | The key lacks the required `questconfig:*` capability. |
| 404 | "Not found, or no access, or the project is not onboarded to Quest Platform." Never say the quest does not exist. |
| 409 | Conflict. |
| 422 | Validation failed. Show `detail` verbatim. |
| 5xx | Server error. Retry reads only. |

Two body shapes exist. Middleware failures return `{"error": "..."}`. Handler
failures return RFC 7807 `application/problem+json`. On 422 the `errors[]`
array is **not** filled in: per-field messages are flattened into one `detail`
string joined with `"; "`. Those `location: message` pairs may be shown to a
human, never parsed for control flow.

`ID 0` is a valid merchant ID and a valid project ID. Never treat it as an
absent value.

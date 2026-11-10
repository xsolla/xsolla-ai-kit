# Quest authoring

The quest is a graph. Use this file to build a quest document: fields, responses, nodes,
connections and activation limits. Publication, edits and proposals have their own files.

Here `{scope}` means the selected production merchant/project path from
[the API contract](qp-api-contract.md#route-templates-snapshot-orientation-only).
Its [preflight](qp-api-contract.md#service-preflight) and
[auth route-miss rules](auth-credentials.md#when-a-route-is-missing) apply.

## Fields

`POST` and `PUT` take the whole quest object.

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | yes | 1 to 255 characters |
| `type` | string | yes | `liveops`, `ads`, `xsolla_app`, `social_quest`; see below. Use `liveops` internally for a gameplay quest unless the developer indicates another context; call it a gameplay quest in the publisher-facing preview |
| `status` | string | yes | `active` or `inactive` on write. `deleted` is set only by `DELETE`, a soft delete, and is rejected on write |
| `created_by` | string | yes | 1 to 255 characters. Use the developer's supplied name when available; otherwise use the internal label `AI Toolkit` without asking |
| `description` | string | no | if present, 5 to 1000 characters. Validate the live contract before relying on a server error message |
| `publisher_id` | string | server-set | set by the server from the selected production route. Never ask for it or invent it; on a `PUT`, send it back as the last read returned it |
| `project_id` | string | server-set | set by the server from the selected production route. On a `PUT`, send it exactly as the last read returned it. See Scope in the auth reference |
| `start_date` | RFC3339 | **only when `active`** | not earlier than exactly 24 hours before the server's now; see below |
| `end_date` | RFC3339 | **only when `active`** | not in the past, and at or after `start_date`. For a new quest without a requested end or duration, offer the end as a choice with a suggestion that matches the request; never pick one silently |
| `nodes` | array | **at least 2 when `active`** | optional and may be empty when `inactive` |
| `connections` | object | required unless `inactive` and empty | see below |
| `activation_limits` | array | no | see below |
| `metadata` | object | no | nesting depth at most 2 |
| `id`, `created_at`, `updated_at`, `version_id` | mixed | server-assigned | ignored on create |
| `has_personalization` | bool | server-derived | `true` when any action is `webshop_personalization`, even though that action is a no-op at run time. Do not set it |
| `sample_data` | any | no | accepted, not validated, **not persisted** |

The conditional requirements are enforced only by the server's hand-written
validator. They do not appear in the OpenAPI document.

`type` is an API classification. The live contract must confirm the accepted
values and any downstream meaning. Keep it out of the normal publisher-facing
preview and use plain language such as "gameplay quest" instead. A loose match
such as "for the Xsolla app" is only a suggestion: ask a confirming question
before it goes into a body.

The `start_date` check compares instants. When you refuse a start before
sending, explain the live rule in your own words, say nothing was sent, and
offer the earliest allowed start. To start now, take the current instant at
send time, not one computed earlier in the conversation.

The `start_date` check runs on **every** write with `status: active`, including a `PUT`
that changes nothing else. A quest whose `start_date` is more than 24 hours old
cannot be saved as active without moving `start_date` forward. For such an edit,
show a proposed start at edit activation time in the before/after diff; if the
old `end_date` has passed, ask for the new end, suggesting the quest's previous duration.
Show both dates in the revised edit for its approval. Both dates must be valid when the `PUT` is sent.

A quest runs only while `active` and `start_date <= now <= end_date` at event
time. A future `start_date` is accepted, but events before it do not run the
quest; warn before sending an event outside the window.

Dates are RFC3339 instants. State exact times in UTC whenever you show them,
including a fixed schedule in the proposal and a publication read-back. Dates come back in the
server's local offset, for example `+03:00`, even when sent in `Z`; convert
them to UTC and compare instants, not strings.

## Responses

Create and update return 200, not 201, with the whole quest. Empty `nodes`,
`connections` and `metadata` come back as `null` rather than `[]` or `{}`;
that is not an error. An empty or absent optional field such as
`activation_limits` or `description` may come back as `null` or be omitted
from the response entirely; treat either as
not set. A `null` `nodes` may be sent back on an `inactive` quest; send real
arrays when activating. An optional field missing from a response is not set;
it is not `0` or an empty string. The list, `GET {scope}/quests`, returns
`{page, limit, total, data[]}`. Query: `page` (default 1; `0` is read as 1),
`limit` (default 10; `0` is read as 10; above 100 it is silently cut to 100,
with no error), `publisherID`. A non-integer value is 422. There is no name
filter: to find a quest by name, page through the whole list (a read-only name check before a create is optional, see Choosing a trigger in `node-subtypes.md`). Page through it
rather than reading one page as the whole list. Its items carry
`project_id` but no `publisher_id`, nodes, connections, dates or `account_id`,
so use the list only to find a quest's `id`; for anything else (the
`publisher` block, the graph, an edit) `GET {scope}/quests/{id}`. The list
covers only the route's project.

`GET {scope}` (the project itself) returns `project_id` (integer), `name`,
`status`, `created_at`, `updated_at` and, only when set, `description`. It
carries no merchant, account or workspace id, so do not read one from it.

## Nodes and connections

```json
{
  "nodes": [
    {"id": "<uuid>", "name": "<3-255 chars>", "type": "trigger", "subtype": "dynamic_event", "parameters": {}},
    {"id": "<uuid>", "name": "<3-255 chars>", "type": "action",  "subtype": "<reward node from the catalog>",  "parameters": {}}
  ],
  "connections": {
    "<source node uuid>": [{"nodeId": "<target node uuid>", "on": "ticket_issued"}]
  }
}
```

- `type` is `trigger`, `action` or `condition`.
- `id` must be a valid, non-zero UUID.
- `on` is optional. An edge without it is always followed. With it, the
  runtime follows the edge only when the source action returns that outcome:
  `ticket_issued`, `no_ticket` or `daily_cap_reached`. Only an `issue_reward`
  with `vc_wallet_ticket` `playtime` returns these outcomes today; never use `issue_reward` for a
  new item reward.
- Every edge must reference a node that exists in `nodes`, and the graph must
  be acyclic.

The smallest quest that can be activated is two nodes and one edge: a trigger
and an action.

Name nodes after what they do, and label anything that is not real in the
name, for example `noop` or `webhook (placeholder)`, so a later read shows it.

### Several actions on one trigger

The runtime walks depth-first, one node at a time in each source's edge-list order,
including sibling actions. The first failed node or condition miss stops the whole walk;
later nodes do not run. An action failure yields `FAILED` with `failReason: ACTION_FAILED`.
Earlier successful external actions stay sent, with no rollback. On the next event for
the same user/quest, succeeded nodes from the failed run are skipped and the rest retried
according to the production runtime contract. Put blocking actions first and explain
that a later failure cannot undo an earlier payout. [Per-action results](verification.md#reading-a-row-with-several-actions).

How the edges are listed decides the shape. For "A then B" on trigger `T`,
either form runs A before B, but they differ when A has an `on` outcome:

```json
{"T": [{"nodeId": "A"}, {"nodeId": "B"}]}
```

Siblings: both hang off the trigger, in list order. B runs after A whatever
outcome A returned (unless A failed).

```json
{"T": [{"nodeId": "A"}], "A": [{"nodeId": "B"}]}
```

Chain: B hangs off A, so an `on` on the `A -> B` edge can gate B on A's
outcome. Without `on`, both shapes run the same way. The keys and `nodeId`s
are node UUIDs; the letters here are placeholders.

## Activation limits

```json
{"activation_limits": [{"type": "per_user", "count": 1, "time_window": {"duration_unit": "day"}}]}
```

`type` is `global` or `per_user`. `count` must be at least 1.
`time_window.duration_unit`, when present, is `day`, `week` or `month`.
If `activation_limits` is absent, `null` or empty, no repeat limit is
configured: every qualifying event runs the actions. Show that unlimited-repeat
behavior, and the resulting payout impact, inside the publication proposal so
the one approval covers it. Do not ask again for the activation `PUT` unless a
material value changed after approval, in which case show the revised proposal
and request approval again. Never silently assume a one-time or per-user limit.

A limit without `time_window` counts over the quest's whole life: `per_user`
`count: 1` means once per user, ever. A retest then needs a new user or a new
quest. With `time_window`, the count resets each calendar day, week or month.
A reward node can have its own repeat rule on top of these limits (a Web3 item pays at most once per
player and quest). Read it from the node description and say it before the proposal when it does not
fit the requested repeat; see `rewards.md`.

During the read-only work before the proposal, and before the first write,
check that the intended trigger reaches an intended action and that no intended
node is orphaned. The server validates references and cycles, but those checks
alone do not prove that the quest is semantically usable.

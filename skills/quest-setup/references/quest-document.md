# The quest document

Stage OpenAPI and local runtime snapshots were checked on 2026-09-23. The
stage deployment revision is not pinned here, so revalidate before writes.

A quest is a **graph**, not a flat record. This one fact drives everything else
in this skill.

## Fields

`POST` and `PUT` take the whole quest object.

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | yes | 1 to 255 characters |
| `type` | string | yes | `liveops`, `ads`, `xsolla_app`, `social_quest` |
| `status` | string | yes | `active` or `inactive` on write. `deleted` is set only by `DELETE`, a soft delete, and is rejected on write |
| `created_by` | string | yes | 1 to 255 characters. Ask the developer; never derive it from the environment |
| `description` | string | no | if present, 5 to 1000 characters |
| `publisher_id` | string | no | 1 to 255 characters. Fixed at create: a `PUT` does not change it |
| `project_id` | string | no | 1 to 255 characters. A `PUT` without it keeps the stored value |
| `start_date` | RFC3339 | **only when `active`** | not earlier than exactly 24 hours before the server's now; see below |
| `end_date` | RFC3339 | **only when `active`** | not in the past, and at or after `start_date`. Ask; there is no default |
| `nodes` | array | **at least 2 when `active`** | optional and may be empty when `inactive` |
| `connections` | object | required unless `inactive` and empty | see below |
| `activation_limits` | array | no | see below |
| `metadata` | object | no | nesting depth at most 2 |
| `id`, `created_at`, `updated_at`, `version_id` | — | server-assigned | ignored on create |
| `has_personalization` | bool | — | server-derived: `true` when any action is `webshop_personalization`, even though that action is a no-op at run time. Do not set it |
| `sample_data` | any | no | accepted, not validated, **not persisted** |

The conditional requirements are enforced only by the server's hand-written
validator. They do not appear in the OpenAPI document.

The `start_date` check compares instants, but its 422 message prints only the
date, which misleads. `2026-09-22T00:00:00Z` sent at `2026-09-23T07:37Z` was
rejected with `start_date must be on or after 2026-09-22.` (observed on stage
2026-09-23, revalidate). To start now, take the current instant at send time,
not one computed earlier in the conversation, and check before sending that it
is no more than 24 hours old.

The check runs on **every** write with `status: active`, including a `PUT`
that changes nothing else. A quest whose `start_date` is more than 24 hours old
cannot be saved as active without moving `start_date` forward. Tell the
developer before such an edit and ask for the new start; `end_date` must also
still be in the future.

A quest runs only while `active` and `start_date <= now <= end_date` at event
time. A future `start_date` is accepted, but events before it do not run the
quest; warn before sending an event outside the window.

Dates come back in the server's local offset, for example `+03:00`, even when
sent in `Z`. Compare instants, not strings.

## Responses

Create and update return 200, not 201, with the whole quest. Empty `nodes`,
`connections` and `metadata` come back as `null` rather than `[]` or `{}`;
that is not an error. An empty or absent `activation_limits` also comes back
as `null`. A `null` `nodes` may be sent back on an `inactive` draft; send real
arrays when activating. An optional field missing from a response is not set;
it is not `0` or an empty string. The list returns
`{page, limit, total, data[]}`, `limit` 10 by default and 100 at most; page
through it rather than reading one page as the whole list. Its items carry no
nodes, connections or `account_id`.

## Draft first, then activate

Because an `inactive` quest needs only four fields, build the quest as a draft,
fill it in while talking to the developer, and activate it as a separate,
explicitly confirmed step. Do not try to assemble a whole valid graph before
the first call.

## Nodes and connections

```json
{
  "nodes": [
    {"id": "<uuid>", "name": "<3-255 chars>", "type": "trigger", "subtype": "dynamic_event", "parameters": {}},
    {"id": "<uuid>", "name": "<3-255 chars>", "type": "action",  "subtype": "issue_reward",  "parameters": {}}
  ],
  "connections": {
    "<source node uuid>": [{"nodeId": "<target node uuid>", "on": "ticket_issued"}]
  }
}
```

- `type` is `trigger`, `action` or `condition`.
- `id` must be a valid, non-zero UUID.
- `on` is optional. An edge without it is always followed. With it, the
  worker follows the edge only when the source action returns that outcome:
  `ticket_issued`, `no_ticket` or `daily_cap_reached`. Only an `issue_reward`
  with `vc_wallet_ticket` `playtime` returns these outcomes today.
- Every edge must reference a node that exists in `nodes`, and the graph must
  be acyclic.

The smallest quest that can be activated is two nodes and one edge: a trigger
and an action.

## Activation limits

```json
{"activation_limits": [{"type": "per_user", "count": 1, "time_window": {"duration_unit": "day"}}]}
```

`type` is `global` or `per_user`. `count` must be at least 1.
`time_window.duration_unit`, when present, is `day`, `week` or `month`.
If `activation_limits` is absent, `null` or empty, no repeat limit is
configured: every qualifying event runs the actions. Before activation, show
that behavior and require the developer to acknowledge it; do not silently
assume a one-time or per-user limit.

A limit without `time_window` counts over the quest's whole life: `per_user`
`count: 1` means once per user, ever. A retest then needs a new user or a new
quest. With `time_window`, the count resets each calendar day, week or month.
A Web3 reward has its own repeat rule on top; see `rewards.md`.

Before activation, also check that the intended trigger reaches an intended
action and that no intended node is orphaned. The server validates references
and cycles, but those checks alone do not prove that the quest is semantically
usable.

## Editing

There is **no PATCH**. Update is a full-document `PUT`: read the quest, change
what you need, and send the whole object back. Tell the developer this before
editing, because a partial body silently drops everything it omits.

Recipe: take the body of a fresh `GET`, change only the fields the developer
asked for, and send the rest verbatim, `null` values included. `id` (the path
wins), `created_at`, `updated_at`, `version_id` and `has_personalization` are
ignored on `PUT`, so they may stay or be dropped. Show the before/after diff of
the changed fields before sending.

An edit to an active quest applies to the next events once the pipeline's
config caches expire (see `events.md`). If the edit adds or changes an action,
a reward or the limits, repeat the activation confirmations for it. If it
changes an amount or SKU, check node names that mention the old value.

`version_id` is server-assigned and changes on every write. It is ignored in
the body: there is no optimistic concurrency, quest `PUT` never returns 409,
and the last write wins. Read the quest immediately before a `PUT`.

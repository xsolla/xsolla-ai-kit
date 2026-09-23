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
| `status` | string | yes | `active` or `inactive` on write. `deleted` exists as a value but is rejected on write |
| `created_by` | string | yes | 1 to 255 characters |
| `description` | string | no | if present, 5 to 1000 characters |
| `publisher_id` | string | no | 1 to 255 characters |
| `project_id` | string | no | 1 to 255 characters |
| `start_date` | RFC3339 | **only when `active`** | not earlier than exactly 24 hours before the server's now; see below |
| `end_date` | RFC3339 | **only when `active`** | not in the past, and at or after `start_date` |
| `nodes` | array | **at least 2 when `active`** | optional and may be empty when `inactive` |
| `connections` | object | required unless `inactive` and empty | see below |
| `activation_limits` | array | no | see below |
| `metadata` | object | no | nesting depth at most 2 |
| `id`, `created_at`, `updated_at`, `version_id` | — | server-assigned | ignored on create |
| `has_personalization` | bool | — | server-derived from the nodes; do not set it |
| `sample_data` | any | no | accepted, not validated, **not persisted** |

The conditional requirements are enforced only by the server's hand-written
validator. They do not appear in the OpenAPI document.

The `start_date` check compares instants, but its 422 message prints only the
date, which misleads. `2026-09-22T00:00:00Z` sent at `2026-09-23T07:37Z` was
rejected with `start_date must be on or after 2026-09-22.` (observed on stage
2026-09-23, revalidate). Use today's date for the safest result.

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
- `on` is optional. When present it must be `ticket_issued`, `no_ticket` or
  `daily_cap_reached`.
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
If `activation_limits` is absent, no repeat limit is configured. Before
activation, show that behavior and require the developer to acknowledge it;
do not silently assume a one-time or per-user limit.

Before activation, also check that the intended trigger reaches an intended
action and that no intended node is orphaned. The server validates references
and cycles, but those checks alone do not prove that the quest is semantically
usable.

## Editing

There is **no PATCH**. Update is a full-document `PUT`: read the quest, change
what you need, and send the whole object back. Tell the developer this before
editing, because a partial body silently drops everything it omits.

`version_id` is server-assigned and changes on every write.

# The quest document

Stage OpenAPI and the code of the deployed qp-server build were checked on
2026-09-25. The deployed revision is inferred, not pinned, so revalidate
before writes.

Every quest route in this file is a project-scoped route,
`/api/v2/merchants/{merchant_id}/projects/{project_id}/quests[/{id}]`. Below,
`{scope}` stands for `/api/v2/merchants/{merchant_id}/projects/{project_id}`. `{merchant_id}` is exactly
`XSOLLA_MERCHANT_ID` and `{project_id}` is `XSOLLA_PROJECT_ID`. The route
family, the credential and the scope rules are owned by
[Project-scoped routes](auth-and-environment.md#project-scoped-routes) in the
auth reference; if the family moves again, only that file changes. A 404
`text/plain` body `Cannot GET ...` means a wrong or old route, not a quest or
auth answer; follow [When a route is missing](auth-and-environment.md#when-a-route-is-missing).

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
| `publisher_id` | string | server-set | set by the server on create to the route's **path** `{merchant_id}` (from code; body values are ignored). Stage does not reject a path merchant that differs from the key's, and such a quest would never match events, so the path must carry exactly `XSOLLA_MERCHANT_ID`. A `PUT` does not change it. Never ask for it or invent it; on a `PUT`, send it back as the last read returned it |
| `project_id` | string | server-set | set by the server on create to the route's path `{project_id}`. On a `PUT`, send it exactly as the last read returned it: a different value in the body would overwrite the stored one (from code). See Scope in the auth reference |
| `start_date` | RFC3339 | **only when `active`** | not earlier than exactly 24 hours before the server's now; see below |
| `end_date` | RFC3339 | **only when `active`** | not in the past, and at or after `start_date`. Ask; there is no default |
| `nodes` | array | **at least 2 when `active`** | optional and may be empty when `inactive` |
| `connections` | object | required unless `inactive` and empty | see below |
| `activation_limits` | array | no | see below |
| `metadata` | object | no | nesting depth at most 2 |
| `id`, `created_at`, `updated_at`, `version_id` | mixed | server-assigned | ignored on create |
| `has_personalization` | bool | server-derived | `true` when any action is `webshop_personalization`, even though that action is a no-op at run time. Do not set it |
| `sample_data` | any | no | accepted, not validated, **not persisted** |

The conditional requirements are enforced only by the server's hand-written
validator. They do not appear in the OpenAPI document.

The `start_date` check compares instants, but its 422 message prints only the
date, which misleads. `2026-09-22T00:00:00Z` sent at `2026-09-23T07:37Z` was
rejected with `start_date must be on or after 2026-09-22.` (observed on stage
2026-09-23, revalidate). To start now, take the current instant at send time,
not one computed earlier in the conversation, and check before sending that it
is no more than 24 hours old. When a requested start is too old, offer a
concrete alternative: the earliest allowed start is the server's now minus 24
hours (in practice, take "now" at send time and keep a margin, for example now
minus 23 hours, or simply now). Dates are RFC3339 instants; state them in UTC
when confirming with the developer.

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
that is not an error. An empty or absent optional field such as
`activation_limits` or `description` may come back as `null` or be omitted
from the response entirely (both seen on stage 2026-09-25); treat either as
not set. A `null` `nodes` may be sent back on an `inactive` draft; send real
arrays when activating. An optional field missing from a response is not set;
it is not `0` or an empty string. The list, `GET {scope}/quests`, returns
`{page, limit, total, data[]}`. Query: `page` (default 1; `0` is read as 1),
`limit` (default 10; `0` is read as 10; above 100 it is silently cut to 100,
with no error), `publisherID`. A non-integer value is 422. There is no name
filter: to find a quest by name, page through the whole list. Page through it
rather than reading one page as the whole list. Its items carry
`project_id` but no `publisher_id`, nodes, connections, dates or `account_id`,
so use the list only to find a quest's `id`; for anything else (the
`publisher` block, the graph, an edit) `GET {scope}/quests/{id}`. The list
covers only the route's project.

`GET {scope}` (the project itself) returns `project_id` (integer), `name`,
`status`, `created_at`, `updated_at` and, only when set, `description`. It
carries no merchant, account or workspace id, so do not read one from it.

## Draft first, then activate

Because an `inactive` quest needs only four fields, build the quest as a draft,
fill it in while talking to the developer, and activate it as a separate,
explicitly confirmed step. Do not try to assemble a whole valid graph before
the first call.

Activation is an ordinary edit: follow the Editing recipe below (fresh `GET`,
full `PUT`) and change only `status` to `active`, `start_date`, `end_date`
and, if the developer set one, `activation_limits`. Everything else goes back
verbatim. For "no repeat limit", sending `activation_limits` as `null` and
leaving it out are the same: the server model is a pointer with `omitempty`
(`lib/models/v2` v2.9.16 `generic_quest/quest.go`, pinned by qp-server), so
both decode to "not set". `[]` also means no limit (see Activation limits).

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

### Several actions on one trigger

The worker walks the graph depth-first from the trigger, one node at a time,
in the order the edges are listed under each source node. Several actions on
one trigger therefore run one after another, not in parallel. They are not
independent (from the worker code, checked 2026-09-25):

- The first node that fails stops the whole walk. Nodes after it, including
  sibling actions listed later, do not run.
- One failed action makes the whole execution `FAILED`
  (`failReason: ACTION_FAILED`). Actions that already succeeded are not
  rolled back: a reward or notification sent before the failure stays sent.
  Observed on stage: rows with a notification and a reward `COMPLETED` and a
  second reward `FAILED`, execution `FAILED`.
- A condition miss also stops the walk; see `conditions.md`.
- On the next event for the same user and quest, the worker skips nodes that
  already succeeded in the failed run and retries the rest (from code).

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

So put the action whose failure should block the others first, and tell the
developer that a later failure does not undo an earlier payout. How to read
per-action statuses is in [`verification.md`](verification.md).

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
ignored on `PUT`, so they may stay or be dropped. GET bodies also carry a
`$schema` link; drop it before the `PUT`. (From code, qp-server at adtech
873d3c7a3c: `PUT` and `GET` share one body schema, where `$schema` is a
read-only property Huma accepts and ignores, so leaving it in should not
fail; not verified live.) For a new node, you generate its `id` as a fresh
random UUID (v4); the server does not assign node ids, and existing node ids
stay unchanged. Show the before/after diff of
the changed fields before sending.

An edit to an active quest applies to the next events once the pipeline's
config caches expire (see `events.md`). If the edit adds or changes an action,
a reward or the limits, repeat the activation confirmations for it. If it
changes an amount or SKU, check node names that mention the old value.

`version_id` is server-assigned and changes on every write. It is ignored in
the body: there is no optimistic concurrency, quest `PUT` never returns 409,
and the last write wins. Read the quest immediately before a `PUT`.

## Pausing

There is no pause route. To pause, send the full-document `PUT` from the recipe
with `status: inactive` and keep the dates, nodes and limits as they are. The
date rules apply only to `active` writes, so an old `start_date` is fine here;
reactivating later runs them again (see Fields).

While the quest is inactive, the consumer drops its events: no workflow, no
execution row, and nothing is queued or replayed on reactivation. The dropped
events are still indexed, so they may count toward an event-count condition
later (inferred from code). For up to the config cache time after the pause,
events can still run the old, active config; see `events.md`. For a quest with
an `issue_reward`, tell the developer that such an event can still pay.

## Deleting

`DELETE {scope}/quests/{id}` needs `questconfig:delete`
(a project key acts with author rights, which include it) and returns 200 with
`{"message": "Quest deleted successfully"}`. It is a soft delete: the quest and
all its triggers get `status: deleted`, so events stop matching it (after the
config cache time), and its qp-data rows stay. After that, `GET`, the list and
a second `DELETE` treat it as not found: 404 problem+json with
`"detail":"Quest not found"` (verified on the merchant project route 2026-09-25). A 404
`{"error":"Project not found"}` is a scope answer instead, not a verdict on
the quest; see the auth reference. There is no restore route. The
update query does not exclude deleted quests, so a `PUT` to the old id may
overwrite and revive it (inferred from code, not tested); never use that as a
restore, and do not `PUT` to a deleted id.

Recipe:

- Delete only quests the developer names by id or exact name. Never select
  them by pattern or "all test quests" without showing the list first.
- Re-list or `GET` right before deleting, and show each quest's name, id,
  `status`, dates and actions. For an `active` quest or one with an
  `issue_reward` or another external action, say it is live and what stops.
- Say that the delete cannot be undone through the API, and get a yes.
- Delete one quest per call. Stop on the first non-200 and report it; after a
  timeout or 5xx, `GET` the quest to check before trying again.
- Re-list afterwards and show that the deleted quests are gone.

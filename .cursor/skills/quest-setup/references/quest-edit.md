# Quest edit, pause and delete

Loaded only for an edit, pause or delete request. Every write here needs its own yes to the
exact body or the exact quest. Route rules: [qp-api-contract.md](qp-api-contract.md).

## Editing

There is **no PATCH**. Update is a full-document `PUT`: read the quest, change
what you need, and send the whole object back. Tell the developer this before
editing, because a partial body silently drops everything it omits.

Recipe: take the body of a fresh `GET`, change only the fields the developer
asked for, and send the rest verbatim, `null` values included. Keep the
server-assigned fields (`id`, `created_at`, `updated_at`, `version_id`,
`has_personalization`) as read: the server ignores them on `PUT` (the path
`id` wins). `has_personalization` turns `true` in the next read after a
`webshop_personalization` (no-op) node is added; that is expected, not a diff
to report as a change. A `$schema` link may be present; drop it before the
`PUT`. For a new node, you generate its `id` as a fresh random UUID (v4); the
server does not assign node ids, and existing node ids stay unchanged. Show the
before/after diff of the changed fields before sending.

Dates on edit: a `PUT` with `status: active` re-runs the date rules even when it
changes only `is_public` or a text. Before the proposal, check the read: if
`start_date` is more than 24 hours old, include a start at apply time, and if
`end_date` has passed, an end 7 days later, in the same before/after diff (rule:
[quest-authoring.md](quest-authoring.md#fields)). Say the old window ended; ask
for approval of that edit, not for a date.

An edit to an active quest applies to the next events after the production
configuration propagation window. Repeat the activation confirmations
for the changed part when the edit touches any of: an action's subtype or
parameters, connections that change which actions run, a reward, the
activation limits, the dates, or `status`. An edit to `name` or
`description` only needs no repeat. If the edit changes an amount or SKU,
check node names that mention the old value. Whenever a reward changes, also
check whether the quest name still describes it. If the name mentions the old
reward (for example, Fire Sword changed to Ice Sword), update the quest name in
the same proposed edit and include it in the before/after diff. Ask only if the
intended new name is unclear. The reward-change confirmation covers the
combined reward and name edit.

`version_id` is server-assigned and changes on every write. It is ignored in
the body: there is no optimistic concurrency, quest `PUT` never returns 409,
and the last write wins. Read the quest immediately before a `PUT`.

## Pausing

There is no pause route. To pause, send the full-document `PUT` from the recipe
with `status: inactive` and keep the dates, nodes and limits as they are. The
date rules apply only to `active` writes, so an old `start_date` is fine here;
reactivating later runs them again (see Fields).

While the quest is inactive, events do not run the inactive configuration and
are not replayed automatically on reactivation. During the production
propagation window, an event may still see the previous configuration; warn
before sending an event for a quest with an external reward.

## Deleting

`DELETE {scope}/quests/{id}` needs `questconfig:delete`
(a project key acts with author rights, which include it) and returns 200 with
`{"message": "Quest deleted successfully"}`. It is a soft delete: the quest and
all its triggers get `status: deleted`, so events stop matching it after the
production propagation window, and its execution records stay. After that,
`GET`, the list and
a second `DELETE` treat it as not found: 404 problem+json with
`"detail":"Quest not found"`. A 404
`{"error":"Project not found"}` is a scope answer instead, not a verdict on
the quest; see the auth reference. There is no restore route. Do not use an
update as a restore, and do not `PUT` to a deleted id.

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

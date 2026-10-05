# The quest document

Use the versioned [Quest Platform publisher API contract](qp-api-contract.md)
for production route discovery. Production OpenAPI is intentionally
unavailable. Before writes, make a read-only request against the selected
public gateway; this reference does not replace checking the live response.

Every quest route in this file is project-scoped. Below, `{scope}` stands for
the selected production project scope. The route family, credential and scope
rules are owned by the [versioned API contract](qp-api-contract.md). A 404
`text/plain` body `Cannot GET ...` means a wrong or old route, not a quest or
auth answer; follow [When a route is missing](auth-and-environment.md#when-a-route-is-missing).

A quest is a **graph**, not a flat record. This one fact drives everything else
in this skill.

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
| `end_date` | RFC3339 | **only when `active`** | not in the past, and at or after `start_date`. For a new quest without a requested end or duration, default to 7 days after the selected start; show this in the draft without asking for a date |
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
old `end_date` has passed, propose an end 7 days later. Ask for approval of the
revised edit, not a date. Both dates must be valid when the `PUT` is sent.

A quest runs only while `active` and `start_date <= now <= end_date` at event
time. A future `start_date` is accepted, but events before it do not run the
quest; warn before sending an event outside the window.

Dates are RFC3339 instants. State exact times in UTC whenever you show them,
including a fixed schedule in the draft and a publication read-back. Dates come back in the
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

## Publication after approval

Before asking for approval of the draft quest, resolve the project, reward,
player action, complete graph, proposed schedule, and repeat limits. Use a
publisher-supplied start or propose activation time. Use a publisher-supplied
end, or add the supplied duration to the selected start, or default to 7 days.
Do not ask separately for dates or event-name approval. Inactive quests are an
internal write step only; they are not a separate user-facing draft workflow and are
excluded from the active public quest list.

One approval of the exact publisher proposal authorizes this ordered sequence:

1. `POST` a complete inactive quest with the full graph and reward from the
   approved proposal (required fields plus nodes and connections).
2. `GET` the created quest by id and confirm scope, graph, and reward.
3. Activate with the Editing recipe below (fresh `GET`, full `PUT`): set
   `status` to `active`, apply the approved `start_date`, `end_date`, and
   `activation_limits`. Everything else goes back verbatim. Do not ask a second
   approval for this activation `PUT`.
4. `GET` again and report active status, scope, reward, dates, limits, and
   `version_id`. Do not claim publication complete until this read-back matches
   the approved proposal.

For "no repeat limit", sending `activation_limits` as `null` and leaving it out
are equivalent when the live contract treats the field as optional. `[]` may
also mean no limit; follow the live contract if these forms differ (see
Activation limits).

A relative duration ("run it for 7 days") counts from the `start_date`
actually sent: `end_date` is that start plus 7x24 hours. If the start moves
(for example a requested time has passed), recompute the end under the approved
duration. Show a revised draft for approval only when this changes a fixed
schedule that the publisher explicitly requested.

"Start now" is stamped when the activation `PUT` is built. Show the rule
("start at activation in UTC, end N days later") in the draft. The one approval
covers both timestamps, even when activation happens later than the draft was
shown. Report the actual UTC timestamps from the publication read-back.

## Ambiguous or partial writes

A `POST` that returned 200 created exactly one quest. Take the quest `id` from
that response. If it was not captured, find the quest by name in the list as
below; never send a second `POST` for the same proposal.

After a timeout or 5xx on a quest `POST` or `PUT`, the write may have landed.
Reconcile with bounded read-back from the route contract before any retry:

- For a `PUT`, `GET` the quest by id and compare to the intended document.
- For a `POST`, page the project list (`limit=100` from `page=1` until
  `page*limit >= total`) for the quest's `name`. Continue or repair the same
  quest when safe; never create a duplicate on timeout.
- Show what you found. Ask before any resend that would create a second quest.
- A 422 saved nothing: validation runs before anything is stored.

Tell the publisher that publication did not finish, whether the quest is
visible, and the concrete next step. Never report publication complete until
the active quest and approved configuration read back.

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
  runtime follows the edge only when the source action returns that outcome:
  `ticket_issued`, `no_ticket` or `daily_cap_reached`. Only an `issue_reward`
  with `vc_wallet_ticket` `playtime` returns these outcomes today.
- Every edge must reference a node that exists in `nodes`, and the graph must
  be acyclic.

The smallest quest that can be activated is two nodes and one edge: a trigger
and an action.

Name nodes after what they do, and label anything that is not real in the
name, for example `noop` or `webhook (placeholder)`, so a later read shows it.

### Several actions on one trigger

The quest runtime walks the graph depth-first from the trigger, one node at a time,
in the order the edges are listed under each source node. Several actions on
one trigger therefore run one after another, not in parallel. They are not
independent:

- The first node that fails stops the whole walk. Nodes after it, including
  sibling actions listed later, do not run.
- One failed action makes the whole execution `FAILED`
  (`failReason: ACTION_FAILED`). Actions that already succeeded are not
  rolled back: a reward or notification sent before the failure stays sent.
  A later failure does not roll back an earlier external action.
- A condition miss also stops the walk; see `conditions.md`.
- On the next event for the same user and quest, the runtime skips nodes that
  already succeeded in the failed run and retries the rest according to the
  production runtime contract.

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
configured: every qualifying event runs the actions. Show that unlimited-repeat
behavior, and the resulting payout impact, inside the publication proposal so
the one approval covers it. Do not ask again for the activation `PUT` unless a
material value changed after approval, in which case show the revised proposal
and request approval again. Never silently assume a one-time or per-user limit.

A limit without `time_window` counts over the quest's whole life: `per_user`
`count: 1` means once per user, ever. A retest then needs a new user or a new
quest. With `time_window`, the count resets each calendar day, week or month.
A Web3 reward has its own repeat rule on top; see `rewards.md`.

During the read-only work before the proposal, and before the first write,
check that the intended trigger reaches an intended action and that no intended
node is orphaned. The server validates references and cycles, but those checks
alone do not prove that the quest is semantically usable.

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

## Conversation contract

Keep the publisher experience business-first and progressive:

- Finish all read-only bring-up before any proposal: project GET, reward
  resolution through an available supported capability (see
  [`rewards.md`](rewards.md)), the player action,
  complete graph, proposed schedule and repeat limits. Do not seek plan
  approval before those GETs.
- Show one concise proposal: publisher project name; what the player does; the
  selected reward in business terms (for a named item, its name, SKU and
  image URL); quantity or amount; schedule; repeat limit
  and payout impact. Omit service names, routes, auth, implementation fields
  and narration. Ask only for approval of this draft quest. If the publisher
  wants a change, they will say so; do not request separate confirmation of
  the schedule or event name.
- Propose safe defaults instead of asking for implementation fields. For a
  gameplay quest, use `liveops` internally but describe it as a gameplay quest.
  Do not show `type` in the proposal. For an item reward, propose quantity one,
  purpose `quest_completion`, and one payout per player. Use `AI Toolkit` as
  the internal creator label unless another name was supplied. For a new quest,
  use the publisher's start or start at activation. Use the publisher's end,
  otherwise add their requested duration to the start, otherwise add 7 days.
  Do not ask for missing dates.
- For a named item (`<requested item>`), resolve via
  [`rewards.md`](rewards.md). Never guess an SKU,
  substitute a reward type, or use public web search for catalog lookup. Stop
  before any Quest Platform write when the resolver is absent, unavailable, or
  returns zero candidates; ask the publisher to choose when multiple candidates
  are plausible. The optional headless Web Shop module is independent of the
  quest flow; follow
  [`web-shop-module.md`](web-shop-module.md) only when
  explicitly requested.
- Use the event name the publisher supplied, or derive a stable `snake_case`
  name from the stated player action (for example, `monster_defeated`). Show
  that name in the draft without asking the publisher to confirm it or flagging
  it as an open question. If the publisher names a different game event later,
  revise the draft then.
- One approval of the exact proposal authorizes create, configure, activate and
  read-back. Test events and shop source edits need separate consent. The
  approval request names only publication; never offer, promise or bundle a
  test event in it. Offer the event after publication, with its payload. If an
  answer requests a material change after approval, show the revised draft
  and ask for approval of that change before writing it.
- A Web Shop quest section is optional and requires an explicit request. For
  an existing headless shop, an explicit request to add or update it authorizes
  those source edits; quest publication approval alone does not. For a new shop,
  ask whether to opt in. Keep the module inside catalog content, never in
  navigation, and follow [`web-shop-module.md`](web-shop-module.md).
  Resolve the public URL from the known production host and the connected
  project scope; never ask the developer to supply it or gate integration on a
  live endpoint readiness check.
- Keep merchant IDs, project IDs, auth lanes, headers, hostnames, service names,
  internal paths and workflow narration out of normal replies. Never reveal
  credentials. Use **Summary**, **Proposed setup**, **Need from you**,
  **Next step** when practical; omit empty sections.

## Safety stops for proposals and actions

- **Show the proposed defaults in the draft.** Use the defaults in the
  Conversation contract when the intent is clear and ask only for approval of
  the complete draft. For a gameplay item quest, the trigger, `issue_reward`
  action, quantity one,
  `quest_completion` purpose and one payout per player may be proposed
  together. Never silently choose between multiple catalog matches or
  materially different reward effects; those are blockers to a complete draft.
  A write's yes counts only for the exact draft shown. If the publisher requests
  a change, show the revised draft and ask for approval of it. Keep separate
  approvals for later edits that change live behavior and for each event. For
  "start now", approval covers activation time in UTC and the stated duration;
  do not request a new approval because the clock advanced.
- No action is side-effect free by default. For a smoke test, offer the no-op
  in [`node-subtypes.md`](node-subtypes.md) rather than a
  real reward (placeholders `e2e-noop`, `e2e-sink.invalid`). For publication
  or a smoke test, say production events are not verified until the events
  preflight passes ([production event gate](events.md#production-event-gate)).
- When an external action is part of the proposal, say what it will do once
  active. The publication approval covers that impact for the approved quest.
  An `issue_reward` can create real payouts; `send_http_webhook` sends event
  data to an external URL; `send_xsolla_app_notification` sends a user
  notification. Activate a `webshop_personalization` node only after the
  developer acknowledges that it is a no-op. For an active quest whose only
  action it is, say before any edit or event that it does nothing and a
  `COMPLETED` row proves only that the quest ran; a `PUT` that keeps it active
  needs that acknowledgement, a pause does not.
- Never point `send_http_webhook` at a private service or an
  [unapproved host](node-subtypes.md#send_http_webhook): a webhook
  cannot mint. To pay out a named item, use an `issue_reward` Web3 reward with
  the verified candidate's catalog project and SKU.
- For a named item reward, propose an explicit `per_user` limit of one and
  explain it as one `<requested item>` per player. Do not ask about Backpack or
  regular versus Web3 delivery. Ask only if the developer asks for repeatable
  or unlimited rewards, or if the intended repeat behavior is otherwise
  ambiguous. For other rewards with no `activation_limits`, show unlimited
  repeat in the publication proposal; the one approval covers it. Do not
  silently choose unlimited behavior.

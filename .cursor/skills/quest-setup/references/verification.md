# Verifying that a quest ran

Written against the contract deployed on stage as of 2026-09-22.

Read-back lives on **qp-data**, a separate, read-only service. Follow
[`auth-and-environment.md`](auth-and-environment.md) for current access
requirements. If read-back is unavailable, report that verification is
unavailable and do not infer execution or reward delivery from event acceptance.

`GET /api/v1/quest-executions`

| Query parameter | Use |
|---|---|
| `questId` | the quest you just triggered |
| `userId` | the user the event named |
| `accountId`, `publisherId` | narrow to a scope |
| `status` | filter by execution status |
| `includeNotTriggered` | also show quests that did not fire |
| `latestPerUser` | one row per user |
| `includeEventBody` | include the originating event |
| `page`, `size` | paging |

## What comes back

Each item carries the execution `status`, the originating `eventId` and
`eventName`, the `quest` with the event names it `listensFor`, the `account`,
the `conditionEvals`, and an `actions` array giving **each action node's own
status**.

## Correlate the submitted event first

Save the collector's returned `event_id` with the submitted payload and
`idempotency_key`. Before asserting current completion, require the execution's
`eventId` to equal that `event_id`, for the intended quest, user and scope.
A completed row for the same quest/user may be a historical success while the
new event is pending or failed. Matching quest/user, event name, timestamps or
the latest row alone is not positive event correlation.

For this lookup, omit `status`, set `includeNotTriggered=true` and
`latestPerUser=false`, and page through results as needed. Compare `eventId`
locally; the query parameters above do not include an event-ID filter. Inspect
the newest state for the matching event and that row's action statuses. If no
matching event is visible, report completion as unverified and retry reads only.

After an uncertain submission, if no `event_id` was received, keep **"result
unknown"** unless read-only evidence positively identifies the originating
event and its `eventId`. `includeEventBody=true` can expose the event body for
inspection, but an unrelated success is never sufficient. Do not assume the
`idempotency_key` equals `eventId`, and do not resend the event to obtain an ID.
If positive identification is unavailable, the result remains unknown.

## Three separate claims

Keep these apart when reporting, because conflating them is how a demo ends up
claiming something untrue.

1. **The event was accepted.** Evidence: a 200 from qp-events-collector with an
   `event_id`.
2. **The quest executed and its reward action completed for this event.**
   Evidence: an item for the intended quest/user/scope whose `eventId` matches
   the collector's returned `event_id` (or the positively identified originating
   event after an uncertain submission), with `status: COMPLETED` and the
   intended `issue_reward` action, identified by `nodeId`, also `COMPLETED`.
3. **The token reached the wallet.** **This skill has no evidence for this and
   must not claim it.** Settlement is asynchronous and happens in a service
   this skill never calls.

Report 1 and 2 from evidence. For 3, say that settlement happens separately and
has to be checked in the wallet.

## When nothing comes back

An empty result after submitting an event usually means one of:

- the event `name` does not match the trigger's `event_name`
- the quest is `inactive`
- the user identifier does not match the one the event carried
- an activation limit already consumed the user's allowance
- the execution has not been ingested yet, so retry the read before concluding
  anything

Reading again is safe. Re-sending the event is not.

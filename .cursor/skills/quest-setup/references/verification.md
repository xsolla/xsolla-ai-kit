# Verifying that a quest ran

Stage OpenAPI and local runtime snapshots were checked on 2026-09-23. The
stage deployment revision is not pinned here, so revalidate before writes.

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

Use a bounded client-side read policy: at most six reads over at most 60 seconds
with backoff (for example 2, 5, 10, 15, 15 and 15 seconds). This is a safety
guardrail, not a platform SLA. Then stop and report `unverified`; after an
uncertain submission without an `event_id`, keep `result unknown`.

After an uncertain submission, if no `event_id` was received, keep **"result
unknown"** unless read-only evidence positively identifies the originating
event and its `eventId`. `includeEventBody=true` can expose the event body for
inspection. Use it only when necessary and redact identifiers, emails and
secret-like properties before showing them. An unrelated success is never
sufficient. Do not assume the
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
   must not claim it.** For a Web3 reward, a `COMPLETED` action means the
   minting service returned a transaction hash, so the claim was submitted.
   On-chain finality, the wallet balance and Backpack display are not visible
   to this skill, and the hash is not in qp-data.

Report 1 and 2 from evidence. For 3, say that the claim was submitted and that
delivery has to be checked on chain or in the wallet by a human; see
[`rewards.md`](rewards.md).

## When the execution came back FAILED

A matching item with `status: FAILED` is a result, not a reason to retry. Each
entry in `actions[]` carries its own `status` and `error`, and the `error`
string names the cause, for example a Web3 amount or SKU rejected by the
minting service with a 400.

1. Report the failed action's `nodeId` and its `error` verbatim.
2. Do not resend the event, with the same key or a new one.
3. Fix the quest configuration with the developer; see
   [`rewards.md`](rewards.md) for the Web3 checks.
4. Only after the developer confirms, send a **new** event with a new
   `idempotency_key`, then verify it from the start.

If a Web3 `issue_reward` is still `RUNNING` after the bounded read policy, or
failed on a timeout, the claim may already have paid. Do not send a new event;
follow the duplicate payout note in [`rewards.md`](rewards.md).

## When nothing comes back

An empty result after submitting an event usually means one of:

- the event `name` does not match the trigger's `event_name`
- the quest is `inactive`
- the user identifier does not match the one the event carried
- an activation limit already consumed the user's allowance
- the execution has not been ingested yet, so retry the read before concluding
  anything

Reading again is safe within the bounded policy above. Re-sending the event is not.

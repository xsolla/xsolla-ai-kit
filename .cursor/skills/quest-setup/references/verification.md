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
| `page`, `size` | paging, `size` at most 200 |

There is no event-ID filter, and a useful lookup needs `questId` or `userId`.
If the developer has only an event id, ask for the quest id or the user.
`userId` takes the raw identifier value of any type; a `gamer_id` event
matched with its plain value and came back under `user.gamerId` (observed on
stage 2026-09-25, revalidate).

qp-data answers without a credential and holds every tenant's data. Query it
only with the developer's own quest id, user id or event, and never list
accounts or other tenants' quests or executions.

## What comes back

Each item carries the execution `status`, the originating `eventId` and
`eventName`, the `quest` with the event names it `listensFor`, the `account`,
the `conditionEvals`, and an `actions` array giving **each action node's own
status**. An action entry has `nodeId`, `status`, `actionType`, `name`,
`parameters`, `reward` for an `issue_reward`, and `error` when it failed; it
carries no provider result. `conditionEvals` is empty for a quest without a
condition. A row may name a quest whose `quest.status` is `deleted`; rows stay
after a soft delete.

qp-data has no running state. The worker writes the row once the execution has
finished, so an execution still in flight shows as no row.

| Level | Value | Meaning |
|---|---|---|
| execution `status` | `COMPLETED` | finished without a failure |
| | `FAILED` | see `failReason`: `ACTION_FAILED` (an action failed), `CONDITION_EVAL_FAILED` (a condition could not be evaluated) or `ACTIVATION_LIMIT_HIT` |
| | `IN_PROGRESS` | a condition was not met for this event; `actions` is empty. Waiting for more events, not stuck. The row never changes; a later event gets its own row |
| | `NOT_TRIGGERED` | the worker ran but the quest was not live when the worker loaded it. Listed only with `includeNotTriggered`. Rare, see "When nothing comes back" |
| action `status` | `COMPLETED`, `FAILED` | per action node |

For `IN_PROGRESS`, read `conditionEvals`: each entry has `nodeId`, `operator`,
`expected`, `actual` and `matched`. For an event-count condition, another
qualifying event advances `actual`, but it is a new event and needs the
developer's confirmation.

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
inspection. Its `eventBody` carries `id` (equal to `eventId`),
`idempotency_key`, `account_id`, `publisher`, `user_ids` and
`server_timestamp`. A matching `idempotency_key` identifies your event,
because you generated it fresh. Compare locally, and do not print bodies; if
one must be shown, redact identifiers, emails and secret-like properties. An
unrelated success is never sufficient. Do not assume the `idempotency_key`
equals `eventId`, and do not resend the event to obtain an ID: a second POST
with the same key returns a new `event_id` that never appears in qp-data. If
positive identification is unavailable, the result remains unknown.

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
[`rewards.md`](rewards.md). A `web3_item` repeat for the same user and quest is
`COMPLETED` without a new mint.

For "is it in my wallet" or "what is the tx hash", give the developer this:
search the chain explorer (see
[`auth-and-environment.md`](auth-and-environment.md)) by the wallet address
from the wallet lookup, filter to the token's `contractAddress` from the
currency bindings, and look around the execution's `ingestedAt`. For the exact
hash, the Quest Platform team can read the worker's logs or ledger given the
quest id, `event_id`, `idempotency_key` and user.

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

If a Web3 execution still has no row after the bounded read policy, or its
`issue_reward` failed on a timeout, the claim may already have paid. Do not send a new event;
follow the duplicate payout note in [`rewards.md`](rewards.md).

## When nothing comes back

An empty result after submitting an event usually means one of:

- the event `name` does not match the trigger's `event_name`
- the quest is `inactive`, or `active` but outside its dates at event time,
  either not started yet or already ended
- the event's `publisher` does not equal the quest's `publisher_id` and
  `project_id`
- the event carried `properties.load_test: "true"`; this is expected, see
  [`events.md`](events.md)
- the event arrived within the config cache time after the quest was created,
  activated or edited
- the user identifier does not match the one the event carried
- the execution has not been ingested yet, so retry the read before concluding
  anything

Do not promise a `NOT_TRIGGERED` row for an event outside the window. The
consumer drops an event unless some quest of the account with that event name
is live, and a dropped event leaves no row at all, even with
`includeNotTriggered=true`. A `NOT_TRIGGERED` row appears only when the worker
ran and then found the quest not live, for example because another quest with
the same event name matched.

An activation limit that is already used up is not an empty result: it shows
as `FAILED` with `ACTIVATION_LIMIT_HIT`.

Reading again is safe within the bounded policy above. Re-sending the event is
not. The worker writes each row once, when the execution ends, so a result
that stays wrong for days will not fix itself: escalate to the Quest Platform team with the quest id,
`event_id`, `idempotency_key`, user and time.

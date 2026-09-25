# Verifying that a quest ran

Stage OpenAPI and local runtime snapshots were checked on 2026-09-23; paging,
the project-lane fields and the worker's action walk were rechecked on
2026-09-25, and the qp-data query parameters against the live OpenAPI on
2026-09-25 after 09:00Z. The stage deployment revision is not pinned here, so revalidate
before writes.

Since about 09:20Z on 2026-09-25 the collector on stage has no event route
for the project credential (see [`events.md`](events.md)), so no new
execution from a Basic-lane event can appear. Reads of earlier executions
still work.

A read-only verification task still needs a preflight, but only for the
services it calls: the qp-server project GET and the project-scoped quest
read (which is also the ownership check below), then the qp-data status read.
Skip the collector; see "Service preflight" in
[`auth-and-environment.md`](auth-and-environment.md).

Read-back lives on **qp-data**, a separate, read-only service. Follow
[`auth-and-environment.md`](auth-and-environment.md) for current access
requirements. If read-back is unavailable, report that verification is
unavailable and do not infer execution or reward delivery from event acceptance.

`GET /api/v1/quest-executions`

| Query parameter | Use |
|---|---|
| `questId` | the quest you just triggered |
| `userId` | the user the event named |
| `accountId`, `publisherId` | narrow to a scope. For a project-route quest, `publisherId` is the merchant id; there is no `projectId` filter on executions |
| `status` | filter by execution status: `NOT_TRIGGERED`, `IN_PROGRESS`, `COMPLETED`, `FAILED` (case-insensitive, repeat for several). When set, it overrides `includeNotTriggered` |
| `includeNotTriggered` | also show quests that did not fire |
| `latestPerUser` | one row per user |
| `includeEventBody` | include the originating event |
| `page`, `size` | paging. `page` starts at 1 (`page=0` returns 422); `size` is 1 to 200, default 50 |

There is no event-ID filter, and a useful lookup needs `questId` or `userId`.
If the developer has only an event id, ask for the quest id or the user. An
event id does not prove ownership: the quest you then read by still needs the
ownership check below before any qp-data read.
`userId` takes the raw identifier value of any type; a `gamer_id` event
matched with its plain value and came back under `user.gamerId` (observed on
stage 2026-09-25, revalidate).

qp-data answers without a credential and holds every tenant's data. Query it
only with the developer's own quest id, user id or event, and never list
accounts or other tenants' quests or executions. To list the developer's
quests there, scope `GET /api/v1/quests` by `publisherId` and `projectId` of
the confirmed project (the executions route has no `projectId` filter).

Before the first qp-data read by quest id, confirm the quest is the
developer's: read it on qp-server with the project-scoped quest read
(`GET .../quests/{id}` under the merchant and project path; the exact path is
in [`auth-and-environment.md`](auth-and-environment.md)). A 200 proves it
belongs to that project. A 404 means "not visible with this credential"; then do not read
its executions from qp-data. A quest id the developer only pasted, without that
read, is not confirmed. On a returned row, `quest.publisherId` and
`quest.projectId` should equal the quest's values; `account.id` is the
project's Quest Platform account.

### Quest not visible with your credential

When the quest read returns 404 (or the quest is on another project, merchant
or lane, for example one created with a service key while the developer is on
Basic), do not read its executions from qp-data, even when the developer
insists or says it is theirs, and even though qp-data would answer. Say that
this credential cannot see the quest, so the skill cannot verify it. Offer
two ways forward: the developer switches to the credential of the project
that owns the quest, or hands the case to the Quest Platform team with the
quest id, the `event_id` if any, the `idempotency_key`, the user and the send
time.

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
| | `FAILED` | see `failReason`: `ACTION_FAILED` (an action failed) or `CONDITION_EVAL_FAILED` (a condition could not be evaluated). The live OpenAPI types `failReason` as a plain string, so report any other value verbatim. The data model also allows `ACTIVATION_LIMIT_HIT`, but the current worker writes no row for a used-up limit; see "When nothing comes back" |
| | `IN_PROGRESS` | a condition was not met for this event; `actions` is empty. Waiting for more events, not stuck. The row never changes; a later event gets its own row |
| | `NOT_TRIGGERED` | the worker ran but the quest was not live when the worker loaded it. Listed only with `includeNotTriggered=true` or `status=NOT_TRIGGERED`. Rare, see "When nothing comes back" |
| action `status` | `COMPLETED`, `FAILED` | per action node |

For `IN_PROGRESS`, read `conditionEvals`: each entry has `nodeId`, `operator`,
`expected`, `actual` and `matched`. For an event-count condition, another
qualifying event advances `actual`, but it is a new event and needs the
developer's confirmation.

## Reading a row with several actions

How the worker runs several actions on one trigger (one at a time, the first
failure stops the rest, nothing is rolled back) is in "Several actions on one
trigger" in [`quest-document.md`](quest-document.md). For the read-back, from
the worker code on stage 2026-09-25, not observed live, revalidate:

- `actions[]` lists only the actions the walk reached, in the quest's `nodes`
  order, not in run order. An action missing from it did not run. After the
  first failed action the later ones are absent, not pending; they will not
  run for this event.
- An execution `FAILED` with some actions `COMPLETED` means those actions'
  effects happened, for example a reward was paid. Report them as done, and
  do not resend to "finish" the run.
- A failed run does not use up an activation limit; the worker rolls the
  counter back.
- **A row that follows a `FAILED` run for the same user and quest can show
  `COMPLETED` actions that did not run for this event.** The worker resumes
  the failed run, skips the actions that already completed, and carries them
  into the new row. They ran for the earlier event.

When you report, name each action by `nodeId` with its status, and name every
action in the graph that is missing from `actions[]` as "not reached".

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

When the send time is unknown, for example the developer asks later about an
earlier event, the policy above has no start. Run one round of reads, match
by `eventId` or a fresh `idempotency_key`, and if nothing matches report
`unverified` and ask when the event was sent. Rows appear within seconds, and
a Web3 reward's retries end within about 10 minutes. A non-Web3 row still
missing 15 minutes after a known send time will not appear: escalate as at
the end of this file. For a Web3 reward, escalate as soon as the read policy
ends empty; see [`rewards.md`](rewards.md). These are client guardrails, not a
platform SLA.

After an uncertain submission, if no `event_id` was received, keep **"result
unknown"** unless read-only evidence positively identifies the originating
event and its `eventId`. `includeEventBody=true` can expose the event body for
inspection. Its `eventBody` carries `id` (equal to `eventId`),
`idempotency_key`, `account_id`, `publisher`, `user_ids` and
`server_timestamp`. A matching `idempotency_key` identifies your event,
because you generated it fresh. Compare locally, and do not print bodies; if
one must be shown, redact identifiers, emails and secret-like properties. An
unrelated success is never sufficient. The key match is strong evidence only
for a key you generated fresh for this event. If the developer supplied or
reused the key, another event may carry it: also require the user and a
`server_timestamp` close to your send time, and say the identification is
weaker. Do not assume the `idempotency_key`
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
   `idempotency_key`, then verify it from the start. For the same user it
   resumes the failed run: actions that already completed are not repeated;
   see "Reading a row with several actions".

If a Web3 execution still has no row after the bounded read policy, or its
`issue_reward` failed on a timeout, the claim may already have paid. Do not send a new event;
follow the duplicate payout note in [`rewards.md`](rewards.md).

## When nothing comes back

Before naming a cause, `GET` the quest and compare it with the payload you
sent. Name only causes that the quest document, the payload or the timing
support; do not list a cause you have not checked. An empty result after
submitting an event usually means one of, in this order:

- the event's `publisher` does not equal the quest's `publisher_id` and
  `project_id`, or the event went to another project or route than the
  quest's; see [`events.md`](events.md)
- the event `name` does not match the trigger's `event_name`
- the quest is `inactive`, or `active` but outside its dates at event time,
  either not started yet or already ended
- the event carried `properties.load_test: "true"`; this is expected, see
  [`events.md`](events.md)
- the event arrived within the config cache time after the quest was created,
  activated, paused or edited
- the user identifier does not match the one the event carried
- the quest's `activation_limits` were already used up for this user or
  globally. Read the limits first; the worker stops before it writes a row
- the execution has not been ingested yet, so retry the read before concluding
  anything

Do not promise a `NOT_TRIGGERED` row for an event outside the window. The
consumer drops an event unless some quest of the account with that event name
is live, and a dropped event leaves no row at all, even with
`includeNotTriggered=true`. A `NOT_TRIGGERED` row appears only when the worker
ran and then found the quest not live, for example because another quest with
the same event name matched.

An empty read-back alone cannot say whether the event was dropped or is not
ingested yet. Rows for simple actions appeared about 1 to 2 seconds after the
event and Web3 rewards up to about 10 seconds, typically about 5 (observed
on stage 2026-09-25, revalidate), so an empty result after the full read policy is not ingest
delay. Then the quest's state at event time decides: if the quest was
inactive, outside its dates or mismatched, say the event was dropped for that
reason. An event sent within the cache time after a write may still have run
on the old config, and then it has a row.

An activation limit that is already used up leaves no row: the worker drops
the run before it writes to qp-data (worker code on stage 2026-09-25, not
observed live, revalidate). Name it only when the quest's limits and earlier
completed rows for that user support it.

Reading again is safe within the bounded policy above. Re-sending the event is
not. The worker writes each row once, when the execution ends, so a result
that stays wrong for days will not fix itself: escalate to the Quest Platform team with the quest id,
`event_id`, `idempotency_key`, user and time.

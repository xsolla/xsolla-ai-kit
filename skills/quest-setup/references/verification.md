# Verification

Status and diagnostics are read-only. They never invoke onboarding or event submission;
list/status keeps the SKILL shortcut, without docs refresh or project preflight.
Use production evidence only, never another environment or an internal key.

## Read-back gate

Read the quest with the selected authenticated production scope and confirm ownership.
Before any execution query, check [Execution read-back](qp-api-contract.md#execution-read-back).
If publisher Basic is refused or the documented probe is a router miss, report read-back
unavailable and stop, with no OpenAPI fetch or fallback key. When supported, query only
the developer's own quest/user/event, never unscoped tenant data. The shapes below are
orientation, not permission to call an unavailable route.

## Why a quest did not complete

Do not list likely causes. Say what you would check, such as the execution read for that player when read-back is usable, or the quest's settings and the event gate otherwise, then ask. Keep to the limits in [reply-format.md](reply-format.md#rules).

## What comes back

An execution read may include a status, event identifier, quest identifier,
user identifier and action results. Treat unknown fields as opaque and report
them only when they explain the outcome.

| Result | Meaning |
|---|---|
| `COMPLETED` | the execution finished according to the production contract |
| `FAILED` | an action or condition failed; read the returned error |
| `IN_PROGRESS` | the condition or execution is not complete |
| `NOT_TRIGGERED` | the event was received but did not run the quest, when supported |

An `IN_PROGRESS` or missing row is not proof that a reward claim is still
running. Follow the contract's timing and retry guidance.

## Correlate the submitted event first

Use the exact event identifier returned by event submission (`event_id`) and
match it to the execution's `eventId`. Also compare the quest id and user
identity. If any of these do not match, report that the event was not proven to
execute this quest.

Do not infer execution from a 200 event response alone. Do not resend an event
after a timeout or unknown response.

## Reading a row with several actions

Read each result in `actions[]` separately. An action absent from the result did not
run. A `COMPLETED` action inside an overall `FAILED` execution did happen and
is not rolled back. Do not resend a reward event merely to finish later nodes.

For a failed action, report the returned error verbatim and stop before any
retry that could create a duplicate external effect.

## Three separate claims

Keep these claims separate:

1. the event was accepted;
2. the quest execution completed;
3. the Web3 reward is visible in the player's Backpack or has reached finality.

This skill can report the first two only when the production contracts prove
them for the publisher credential. It must not claim the third from an
execution row alone.

## When nothing comes back

Use the bounded read policy from the contract. If the event identifier is
absent after that policy, report that execution was not found and do not resend
automatically. A condition miss or activation limit may produce no completed
action; do not call it a reward failure without evidence.

## Unknown results

An unknown event or reward outcome is a safety stop. Preserve the original
event id, idempotency key, quest id, user and send time. Escalate with those
values or perform the documented read-only lookup when it is publisher-usable.
Never generate a new event to discover what happened.

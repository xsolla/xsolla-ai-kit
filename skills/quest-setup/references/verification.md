# Verification

Verification runs on the target selected by `XSOLLA_QP_ENV` (production when
absent). The event must pass the gate in
[`events.md`](events.md), and execution read-back must be publisher-usable per
[`qp-api-contract.md`](qp-api-contract.md) before any read-back call. Never use
staging execution data as proof of a production run. Never use an internal
service key to force read-back.

## Read-back gate

1. Read the quest through the authenticated production Quest Platform scope.
2. Confirm that the quest belongs to that scope.
3. Confirm execution read-back from [`qp-api-contract.md`](qp-api-contract.md):
   the route template, auth lane, and probe result. If the contract says the
   publisher Basic lane is not accepted, or the production probe is a router
   miss, stop and report that execution read-back is unavailable to the
   publisher credential. Do not fetch production OpenAPI, and never fetch stage
   OpenAPI on a production run.
4. When read-back is publisher-usable, query only the developer's own quest,
   user or event. Never use an unscoped query that could return another
   tenant's data.
5. **STAGE DEMO ONLY:** when the [stage demo gate](stage-demo.md#gate) passes,
   read-back is publisher-usable through
   [Execution read-back](stage-demo.md#execution-read-back) for the developer's
   own quest and user. No key is sent. Every other run keeps step 3.

The shapes below summarize the versioned contract. Do not call a route the
contract marks unavailable to the publisher key.

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

Read each action result separately. An action absent from the result did not
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

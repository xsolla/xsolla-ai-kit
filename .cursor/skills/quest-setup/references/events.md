# Events

This skill sends events only through the event-ingestion route in
[`qp-api-contract.md`](qp-api-contract.md) on the production base. Confirm that
contract's publisher Basic lane and the production probe result before the
first event. Never use another environment's service, an internal key or a
guessed route as a fallback.

## Production event gate

Before sending an event:

1. Confirm `POST /api/v2/events` on the public production base from
   [`qp-api-contract.md`](qp-api-contract.md), including the publisher Basic
   lane and required `publisher` body fields.
2. Confirm that the event's publisher/project block matches the selected
   production quest scope.
3. If the contract marks the route unavailable to the publisher key, or the
   documented probe shows a router miss, stop and report that production event
   execution is not verified. Do not fetch OpenAPI.
4. If the quest is inactive or outside its dates, say that an event could not
   run it and offer activation first.

For a mixed request, complete the separately confirmed quest work first. Then
report the event blocker with the quest id, current status and trigger name.
Do not claim the quest was verified.

## Payload

```json
{
  "idempotency_key": "<uuid>",
  "name": "<event_name from the trigger>",
  "client_timestamp": "<RFC3339 timestamp>",
  "user_ids": [{"identifier_type": "xsolla_id", "value": "<uuid>"}],
  "quest_id": "<uuid>",
  "scope": "private",
  "publisher": {"publisher_id": "<string>", "project_id": "<string>"},
  "properties": {"key": "string value"}
}
```

| Field | Required | Rules |
|---|---|---|
| `idempotency_key` | yes | valid, non-zero UUID; generate a fresh one per event |
| `name` | yes | must match the quest trigger's `event_name` |
| `client_timestamp` | yes | RFC3339 |
| `user_ids` | yes | at least one entry |
| `quest_id` | no | valid UUID when present; restricts matching to one quest |
| `scope` | no | default `private` unless the developer asks otherwise |
| `publisher` | yes for Basic lane | must match the quest's read-back scope; positive integer Xsolla IDs |
| `properties` | no | use only values accepted by the contract; never include secrets |

`user_ids[].identifier_type` is `xsolla_id`, `gamer_id`, `guest_id` or `email`
per the contract. A Web3 reward requires an `xsolla_id` whose user already has
a wallet. Check it with the recipient read in `auth-and-environment.md` before submitting.

A successful response returns `event_id` (and echoes `idempotency_key`). Keep
`event_id` and use it to correlate the read-only execution result when
read-back is publisher-usable. If the response shape differs, follow the
versioned contract, not a guessed OpenAPI fetch.

## Before sending

- Wait for the production runtime to refresh after a quest write, according to
  the contract.
- Check that the quest is active and inside its date window.
- Show the exact payload, including the generated `idempotency_key`.
- If the developer changes anything, generate a new key and show the payload
  again.

## Test events

Do not use a test bypass unless the production contract documents it and the
developer explicitly wants acceptance testing rather than execution. To verify
execution, send a normal event and warn that matching actions may run for real.

## Idempotency

The body `idempotency_key` identifies the event. Do not confuse it with an
optional HTTP idempotency header unless the contract requires one. Generate a
fresh UUID per event.

## After an uncertain response

If the request times out or the outcome is otherwise unknown, stop. Do not
resend with the same or a new key. Report "result unknown" and use the
read-only execution check to find out what happened when that check is
publisher-usable.

If the developer later agrees to a new event, show the saved payload or ask for
it again, generate a new key and get a new yes.

### An event the developer sent, not you

When the developer says their own script or tool sent an event, you never saw
the request or response. Do not resend it. Ask for the payload or, at minimum,
the quest id, name, idempotency key, user and send time. Then verify read-only
as described in [`verification.md`](verification.md).

## Flow step detail: submitting an event

5. **Event.** Production event submission is allowed only after the event
   gate in [`events.md`](events.md) confirms the
   versioned contract route and publisher Basic lane. Until then, do not send
   an event; say event execution is not yet verified. Never fall back to
   an internal key or a different route. For an `inactive` quest, say
   an event could not run it anyway. Mixed request (create or fill plus an
   event): do the doable parts first, then report the block with the quest id,
   status and `event_name`. Event submission always needs its own approval,
   separate from publication.

## Safety stops for events and failed rewards

- Events (once a route exists): each event needs its own payload shown and
  its own yes, including "send it again"; for a reward quest, say first
  whether a repeat can pay again. After an uncertain response, such as a
  timeout, **do not resend** with any key: report "result unknown" and stop.
- After a timeout or 5xx on a quest `POST` or `PUT`, reconcile before retry per
  [Ambiguous or partial writes](quest-document.md#ambiguous-or-partial-writes).
  A 422 saved nothing: validation runs before anything is stored.
- After a `FAILED` reward action, do not resend the event. Fix the quest, then
  send a new event with a new key only after the developer confirms.
- A missing or timed-out Web3 reward row is never a reason to send another
  event: the reward may already have paid; see
  [`rewards.md`](rewards.md).

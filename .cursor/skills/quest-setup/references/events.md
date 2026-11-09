# Events

Use only [the contract's production event route and Basic lane](qp-api-contract.md#event-ingestion).
No alternate environment, internal key or guessed-route fallback.

## Login event with Xsolla ID

For "add a login event that uses my Xsolla ID", the live docs support this much and no more:

- The quest trigger is a `dynamic_event` node whose `event_name` matches the name the site sends.
- A publisher event identifies the player in `user_ids[]` with `identifier_type` `xsolla_id`
  (other types: `gamer_id`, `guest_id`, `email`).
- The Quests block sends `login_xsolla_id` once, from the browser with the player's token (live run,
  2026-11-05). The public docs do not name it. A quest that reacts to it uses a `dynamic_event`
  trigger with `event_name` `login_xsolla_id` and `client_sendable: true`
  ([node-subtypes](node-subtypes.md#dynamic_event-client_sendable)). For any other name, follow
  [Choosing a trigger](node-subtypes.md#choosing-a-trigger); never infer a configured login binding
  from a quest title.
- Never write `autoEvents` or `loginEventName` on the block: the gate cannot write them (they are not in its patchable settings). The block sends events itself once the player is authorized, and a quest trigger must match the event name exactly.

An "add" request never modifies an existing quest. First list the quests (two calls, see SKILL.md)
and check whether a quest already uses a login-type trigger. Tell the publisher what exists (quest
name, event name, status) and ask ONE question: create a new quest, or edit that quest. An edit then
needs its own before/after diff and yes ([quest-edit.md](quest-edit.md#editing)). The event name
must match the site's actual binding under [Choosing a trigger](node-subtypes.md#choosing-a-trigger).
Never invent or rename a live event name on an active quest, and never re-point an
existing quest's trigger as part of an "add".

For a new quest, show the trigger and event name, wait for a yes in the same conversation, make the
change, then read the quest back and report the trigger as saved. Say that the site must send this
event itself.

## Production event gate

Before any send, confirm the documented project-scoped production POST and publisher
Basic lane against live docs and [the snapshot](qp-api-contract.md#event-ingestion).
Path IDs must match the selected production quest scope; the body has no `publisher`.
If the contract is unavailable to the key or its documented probe is a router miss,
stop and report production event execution unverified. Never fetch OpenAPI.
An inactive or out-of-date quest cannot run: offer activation first.
For mixed requests, finish separately approved quest work first, then report the event
blocker with quest id, current status and trigger name. Do not claim verification.

## Payload

Snapshot of the live docs for `POST /api/v2/merchants/{merchant_id}/projects/{project_id}/events`.
The body accepts only the fields below: any other field, including `publisher`, is
rejected. If the live docs differ, the live docs win.

```json
{
  "idempotency_key": "<uuid>",
  "name": "<event_name from the trigger>",
  "client_timestamp": "<RFC3339 timestamp>",
  "user_ids": [{"identifier_type": "xsolla_id", "value": "<uuid>"}],
  "quest_id": "<uuid>",
  "scope": "private",
  "properties": {"key": "string value"}
}
```

| Field | Required | Rules |
|---|---|---|
| `idempotency_key` | yes | a UUID; generate a fresh one per event, reuse the same one only when retrying that event |
| `name` | yes | must match the quest trigger's `event_name` |
| `client_timestamp` | yes | RFC3339 |
| `user_ids` | yes | at least one `{identifier_type, value}`; nonempty `value`; `xsolla_id` requires UUID, `email` requires `@` |
| `quest_id` | no | string containing a valid UUID when present; restricts matching to one quest |
| `scope` | no | one of `global`, `private`, `within_project`, `within_quest`, `within_publisher`; default `private` unless the developer asks otherwise |
| `properties` | no | object containing only contract-accepted values; never include secrets |

`user_ids[].identifier_type` is `xsolla_id`, `gamer_id`, `guest_id` or `email`
per the contract. A Web3 reward requires an `xsolla_id` whose user already has
a wallet. Ask the publisher to confirm it in Publisher Account as described in [`rewards.md`](rewards.md#recipient-wallet) before submitting.

A successful response returns `event_id` (and echoes `idempotency_key`). Keep
`event_id` and use it to correlate the read-only execution result when
read-back is publisher-usable. If the response shape differs, follow the
versioned contract, not a guessed OpenAPI fetch.

A 401 `Authentication required` or `Invalid credential` is uniform publisher denial,
not a project enumeration result. A 422 is payload validation.
A 503 `Credential validation is temporarily unavailable` says nothing about key validity.
Follow [auth errors](auth-credentials.md#errors).

The body key, not an optional HTTP header, identifies the event unless the contract
explicitly requires a header. Key reuse never authorizes an automatic resend.

## Client events

The Quests block and game clients send events with the player's token, not a publisher key. The body
has only `idempotency_key`, `name`, `client_timestamp` and `properties`. The token identifies the
player, so `user_ids`, `quest_id` and `scope` are not sent.

- An event is accepted only while an active quest of the project allows it: a `dynamic_event` trigger
  with `client_sendable: true`, or an event operand with `include_client_events: true`. Otherwise the
  answer is 403.
- 404 means the client endpoint is off in that environment. The endpoint is rate limited.
- Event-count checks count a client event only where the operand sets `include_client_events`.

## Before sending

- Wait for the production runtime to refresh after a quest write, according to
  the contract.
- Check that the quest is active and inside its date window.
- Show the exact payload, including the generated `idempotency_key`.
- If the developer changes anything, generate a new key and show the payload
  again.
- Get a separate yes to this exact payload, including any repeat, and explain whether
  it can pay again. Publication approval never covers an event.

## Test events

A test event is for a real player of the publisher's project. The Xsolla ID in `user_ids` must come
from the publisher and be a real Xsolla ID UUID. Never invent or reuse a made-up player id. If they
give something that is not a UUID, or none, ask for the real one and stop. The quest must be active
for the event to run it; activation is its own yes, never implied by the event yes. Write the event
body to a file in the one `mktemp -d` folder and pass `--body-file <that file>`; never pipe it through
`/dev/stdin` or a heredoc, and never retry a failed send in a loop.

Do not use a test bypass unless the production contract documents it and the
developer explicitly wants acceptance testing rather than execution. To verify
execution, send a normal event and warn that matching actions may run for real.

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

## Safety stops for events and failed rewards

- After a timeout or 5xx on a quest `POST` or `PUT`, reconcile before retry per
  [Ambiguous or partial writes](quest-publish.md#ambiguous-or-partial-writes).
  A 422 saved nothing: validation runs before anything is stored.
- After a `FAILED` reward action, do not resend the event. Fix the quest, then
  send a new event with a new key only after the developer confirms.
- A missing or timed-out Web3 reward row is never a reason to send another
  event: the reward may already have paid; see
  [`rewards.md`](rewards.md).

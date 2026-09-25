# Events

Stage OpenAPI and local runtime snapshots were checked on 2026-09-23. The
stage deployment revision is not pinned here, so revalidate before writes.

Events go to **qp-events-collector**, not to qp-server. Sending an event to
qp-server produces a 404 that looks like a missing quest.

`POST /api/v2/events`

## Payload

```json
{
  "idempotency_key": "<uuid>",
  "name": "<event_name from the trigger>",
  "client_timestamp": "2026-09-22T10:30:00Z",
  "user_ids": [{"identifier_type": "xsolla_id", "value": "<uuid>"}],
  "quest_id": "<uuid>",
  "scope": "private",
  "publisher": {"publisher_id": "<string>", "project_id": "<string>"},
  "properties": {"any": "string values only"}
}
```

| Field | Required | Rules |
|---|---|---|
| `idempotency_key` | yes | a valid, non-zero UUID. Any version is accepted despite the schema hinting at v4 |
| `name` | yes | must match the `event_name` on the quest's `dynamic_event` trigger |
| `client_timestamp` | yes | RFC3339 |
| `user_ids` | yes | at least one entry |
| `quest_id` | no | a valid UUID when present. Restricts matching to that one quest; without it, every live quest of the account with that `event_name` runs |
| `scope` | no | `global`, `private`, `within_project`, `within_quest`, `within_publisher`. Defaults to `private`. It decides which quests' event-count conditions can count this event later, not which quest runs. Keep the default unless the developer asks. The published schema shows a bare string and the older struct hint lists only three values; the server accepts all five |
| `publisher` | no | if the object is present, the live schema requires both `publisher_id` and `project_id`. They must equal the quest's values, or the event matches no quest and leaves no execution row. Omit it for a quest without them |
| `properties` | no | string values only |

`user_ids[].identifier_type` is `xsolla_id`, `gamer_id`, `guest_id` or `email`.
An `xsolla_id` value must parse as a UUID; an `email` value must contain `@`;
`gamer_id` and `guest_id` need only be non-empty.

A quest with a `web3_item` or `web3_token` reward needs an `xsolla_id` entry
whose user already has a wallet. Check it before submitting; see
[`rewards.md`](rewards.md).

The account is **not** in the body. It comes from the credential.

A 200 returns `{"idempotency_key": "...", "event_id": "<uuid>"}`.

Use only `POST /api/v2/events`. The collector's other routes,
`/api/v2/projects/{project_id}/events` and `/api/v2/debug/trigger-outbox`, are
not part of this skill; do not call them.

## Before sending

- **Wait after a quest write.** The pipeline caches quest config for up to 60
  seconds (see [`auth-and-environment.md`](auth-and-environment.md)). After
  creating, activating or editing a quest, wait about 90 seconds before the
  first event, or the event may be matched against the old config.
- **Check the window.** The quest must be `active` and inside its dates at
  event time; see [`quest-document.md`](quest-document.md).
- **Show the exact payload**, including the `idempotency_key` you generated.
  If the developer changes anything, generate a new key.

## Test events and `load_test`

`properties.load_test` set to exactly `"true"` makes quest-engine drop the
event before it starts a workflow, where the bypass is enabled (see
[`auth-and-environment.md`](auth-and-environment.md)). The collector still
returns 200 with an `event_id`, but the quest never runs and qp-data gets no
row. Report that as the expected outcome, not as unverified.

- Use it only when the developer wants to test acceptance, not execution.
- To verify execution, omit it. Each untagged event that matches a live quest
  starts a billable workflow and runs its actions for real, so say so and get
  the developer's explicit choice. Removing the flag from a test payload turns
  it into a real event and needs the same decision.
- Any value other than the exact string `"true"` does not bypass.

## Idempotency

There are two separate mechanisms and they are easy to confuse:

- the body field `idempotency_key`, which the platform uses as the message key
- a generic HTTP `X-Idempotency-Key` header handled by middleware, which must
  be exactly 36 characters

Use the body field. Generate a fresh UUID per event.

## After an uncertain response

If the request times out or the outcome is otherwise unknown, **stop**. Do not
resend, not with the same key and not with a new one. A timeout is not a
failure: the event may have been accepted and the quest may already be paying
out. Report "result unknown", and use the execution read-back to find out what
really happened.

If the developer later agrees to a new event, use the saved payload or ask
them to paste it again, show it, and get a new yes. Never rebuild it from memory or from a read-back
`eventBody`.

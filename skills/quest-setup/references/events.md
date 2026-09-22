# Events

Written against the contract deployed on stage as of 2026-09-22.

Events go to **qp-events-collector**, not to qp-server. Sending an event to
qp-server produces a 404 that looks like a missing quest.

`POST /api/v2/events`

## Payload

```json
{
  "idempotency_key": "<uuid>",
  "name": "web3.token_test",
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
| `quest_id` | no | a valid UUID when present |
| `scope` | no | `global`, `private`, `within_project`, `within_quest`, `within_publisher`. Defaults to `private`. The published schema shows a bare string and the older struct hint lists only three values; the server accepts all five |
| `publisher` | no | if the object is present and non-empty, `publisher.publisher_id` is required |
| `properties` | no | string values only |

`user_ids[].identifier_type` is `xsolla_id`, `gamer_id`, `guest_id` or `email`.
An `xsolla_id` value must parse as a UUID; an `email` value must contain `@`;
`gamer_id` and `guest_id` need only be non-empty.

The account is **not** in the body. It comes from the credential.

A 200 returns `{"idempotency_key": "...", "event_id": "<uuid>"}`.

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

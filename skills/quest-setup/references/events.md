# Events

Events go to the events endpoint on the same host, with the same credential
as quest configuration; see [`auth-and-environment.md`](auth-and-environment.md).

`POST /api/v2/projects/{project_id}/events`

`project_id` is `XSOLLA_PROJECT_ID`. The project is taken from the path, so
the body names no publisher, project or account.

## Payload

```json
{
  "idempotency_key": "<uuid>",
  "name": "<event_name from the trigger>",
  "client_timestamp": "2026-01-15T10:30:00Z",
  "user_ids": [{"identifier_type": "xsolla_id", "value": "<uuid>"}],
  "quest_id": "<uuid>",
  "scope": "private",
  "properties": {"any": "string values only"}
}
```

| Field | Required | Rules |
|---|---|---|
| `idempotency_key` | yes | a valid, non-zero UUID. Any UUID version is accepted |
| `name` | yes | must match the `event_name` on the quest's `dynamic_event` trigger |
| `client_timestamp` | yes | RFC3339 |
| `user_ids` | yes | at least one entry |
| `quest_id` | no | a valid UUID when present |
| `scope` | no | `global`, `private`, `within_project`, `within_quest`, `within_publisher`. Defaults to `private` |
| `properties` | no | string values only |

`user_ids[].identifier_type` is `xsolla_id`, `gamer_id`, `guest_id` or `email`.
An `xsolla_id` value must parse as a UUID; an `email` value must contain `@`;
`gamer_id` and `guest_id` need only be non-empty.

A quest with a `web3_item` or `web3_token` reward needs an `xsolla_id` entry
whose user already has a wallet. Confirm it with the developer before
submitting; see [`rewards.md`](rewards.md).

## Idempotency

There are two separate mechanisms and they are easy to confuse:

- the body field `idempotency_key`, which identifies the event
- a generic HTTP `X-Idempotency-Key` header, which must be exactly 36
  characters

Use the body field. Generate a fresh UUID per event.

## After a 200

A 200 returns `{"idempotency_key": "...", "event_id": "<uuid>"}`. Report
"event accepted, `event_id=<id>`". Then say that this skill cannot yet read
back whether the quest executed, and that the developer should check the
outcome where the reward lands. Never claim a reward was delivered.

## After an uncertain response

If the request times out or the outcome is otherwise unknown, **stop**. Do not
resend, not with the same key and not with a new one. A timeout is not a
failure: the event may have been accepted and the quest may already be paying
out. Report "result unknown".

A 404 with a plain-text body such as `Cannot POST /api/v2/projects/<id>/events`
is not an uncertain response. It means event submission is not available for
project API keys yet; see [`auth-and-environment.md`](auth-and-environment.md).

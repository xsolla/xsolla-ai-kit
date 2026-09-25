# Events

Stage OpenAPI and local runtime snapshots were checked on 2026-09-23; the
event route, its auth and the publisher rule were rechecked on 2026-09-25.
Stage deployments churn and the revision is not pinned here, so revalidate
before writes.

Events go to **qp-events-collector**, not to qp-server. Sending an event to
qp-server produces a 404 that looks like a missing quest.

## No event route for the project credential on stage

**Fact, checked against the live collector OpenAPI at about 09:20Z on
2026-09-25 (rechecked 09:27Z): the collector lists only `POST /api/v2/events`,
plus `/api/v2/debug/trigger-outbox` and health routes.** Its security schemes
are an API key and a Bearer token. The project route
`/api/v2/projects/{project_id}/events` is gone, and there is no
`/merchants/...` event route. So a developer on the Basic project credential
has **no event route at all** on stage, and `POST /api/v2/events` does not
take that credential (it answers 401
`{"error":"X-REQUEST-APIKEY header is required"}`).

When the developer on the Basic lane asks to send an event:

1. Stop. Do not send anything. Report "the collector on stage has no event
   route for the project credential since about 09:20Z 2026-09-25".
2. **Do not fall back to another credential or route.** Never switch to a
   service key, an API key or a Bearer token, and never call
   `POST /api/v2/events` or `/api/v2/debug/trigger-outbox` to get the event
   through. Such an event lands in another account and never matches a quest
   created on the project route, so it would prove nothing about this quest.
3. Say that execution verification cannot run, and that the Quest Platform
   team owns the fix. Reads of earlier executions still work; see
   [`verification.md`](verification.md).
4. If the quest is `inactive` (or `active` but outside its dates), also say
   that an event could not run it anyway, and offer activation first; see
   [`quest-document.md`](quest-document.md).

Revalidate: once the live collector OpenAPI lists an event route that takes
the project credential, this section no longer applies. The rest of this file
describes the event body and rules for when a route exists.

**History (dated, not current):** from the qp-server redeploy around 08:20Z
until the collector redeploy around 09:20Z on 2026-09-25, the project route
`POST /api/v2/projects/{project_id}/events` still existed but answered every
Basic event with 404 `{"error":"Not Found"}`, the same for an empty body, a
wrong key, an unknown project and another merchant. Nothing was ingested. The
cause, inferred from code, was that the collector validated the credential
without a `merchant_id`. A 404 from that route is no longer the expected
answer; the route itself is gone.

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
| `quest_id` | no | a valid UUID when present. Restricts matching to that one quest; without it, every live quest of the project's account with that `event_name` runs |
| `scope` | no | `global`, `private`, `within_project`, `within_quest`, `within_publisher`. Defaults to `private`. It decides which quests' event-count conditions can count this event later, not which quest runs. Keep the default unless the developer asks. The published schema shows a bare string and the older struct hint lists only three values; the server accepts all five |
| `publisher` | no | see "The `publisher` block" below |
| `properties` | no | string values only |

`user_ids[].identifier_type` is `xsolla_id`, `gamer_id`, `guest_id` or `email`.
An `xsolla_id` value must parse as a UUID; an `email` value must contain `@`;
`gamer_id` and `guest_id` need only be non-empty.

### The `publisher` block

A quest created on the project route always carries the server-set
`publisher_id` (the merchant id) and `project_id`. The collector does not fill
`publisher` from the route; it keeps whatever you send. Either:

- **omit it**, so the event is not filtered by publisher and matches, or
- send **exactly** the quest's values as read back from the quest, both as
  strings: `{"publisher_id": "<quest publisher_id>", "project_id": "<quest project_id>"}`.
  The live schema requires both when the object is present.

Any other value, including the right merchant with another project, matches
no quest and leaves **no** qp-data row, not even `NOT_TRIGGERED`. Never take
the values from memory or from the credential; copy both from a single-quest
GET (or the create response), never from the quest list: list items carry
`project_id` but no `publisher_id`. If that read has no `publisher_id`, stop
and ask; do not fill it in.

Some rewards read the merchant or project from the event, not from the quest,
and fail without the block; see "Event-side requirements" in
[`rewards.md`](rewards.md). For those, send the exact quest values; do not
omit the block.

A quest with a `web3_item` or `web3_token` reward needs an `xsolla_id` entry
whose user already has a wallet. Check it before submitting; see
[`rewards.md`](rewards.md).

The account is **not** in the body. On the old project route the collector
took it from the project in the path.

A 200 returns `{"idempotency_key": "...", "event_id": "<uuid>"}`.

The scopeless `POST /api/v2/events` takes an API key or a Bearer token, not
the project credential; see
[`auth-and-environment.md`](auth-and-environment.md) for who may use those
lanes. Never call `/api/v2/debug/trigger-outbox`.

## Before sending

- **Wait after a quest write.** The pipeline caches quest config for up to 60
  seconds (see [`auth-and-environment.md`](auth-and-environment.md)). After
  creating, activating, pausing or editing a quest, wait about 90 seconds
  before the first event, or the event may be matched against the old config.
  Right after a pause, an event can still run the quest as active; for a quest
  with an `issue_reward`, say so and wait before sending.
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

### An event the developer sent, not you

When the developer says their own script or tool sent an event and asks what
happened, you never saw the request or its response. Do not resend it to find
out, and do not treat it as yours. Ask for the exact payload (or at least the
quest id, `name`, `idempotency_key` and user), which user it named, and when
it was sent, and whether they got an `event_id` back. Then verify read-only
as in [`verification.md`](verification.md). A key the developer's script
generated or reused is a developer-supplied key: the match is weaker
identification, so also require the user and a `server_timestamp` close to
the stated send time, and say so in the report.

# Node subtypes

Stage OpenAPI and local runtime snapshots were checked on 2026-09-22. The
stage deployment revision is not pinned here, so revalidate before writes.

The OpenAPI document types `subtype` as a bare `string`. The real list lives in
the server's validator, and it is shorter than the constants suggest.
Node `parameters` are raw JSON in OpenAPI; use the source-backed rules below
for their shapes and validation, following the skill's source-of-truth order.

## Accepted

| `subtype` | Used with `type` | `parameters` |
|---|---|---|
| `date_and_time` | trigger | accepted without parameter validation; scheduling is not implemented |
| `dynamic_event` | trigger | `{"event_name": "<non-empty string>"}` |
| `custom_attributes_check` | condition | see `conditions.md` |
| `issue_reward` | action | see `rewards.md` |
| `send_xsolla_app_notification` | action | `topic`, `notification_type`, `title`, `message`; optional `data`, see below |
| `send_http_webhook` | action | `url`, see below |
| `webshop_personalization` | action | configuration is accepted, but the current worker maps it to `SkipExecution`; see below |

## Action parameters

These rules are enforced by the server's hand-written validators, registered
in `adtech/qp-server/internal/http/validation/quest_config.go`. Each of these
three actions requires `parameters` that decode into its model and pass
validation; OpenAPI does not supply this contract. Ask the developer for actual
values, including the notification topic, webhook URL and personalization IDs.

Configuration acceptance is not runtime support. The current worker maps
`webshop_personalization` to `SkipExecution`; it must not be presented as a
working personalization effect without an owner-approved stage fixture and a
deployed implementation check.

### send_http_webhook

```json
{"url": "<developer-supplied HTTP or HTTPS URL>"}
```

`url` is the only modeled parameter. It must be a non-empty string, parse with
Go's `url.ParseRequestURI`, use the `http` or `https` scheme, and have a
non-empty host. The model supplies no method, headers or body parameters.
When the quest executes, the worker sends the full event JSON by HTTP POST to
this URL, including the user identifiers. Never treat an arbitrary URL as a
harmless placeholder.

- **Approved** means an endpoint the developer owns or controls and names
  explicitly. A public request bin receives that JSON too; use one only after
  the developer acknowledges it.
- Never point it at an internal host, a Quest Platform service or the minting
  service (see [`auth-and-environment.md`](auth-and-environment.md)).
  qp-server rejects a minting-service host with a 422 (deployed build,
  checked 2026-09-25). To pay out, use an `issue_reward` Web3 reward instead.
- The webhook fires only after activation. Warn when the URL goes into the
  draft, and confirm again before activating.

Source: `adtech/lib/models/generic_quest/http_webhook.go`.

### send_xsolla_app_notification

```json
{
  "topic": "<developer-supplied topic>",
  "notification_type": "<developer-supplied notification type>",
  "title": "<developer-supplied title>",
  "message": "<developer-supplied message>",
  "data": {}
}
```

`topic`, `notification_type`, `title` and `message` are required non-empty
strings. `topic` is required by `Validate()` despite its `omitempty` JSON tag.
The validator does not constrain these strings to an enum or check a topic's
existence. `data` is optional, a JSON object with string keys and arbitrary
JSON values; it has no additional validation. Do not invent a topic or
notification-type value.

At run time `topic` is the Kafka topic the worker publishes to. Values in use
on stage (observed 2026-09-25, revalidate): `topic` `qp.notifications` with
`notification_type` `reward_earned` or `reward`. The recipient is the event's
`xsolla_id`, else its `guest_id`, else its `gamer_id`; with none of them the
action is skipped and still reports `COMPLETED`. `COMPLETED` means the message
was published, not that the user saw it. Behavior with an unknown topic has not
been verified.

Source: `adtech/lib/models/generic_quest/xsolla_app_notification.go`.

### webshop_personalization

```json
{"items": [{"id": "<developer-supplied item ID>"}]}
```

`items` must be a non-empty array. Each item is modeled as an object with a
string `id`. The validator checks only the array length; it does not require
each `id` to be present or non-empty, check its format, or verify that the item
exists. Obtain real IDs from the developer rather than treating acceptance as
proof of a valid item.

Source: `adtech/lib/models/generic_quest/webshop_personalization.go`.

## Accepted for configuration, not a working runtime action

`webshop_personalization` is accepted by the configuration validator, but the
current worker routes it to `SkipExecution`. Do not use API acceptance or a
`COMPLETED` execution row as evidence that personalization occurred.

That makes it the only action with no external effect, so it is the one to
offer for a smoke test of create, event and execution. Use it only when the
developer chooses it as a no-op, name the node so (for example `noop`), and
never present it as personalization. Every other action has a real effect. A
draft for CRUD-only checks can also stay without an action.

## Rejected, despite existing

`event_check` is declared as a constant in the platform's models but is **not**
in the accepted list. A node using it fails validation. Do not offer it, and if
a developer asks for it, say it is not accepted by the API. For "after N
events", use a `custom_attributes_check` condition with an `event` operand; see
[`conditions.md`](conditions.md).

## Choosing a trigger

For a quest that should run when something happens, use `dynamic_event` and set
`event_name` to the name the event will carry. That name is what ties the quest
to the event submitted later; see `events.md`. Ask the developer for it; never
reuse the quest name or invent one. Every active quest in the account with the
same trigger name runs on that event, so a test quest needs a unique name.

`date_and_time` is accepted by the API and its parameters are not validated
on write, but **runtime scheduling is not implemented**. The current
`DateAndTimeTrigger` is a TODO stub (QP-591): it logs and returns success when
invoked, without reading schedule parameters or scheduling an execution.
API acceptance or a successful stub invocation is not evidence that a schedule
will run. Do not recommend it as a working scheduler or invent schedule fields.
For a scheduling request, explain this limitation before configuring a quest.
The alternative is a `dynamic_event` trigger and a scheduler the developer runs
that submits the event at the right time.

Source: local `adtech/qp-worker-generic-quest/internal/temporal/generic_quest/activity/trigger.go`,
checked on 2026-09-22. Revalidate the deployed worker before claiming runtime behavior.

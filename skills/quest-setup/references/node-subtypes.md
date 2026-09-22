# Node subtypes

Written against the contract deployed on stage as of 2026-09-22.

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
| `webshop_personalization` | action | `items` array of objects with `id`, see below |

## Action parameters

These rules are enforced by the server's hand-written validators, registered
in `adtech/qp-server/internal/http/validation/quest_config.go`. Each of these
three actions requires `parameters` that decode into its model and pass
validation; OpenAPI does not supply this contract. Ask the developer for actual
values, including the notification topic, webhook URL and personalization IDs.

### send_http_webhook

```json
{"url": "<developer-supplied HTTP or HTTPS URL>"}
```

`url` is the only modeled parameter. It must be a non-empty string, parse with
Go's `url.ParseRequestURI`, use the `http` or `https` scheme, and have a
non-empty host. The model supplies no method, headers or body parameters.

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

## Rejected, despite existing

`event_check` is declared as a constant in the platform's models but is **not**
in the accepted list. A node using it fails validation. Do not offer it, and if
a developer asks for it, say it is not accepted by the API.

## Choosing a trigger

For a quest that should run when something happens, use `dynamic_event` and set
`event_name` to the name the event will carry. That name is what ties the quest
to the event submitted later; see `events.md`.

`date_and_time` is accepted by the API and its parameters are not validated
on write, but **runtime scheduling is not implemented**. The current
`DateAndTimeTrigger` is a TODO stub (QP-591): it logs and returns success when
invoked, without reading schedule parameters or scheduling an execution.
API acceptance or a successful stub invocation is not evidence that a schedule
will run. Do not recommend it as a working scheduler or invent schedule fields.
For a scheduling request, explain this limitation before configuring a quest.

Source: `adtech/qp-worker-generic-quest/internal/temporal/generic_quest/activity/trigger.go`,
checked against current source on 2026-09-22.

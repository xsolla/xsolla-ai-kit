# Node subtypes

`subtype` is a string, but only the values below are accepted.

## Accepted

| `subtype` | Used with `type` | `parameters` |
|---|---|---|
| `date_and_time` | trigger | accepted without parameter checks; scheduling is not implemented, see below |
| `dynamic_event` | trigger | `{"event_name": "<non-empty string>"}` |
| `custom_attributes_check` | condition | see `conditions.md` |
| `issue_reward` | action | see `rewards.md` |
| `send_xsolla_app_notification` | action | `topic`, `notification_type`, `title`, `message`; optional `data`, see below |
| `send_http_webhook` | action | `url`, see below |
| `webshop_personalization` | action | `items`; accepted, but has no runtime effect today, see below |

## Action parameters

Each of these three actions needs `parameters` in the shape below. A node
whose `parameters` do not match is rejected with a 422. Ask the developer for
actual values, including the notification topic, the webhook URL and the
personalization item IDs.

### send_http_webhook

```json
{"url": "<developer-supplied HTTP or HTTPS URL>"}
```

`url` is the only parameter. It must be an absolute `http` or `https` URL with
a host. There are no method, header or body parameters. When the quest
executes, the platform sends the full event JSON by HTTP POST to this URL.
Use only an endpoint the developer controls, and get explicit approval before
activation. Never treat an arbitrary URL as a harmless placeholder.

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
strings. The API does not check them against a list and does not check that a
topic exists. `data` is optional: a JSON object with string keys and any JSON
values. Do not invent a topic or a notification type.

### webshop_personalization

```json
{"items": [{"id": "<developer-supplied item ID>"}]}
```

`items` must be a non-empty array of objects with a string `id`. The API
checks only that the array is not empty. It does not check that each `id` is
present, well formed or a real item, so obtain real IDs from the developer.

This subtype is accepted, but it has no runtime effect today. Do not present
it as a working personalization action, and do not treat API acceptance as
evidence that personalization happens.

## Not accepted

`event_check` is not accepted by the API. A node using it fails validation. Do
not offer it, and if a developer asks for it, say it is not accepted by the
API.

## Choosing a trigger

For a quest that should run when something happens, use `dynamic_event` and set
`event_name` to the name the event will carry. That name is what ties the quest
to the event submitted later; see `events.md`.

`date_and_time` is accepted, but scheduling is not implemented. Do not offer it
as a scheduler, and do not invent schedule fields. For a scheduling request,
explain this limitation before configuring a quest.

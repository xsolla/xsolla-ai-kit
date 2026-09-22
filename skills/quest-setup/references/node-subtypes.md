# Node subtypes

Written against the contract deployed on stage as of 2026-09-22.

The OpenAPI document types `subtype` as a bare `string`. The real list lives in
the server's validator, and it is shorter than the constants suggest.

## Accepted

| `subtype` | Used with `type` | `parameters` |
|---|---|---|
| `date_and_time` | trigger | not validated on write |
| `dynamic_event` | trigger | `{"event_name": "<non-empty string>"}` |
| `custom_attributes_check` | condition | see `conditions.md` |
| `issue_reward` | action | see `rewards.md` |
| `send_xsolla_app_notification` | action | notification parameters |
| `send_http_webhook` | action | webhook parameters |
| `webshop_personalization` | action | personalization parameters |

## Rejected, despite existing

`event_check` is declared as a constant in the platform's models but is **not**
in the accepted list. A node using it fails validation. Do not offer it, and if
a developer asks for it, say it is not accepted by the API.

## Choosing a trigger

For a quest that should run when something happens, use `dynamic_event` and set
`event_name` to the name the event will carry. That name is what ties the quest
to the event submitted later; see `events.md`.

For a quest that should run on a schedule, use `date_and_time`. Its parameters
are not checked on write, so mistakes there surface at runtime rather than at
create time. Say so when you use it.

# Node subtypes

Stage OpenAPI and the code of the deployed qp-server build and stage worker
were checked on 2026-09-25. Both revisions are inferred, not pinned, so
revalidate before writes.

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

The deployed validator also accepts `scheduled_event` (trigger) and
`crm_send_email` (action). Neither runs on stage today; see
[Accepted, but not runnable on stage](#accepted-but-not-runnable-on-stage).

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
When the quest executes, the worker sends the event by HTTP POST to this URL
as JSON: `id`, `idempotency_key`, `name`, `scope`, `quest_id`, `account_id`,
`user_ids`, `publisher`, `properties` and `server_timestamp`. That includes
the user identifiers. Never treat an arbitrary URL as a harmless placeholder.

- **Approved** means an endpoint the developer owns or controls and names
  explicitly. A public request bin receives that JSON too; use one only after
  the developer acknowledges it.
- Never point it at an internal host or the minting service. An **internal
  host** is any `*.srv.local` name, `localhost`, a loopback or private IP
  (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `::1`,
  `fc00::/7`), and every host in the Services table of
  [`auth-and-environment.md`](auth-and-environment.md#services), which
  includes the Quest Platform services and the minting service. A
  webhook cannot pay out: it posts the raw event above, not a mint claim, and
  it carries no credentials. To pay out, use an `issue_reward` Web3 reward.
  The 09-24 qp-server build rejected a minting-service host with a 422; the
  build deployed on 2026-09-25 has no such check (from code), so do not rely
  on the server to stop it.
- A reserved, never-resolving host such as `https://e2e-sink.invalid/hook` is
  fine as a placeholder in an `inactive` draft: the validator checks only the
  URL's form, not that it resolves. Label it as a placeholder, and replace it
  with the developer's real endpoint before activation. Never activate with
  it.
- The webhook fires only after activation. Warn when the URL goes into the
  draft, and confirm again before activating.

At run time any status of 400 or above, a timeout (30 s) or an unresolvable
host is an error. The worker retries it: the HTTP client retries failed
connections up to 3 times, and the action itself is attempted up to 3 times
(stage config, from code), so the endpoint may receive the same event more
than once. After that the action is
`FAILED` and the execution is `FAILED` with `failReason: ACTION_FAILED`
(observed on stage: `webhook request failed with status: 404` and `502`).
Tell the developer to deduplicate by `idempotency_key`.

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
JSON values; it has no additional validation. Do not invent any of the four
values: `topic`, `notification_type`, `title` or `message`. Ask for them, or
show a concrete proposal and get a yes; "pick something sensible" delegates
the choice, it does not confirm a value, so still show the proposal. You may suggest the observed stage values below
(`qp.notifications`, `reward_earned` or `reward`) as options, labelled as
observed on stage, but the developer confirms them before they go into the
draft; a suggestion is not a confirmation. The worker adds the event's `properties`,
`quest_id` and `idempotency_key` to `data` (from code), so do not put secrets
in event properties.

At run time `topic` is the Kafka topic the worker publishes to. Values in use
on stage (observed 2026-09-25, revalidate): `topic` `qp.notifications` with
`notification_type` `reward_earned` or `reward`. The recipient is the event's
`xsolla_id`, else its `guest_id`, else its `gamer_id`; with none of them the
action is skipped and still reports `COMPLETED`. `COMPLETED` means the message
was published, not that the user saw it. Behavior with an unknown topic has not
been verified.

`topic` is a raw Kafka topic, not a label. The only topic confirmed on stage
is `qp.notifications` (every notification row in qp-data samples of
2026-09-25). If the developer names another topic, say that it is
unconfirmed and that the message may go nowhere or to another consumer. It
may stay in an `inactive` draft, but do not activate a quest with it until
the developer confirms that the Quest Platform team approved the topic.

Source: `adtech/lib/models/generic_quest/xsolla_app_notification.go`.

### webshop_personalization

```json
{"items": [{"id": "<developer-supplied item ID>"}]}
```

`items` must be a non-empty array. Each item is modeled as an object with a
string `id`. The validator checks only the array length; it does not require
each `id` to be present or non-empty, check its format, or verify that the item
exists. Obtain real IDs from the developer rather than treating acceptance as
proof of a valid item. The one exception is the labelled no-op placeholder
described below.

Source: `adtech/lib/models/generic_quest/webshop_personalization.go`.

## Accepted for configuration, not a working runtime action

`webshop_personalization` is accepted by the configuration validator, but the
current worker routes it to `SkipExecution`. Do not use API acceptance or a
`COMPLETED` execution row as evidence that personalization occurred.

That makes it the only action with no external effect, so it is the one to
offer for a smoke test of create, event and execution. Use it only when the
developer chooses it as a no-op, name the node so (for example `noop`,
never a name with "personalization" in it), and never present it as
personalization. For the no-op you do not need a real item
id: use a labelled placeholder such as `{"items": [{"id": "e2e-noop"}]}` (the
validator checks only that `items` is non-empty, and the worker never reads
it), and tell the developer it is a placeholder. Ask for real item ids only
when the developer wants actual personalization, which does not run today. Every other action has a real effect. A
draft for CRUD-only checks can also stay without an action.

## Accepted, but not runnable on stage

The qp-server build deployed on 2026-09-25 accepts two more subtypes (from its
code; stage does not publish the list). Do not offer them. If the developer
asks for one, explain why:

- `scheduled_event` (trigger), parameters `event_name` plus exactly one of
  `cron` or `date_time`. Activating it makes qp-server register the schedule
  with the collector, forwarding only a Bearer Publisher Account token or an
  API key. With the Basic credential this skill uses, an `active` write fails
  with 400 `scheduled quests require a Publisher Account token or an API key`
  and is not saved (from the qp-server code deployed on 2026-09-25, not
  observed on stage). The stage worker also has no handler for it.
- `crm_send_email` (action), parameters `subject`, `game_title`, `content`,
  `crm_segment`, all required. The stage worker has no handler for it, so it
  would fail at run time.

Revalidate before relying on either; both are new and still moving.

## Rejected, despite existing

`event_check` is declared as a constant in the platform's models but is **not**
in the accepted list. A node using it fails validation. Do not offer it, and if
a developer asks for it, say it is not accepted by the API. For "after N
events", use a `custom_attributes_check` condition with an `event` operand. A
condition cannot read the event's `properties`; see
[`conditions.md`](conditions.md#operands).

## Choosing a trigger

For a quest that should run when something happens, use `dynamic_event` and set
`event_name` to the name the event will carry. That name is what ties the quest
to the event submitted later; see `events.md`. Ask the developer for it; never
reuse the quest name or invent one. Every active quest in the account with the
same trigger name runs on that event (on the project lane the account is the
project's), so a test quest needs a unique name.

If the `event_name` the developer gives looks unrelated to the quest (for
example `level_up` on a "first purchase" quest, or a test id from another case
such as `e2e-uc03-...` on a UC02 quest), say so once and ask them to confirm
it; do not change it yourself.

Two optional read-only checks, never blocking:

- **Name check before a create:** page through the list (see
  `quest-document.md` Responses) and say if a quest with the same name already
  exists.
- **Collision check before activation:** offer it when the list shows another
  `active` quest with a similar name or test prefix, or the `event_name` is
  generic (`purchase`, `level_up`). `GET` each `active` quest (list items
  carry no nodes) and report any whose trigger has the same `event_name`. The
  list covers only the route's project, not the whole account, so a clean
  result is not proof of no collision; say so.

`date_and_time` is accepted by the API and its parameters are not validated
on write, but **runtime scheduling is not implemented**. The current
`DateAndTimeTrigger` is a TODO stub (QP-591): it logs and returns success when
invoked, without reading schedule parameters or scheduling an execution.
API acceptance or a successful stub invocation is not evidence that a schedule
will run. Do not recommend it as a working scheduler or invent schedule fields.
For a scheduling request, explain this limitation before configuring a quest.
`scheduled_event` is not an alternative today; see above. The alternative is a
`dynamic_event` trigger and a scheduler the developer runs that submits the
event at the right time. On stage that is blocked too for now: the Basic
credential has no event route (see `events.md`), and an event sent with
another credential lands in another account and never matches the quest.

Source: local `adtech/qp-worker-generic-quest/internal/temporal/generic_quest/activity/trigger.go`,
checked on 2026-09-22. Revalidate the deployed worker before claiming runtime behavior.

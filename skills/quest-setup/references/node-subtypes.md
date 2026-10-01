# Node subtypes

The node shapes below are reference material. Confirm them against
[`qp-api-contract.md`](qp-api-contract.md) and the read-back of the saved quest
before using an optional subtype. A published OpenAPI may type `subtype` as a
bare `string`; use only values this skill's `references/` accept. On conflict,
`references/` wins on node rules.

## Accepted

| `subtype` | Used with `type` | `parameters` |
|---|---|---|
| `date_and_time` | trigger | accepted only when the production contract confirms scheduling |
| `dynamic_event` | trigger | `{"event_name": "<non-empty string>"}` |
| `custom_attributes_check` | condition | see `conditions.md` |
| `issue_reward` | action | see `rewards.md` |
| `send_xsolla_app_notification` | action | `topic`, `notification_type`, `title`, `message`; optional `data` |
| `send_http_webhook` | action | `url`, see below |
| `webshop_personalization` | action | configuration may be accepted without producing a personalization effect |

Do not offer any additional subtype until its production contract and runtime
support are confirmed. Configuration acceptance is not runtime support.

## Action parameters

Node parameters are raw JSON in OpenAPI and may have additional validation.
Ask for actual values, including notification topic, webhook URL and
personalization IDs. Never invent a value that has an external effect.

### send_http_webhook

```json
{"url": "<developer-supplied HTTP or HTTPS URL>"}
```

`url` is the only modeled parameter. It must be a non-empty HTTP or HTTPS URL
with a host. The runtime sends the event by HTTP POST as JSON, including user
identifiers. Never treat an arbitrary URL as a harmless placeholder.

- **Approved** means an endpoint the developer owns or controls and names
  explicitly. A public request bin receives the event too; use one only after
  the developer acknowledges it while building the publication proposal (not as
  a separate post-approval gate).
- Never point it at a private platform service or the minting service. A
  webhook cannot pay out and carries no credentials. To pay out, use an
  `issue_reward` Web3 reward with the values listed in `rewards.md`.
- A reserved host such as `https://e2e-sink.invalid/hook` is never written and
  must never appear in a publication proposal. Replace it with the developer's
  approved endpoint before showing the proposal.
- The webhook fires only after the quest is active. State that timing and the
  destination in the publication proposal so the one approval covers it. Do not
  ask again before activation unless the endpoint changed after approval, in
  which case show the revised proposal and request approval again.

An error response, timeout or unresolvable host fails the action. The runtime
may retry it, so the endpoint may receive the same event more than once.
Tell the developer to deduplicate by `idempotency_key`.

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
strings. `data` is optional and must be a JSON object. Do not invent any of
the four required values. Show a concrete proposal and get a yes. Confirm the
topic and recipient rules against the production contract. `COMPLETED` means
the platform accepted the action, not that the user saw the message.

### webshop_personalization

```json
{"items": [{"id": "<developer-supplied item ID>"}]}
```

Use this only when the developer chooses it as a labelled no-op or when live
production support is confirmed. A CRUD smoke test may use
`{"items": [{"id": "e2e-noop"}]}` in an inactive draft. Never present a no-op
as a working personalization effect.

## Accepted, but not yet production-confirmed

Some deployments may expose `scheduled_event` or `crm_send_email`. Do not offer
them until the production contract and runtime support are confirmed. A
successful configuration write alone is not enough.

## Rejected, despite existing

`event_check` is not a supported subtype unless the live production contract
explicitly adds it. For "after N events", use a `custom_attributes_check`
condition with an `event` operand. A condition cannot read the event's
`properties`; see [`conditions.md`](conditions.md#operands).

## Choosing a trigger

For a quest that should run when something happens, use `dynamic_event` and set
`event_name` to the name the event will carry. Ask the developer for it; never
reuse the quest name or invent one. Every active quest in the selected project
with the same trigger name may run on that event, so a test quest needs a
unique name.

If the `event_name` looks unrelated to the quest, say so once and ask the
developer to confirm it. Do not change it yourself.

Two optional read-only checks are useful:

- page through the list before a create and report exact or near-duplicate
  names;
- during the read-only checks before the proposal, check active quests in the
  selected project for the same trigger name when the event is generic.

A clean project-level result is not proof that no other scope has a collision.

`date_and_time` is not a working scheduler unless the live production runtime
confirms it. For scheduling, use a `dynamic_event` trigger and a scheduler that
submits the event at the required time, after the production event gate passes.

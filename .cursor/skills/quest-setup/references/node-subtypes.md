# Node subtypes

The publisher's node catalog (`GET .../quests/node-types`, see
[rewards.md](rewards.md#choose-from-the-node-catalog)) and the live docs are the source of truth:
any node the catalog lists can be used. This snapshot lists only the nodes this file has notes on,
for orientation.
Use [SKILL docs refresh](../SKILL.md#live-docs-and-rewards) and
[Source of truth](qp-api-contract.md#source-of-truth) for conflicts/unavailability.
Read back the saved quest before using an optional subtype.

## Accepted (snapshot, orientation only)

| `subtype` | Used with `type` | `parameters` |
|---|---|---|
| `date_and_time` | trigger | accepted only when the production contract confirms scheduling |
| `dynamic_event` | trigger | `{"event_name": "<non-empty string>"}`, optional `"client_sendable": true` |
| `custom_attributes_check` | condition | see `conditions.md` |
| `issue_web3_item` | action | `purpose`, `project`, `item_sku`, `quantity`; see `rewards.md` (the older `issue_reward` is deprecated) |
| `issue_catalog_item` | action | `items` (one or more `{sku, quantity}`) and `purpose`, see below and `rewards.md` |
| `send_xsolla_app_notification` | action | `topic`, `notification_type`, `title`, `message`; optional `data` |
| `send_http_webhook` | action | `url`, see below |
| `webshop_personalization` | action | configuration may be accepted without producing a personalization effect |

Any node the project's `node-types` catalog returns may be offered and used; this table only
holds notes on some of them.

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
  webhook cannot pay out and must never carry credentials. To pay out, use an
  reward node from the node catalog, as in `rewards.md`.
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
`{"items": [{"id": "e2e-noop"}]}` in an inactive quest. Never present a no-op
as a working personalization effect.

### issue_catalog_item

```json
{"items": [{"sku": "<catalog SKU>", "quantity": 1}], "purpose": "<developer-supplied reason>"}
```

- `items` needs at least one entry. `quantity` is 1 to 100 (default 1). Leave out `items[].type`:
  it defaults to `virtual_item`, and the live run granted virtual_good catalog items that way.
- Send no merchant or project fields. Publisher routes set them from the path.
- The grant goes to the player's Backpack by `xsolla_id`. No mint, wallet or gas. Guests cannot
  receive it.
- The node sends only SKUs. Backpack takes the name and image from the catalog, and an unknown
  SKU fails with `not_found`.
- Use it as described in [Backpack grants](rewards.md#backpack-grants-issue_catalog_item).

### dynamic_event client_sendable

`client_sendable` is off by default: only the publisher's backend can send the event. The Shop
Builder Quests block sends `login_xsolla_id` (once), `daily_visit` and `weekly_visit` from the
browser with the player's token, so a quest triggered by any of them must set
`"client_sendable": true` on its trigger. The player events route accepts a client event only
while an active quest of the project allows it: this flag, or an event operand with
`include_client_events: true`. Otherwise it answers 403. Say in the proposal that the browser or
game client can send this event, and which one. Never set it on an event only the backend sends.

## Rejected, despite existing

`event_check` is not a supported subtype unless the live production contract
explicitly adds it. For "after N events", use a `custom_attributes_check`
condition with an `event` operand. A condition cannot read the event's
`properties`; see [`conditions.md`](conditions.md#operands).

## Choosing a trigger

The trigger kinds on offer are the trigger nodes `node-types` returns, in its order, each with the
constraint from its own description; when the request leaves the trigger open, offer them as one
question ([the menu](rewards.md#choose-from-the-node-catalog)). The same goes for condition nodes.
For an event trigger, use `dynamic_event` with the actual event name the caller/site emits. Reuse a verified
binding or a publisher-supplied actual name; never infer a deployed binding from a quest
title or player-action description. If unresolved, ask for the actual name. You may
propose a `snake_case` candidate labelled "proposed, unverified", but before any quest
write require a verified binding or the publisher's explicit confirmation of what the
caller emits. General publication approval does not establish configured site emission.
The Quests block (0.2.22) sends three built-in events itself for a signed-in player, and they
count as a verified binding on a site with the block: `login_xsolla_id` once per session,
`daily_visit` once per UTC day and `weekly_visit` once per ISO week. Map "daily login" to
`daily_visit`, "weekly login" to `weekly_visit` and "first sign-in" to `login_xsolla_id`, with
`client_sendable: true` on the trigger. These events carry only the signed-in player's
`xsolla_id` (from their Xsolla Login token), never a `gamer_id`, so a reward node whose
description needs `gamer_id` (an item delivered into the game, a currency or points paid by
game account) cannot pay from a block-driven quest: say so in the menu next to that option.
For a login sent from elsewhere, follow the
[login flow](events.md#login-event-with-xsolla-id).
Every active quest in the selected project with the same trigger name may run, so a
test quest needs a unique name.

If the `event_name` looks unrelated to the quest, say so once and ask the
developer to confirm it. Do not change it yourself.

Two optional read-only checks are useful:

- page through the list before a create and report exact or near-duplicate
  names;
- during the read-only checks before the proposal, check active quests in the
  selected project for the same trigger name when the event is generic.

A clean project-level result is not proof that no other scope has a collision.

Unless production confirms `date_and_time` scheduling, use `dynamic_event` with an
external scheduler submitting at the required time after the [event gate](events.md#production-event-gate).

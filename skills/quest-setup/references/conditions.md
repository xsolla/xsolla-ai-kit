# Conditions

Stage OpenAPI and local runtime snapshots were checked on 2026-09-22; the
worker's counting code was rechecked on 2026-09-25. The stage deployment
revision is not pinned here, so revalidate before writes.

These are the `parameters` of a node with `type: condition` and
`subtype: custom_attributes_check`. The OpenAPI document does not describe
them at all.

## Shape

```json
{
  "type": "comparison",
  "operator": {"type": "numeric", "operation": "gte"},
  "left":  {"type": "attribute", "value": "user.level"},
  "right": {"type": "value", "value": 10}
}
```

`type` is `and`, `or` or `comparison`.

- `and` and `or` need a non-empty `conditions` array of nested condition
  objects, and ignore `left`, `right` and `operator`.
- `comparison` needs `operator`, `left` and `right`.

## Operands

`left` and `right` are operands. Each has a `type`:

| Operand `type` | `value` | Extra |
|---|---|---|
| `value` | a literal | none |
| `attribute` | a non-empty string path, for example `user.level` | none |
| `event` | a non-empty string, the event name | **must** carry `time_window.duration_unit`, one of `day`, `week`, `month` |

An `event` operand supports numeric comparison only, and the threshold it is
compared against must be a whole number.

## Operators

`operator.type` constrains `operator.operation`:

| `type` | allowed `operation` |
|---|---|
| `numeric` | `eq`, `neq`, `gt`, `lt`, `gte`, `lte`, `mod` |
| `string` | `eq`, `neq`, `contains` |
| `boolean` | `eq`, `neq` |
| `string_array` | `in`, `not_in`, `intersects` |

For `mod`, the divisor must be greater than zero.

## Counting events

To express "did this at least three times this week":

```json
{
  "type": "comparison",
  "operator": {"type": "numeric", "operation": "gte"},
  "left":  {"type": "event", "value": "level.completed", "time_window": {"duration_unit": "week"}},
  "right": {"type": "value", "value": 3}
}
```

Leaving out `time_window` on an `event` operand is the most common mistake
here, and the error comes back as a flattened 422 string rather than a field
error.

## Runtime prerequisites

- An attribute operand causes the current worker to load user attributes from
  Login and requires an `xsolla_id` on the event. The attribute path must exist;
  a structurally valid `user.country` comparison can still be unevaluable.
- An event operand counts distinct `idempotency_key`s of ingested events for
  the same identity and a visible scope. The identity is the event's
  `xsolla_id`, else `gamer_id`, else `email`; a `guest_id` is not used for
  counting. The triggering event and its history must use the intended user
  and event name.
- Counting is per account: only events that arrived in the quest's account
  count. On the project lane that means events sent through the same
  project's event route; events sent with another credential land in another
  account and never count (from the worker code). The event's `publisher`
  block, if any, adds publisher and project scopes to what is visible; it does
  not narrow the count. See `events.md`.
- **The arriving event counts.** `gte 2` per `day` passes on the second
  qualifying event: the first gave `IN_PROGRESS` with `actual` 1, the second
  `COMPLETED` with 2 (observed on stage 2026-09-25).
- Events are indexed on ingestion, before quest matching, so events sent while
  the quest was inactive or out of its dates, or tagged `load_test`, can count
  too (from the consumer code; the deployed revision is not pinned).
- `day`, `week` and `month` are fixed calendar windows, not rolling ones: the
  current day, the week from Monday, or the calendar month, taken in the
  timezone of the event's server timestamp, which reads back as UTC. Events of
  the last few minutes can also count from a short-lived index regardless of
  the window, so near a boundary the count can include an event from the
  previous period. Do not promise a local-calendar interpretation.
- A condition miss leaves an `IN_PROGRESS` row with no actions; it never turns
  into `COMPLETED` by itself. See [`verification.md`](verification.md).

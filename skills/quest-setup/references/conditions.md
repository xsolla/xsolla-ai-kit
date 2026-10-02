# Conditions

The condition schema below is reference material. Production evaluation must be
confirmed against the live contract before relying on runtime behavior.

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

An `attribute` operand cannot read the event's `properties`. Conditions use
event counts for `event` operands and the user's profile attributes for
`attribute` operands. No operand reads the arriving event's payload. For a
vague "check the event", ask what should be checked and offer what exists: an
`event` count operand (how many times), or the trigger's `event_name` (which
event starts the quest). A check on a property value cannot be expressed today;
say so.

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

- An attribute operand requires a supported user identity and a matching
  profile attribute. The attribute path must exist; a structurally valid path
  can still be unevaluable for a user who lacks that attribute.
- An event operand counts qualifying events for the same user and visible
  production scope. The event history must use the intended user and event
  name. Confirm identity mapping against the live contract.
- Events sent through another project or credential do not count. The event's
  `publisher` block, if present, adds publisher and project scope to what is
  visible; it does not narrow the count. See `events.md`.
- **The arriving event counts.** `gte 2` per `day` passes on the second
  qualifying event. So `gte 1` (or `gt 0`)
  always passes on the first qualifying event, because that event is already
  counted: it gates nothing. For "on the Nth event", use `gte N`.
- Events may be indexed before quest matching. Confirm how inactive, out-of-date
  or test-tagged events are handled against the live production contract.
- `day`, `week` and `month` are fixed calendar windows, not rolling ones: the
  current day, the week from Monday, or the calendar month, taken in the
  timezone of the event's server timestamp, which reads back as UTC. Events of
  the last few minutes can also count from a short-lived index regardless of
  the window, so near a boundary the count can include an event from the
  previous period. Do not promise a local-calendar interpretation.
- A condition miss leaves an `IN_PROGRESS` row with no actions; it never turns
  into `COMPLETED` by itself. See `verification.md`.

# Conditions

Stage OpenAPI and local runtime snapshots were checked on 2026-09-22. The
stage deployment revision is not pinned here, so revalidate before writes.

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
| `value` | a literal | — |
| `attribute` | a non-empty string path, for example `user.level` | — |
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
- An event operand counts previously ingested events for the same identity and
  scope. The triggering event and its history must use the intended user and
  event name, and the relevant events must be visible to the worker's data
  sources.
- The contract does not define the calendar boundary or timezone for `week`.
  Do not promise a local-calendar interpretation without owner confirmation.

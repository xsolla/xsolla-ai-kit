# Description handoff format

This skill produces data, not a second executable plan. The authoritative,
confirmation-bound plan is rendered by `shop-builder-assembly` once this handoff
validates.

## Example

```json
{
  "version": 1,
  "project": {
    "merchant_id": 12345,
    "project_id": 67890,
    "environment": "test",
    "test_project_acknowledged": true
  },
  "game": { "name": "Tidepool", "platforms": ["mobile"], "lifecycle": "launch" },
  "site": {
    "name": "Tidepool Web Shop",
    "slug": "tidepool-web-shop",
    "preset": "auto",
    "primary_locale": "en-US",
    "locales": ["en-US"]
  },
  "catalog": {
    "groups": [
      { "external_id": "__all__", "type": "virtual_currency", "placement": "primary" }
    ],
    "featured_skus": []
  },
  "brand": {},
  "content": {},
  "sources": [
    { "kind": "description", "note": "Publisher supplied a plain-language game description" }
  ]
}
```

Use real values discovered from the selected test project; never copy the example IDs.
Raise uncertainty in conversation before serializing — do not add unofficial fields to
the shared contract.

## Rules

1. Every required field is stated, safely inferred, or explicitly answered.
2. Every catalog mapping exists in the same project.
3. `sources` records the description and any publisher answers.
4. The shared validator passes.
5. No Shop Builder write and no separate approval happens in this skill.
6. `shop-builder-assembly` renders the pages, blocks, omissions, exact removals, and the
   final confirmation ID.

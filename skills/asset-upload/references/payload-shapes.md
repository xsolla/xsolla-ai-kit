# Payload shapes: GET → PUT per item type

Admin update calls replace the whole item. For virtual items and virtual currency,
the object GET returns is (almost) exactly what PUT accepts — add `image_url` and
send it back. Bundles and currency packages are the exception: GET expands
nested fields into full objects for display, and PUT rejects that expanded shape.
This reference is the exact transform for each field, and the error you get if
you skip it.

## `groups`

Items and bundles return `groups` as an array of expanded objects; virtual
currency packages return it as an array of plain strings. PUT wants
`external_id` strings in both cases.

```
# GET (virtual item / bundle)
"groups": [{ "external_id": "turret_skins", "name": {...}, "id": 46451, ... }]

# GET (currency package)
"groups": ["currency"]

# PUT (both)
"groups": ["turret_skins"]
```

Sending the expanded object back does not error outright but is the kind of
shape mismatch worth normalizing defensively — always reduce to `external_id`.

## `content` (bundles, currency packages)

GET expands every bundle/package line item into its full underlying object
(name, description, image_url, item_id, type, …). PUT wants only the SKU and
quantity.

```
# GET
"content": [{
  "item_id": 1553624, "sku": "cores", "type": "virtual_currency",
  "name": {...}, "description": {...}, "image_url": null,
  "quantity": 1200
}]

# PUT
"content": [{ "sku": "cores", "quantity": 1200 }]
```

Sending the GET shape back on `content[0]` returns:

```
422 { "errorCode": 1102, "errorMessage": "[0401-1102]: Unprocessable Entity",
      "errorMessageExtended": [{ "property": "content[0]", "message": "..." }] }
```

## `virtual_prices` → `vc_prices` (bundles only)

This is the one that costs the most debugging time, because the error message
talks about pricing, not shape. GET returns a bundle's VC price under
**`virtual_prices`**, fully expanded (the paying currency's full item object).
PUT does not accept `virtual_prices` back at all — it wants the same data
reduced and **renamed** to **`vc_prices`**.

```
# GET
"virtual_prices": [{
  "sku": "cores", "amount": 4000, "is_default": true,
  "item_id": 1553624, "type": "virtual_currency",
  "name": {...}, "description": {...}, "image_url": "..."
}]

# PUT
"vc_prices": [{ "sku": "cores", "amount": 4000, "is_default": true }]
```

Sending `virtual_prices` back (expanded or reduced, doesn't matter — the field
name itself is wrong for PUT) returns:

```
422 { "errorCode": 4055, "errorMessage": "[0401-4055]: Item default price not set" }
```

This reads like the bundle's price configuration is broken. It isn't — the
default *is* set, PUT just never saw it because it was looking for `vc_prices`.
Virtual items use `vc_prices` on both GET and PUT, which is why this only shows
up on bundles: it's the one entity where the field is named differently on the
way in and the way out.

## Fields to drop entirely before PUT

Read-only, rejected or ignored on write depending on item type: `item_id`,
`regional_prices` (computed from `prices` + `regions`, not settable directly),
`media_list`, `type`, `is_paid_randomized_reward`. Leaving these in generally
doesn't error, but strip them for a cleaner diff against your pre-update backup.

## Verifying you got it right

Before running the transform across every SKU, PUT one item back with **no
changes at all** (not even the image) and diff the GET response before and
after. Any field that moved besides the one you intentionally changed means
the transform above is incomplete for that item type — fix it before writing
the rest of the catalog.

# Finding a reward item in the Store catalog

Read before proposing a reward that names a Store item. The Quest Platform does not look items up:
this is how the skill finds the SKU, the name and the image itself.

## The reads

Only these reads of the Store admin catalog, on `https://store.xsolla.com`, for the configured
project, with the publisher key ([auth-credentials.md](auth-credentials.md)). Each list pages the
same way and returns items with the same fields (`sku`, `name`, `image_url`, `type`,
`is_enabled`, `is_show_in_store`, `periods`):

| Read | Use |
|---|---|
| `GET /api/v2/project/{project_id}/admin/items/virtual_items?limit=50&offset={offset}` | Virtual items |
| `GET /api/v2/project/{project_id}/admin/items/bundle?limit=50&offset={offset}` | Bundles |
| `GET /api/v2/project/{project_id}/admin/items/virtual_currency?limit=50&offset={offset}` | Virtual currencies |
| `GET /api/v2/project/{project_id}/admin/items/virtual_currency/package?limit=50&offset={offset}` | Currency packages |
| `GET /api/v2/project/{project_id}/admin/items/virtual_items/sku/{sku}` | Check a SKU of a virtual item the publisher typed |

Read all four lists before saying an item is not in the store. A SKU of another kind that the
publisher typed is checked by finding it in its list.

The item's **name** and its **SKU** are different values: show the name to the publisher, and put
the SKU in the reward. Never call an item by its SKU or a SKU by the item's name.

Never write to the Store, even when asked: creating or editing items is outside this skill. Never
use web search to find an item.

## Paging

Start at offset 0 and, while `has_more` is `true`, add the number of items on the page to the
offset. Every page must be a 200 with an `items` array, a boolean `has_more` and a numeric
`total_items_count`. Stop the lookup on any other answer, on an empty page with `has_more: true`,
or when the final count differs from `total_items_count`. A stopped lookup is not an empty
catalog: say the item lookup could not be completed, and propose nothing.

## Matching a name

Read the whole catalog before deciding. Match the requested name case-insensitively against
`name.en`, then the other locales.

- **One exact match:** use its SKU, and show its name, SKU and image in the proposal.
- **Several, or only partial matches:** show them and let the publisher choose. Never pick.
- **None, in all four lists:** say it was not found in the store, show the items that are there
  by name, and ask whether it is delivered into the game instead (then follow
  [Rewards that are not Store virtual items](#rewards-that-are-not-store-virtual-items)). Never
  tell the publisher where to find a SKU in Publisher Account: this skill does not know. Never
  substitute another item.

A SKU the publisher typed is not checked until the single-item read returns it; a 404 means it is
not in the catalog. Do not ask the publisher to type a SKU for a Store item.

## Available as a Web3 reward

For a Web3 item, use only an item that is enabled (`is_enabled`), shown in the store
(`is_show_in_store`) and inside its sale period (`periods` empty, or one period contains now). When
the name matches only items that fail this, say the item exists but is not available as a Web3
reward, and stop.

## Rewards that are not Store virtual items

A loyalty program, a scoped currency, a Web3 token or an item delivered into the game has no
catalog read here. Ask the publisher for its SKU or ID once, show it in the proposal exactly as
given and marked "not checked", and let the yes cover it. Never invent one.

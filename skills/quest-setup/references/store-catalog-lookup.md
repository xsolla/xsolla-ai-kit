# Finding a reward item in the Store catalog

Read before proposing a reward that names a Store item. The Quest Platform does not look items up:
this is how the skill finds the SKU, the name and the image itself.

## The two reads

Only these two reads of the Store admin catalog, on `https://store.xsolla.com`, for the configured
project, with the publisher key ([auth-credentials.md](auth-credentials.md)):

| Read | Use |
|---|---|
| `GET /api/v2/project/{project_id}/admin/items/virtual_items?limit=50&offset={offset}` | Page through the whole catalog |
| `GET /api/v2/project/{project_id}/admin/items/virtual_items/sku/{sku}` | Check a SKU the publisher typed |

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
- **None:** say the item was not found and suggest checking its exact name or whether it is
  enabled. Never substitute another item.

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

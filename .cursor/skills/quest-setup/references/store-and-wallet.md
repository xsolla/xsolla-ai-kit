# Store catalog and recipient wallet

Read-only checks for a named Web3 reward. The catalog read and the wallet check are the only
GET calls on these hosts. Rewards are described in [rewards.md](rewards.md).

## Store admin catalog

Resolve a named `web3_item` through the Store admin virtual items reads at
`https://store.xsolla.com/api/v2/project/{project_id}/admin/items/virtual_items`,
with `{project_id}` set to the project id of the configured scope. Use only these
two GET routes:

| Route | Use |
|---|---|
| `GET .../admin/items/virtual_items?limit=50&offset={offset}` | page the full catalog |
| `GET .../admin/items/virtual_items/sku/{sku}` | validate a SKU the publisher typed |

Both reads go only through the request script with the `--store` flag, for example
`python3 "<skill base dir>/scripts/qp_request.py" GET /api/v2/project/{project_id}/admin/items/virtual_items --store --query limit=50 --query offset=0`
or `GET /api/v2/project/{project_id}/admin/items/virtual_items/sku/<sku> --store`. The
script fills `{project_id}` from the configured set and refuses any other store route,
any other method and a different project id (`scope_mismatch`).

Never issue a `POST`, `PUT`, `PATCH` or `DELETE` to any Store admin route, even
when the publisher asks for it; creating or editing items is outside this
skill. Never call a claim endpoint directly. Rewards are issued only by an
activated quest.

Start at offset 0 and, while the page's `has_more` is `true`, advance the
offset by the number of items on that page.
Require HTTP 200 and a JSON object with an `items` array, a boolean `has_more`
and a numeric `total_items_count` on every page. Abort the lookup on a 401, any
other non-200 status, a malformed body, an empty page with `has_more: true`,
or a final item count different from
`total_items_count`; never treat an aborted read as an empty catalog. Read the
complete catalog before deciding that a name has zero, one or several matches.

Each item has `sku`, a localized `name` object (for example `{"en": "Fire
Sword"}`), a localized `description` or `null`, `image_url` or `null`, `type`,
`is_enabled`, `is_show_in_store`, `periods`, `groups` and `attributes`. Match
the requested name case-insensitively against `name.en` first, then against the
other locales. An exact match is a candidate; when there is no exact match,
items whose name contains the requested words are candidates to show, never to
pick on your own.

Only an item that is mintable is a valid `web3_item` SKU: `is_enabled` and
`is_show_in_store` are both `true`, and `periods` is empty or one period
contains the current time. When the requested name matches only items that
fail this rule, say the item exists but is not available as a Web3 reward
(disabled, hidden from the store or outside its sale period) and stop.

A named item is resolved from the list pages alone. A SKU the publisher typed
is validated with the single-item read instead: require HTTP 200, the same
`sku`, and the mintable rule above. A 404 means the SKU is not in the catalog.
Abort on any other failure. The catalog project for the `web3_item` body is the
project id the read was scoped to. A zero or ambiguous result stops
the flow.

## Recipient wallet

The recipient check is the only call to the Web3 minting service:
`GET https://web3-minting-service.gcp-k8s-web3-prod.srv.local/wallet/{xsolla_id}`.
It resolves only on the corporate network and needs no credential; never send
the project API key to it and never issue writes to it.

HTTP 200 with a `walletAddress` means the user has a wallet; 404 means the user
has no wallet, which is a non-retryable blocker for a Web3 reward. Any other
status or a malformed body aborts the check; never treat an error as a missing
wallet. When the host cannot be resolved or reached, report the wallet check as
not run, never as "no wallet" and never as a confirmed wallet. Name the
unverified recipient wallet in the proposal or the event payload review so the
publisher's approval covers it.

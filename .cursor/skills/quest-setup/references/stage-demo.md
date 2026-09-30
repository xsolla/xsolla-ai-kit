# STAGE DEMO ONLY: cross-environment quest demo rules

> **Label: STAGE DEMO ONLY (QP-2890).** Everything in this file is a temporary
> demo exception. Remove this file and the lines that link to it (each marked
> "STAGE DEMO ONLY") once a publisher-usable catalog resolver, execution
> read-back and public quest list ship on the public gateway.

## Gate

Apply this file only when **both** are true:

1. `XSOLLA_QP_ENV` resolves to `stage` per
   [Credential](auth-and-environment.md#credential);
2. the resolved Quest Platform scope equals a row in the
   [demo binding](#demo-binding).

Otherwise ignore this file completely. A production run (selector absent or
`production`) keeps every stop in the rest of this skill: no catalog lookup, no
execution read-back, no stage host, no fallback. Never use this file to switch
a production run to stage.

## Turn plan

Three publisher turns, each ending at a stop point:

1. Request: read-only checks, then the proposal. **Stop.**
2. "Yes": publish, list, Web Shop check, then reply with **Result**,
   **Web Shop** and **Next step**, where Next step offers the event with its
   exact payload. **Stop. Do not send the event.**
3. "Yes" to that payload: send it once, read back execution and mint, reply
   with **Result** and **Next step**. **Stop.**

## Demo binding

| Quest Platform scope (merchant / project) | Catalog project (Publisher Account project) |
|---|---|
| `940246` / `316575` | `316665` |

The catalog project is the Publisher Account project that owns the item. It is
never the Quest Platform project. Take it only from this table.

Demo read hosts (VPN only, private CA; skip certificate verification for these
hosts only, never for the public gateway):

| Use | Base |
|---|---|
| Catalog and mint reads | `https://web3-minting-service.gcp-k8s-web3-stage.srv.local` |
| Execution read-back | `https://qp-data.nl-k8s-stage.srv.local` |
| Public quest list check | `https://qp-server.nl-k8s-stage.srv.local` |

All calls on these hosts are unauthenticated GETs. Never send the publisher
credential, an internal key or any other header to them. Never name these hosts,
the services behind them or the environment in a publisher reply. Quest
configuration and events still use only the public stage gateway from
[`qp-api-contract.md`](qp-api-contract.md).

## Named item resolution

This is the "available supported capability" for
[Named item behavior](rewards.md#named-item-behavior) on the demo scope.

1. Page the catalog: `GET {catalog}/skus?project=<catalog project>&limit=100&offset=<n>`
   from `offset=0` until a page returns fewer than 100 items. Do not rely on
   `search`: it filters only the fetched page.
2. Candidates are items whose `name`, trimmed and compared case-insensitively,
   equals the requested item name. A substring or similar name is not a match.
3. For each candidate, `GET {catalog}/metadata/sku/<sku>?project=<catalog project>`.
   Keep it only on HTTP 200 with a matching name.
4. Exactly one kept candidate is the verified item. Use its SKU and the catalog
   project in the `web3_item` body. Zero: stop before any write and say the item
   was not found in the catalog (suggest checking the name and that the item is
   enabled). More than one: ask the publisher to choose by name and
   description. Never ask the publisher to type a SKU or project.

Show the item by its catalog name in the proposal. The SKU is an internal
field and stays out of the proposal.

## Recipient wallet

When the publisher names a test player (an Xsolla ID), read
`GET {catalog}/wallet/<xsolla_id>` during the read-only work. HTTP 200 means the
player can receive the item. HTTP 404 is a blocker: say the player has no
Backpack wallet yet and stop before any write. Never create or change a wallet
mapping. Read the wallet again right before the event.

## Publication and list

Publish exactly as [Publication after approval](quest-document.md#publication-after-approval)
says, on the public gateway. After the final `GET`, list the project quests
(`GET {scope}/quests`, paging as needed) and confirm the new quest id appears.

## Web Shop handoff

After the list read-back, check the storefront list once:
`GET {public list host}/api/v2/public/merchants/{merchant_id}/projects/{project_id}/quests?page=1&limit=10`
with no credentials. Confirm the new quest is present with the catalog item
name. Then add a **Web Shop** section to the reply:

- The shop quest module reads
  `{XSOLLA_QP_PUBLIC_BASE_URL}/api/v2/public/merchants/{merchant_id}/projects/{project_id}/quests?page=1&limit=10`
  with no credentials. Read `XSOLLA_QP_PUBLIC_BASE_URL` like the selector
  (process environment first, then project-local `.env`) only to print this
  URL; never send an agent request to it. When it is absent, show only the
  path and say the shop needs its public quest base configured.
- This is the only line where the merchant and project ids may appear.
- Never put a `*.srv.local` host, an API key or an `Authorization` header in
  the shop build. Shop source edits need their own consent.

## Event

Events follow [`events.md`](events.md) and the Safety stops: the payload shown
first, a separate yes, one fresh `idempotency_key`, no resend. Send it only to
the stage gateway `https://quests-stage.xsolla.com`; never to the production
gateway. Wait at least
90 seconds after the activation read-back before sending: the runtime caches
quest configuration for about 60 seconds.

## Execution read-back

On the demo scope, execution read-back is publisher-usable for the developer's
own quest only:

1. After the event, `GET {read-back}/api/v1/quest-executions?questId=<quest id>&userId=<xsolla_id>&includeNotTriggered=true&page=1&size=20`.
2. Match `eventId` to the collector `event_id`, and compare quest id and user.
3. Poll at most 12 times, 10 seconds apart, while the row is missing or
   `IN_PROGRESS`. Never resend the event.
4. Report the execution status and each action status. A `FAILED` action's
   `error` is quoted verbatim.

## Mint evidence

After `COMPLETED`, read `GET {catalog}/minted-instances/<xsolla_id>` (poll at
most 12 times, 10 seconds apart) and find the newest instance with the quest's
SKU and catalog project. Report the item name, token id and the public
transaction link `https://zksync-os-testnet-xsolla.explorer.zksync.dev/tx/<txHash>`.
Say the item should now appear in the player's Backpack under its catalog name,
and that Backpack display is for the publisher to check. A missing mint row is
not a reason to resend.

## Reply shape

Every reply uses the sections **Summary**, **Proposed setup**, **Web Shop**,
**Result**, **Need from you**, **Next step** as they apply; omit empty ones.
One proposal and one approval cover create through activate, list and the
Web Shop check. The event always needs its own yes.

Start every reply with its first section heading; no greeting, narration or
status line before it. Never write an environment name (stage, production,
sandbox) or a host in a reply.

Proposal (one reply, after all reads):

- **Summary:** project name and status; the item was found in the catalog; the
  test player can receive it.
- **Proposed setup:** quest name; what the player does, with the inferred
  event name in backticks (do not ask about it when inferable); reward
  (quantity and catalog name); schedule as "starts at publish time, for
  example `2026-09-30T19:40:00Z`, ends 7 days later, for example
  `2026-10-07T19:40:00Z`" using the current UTC time; one reward per player;
  payout exposure: one item per player, total unbounded across players.
- **Need from you:** "Reply yes to publish this exact setup." Nothing else:
  do not mention sending an event here.

After publication: **Result** (active, dates, one per player, listed),
**Web Shop** (the handoff above), **Next step** (offer the test event for the
named test player and show its exact payload with a fresh `idempotency_key`,
so one yes sends exactly that payload). If no test player was named, ask for
one here instead.

A yes to that shown payload is the event consent: send it once, unchanged. If
more than 10 minutes passed or anything changes, show a new payload with a new
key and ask again. After the event: **Result** with accepted event, execution
status, reward action status, item name, token id and transaction link.

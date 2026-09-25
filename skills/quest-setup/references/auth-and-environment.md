# Authentication and environment

Stage OpenAPI and local runtime snapshots were checked on 2026-09-23;
credential lanes, scope and 401 bodies were rechecked on 2026-09-25. Stage
deployments churn and the revision is not pinned here, so revalidate before
writes.

This is the **only** file that names the hosts, the header or the credential.
Everywhere else says "an authenticated Quest Platform request". Keep it that
way: the credential lane is being replaced, and this file is the seam.

## Services

Three Quest Platform services, three jobs, plus one read-only Web3 helper.
Sending a request to the wrong one is the most common mistake.

| Service | Job | Stage host |
|---|---|---|
| qp-server | quest CRUD | `https://qp-server.nl-k8s-stage.srv.local` |
| qp-events-collector | event ingestion | `https://qp-events-collector.nl-k8s-stage.srv.local` |
| qp-data | read-only execution and metrics | `https://qp-data.nl-k8s-stage.srv.local` |
| web3-minting-service | the minting service; this skill uses read-only lookups only | `https://web3-minting-service.gcp-k8s-web3-stage.srv.local` |

All four are internal. They resolve only on the corporate network. There is no
environment variable for them; this table is the source. Their TLS certificates
are issued by Xsolla's private CA, which corporate devices trust. If
certificate verification fails, say so and ask for the CA file; never disable
verification.

Each service publishes its own OpenAPI document at `/openapi.json`, without a
credential, on stage. qp-server blocks those paths in production.

## Minting service

The Web3 reward provider. Observed on stage 2026-09-23, revalidate: these reads
returned 200 without a credential.

| Read | Use |
|---|---|
| `GET /currency-bindings` | ERC-20 SKU bindings: `bindings[]` with `projectId`, `sku`, `tokenStandard` |
| `GET /skus?project=<project id>` | NFT catalog of a project: `items[].sku`, paged with `limit` and `offset` |
| `GET /wallet/{xsolla_id}` | 200 with `walletAddress`, or 404 when the user has no wallet |

Never call `POST /claim`, `POST /claim/erc20` or any other write on it. Only the
worker pays out, and only through an activated quest.

Worker settings that decide Web3 behavior (observed on stage 2026-09-23,
revalidate):

- **ERC-20 project**: `WEB3_ERC20_PROJECT`, `306916` on stage. It is empty in
  the dev, local and prod worker configs, where every `web3_token` reward fails
  with `Web3TokenNotConfigured`, non-retryable. The quest's `publisher_id` and
  `project_id` do not change it.
- **Default NFT catalog**: the worker sends no project when it lists or claims
  `web3_item` SKUs, so the service's default project applies, `44056` on stage.

For manual checks by a human only: the stage chain is Xsolla ZK Sepolia
testnet, chain id `579029`, explorer
`https://zksync-os-testnet-xsolla.explorer.zksync.dev`, RPC
`https://579029.rpc.thirdweb.com`. This skill does not call them.

## Credential

Two lanes. Name the variable you found; do not look for other credentials in
the environment or in files without asking.

| Lane | Variables | Sent as |
|---|---|---|
| Publisher Basic, the target | `XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_API_KEY` | `Authorization: Basic base64(merchant_id:api_key)` |
| Service key, Xsolla-internal interim | `QP_SERVICE_KEY` | `X-REQUEST-APIKEY: <key>` |

**Basic is not accepted yet.** On the deployed build, qp-server recognises only
`Authorization: Bearer` (human sign-in, not used by this skill; it wins if both
are sent) and `X-REQUEST-APIKEY`, so a Basic credential is rejected as if no
credential were sent. The implementation is QP-2862, inside QP-2858 Phase 3,
which depends on Phase 1 (QP-2851) and Phase 2 (QP-2852).

**The service key is the lane that works on stage today** (2026-09-25,
revalidate). It is an internal Quest Platform key bound to one account, and it
is not a publisher credential. If only the Basic variables are set, say Basic
is not accepted yet, name QP-2862, and ask whether an internal service key is
available. Never print, log or commit the key; refer to it by its first four
characters. The OpenAPI document labels the header "Master API key"; a service
key is not a master key.

### Reading a 401

| Service | Body | Meaning |
|---|---|---|
| qp-server | `{"error":"Authentication required"}` | no recognised credential. Every Basic credential gets this, valid or not, so it says nothing about the Basic key |
| qp-server | `Invalid API key` or `Invalid API key format` | the service key was sent and rejected |
| qp-events-collector | `X-REQUEST-APIKEY header is required` | no key sent |
| qp-events-collector | `Invalid or inactive API key` | the key was rejected |

## Service preflight

Do not assume one service's credential works for the others. One read each,
before the first write:

- `qp-server`: `GET /api/v2/quests?limit=1`. A 200 proves the credential is
  accepted and can read quests; it does not prove write capabilities.
- `qp-events-collector`: no read checks the key. `POST /api/v2/events` takes
  only `X-REQUEST-APIKEY` and validates it against qp-server (cached up to 5
  minutes), so the qp-server read with the same service key is the evidence.
  Do not use its project-scoped event route; it depends on a qp-server
  endpoint that is not deployed.
- `qp-data`: `GET /api/v1/quest-executions?size=1`. It answered 200 without a
  credential on 2026-09-25. Treat that as a snapshot, not a contract.

Bring-up and preflight are GET-only. Ask before any other call.

## Scope

With the service key, scope is the key's own account, which belongs to a
workspace. The key carries no `publisher_id` or `project_id`: they are optional
per-quest body values, and events match on them (see `events.md`). A quest list
is not a scope readout: its items carry no `account_id`, and an empty list
returns nothing.

1. Ask the developer which account the key belongs to, read it with
   `GET /api/v2/accounts/{account_id}`, and show `name`, `status` and
   `workspace_id`. If they do not know the id,
   `POST /api/v2/keys/validate` returns the key's `account_id` and changes
   nothing. Ask before calling it, and never show its `key` field, which
   echoes the full key.
2. At create time, ask for `publisher_id` and `project_id`, or get an explicit
   "none". `XSOLLA_PROJECT_ID`, if set, may be offered as a suggestion, never
   used silently.
3. After confirmation, stay on the scopeless quest routes; they resolve to the
   key's account. Use `/api/v2/accounts/{account_id}/quests` only when the
   developer names an account explicitly.

Do not guess a scope, and do not silently accept whichever scope the
credential happens to carry. When the Basic lane lands, its scope comes from
the merchant and project; revisit this section then.

## Route families this skill does not drive

They exist on the platform. They are listed so that you neither pretend they
are missing nor wander into them.

- `/api/v2/quests/{publisher_id}/{id}` — a publisher-scoped update, delete and
  get. No create and no list, so it cannot carry the flow. Use it only if a
  developer asks for it by name.
- `GET /api/v2/quests/find-quests` and `GET /api/v2/quests/find-quests-triggers`:
  internal processing endpoints. A service key gets 403 `Master role
  required`. Do not call them.
- `GET /api/v2/quests/personalization/{user_id}` and its account-scoped twin:
  a personalization read path, not quest management. Read-only, and only if a
  developer asks for it by name.

**Off-limits**, even when the key reaches them: `/api/v2/workspaces/**`,
`/api/v2/accounts/{account_id}/grants/**`, `/api/v2/accounts/{account_id}/keys/**`,
`DELETE /api/v2/accounts/{account_id}`, `/api/v2/subscriptions/**` and
`POST /api/v2/qp-data/republish`. They administer identity, access and data
pipelines. Do not probe them; for scope, use only the account read above. A
developer who needs one should go to the Quest Platform team.

## Incoming changes

These are open and unmerged. Re-read the deployed contract before assuming any
of it; do not implement against the tickets.

- QP-2851 Phase 1, service identities and machine identity groundwork. Changes
  how a service principal's scope is resolved, and can resolve to a workspace
  rather than an account.
- QP-2852 Phase 2, a second human issuer, Xsolla Publisher Account.
- QP-2858 Phase 3, Xsolla scope mapping and the publisher machine lane.
  QP-2860 may add project-scoped publisher-facing routes, in which case the
  scopeless choice above should be revisited.
- QP-2862, the Basic lane this skill targets.

Today a quest outside the credential's account returns the same 404
`Quest not found` as a missing one. Phase 3 plans byte-identical 404s for
unknown, un-onboarded and unauthorized projects, so that the endpoint cannot
be used to enumerate them. Either way, report a 404 as "not visible with this
credential", never as "deleted" or "does not exist".

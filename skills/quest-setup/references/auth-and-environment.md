# Authentication and environment

Stage OpenAPI and local runtime snapshots were checked on 2026-09-23. The
credential lanes, the project routes, onboarding, scope and the 401/404 bodies
were rechecked live on 2026-09-25, after the project routes moved under
`/api/v2/merchants/{merchant_id}/...`. The collector route list was rechecked
live the same day, around 09:20Z: it lists only `POST /api/v2/events` (plus
health and a debug route). Stage deployments churn and the revision is not
pinned here, so revalidate before writes.

This is the **only** file that names the hosts, the headers or the
credentials. Everywhere else says "an authenticated Quest Platform request".
Keep it that way: this file is the auth seam, and a lane change is edited here
and nowhere else.

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
worker pays out, and only through an activated quest. The same holds for quest
config: never point a `send_http_webhook` node at it (see
[send_http_webhook](node-subtypes.md#send_http_webhook)).

Worker settings that decide Web3 behavior (observed on stage 2026-09-23,
revalidate):

- **ERC-20 project**: `WEB3_ERC20_PROJECT`, `306916` on stage. It is empty in
  the dev, local and prod worker configs, where every `web3_token` reward fails
  with `Web3TokenNotConfigured`, non-retryable. The quest's `publisher_id` and
  `project_id` do not change it.
- **Default NFT catalog**: when a `web3_item` body has no `project`, the worker
  sends none when it lists or claims SKUs, so the service's default project
  applies, `44056` on stage. A `web3_token` without `project` uses the ERC-20
  project above.

Pipeline settings that decide event timing (stage, from the service configs;
revalidate):

- **Config caches**: qp-consumer-service and the worker each cache quest config
  for 60 seconds. The collector caches service-key validation for 5 minutes
  (code read, 2026-09-25).
- **`load_test` bypass**: `LOAD_TEST_BYPASS_ENABLED` is on in quest-engine on
  stage and off in production. There, a `load_test: "true"` event is a real
  event.

For manual checks by a human only: the stage chain is Xsolla ZK Sepolia
testnet, chain id `579029`, explorer
`https://zksync-os-testnet-xsolla.explorer.zksync.dev`, RPC
`https://579029.rpc.thirdweb.com`. This skill does not call them.


## Credential

The lane is the **Xsolla publisher project key**, sent as HTTP Basic on the
project-scoped routes. It works on stage (verified 2026-09-25).

| Variable | Use |
|---|---|
| `XSOLLA_MERCHANT_ID` | the Basic username and the `{merchant_id}` in every route below: the merchant that owns the project |
| `XSOLLA_PROJECT_API_KEY` | the Basic password: the project's API key from Publisher Account |
| `XSOLLA_PROJECT_ID` | the `{project_id}` in every route below. Optional; if unset, ask the developer |

Every qp-server request carries exactly one header:

`Authorization: Basic base64(<merchant_id>:<api_key>)`

Build it at call time from the variables. Never print, log or commit the key
or the encoded header; refer to the key by its first four characters. The
ids in a path (merchant, project, quest) are not secret and may be shown; only
the key and the encoded header are masked. Send
only one credential per request: `Authorization` together with
`X-REQUEST-APIKEY` returns 400 `Only one authentication method may be used per
request`.

Where to look:

- Check the process environment and the project's own `.env` for exactly the
  variable names above. That needs no extra yes. Report which names are set,
  never their values.
- Read `.env` as text: take only lines of the form `KEY=value`, allow an
  `export ` prefix and one pair of surrounding quotes, and skip comments and
  blank lines. Never source, `.` or otherwise execute the file, and never echo
  a line of it.
- If the developer names a differently named variable or file, use it after
  saying which one you will read.
- Do not search other files, other variables, keychains or shell history for
  credentials. If a variable is missing, say which one and ask.
- `ID 0` is a valid merchant ID and a valid project ID; never treat it as
  absent.

A project id the developer offers, or `XSOLLA_PROJECT_ID`, is a candidate until
`GET /api/v2/merchants/{merchant_id}/projects/{project_id}` returns 200 with
that key. Do not write before that.

If the developer names a project id that differs from a set
`XSOLLA_PROJECT_ID`, stop and ask which one they mean. The key most likely
belongs to the `.env` project, so the other id probably needs its own key. Do
not call either route before the answer.

### The merchant id in the path

`{merchant_id}` is always `XSOLLA_MERCHANT_ID`, the same value as the Basic
username. Never take it from a quest body, a qp-data row, an earlier answer,
the developer's memory or a guess, and never put a different value in the path
than in the header. If the developer names another merchant, it needs another
key; ask for both variables instead of mixing them.

Why this matters: stage does not check the path merchant (verified
2026-09-25: a valid key with a path merchant that is not its own still got
200). On every create the server stamps the quest's `publisher_id` from the
**path** `{merchant_id}`. So a wrong path merchant is not rejected; it silently
stores a wrong `publisher_id`, and that quest never matches the developer's
events. Production is expected to answer 404 instead (inferred from code, not
checked).

### Project-scoped routes

Basic works only on this family. Scope comes from the route, never from the
credential or the body.

| Route | Use |
|---|---|
| `GET /api/v2/merchants/{merchant_id}/projects/{project_id}` | scope readout and onboarding check |
| `POST /api/v2/merchants/{merchant_id}/projects/{project_id}/onboard` | one-time onboarding, see below. A write |
| `GET /api/v2/merchants/{merchant_id}/projects/{project_id}/quests` | list; query `page`, `limit`, `publisherID`. No name filter |
| `POST /api/v2/merchants/{merchant_id}/projects/{project_id}/quests` | create |
| `GET`, `PUT`, `DELETE /api/v2/merchants/{merchant_id}/projects/{project_id}/quests/{id}` | read, full replace, soft delete |

The old family `/api/v2/projects/{project_id}/...` is gone from qp-server on
stage (2026-09-25); it answers 404 plain text `Cannot GET <path>`. If the
developer says "project routes" or names an old `/api/v2/projects/...` path,
they mean this merchant family: say the mapping in one line and continue. It
is the documented family, so it needs no separate yes.

On every other qp-server route, including the scopeless `/api/v2/quests`,
`/api/v2/accounts/**`, `/api/v2/workspaces` and the merchant's project list
`GET /api/v2/merchants/{merchant_id}/projects` (no `{project_id}`), a Basic
credential gets 401 `{"error":"Basic credentials are only accepted on
project-scoped routes"}`. That means the route is wrong for this lane, not that
the key is bad. Do not retry it with another credential.

**Events: Basic has no route (stage, verified 2026-09-25 around 09:20Z).** The
live collector OpenAPI lists only `POST /api/v2/events`, with a service key
(`X-REQUEST-APIKEY`) or a Bearer token, plus health and a debug route. The
project event route `/api/v2/projects/{project_id}/events` was removed, and
there is no `/merchants/...` event route. So this skill cannot send an event
on the Basic lane. Do not send Basic to `/api/v2/events`, and do not try other
paths. See `events.md` for what to say instead.

### When a route is missing

A 404 with a plain text body `Cannot GET <path>` (or another method in place
of `GET`) is a router miss: no route with that path is deployed. It is not an
auth answer and not a project answer, so never report it as a bad key, a
missing project or a project that needs onboarding. The rule is the same
whether a read or a write failed:

1. Stop. Do not retry the call, and do not try other paths by hand.
2. Fetch the live `/openapi.json` of that service and look for the same
   operation (same method and purpose) under another route family.
3. If you find it, tell the developer the old path, the new path and where
   you saw it, and ask before calling it. That holds for reads too; nothing on
   the new family is called until the developer says yes. For a write, show
   the request again on the new path before the yes.
4. If you do not find it, say that the operation is not deployed on this
   environment and stop.

Stage routes churn. The live OpenAPI decides the path; the developer decides
the switch. A path in this file that the live OpenAPI does not list is stale:
report it, do not work around it silently.

The same holds **before** a call. If a route this skill names is absent from
the live OpenAPI you fetched, do not call it, not even once as a probe. Say
which route is missing and from which service's OpenAPI, follow steps 2 to 4
above, and ask the developer how to continue.

### Reading a 401 or 404

The auth layer returns plain `{"error": "..."}` bodies. Quote them verbatim.

| Service | Status and body | Meaning |
|---|---|---|
| qp-server | 401 `{"error":"Authentication required"}` | no credential header was sent |
| qp-server | 401 `{"error":"Invalid credentials"}` | the project is known, and Xsolla rejected the merchant and key for it, or the header is malformed |
| qp-server | 401 `{"error":"Invalid token"}` | a Bearer header was sent and rejected; this skill does not send Bearer |
| qp-server | 401 `{"error":"Basic credentials are only accepted on project-scoped routes"}` | Basic sent to a route outside the project family; use the project route |
| qp-server | 404 `{"error":"Project not found"}` | see below |
| qp-server | 404 plain text `Cannot GET <path>` | router miss; see "When a route is missing" |
| qp-server | 422 problem+json `invalid integer`, `location` `path.merchant_id` | the path merchant is not an integer; check `XSOLLA_MERCHANT_ID` |
| qp-server | 400 `{"error":"Only one authentication method may be used per request"}` | two credential headers were sent |
| qp-server | 503 `Credential validation is temporarily unavailable` (from code, not observed) | Xsolla could not be reached; retry a read later, do not resend a write |
| qp-server | 403 `Service identity is inactive` (from code, not observed) | the project's access was deactivated; go to the Quest Platform team |

**`Project not found` is deliberately uniform.** An unknown project id, a
project that is not onboarded, a project owned by another merchant (the key's
merchant is not the project's stored merchant) and a non-integer project id
all return the same 404 with the same body. For an unknown project the key is
not even checked, so a wrong key there also gives this 404. The skill cannot
tell these cases apart. Say so, name the merchant id and project id you used,
and ask the developer to check them. Never report it as "the project does not
exist" or "the key is wrong". No read-only step narrows it down: every GET
this lane can make gets the same 404, so do not probe further. A path merchant
that differs from the key's merchant does not produce this 404 on stage (see
"The merchant id in the path"). Whether to offer onboarding next is decided in
"Onboarding" below.

A missing quest on a known project is a different body: problem+json with
`"detail":"Quest not found"`. Report it as "not found, or not visible with this
credential".

## Onboarding

A project must be onboarded once before any quest route works for it. When
`GET /api/v2/merchants/{merchant_id}/projects/{project_id}` returns 200, the
project is onboarded: there is nothing to offer. When it returns 404
`{"error":"Project not found"}`, onboarding is one possible cause among those
above. A `Cannot GET` 404 is never a reason to onboard.

Offer onboarding only after the developer says the project belongs to their
merchant (the one in `XSOLLA_MERCHANT_ID`). Until then, report the uniform 404,
name the ids used, and ask them to check the ids; do not offer the call.

`POST /api/v2/merchants/{merchant_id}/projects/{project_id}/onboard` with body
`{"merchant_name": "<string>", "project_name": "<string>"}`, both required.
`{merchant_id}` is `XSOLLA_MERCHANT_ID`, as on every route.

It is a write. **Never call it silently or as a probe.** Offer it, and call it
only after an explicit yes:

1. Lead with the side effect: it grants publisher-key access to **every
   project of the key's merchant**, not only this one. In the same
   transaction it creates, if missing, a Quest Platform workspace for that
   merchant and an account for this project. This skill cannot undo it;
   whether it can be undone at all is not verified, so point to the Quest
   Platform team for that.
2. Say that the 404 has several possible causes the skill cannot tell apart,
   and that onboarding fixes only the "not onboarded" one.
3. Ask for `merchant_name` and `project_name`. Never invent them. They are
   used only for rows the call creates.
4. Show the request, without the credential, and wait for the yes.

Outcomes (from the OpenAPI and code, 2026-09-25; not called live):

| Response | Meaning |
|---|---|
| 200 with `{project_id, name, status, created_at, updated_at}` | onboarded, or already onboarded (the call is idempotent and changes nothing the second time). Re-read `GET /api/v2/merchants/{merchant_id}/projects/{project_id}` and continue with Scope |
| 401 `Invalid credentials` | Xsolla rejected this merchant and key for this project id; this route checks the key even for an unknown project |
| 404 `{"error":"Project not found"}` | the project is mapped to another merchant's workspace, or the id is not an integer |
| 404 plain text `Cannot GET` or `Cannot POST <path>` | router miss; see "When a route is missing" |
| 403 | the credential is not a publisher lane |

After a timeout or 5xx, read
`GET /api/v2/merchants/{merchant_id}/projects/{project_id}` before offering
the call again.

## Service preflight

Do not assume one service's credential works for the others. One read each,
before the first call to that service, and only for the services the task
will call. A read-only verification flow needs no qp-server preflight beyond
the project GET in Scope; it runs only the qp-data check before its first
qp-data read.

- `qp-server`: `GET /api/v2/merchants/{merchant_id}/projects/{project_id}`,
  then `GET /api/v2/merchants/{merchant_id}/projects/{project_id}/quests?limit=1`.
  Two 200s prove the key is accepted for the project and can read quests; they
  do not prove write capabilities, and on stage they do not prove the path
  merchant is right (it is not checked). A `Cannot GET` here follows "When a
  route is missing".
- `qp-events-collector`: nothing to preflight on Basic. Say at every bring-up
  that events cannot be sent on this lane on stage (no Basic event route,
  2026-09-25), and say it again whenever the developer asks for activation or
  a smoke test. See `events.md`.
- `qp-data`: `GET /api/v1/quests?publisherId=<XSOLLA_MERCHANT_ID>&projectId=<confirmed project id>&size=1`
  (200 verified 2026-09-25, rows matched the scope). Run it only after Scope
  step 1 confirmed the project. It answers without a credential; treat that
  as a snapshot, not a contract. Check that every returned row carries the
  same `publisherId` and `projectId`; if any does not, discard the body,
  show nothing from it, and report that the filter was not applied. Never use
  an unscoped probe such as `GET /api/v1/quest-executions?size=1`: it pulls
  another tenant's row into context. Later reads go only by the developer's
  own quest id, user id, event, or by `publisherId` together with `projectId`
  for the confirmed scope. Do not call `GET /api/v1/accounts`, and do not
  list other tenants' quests or executions; it is not a scope readout.

Bring-up and preflight are GET-only. Ask before any other call.

## Scope

With Basic, scope is the merchant and project in the route. Behind it, the
project maps to one Quest Platform account inside the merchant's workspace.

1. Read `GET /api/v2/merchants/{merchant_id}/projects/{project_id}` and show
   the merchant id you used, `project_id`, `name` and `status`. The response
   has no merchant id of its own. Get the developer's confirmation that this
   is the intended project before the first write.
2. The server sets the quest's `publisher_id` to the path `{merchant_id}` and
   its `project_id` to the path `{project_id}` on every create, as strings,
   and ignores the values in the body. Do not ask for them, do not invent
   them, and do not try to override them. Show them from the create response,
   and check that `publisher_id` equals `XSOLLA_MERCHANT_ID`; if it does not,
   stop and report it.
3. On a full `PUT`, send `publisher_id` and `project_id` exactly as the last
   read returned them. A `PUT` keeps the stored `publisher_id`, and a
   different `project_id` in the body would overwrite the stored one (from
   code, not observed).
4. The response carries no `account_id` or `workspace_id`, and Basic cannot
   read them. The only readout is qp-data's `accountId` on the developer's own
   quest, after the first create. Do not guess them.

Do not guess a scope, and do not switch projects, merchants or credentials
without the developer saying so.

## Service key: staff only

`X-REQUEST-APIKEY: <key>` from `QP_SERVICE_KEY` is an Xsolla-internal Quest
Platform key bound to one account, on the scopeless `/api/v2/quests` routes.
It is not a publisher credential, and its account is not the project's
account: a quest made with it does not match events sent on the project lane,
and the reverse. Use it only when the developer explicitly chooses it, never
as a silent fallback after a Basic failure.

A quest made on this lane lives in the service key's account, not in the
project's. A developer on Basic cannot read, edit or verify it: it answers
`Quest not found` on the project routes (inferred from the account scoping,
not checked). Do not switch lanes to reach it and
do not read its qp-data rows; say that it belongs to another lane and point
them to the Quest Platform team.

Status on stage, 2026-09-25: keys created after migration 000014 get 401
`{"error":"Invalid API key"}` (seen on `GET /api/v2/quests`; a backend bug
on the Quest Platform side). If that happens, report it verbatim and stop; do not
debug the key. If a key does work, its account name comes from
`GET /api/v2/accounts/{account_id}`; the `name` from `POST /api/v2/keys/validate`
is the key's name, not the account's. The OpenAPI labels the header "Master
API key"; a service key is not a master key.

## Bearer lane: not covered

The project routes and the collector also accept a Publisher Account token
(`Authorization: Bearer <JWT>`; seen in the stage OpenAPI and code,
2026-09-25). This skill does not cover or verify that lane. Do not ask for a
token, do not send one, and do not suggest it as a workaround. If the
developer wants it, say that it is outside this skill and point them to the
Quest Platform team.

## Route families this skill does not drive

They exist on the platform. They are listed so that you neither pretend they
are missing nor wander into them.

- `/api/v2/quests/{publisher_id}/{id}`: a publisher-scoped update, delete and
  get with no create or list. Basic is rejected there. Do not use it.
- `POST /api/v2/publisher-credentials/validate`: internal, master key only
  (401 `X-REQUEST-APIKEY header is required` otherwise). Do not call it. Its
  body is `{project_id, merchant_id, authorization}`; that only matters when
  reading a diagnosis.
- `GET /api/v2/merchants/{merchant_id}/projects`: the merchant's project list,
  not reachable with Basic.
- `GET /api/v2/quests/find-quests` and `GET /api/v2/quests/find-quests-triggers`:
  internal processing endpoints. Do not call them.
- `GET /api/v2/merchants/{merchant_id}/projects/{project_id}/quests/personalization/{user_id}`
  and its scopeless twins: a personalization read path, not quest management.
  Read-only, and only if a developer asks for it by name.

**Off-limits**: `/api/v2/workspaces/**`, `/api/v2/accounts/{account_id}/grants/**`,
`/api/v2/accounts/{account_id}/keys/**`, `DELETE /api/v2/accounts/{account_id}`,
`/api/v2/subscriptions/**` and `POST /api/v2/qp-data/republish`. They
administer identity, access and data pipelines. Do not probe them. A developer
who needs one should go to the Quest Platform team.

## Deployment status

Stage runs a pre-release build of the publisher lane (QP-2858, tag
`stage-adtech-qp-server-publisher-auth-v6`; inferred from the stage tag and the
live OpenAPI, 2026-09-25). Production was not checked and may not have the
project routes or onboarding. On another environment, fetch its OpenAPI route
list first; if `/api/v2/merchants/{merchant_id}/projects/{project_id}` is
missing, follow "When a route is missing": name any other family that carries
the same operations and ask, or say that the publisher lane is not deployed
there and stop. Do not fall back to another lane without the developer's
choice.

# Quest Platform publisher API contract

This reference records the publisher-facing Quest Platform route contract
verified against the source revision below. Use it for Quest Platform route
discovery in this skill, then make a read-only request against the selected
public gateway before any write. Do not infer that a route works in a given
environment from source alone.

## Provenance and gateway baseline

- Source repository: `adtech-QP-2934` (qp-server, qp-events-collector, qp-data)
- Inspected revision: `9aa6e3aa2d03e82834d226e56adf148701253aa6`
  (short `9aa6e3aa2d`; quest configuration, event ingestion and execution
  read-back all verified at this same revision)
- Quest route and auth source: `qp-server/internal/http/handler/xsolla_scoped.go`,
  `qp-server/internal/http/middleware/publisher_key.go`
- Production OpenAPI behavior: each service's `internal/http/router.go`
- Gateway sources: `*/postman/environment-prod.json` and
  `*/postman/environment-stage.json`
- Public bases: production `https://quests-platform.xsolla.com`; stage
  `https://quests-stage.xsolla.com`

Unauthenticated probes run on 2026-09-30, with no query parameters:

| Request | Status | Effective URL |
|---|---:|---|
| `GET https://quests-stage.xsolla.com/openapi.json` | 200 | `https://quests-stage.xsolla.com/openapi.json` |
| `GET https://quests-platform.xsolla.com/openapi.json` | 404 | `https://quests-platform.xsolla.com/openapi.json` |

The production `404` is intentional: the production router explicitly blocks
`/openapi.json` and related docs/schema paths. Do not fetch production OpenAPI
for route discovery. Consult stage OpenAPI only when `XSOLLA_QP_ENV=stage`
selects stage. On a production run, never fetch stage OpenAPI or any
non-selected target, and never fall back to stage credentials or services.

## Publisher authentication and scope

For the publisher Basic lane, send HTTP Basic credentials whose value is
`base64(merchant_id:api_key)`: the merchant ID is the Basic username and the
selected project's API key is its password. The IDs and key are the
production credential set resolved from one configured source. The API key is
not the username by itself. Never print or persist the encoded credential.

The project ID remains an explicit route parameter. The Basic credential does
not supply project scope. Do not move project scope into a query or request
body, and do not substitute internal `X-REQUEST-APIKEY` routes. Merchant and
project path values must match the same selected production credential set.

## Verified route templates

`{merchant_id}` and `{project_id}` are Xsolla IDs. `{quest_id}` is the quest
UUID. All routes below use the public production base above when configuring a
production quest.

| Operation | Method and path | Use |
|---|---|---|
| Read project | `GET /api/v2/merchants/{merchant_id}/projects/{project_id}` | Confirm project scope and visibility before setup |
| List project quests | `GET /api/v2/merchants/{merchant_id}/projects/{project_id}/quests` | Page through quests in this project |
| Create quest | `POST /api/v2/merchants/{merchant_id}/projects/{project_id}/quests` | Create with `status: inactive` for a draft |
| Read quest | `GET /api/v2/merchants/{merchant_id}/projects/{project_id}/quests/{quest_id}` | Read the full quest document |
| Replace quest | `PUT /api/v2/merchants/{merchant_id}/projects/{project_id}/quests/{quest_id}` | Replace the full quest document |

There is no partial update route in this contract. Create the quest with
`status: inactive`, then activate it in a later full-document `PUT`, after a fresh
`GET` and the confirmations in [The quest document](quest-document.md).

## Interpreting failures

These outcomes answer different questions:

- `401` means authentication was required or the supplied credential was not
  accepted. Do not switch credentials or auth schemes as a retry.
- A project-scope `404` can represent an unknown, un-onboarded or inaccessible
  project. It does not identify which condition applies, and it is not a
  router-discovery result.
- A router-miss `404` such as a plain `Cannot GET ...` means the method/path is
  not routed at that location. It does not establish a credential or project
  result.
- A timeout, DNS/TLS error or other connection failure is transport
  unavailability. It establishes neither authentication nor project state.

Stop after a failure and report its status and safe response detail. Do not
guess another path or change environment based on the status alone.

## Event ingestion (qp-events-collector)

Provenance for this section matches the same inspected revision
`9aa6e3aa2d03e82834d226e56adf148701253aa6` (quest configuration routes were
verified earlier at the same short form `9aa6e3aa2d`).

| Item | Value |
|---|---|
| Source | `qp-events-collector/internal/http/handler/event.go`, `middleware/middleware.go`, `validation/event_payload.go` |
| Production base | `https://quests-platform.xsolla.com` (`qp-events-collector/postman/environment-prod.json`) |
| Stage base | `https://quests-stage.xsolla.com`, only when `XSOLLA_QP_ENV=stage` (unauthenticated probe 2026-09-30: `POST /api/v2/events` with `{}` returned 401 `Authentication required`, routed) |
| Route | `POST /api/v2/events` |
| Publisher auth lane | HTTP Basic `base64(merchant_id:api_key)` (merchant ID username, project API key password). A Publisher Account Bearer JWT is also admitted by the collector; this skill uses only the Basic lane. |
| Publisher body scope | For the Basic lane, `publisher.publisher_id` and `publisher.project_id` are required positive integer Xsolla IDs in the JSON body. |
| Server-side dependency | The collector validates the Basic header via qp-server `POST /api/v2/publisher-credentials/validate` using a master service key. That validate route exists at this revision and is internal (master `X-REQUEST-APIKEY` only). The publisher never calls it, and this skill never uses a master or request API key. |

Required payload fields (hand-written validator):

| Field | Required | Rules |
|---|---|---|
| `idempotency_key` | yes | non-zero UUID |
| `name` | yes | non-empty |
| `client_timestamp` | yes | RFC3339 |
| `user_ids` | yes | at least one entry; `identifier_type` one of `xsolla_id`, `gamer_id`, `guest_id`, `email`, with type-specific `value` rules |
| `publisher` | yes for Basic lane | `publisher_id` and `project_id` positive integer strings |
| `quest_id` | no | UUID when present |
| `scope` | no | default `private`; also `global` or `within_project` |
| `properties` | no | string map; never include secrets |

Success body: `idempotency_key` echoed and `event_id` (new event identifier). Keep
`event_id` for correlation.

Failure meanings (publisher-visible):

- `401` `Authentication required` or `Invalid credential`: missing or rejected
  publisher credential (uniform denial; do not enumerate projects).
- `422`: payload validation failed.
- `503` `Credential validation is temporarily unavailable`: qp-server could not
  check the key; says nothing about the key itself.

Unauthenticated production probes (2026-09-30, no Authorization, no secrets):

| Request | Status | Interpretation |
|---|---:|---|
| `POST https://quests-platform.xsolla.com/api/v2/events` with `Content-Type: application/json` and body `{}` | 401 | Routed (`{"error":"Authentication required"}`) |
| `GET https://quests-platform.xsolla.com/openapi.json` | 404 | OpenAPI blocked on the production gateway |

Publisher Basic lane: **yes**, a publisher project key may submit events on
this production route after the gate in [`events.md`](events.md).

## Execution read-back (qp-data)

Provenance: same revision `9aa6e3aa2d03e82834d226e56adf148701253aa6`.

| Item | Value |
|---|---|
| Source | `qp-data/internal/http/handler/quest_executions.go`, `middleware/auth.go`, `router.go`, `internal/service/query_service.go` |
| Production base recorded in Postman | `https://quests-platform.xsolla.com` (`qp-data/postman/environment-prod.json` shares the QP gateway keys; the collection uses `{{base_url}}`) |
| Route template in source | `GET /api/v1/quest-executions` with repeatable filters `questId`, `userId`, `publisherId`, `accountId`, `status`, plus `latestPerUser`, `includeNotTriggered`, `includeEventBody`, `page`, `size` |
| Auth lane in source | Overlay header `X-QP-Api-Key` (admin or overlay key) when `AUTH_ENABLED` is true. Production config sets `AUTH_ENABLED: 'true'`. **Publisher Basic is not accepted.** |

Response item fields (source): `eventId`, `eventName`, `questId`, `accountId`,
`status` (`NOT_TRIGGERED` / `IN_PROGRESS` / `COMPLETED` / `FAILED`),
`failReason`, `ingestedAt`, `user`, `quest`, `account`, `actions[]`
(with per-action `status`, `error`, `actionType`), `conditionEvals[]`.

Unauthenticated production probes (2026-09-30):

| Request | Status | Interpretation |
|---|---:|---|
| `GET https://quests-platform.xsolla.com/api/v1/quest-executions` | 404 | Router miss (`Cannot GET /api/v1/quest-executions`) |
| `GET https://quests-platform.xsolla.com/openapi.json` | 404 | OpenAPI blocked |

Publisher Basic lane: **no**. Execution read-back is not publisher-usable with
the project API key. The skill must stop and report that read-back is
unavailable to the publisher credential. Never use an internal overlay or
request API key as a fallback.

**STAGE DEMO ONLY:** the stage deployment runs execution read-back with overlay
auth disabled. When the [stage demo gate](stage-demo.md#gate) passes, use
[Execution read-back](stage-demo.md#execution-read-back) without any key. The
production row above is unchanged.

# Quest Platform publisher API contract

This reference records the publisher-facing Quest Platform route contract.
Use it for Quest Platform route discovery in this skill, then make a read-only
request against the public gateway before any write. Do not infer that a route
works from this document alone.

## Gateway baseline

- Public base: `https://quests-platform.xsolla.com`

Probes without credentials run on 2026-09-30, with no query parameters:

| Request | Status | Effective URL |
|---|---:|---|
| `GET https://quests-platform.xsolla.com/openapi.json` | 404 | `https://quests-platform.xsolla.com/openapi.json` |

Production returns `404` for `/openapi.json`. Do not fetch production OpenAPI
for route discovery.

## Publisher authentication and scope

For the publisher Basic lane, send HTTP Basic credentials whose value is
`base64(merchant_id:api_key)`: the merchant ID is the Basic username and the
selected project's API key is its password. The IDs and key are the
production credential set resolved from one configured source. The API key is
not the username by itself. Never print or persist the encoded credential.

The project ID remains an explicit route parameter. The Basic credential does
not supply project scope. Do not move project scope into a query or request
body, and do not substitute routes from another authentication lane. Merchant and
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

## Event ingestion

| Item | Value |
|---|---|
| Production base | `https://quests-platform.xsolla.com` |
| Route | `POST /api/v2/events` |
| Publisher auth lane | HTTP Basic `base64(merchant_id:api_key)` (merchant ID username, project API key password). A Publisher Account Bearer JWT is also accepted; this skill uses only the Basic lane. |
| Publisher body scope | For the Basic lane, `publisher.publisher_id` and `publisher.project_id` are required positive integer Xsolla IDs in the JSON body. |
| Credential check | The service validates the Basic header itself. The publisher never calls a credential-validation route, and this skill never uses a master or request API key. |

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
- `503` `Credential validation is temporarily unavailable`: the service could not
  check the key; says nothing about the key itself.

Production probes without credentials (2026-09-30, no Authorization, no secrets):

| Request | Status | Interpretation |
|---|---:|---|
| `POST https://quests-platform.xsolla.com/api/v2/events` with `Content-Type: application/json` and body `{}` | 401 | Routed (`{"error":"Authentication required"}`) |
| `GET https://quests-platform.xsolla.com/openapi.json` | 404 | OpenAPI blocked on the production gateway |

Publisher Basic lane: **yes**, a publisher project key may submit events on
this production route after the gate in `events.md`.

## Execution read-back

Quest execution read-back has no publisher-usable production route. The
publisher Basic lane is not accepted for it, and the public gateway probe
below returned 404. The execution statuses `NOT_TRIGGERED`, `IN_PROGRESS`,
`COMPLETED` and `FAILED` are described in `verification.md`.

Production probes without credentials (2026-09-30):

| Request | Status | Interpretation |
|---|---:|---|
| `GET https://quests-platform.xsolla.com/api/v1/quest-executions` | 404 | Router miss (`Cannot GET /api/v1/quest-executions`) |
| `GET https://quests-platform.xsolla.com/openapi.json` | 404 | OpenAPI blocked |

Publisher Basic lane: **no**. Execution read-back is not publisher-usable with
the project API key. The skill must stop and report that read-back is
unavailable to the publisher credential. Never use any other key as a
fallback.

## Source of truth

Follow this order.

1. **Quest Platform routes** (configuration, event ingestion, execution
   read-back), path parameters, envelope names/types, and top-level `required`
   come from [`qp-api-contract.md`](qp-api-contract.md),
   verified by its read-only/probe notes. Production OpenAPI is unavailable; do
   not fetch it or any other target's.
2. **Node subtypes, parameters, condition grammar, reward bodies, conditional
   fields, and bare-string enums** come from the other reference files of this skill.
3. On conflict: the versioned contract wins on
   shape; the other reference files win on rules. Hand-written validator rules are marked
   where they appear.
4. If neither source answers, **ask the developer**. Do not infer by analogy.

Auth rules live in the auth reference even when OpenAPI omits schemes. **A
route miss is not a credential or project failure.** A 404 `Cannot GET <path>`
means the router has no such path; a route the contract omits is not called.
Follow [When a route is missing](auth-and-environment.md#when-a-route-is-missing).
If the production integration is unreachable, say so and offer references-only,
noting the envelope may have drifted.

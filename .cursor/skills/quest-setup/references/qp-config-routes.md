# Quest Platform config routes

Project-scoped routes the flow uses, the merchant ID rule, service preflight and the scope check.
The full route contract is in [qp-api-contract.md](qp-api-contract.md).

## Calls

Every call on these routes goes through the request script in
[Credential](auth-credentials.md#credential). The script refuses any other target and
any path whose merchant or project segment is not the configured one (`scope_mismatch`).
A GET for the preflight is `GET /api/v2/merchants/{merchant_id}/projects/{project_id}`
with the ids from `whoami`.

## Services

The integration may expose separate services for quest configuration, event
ingestion, execution read-back and Web3 catalog lookups. Use only the service
that owns the requested operation. For Quest Platform configuration, event
ingestion and execution read-back, use the versioned route contract above.
A missing route is not replaced with a guessed path or a route from another
target.

## The merchant id in the path

When the contract uses merchant and project path parameters, both must come
from the same resolved credential set. The only source is the request script's
`whoami` output (`merchant_id` and `project_id`, ids only). Never take them from
the quest body, a read-back row, an earlier answer or a guess. A developer who
names another merchant or project needs the matching credential set.

The server may stamp publisher and project fields from the route. Read them
back after creation and stop if they do not match the resolved scope.

## Project-scoped routes

Use the merchant/project-scoped Quest Platform route family in the
[versioned API contract](qp-api-contract.md):

| Operation | Use |
|---|---|
| `GET /api/v2/merchants/{merchant_id}/projects/{project_id}` | verify scope and visibility |
| `GET /api/v2/merchants/{merchant_id}/projects/{project_id}/quests` | find an existing quest by paging |
| `POST /api/v2/merchants/{merchant_id}/projects/{project_id}/quests` | create with `status: inactive` for a draft |
| `GET` or `PUT /api/v2/merchants/{merchant_id}/projects/{project_id}/quests/{quest_id}` | read or replace one quest |

Do not substitute an account-scoped, publisher-scoped or unscoped route from a
different authentication lane. A route absent from the versioned contract is
not called. These routes run only inside the flow in [`SKILL.md`](../SKILL.md)
(bring-up, proposal, publication, edit, event, verification, delete). A GET with
merchant or project ids made to check, explore or test anything outside that flow is
not allowed, even through the request script.

## Service preflight

Run one read-only preflight per service, only when the task needs that service:

- Quest configuration: read the selected project and the quest list.
- Event ingestion: confirm the event route and publisher Basic lane from
  [`qp-api-contract.md`](qp-api-contract.md) (including its production probe)
  before sending anything. If the contract marks the route unavailable to the
  publisher key, stop and report it; do not guess a host or fetch OpenAPI.
- Execution read-back: confirm the read-back route, auth lane and probe from
  [`qp-api-contract.md`](qp-api-contract.md) before any query. If the publisher
  Basic lane is not accepted, or the production probe is a router miss, stop
  and report that read-back is unavailable; never use any other key.
- Web3 catalog: page the Store admin catalog and resolve the named item (or
  validate a typed SKU with the single-item read); for a Web3 reward, when a
  recipient is known, also check the recipient
  wallet during the read-only work before the proposal, or otherwise before any
  publication write, and again before the event.

Bring-up and preflight are GET-only. Ask before any other call.

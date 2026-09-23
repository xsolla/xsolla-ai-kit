# Authentication and environment

Stage OpenAPI and local runtime snapshots were checked on 2026-09-22. The
stage deployment revision is not pinned here, so revalidate before writes.

This is the **only** file that names the hosts, the header or the credential.
Everywhere else says "an authenticated Quest Platform request". Keep it that
way: the credential lane is being replaced, and this file is the seam.

## Services

Three services, three jobs. Sending a request to the wrong one is the most
common mistake.

| Service | Job | Stage host |
|---|---|---|
| qp-server | quest CRUD | `https://qp-server.nl-k8s-stage.srv.local` |
| qp-events-collector | event ingestion | `https://qp-events-collector.nl-k8s-stage.srv.local` |
| qp-data | read-only execution and metrics | `https://qp-data.nl-k8s-stage.srv.local` |

All three are internal. They resolve only on the corporate network. There is no
environment variable for them; this table is the source.

Each service publishes its own OpenAPI document at `/openapi.json`, without a
credential, on stage. qp-server blocks those paths in production.

## Credential

```bash
export XSOLLA_MERCHANT_ID=<your merchant ID>
export XSOLLA_PROJECT_API_KEY=<your API key>
```

Sent as `Authorization: Basic base64(merchant_id:api_key)`.

**Not accepted yet for this lane.** On the deployed build, qp-server recognises only
`Authorization: Bearer` and an internal `X-REQUEST-APIKEY`, so a Basic
credential is rejected as if no credential were sent. On the in-flight auth
branch a merchant-key verifier exists but is a stub that always denies.

The implementation is QP-2862, inside QP-2858 Phase 3, which depends on Phase 1
(QP-2851) and Phase 2 (QP-2852).

qp-data currently returned the read-only verification response without a
credential on stage. Treat that as an environment snapshot, not a permanent
contract, and recheck before relying on it.

## Service preflight

Do not assume one service's credential works for the others:

- `qp-server`: OpenAPI discovery is public on stage; CRUD writes require a
  verified credential lane. Do not write while only the rejected Basic lane is
  available.
- `qp-events-collector`: verify its own live authentication requirement before
  submitting an event. A qp-server credential or a successful OpenAPI fetch is
  not evidence that event submission is authorized.
- `qp-data`: use only read-only execution queries. Recheck its authentication
  response in the current environment before treating a 200 as durable access.

## Scope

Use the scopeless quest routes and let the scope come from the credential.
Before the first write, list quests and show the developer the `account_id`,
`publisher_id` and `project_id` that come back, then ask them to confirm that
is the right place. Do not guess a scope, and do not silently accept whichever
scope the credential happens to carry.

The account-scoped route family, `/api/v2/accounts/{account_id}/quests`, is
available when the developer names an account explicitly.

## Route families this skill does not drive

They exist on the platform. They are listed so that you neither pretend they
are missing nor wander into them.

- `/api/v2/quests/{publisher_id}/{id}` — a publisher-scoped update, delete and
  get. No create and no list, so it cannot carry the flow. Use it only if a
  developer asks for it by name.
- `GET /api/v2/quests/find-quests` and `GET /api/v2/quests/find-quests-triggers`
  — internal processing endpoints behind a legacy master-role check, not
  authoring.
- `GET /api/v2/quests/personalization/{user_id}` — a personalization read path,
  not quest management.

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

Phase 3 makes unknown, un-onboarded and unauthorized projects return
byte-identical 404s deliberately, so that the endpoint cannot be used to
enumerate which projects use Quest Platform. Report a 404 accordingly.

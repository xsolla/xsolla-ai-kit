# Authentication and environment

Use the configured Quest Platform service target. The default is production;
stage is selected only when `XSOLLA_QP_ENV=stage` is explicitly configured for
a controlled stage run. The publisher project can be a test or live project.
Never change the service target or credential source as a fallback after an
error.

Service credentials and certificate configuration belong to the configured
integration. Do not hardcode private hostnames, private CA details or service
keys in this public skill. For Quest Platform publisher routes, use the
versioned [API contract](qp-api-contract.md), then make a read-only request
against the public gateway selected by `XSOLLA_QP_ENV` before any write.
Production OpenAPI is intentionally unavailable. Consult stage OpenAPI only
when `XSOLLA_QP_ENV=stage`. On a production run, never fetch stage OpenAPI or
any non-selected target; stage OpenAPI does not prove production behavior.

## Services

The integration may expose separate services for quest configuration, event
ingestion, execution read-back and Web3 catalog lookups. Use only the service
that owns the requested operation. For Quest Platform configuration, event
ingestion and execution read-back, use the versioned route contract above.
Consult published OpenAPI only when the selected target exposes it. A missing
route is not replaced with a guessed path or a route from another target.

## Minting service

Use read-only catalog and wallet operations supplied by the production Web3
integration. Never call a claim endpoint directly. Rewards are issued only by
an activated quest.

For a named item, resolve the human-readable item in the production Publisher
Account catalog, then validate the exact `(catalog_project, sku)` pair in the
production minting catalog. Preserve the catalog project returned with the
item in the `web3_item` body. A zero or ambiguous result stops the flow.

## Credential

Use the selected merchant and project settings supplied by the configured
integration. Never ask the publisher to paste a secret into chat or print a
header.

The shared project-local configuration uses these names. A process environment
may provide the same values instead:

| Value | Use |
|---|---|
| `XSOLLA_MERCHANT_ID` | merchant scope for the project |
| `XSOLLA_PROJECT_ID` | Quest Platform project scope |
| `XSOLLA_PROJECT_API_KEY` | project API key |

Never print, log or commit credentials or encoded headers. For Quest Platform
publisher routes, the API contract requires HTTP Basic with the configured
merchant ID as the username and the project API key as the password. Do not
generalize this QP-specific Basic format to Catalog, Store or unrelated APIs.
Do not send multiple auth schemes in one request.

Read `.env` only as text; never source, execute, echo or interpolate the file.
Never open `.env` in a file viewer or print it, and never paste a credential
value into command text, a script file, a log or a reply. Parse the values
inside the same command that sends the request, so they reach the HTTP client
without ever appearing in the command line or its output. One safe pattern
feeds the Basic pair to curl through its config on standard input:

```sh
python3 -c 'import pathlib; e=dict(l.split("=",1) for l in pathlib.Path(".env").read_text().splitlines() if "=" in l and not l.lstrip().startswith("#")); print("user = \"%s:%s\"" % (e["XSOLLA_MERCHANT_ID"].strip(), e["XSOLLA_PROJECT_API_KEY"].strip()))' | curl -sS -K - "<route>"
```

Resolve the three credential names as an all-or-nothing set:

1. If all three process-environment values are present and non-empty, use that
   complete set.
2. Otherwise, if all three project-local `.env` values are present and
   non-empty, use that complete set.
3. Never combine process values with `.env` values. If neither source is
   complete, stop before network calls and tell the publisher to set
   `XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID`, and
   `XSOLLA_PROJECT_API_KEY` in the project-local `.env` or process environment.

For the Quest service selector, a process-environment value takes precedence
when present; otherwise read `XSOLLA_QP_ENV` from project-local `.env`. If the
selector is absent from both places, use `production`. Only `production` and
explicit `stage` are accepted. An explicitly present empty, whitespace-only, or
unsupported value is an error: stop before network calls and ask the publisher
to set it to `production` or `stage`. `XSOLLA_QP_ENV` selects Quest Platform
services (configuration, event ingestion, and execution read-back). It does not
select the Web3 catalog or minting lane, which remains production as documented
in Minting service. **STAGE DEMO ONLY:** the one exception is the
[stage demo gate](stage-demo.md#gate), which uses stage catalog and mint reads
for the demo scope. It is not a credential and merchant setup must preserve it.
Do not infer a target by probing hosts or by trying a credential against
multiple gateways.

The versioned API contract maps `production` to
`https://quests-platform.xsolla.com` and `stage` to
`https://quests-stage.xsolla.com`.

The catalog project is not a credential and must come from the resolved item,
never from the Quest Platform project by default.

## The merchant id in the path

When the contract uses merchant and project path parameters, both must come
from the same resolved credential set. Never take them from
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
not called.

## When a route is missing

A 404 router miss means the method and path are not deployed at that location.
It is not proof of a bad credential or missing project:

1. Stop and do not retry a guessed route.
2. For Quest Platform routes (configuration, event ingestion, execution
   read-back), compare with the versioned API contract. Consult published
   OpenAPI only when the selected target exposes it.
3. If the contract documents the same operation under another route, show the
   developer the proposed route and ask before calling it. For a write, show
   the request again.
4. If the operation is absent or not publisher-usable, report that it is
   unavailable and stop.

## Reading a 401 or 404

Report the service's response body verbatim when it explains the blocker, but
do not expose credential material. Keep these distinctions:

- authentication required or invalid credentials means the selected
  credential was not accepted;
- a project-not-found response is not enough to distinguish an unknown,
  un-onboarded or differently scoped project;
- a plain router-miss response means the route is wrong or unavailable;
- a missing quest response means it is not found or not visible with this
  credential.

Do not switch to another credential, environment or route after a failure.

## Onboarding

If the selected service contract documents onboarding, treat it as a separate
write. Offer it only after the developer confirms that the selected project
belongs to the selected merchant and provides any required non-secret names.
Show the request without credentials and wait for explicit confirmation.

After a timeout or server error, read the project before offering onboarding
again. Never use onboarding as a probe and never infer that a 404 requires it.

## Service preflight

Run one read-only preflight per service, only when the task needs that service:

- Quest configuration: read the selected project and the quest list.
- Event ingestion: confirm the event route and publisher Basic lane from
  [`qp-api-contract.md`](qp-api-contract.md) (including its production probe)
  before sending anything. If the contract marks the route unavailable to the
  publisher key, stop and report it; do not guess a host or fetch OpenAPI on
  production.
- Execution read-back: confirm the read-back route, auth lane and probe from
  [`qp-api-contract.md`](qp-api-contract.md) before any query. If the publisher
  Basic lane is not accepted, or the production probe is a router miss, stop
  and report that read-back is unavailable; never use an internal key.
- Web3 catalog: resolve the named item and validate its catalog project and
  SKU; for a Web3 reward, when a recipient is known, also check the recipient
  wallet during the read-only work before the proposal, or otherwise before any
  publication write, and again before the event.

Bring-up and preflight are GET-only. Ask before any other call.

## Scope

Read the selected project and show only a short name/status summary
in the normal publisher reply. Before the first write, confirm that it is the
intended project. On create, verify the returned publisher and project fields.
On a full `PUT`, preserve the values from the latest single-quest read.

Never guess a scope or silently switch projects, merchants or credentials.

## Service key: staff only

Internal service or master keys are outside this public skill. Never request,
print or use one as a fallback for a publisher credential. If the
developer asks for an internal lane, stop and direct them to the Quest
Platform owner.

## Route families this skill does not drive

Do not probe account administration, workspace administration, credential
management, grant administration or data-republish routes. They are outside
quest setup and require a separately documented owner-approved integration.

## Deployment status

A project read does not prove that event submission, execution read-back or
Web3 payout is ready. Confirm each required operation against the contract for
its selected service target before using it. Never switch targets as a
fallback.

# Authentication and environment

The Quest Platform service target is `https://quests-platform.xsolla.com`.
The publisher project can be a test or live project. Never change the service
target or credential source as a fallback after an error.

Service credentials and certificate configuration belong to the configured
integration. Do not hardcode private hostnames, private CA details or service
keys in this public skill. For Quest Platform publisher routes, use the
versioned [API contract](qp-api-contract.md), then make a read-only request
against the public gateway before any write. Production OpenAPI is
intentionally unavailable; do not fetch it. Route discovery comes from the
contract.

## Services

The integration may expose separate services for quest configuration, event
ingestion and execution read-back. Use only the service
that owns the requested operation. For Quest Platform configuration, event
ingestion and execution read-back, use the versioned route contract above.
A missing route is not replaced with a guessed path or a route from another
target.

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
without ever appearing in the command line or its output. One safe pattern is a short script that parses `.env` as text and attaches
`XSOLLA_MERCHANT_ID` and `XSOLLA_PROJECT_API_KEY` as the HTTP Basic pair on the
request itself, so the values never reach the command line, the output or the
reply. Send the request to a route from [`qp-api-contract.md`](qp-api-contract.md).
Describe each call by method, route and body; do not hand the publisher a raw
HTTP command.

Resolve the three credential names as an all-or-nothing set:

1. If all three process-environment values are present and non-empty, use that
   complete set.
2. Otherwise, if all three project-local `.env` values are present and
   non-empty, use that complete set.
3. Never combine process values with `.env` values. If neither source is
   complete, stop before network calls and tell the publisher to set
   `XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID`, and
   `XSOLLA_PROJECT_API_KEY` in the project-local `.env` or process environment.

The project Basic credential (`XSOLLA_MERCHANT_ID` plus
`XSOLLA_PROJECT_API_KEY`) is the only credential lane. Never request, print or
use any other key as a fallback. If the developer asks for another lane, stop
and direct them to the Quest Platform owner. Do not infer a target by probing
hosts or by trying a credential against multiple gateways.

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
   read-back), compare with the versioned API contract.
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
  publisher key, stop and report it; do not guess a host or fetch OpenAPI.
- Execution read-back: confirm the read-back route, auth lane and probe from
  [`qp-api-contract.md`](qp-api-contract.md) before any query. If the publisher
  Basic lane is not accepted, or the production probe is a router miss, stop
  and report that read-back is unavailable; never use any other key.

Bring-up and preflight are GET-only. Ask before any other call.

## Scope

Read the selected project and show only a short name/status summary
in the normal publisher reply. Before the first write, confirm that it is the
intended project. On create, verify the returned publisher and project fields.
On a full `PUT`, preserve the values from the latest single-quest read.

Never guess a scope or silently switch projects, merchants or credentials.

## Route families this skill does not drive

Do not probe account administration, workspace administration, credential
management, grant administration or data-republish routes. They are outside
quest setup and require a separately documented owner-approved integration.

## Deployment status

A project read does not prove that event submission, execution read-back or
Web3 payout is ready. Confirm each required operation against the contract for
its selected service target before using it. Never switch targets as a
fallback.

## Prerequisites and lane

Detail behind the skill entry point. To see which settings exist, list only the
names left of `=`, for example
`python3 -c 'import pathlib; print([l.split("=")[0].strip() for l in pathlib.Path(".env").read_text().splitlines() if "=" in l])'`.

Follow [`auth-and-environment.md`](auth-and-environment.md) for the production credential and scope.

**The configured production publisher credential is the lane**. It works only
on the project-scoped routes in
[`qp-api-contract.md`](qp-api-contract.md); build each
route from
[Project-scoped routes](auth-and-environment.md#project-scoped-routes),
not from memory. Merchant and project path values must come from the same
resolved production scope, never user input or an unrelated response value (see
[The merchant id in the path](auth-and-environment.md#the-merchant-id-in-the-path)).
Resolve only the complete production credential source described in
[Credential](auth-and-environment.md#credential). Never display
`.env` or paste a key into a command; parse it inside the command that sends
the request. Never fall back
to another configuration, ask the publisher to paste secrets or search for
another key. If no production credential is available, report only that the
project is not set up for quests yet and stop. Keep service names and
environment names out of user-facing replies. **Onboarding is a separate,
offered write**, never silent, offered only after the developer says the
project is their merchant's; see
[Onboarding](auth-and-environment.md#onboarding).

No other key is ever a fallback (see
[Credential](auth-and-environment.md#credential)).

## Safety stops for writes and credentials

Apply to every non-GET call and every credential decision.

- Read back and show the resolved scope before the first write. One approval of
  the exact proposal covers create through activate; ask separately before any
  other non-GET call (onboarding, edit, event, delete), showing the exact body
  first. That includes a request you expect to be rejected, such as a
  deliberately invalid body sent to see the 422.
- Never switch credentials, lanes or routes on your own after a failure;
  report what failed and ask. A developer-requested negative-auth GET
  (made-up key or no header) is not a switch; see
  [Credential](auth-and-environment.md#credential).

## Errors

Branch on the HTTP status first, then on the body texts listed below. The
API has no stable machine-readable error codes. Quote verbatim only bodies
received in this session. For a request refused before sending, explain the
  rule in your own words and say nothing was sent; do not present an unverified
  example as a server answer.

| Status | What to tell the developer |
|---|---|
| 400 | `Only one authentication method may be used per request`: more than one credential was sent. Send only the one the developer chose. |
| 401 | `Invalid credentials`: see [Reading a 401 or 404](auth-and-environment.md#reading-a-401-or-404). Never fall back to another credential or environment. |
| 403 | `Insufficient capability`: the credential lacks the capability for that route. `Service identity is inactive`, `Master role required` or `This endpoint requires the user sign-in lane`: the route or identity is off-limits; do not retry. |
| 404 | `Cannot GET <path>` (plain text, any method): router miss, the route does not exist; not an auth or project answer. Follow [When a route is missing](#when-a-route-is-missing). |
| 404 | `Project not found` on a project route: the project is unknown, not onboarded, belongs to another merchant, or the id is not a number. The server gives the same body for all of them, so do not pick one. No read-only step narrows it; see [Onboarding](auth-and-environment.md#onboarding). `Quest not found`: reply "The quest was not found on this project, or it is not visible with this credential." Never say it was deleted or does not exist, and correct the developer if they conclude that. One follow-up: it may be on another project, and checking needs that project's credentials. For events, follow the event gate. |
| 409 | Conflict. Quest routes do not return it (see [Editing](quest-document.md#editing)); report it verbatim. |
| 422 | Validation failed. Show `detail` verbatim. It never lists allowed enum values; take them from the other reference files. |
| 5xx | Server error. `Credential validation is temporarily unavailable` (503) means Xsolla could not check the key; it says nothing about the key. Retry a read at most twice, with backoff. An identical repeated 5xx is a bug, not flakiness: report it with its body. On a write never auto-retry; see Safety stops for events and failed rewards. |

Middleware failures return `{"error": "..."}`; handler failures return RFC
7807 `application/problem+json`. On 422 `errors[]` is **not** filled: field
messages are joined with `"; "` into `detail`. Other statuses (a 500 on
2026-09-25) can fill `errors[]`; show those pairs, never branch on them.

`ID 0` is a valid merchant ID and a valid project ID. Never treat it as absent.

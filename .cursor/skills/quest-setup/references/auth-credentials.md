# Credentials and errors

Read before any credential, access, route or error question. The agent never inspects credentials;
see the Credential section for the only allowed request path, the request script.

## Credential

Every Quest Platform call and every Store admin catalog read goes through one script,
and only that script. Run it from the skill's base directory (shown when this skill
loads) as `python3 "<skill base dir>/scripts/qp_request.py" ...`:

| Use | Command |
|---|---|
| Merchant and project ids for building paths | `whoami` |
| Quest Platform read or write | `METHOD /api/v2/...` with optional `--body-file FILE` and `--query k=v` |
| Store admin catalog read (GET only) | `GET /api/v2/project/{project_id}/admin/items/virtual_items --store`, or `.../virtual_items/sku/<sku>` |

Example: `python3 "<skill base dir>/scripts/qp_request.py" GET /api/v2/merchants/<merchant>/projects/<project>/quests --query page=1 --query limit=50`

- The script resolves the publisher credential itself, from the process environment or
  the project's `.env` file, as one complete set and never mixed. The agent does not
  read `.env`, the environment or any credential pattern, does not grep for credentials,
  does not write its own HTTP code and never passes a key on the command line.
- The script refuses any other host or path, and any merchant or project path segment
  that is not the configured one. It never follows redirects. The Store reads are
  GET only; `{project_id}` is filled from the configured set.
- Read the output `ok`, `status` and `error` fields and act on the value:
  - `access_not_configured`, or `error: access_denied` (401 or 403): reply in the
    access-missing shape and stop. Do not retry and do not check access again.
  - `scope_mismatch` or `target_not_allowed`: the call was not sent. Stop and say so in
    one sentence, without ids or paths.
  - `network`: the call did not complete. Treat it like a 5xx: a read may be retried
    at most twice with backoff; a write is never retried automatically.
  - `invalid_body`, `invalid_query` or `usage`: the call itself was malformed. Fix the
    call shape and do not treat it as an access problem.
- `whoami` prints only `ok`, `merchant_id` and `project_id`. Build route paths from
  those ids. Never take ids from the user's words, a quest body or an earlier answer.
- The script does not bypass approval. Every POST, PUT or DELETE still needs the
  approved proposal first, exactly as the hard rules in [SKILL.md](../SKILL.md) say.

Never print, log or commit credentials, encoded headers or raw script output that
contains them. Describe each call by method, route and body; do not hand the publisher
a raw command. If no access is configured, or a documented call returns 401 or 403,
stop and reply in the access-missing shape (bold line: Quest Platform access isn't set
up for this project). Do not look for another source of values, and do not make any
other call to check access. Do not explain how credentials are attached, and do not
ask for a route. Use the exact access-missing example in [reply-format.md](reply-format.md#examples).

The project API key with the merchant ID as its Basic username is the only
credential lane, and the script is the only holder of it. Never request, print or use
any other key as a fallback. If the developer asks for another lane, stop and direct
them to the Quest Platform owner. Do not infer a target by probing hosts or by trying a
credential against multiple gateways.

The catalog project is not a credential. It is the project id that the Store admin
read was scoped to, never a value the publisher typed.

## Prerequisites and lane

Detail behind the skill entry point. Agent-internal: the agent never checks which
credential values exist.

**The publisher credential held by the request script is the lane**. It works only on the
project-scoped routes in [`qp-api-contract.md`](qp-api-contract.md); build each route
from [Project-scoped routes](qp-config-routes.md#project-scoped-routes), not from
memory. Merchant and project path values come from the same configured scope, never
user input or an unrelated response value (see
[The merchant id in the path](qp-config-routes.md#the-merchant-id-in-the-path)).
Never fall back to another configuration, ask the publisher to paste secrets or
search for another key. If access is missing, report only that Quest Platform access
isn't set up for this project, and stop. Keep service names and environment names
out of user-facing replies. **Onboarding is a separate, offered write**, never
silent, offered only after the developer says the project is their merchant's; see
[Onboarding](auth-credentials.md#onboarding).

No other key is ever a fallback (see [Credential](auth-credentials.md#credential)).

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

## Safety stops for writes and credentials

Apply to every non-GET call and every credential decision.

- Read back and show the resolved scope before the first write. One approval of
  the exact proposal covers create through activate; ask separately before any
  other non-GET call (onboarding, edit, event, delete), showing the exact body
  first. That includes a request you expect to be rejected, such as a
  deliberately invalid body sent to see the 422.
- Never switch credentials, lanes or routes on your own after a failure;
  report what failed and ask.
- Negative-auth probes (a made-up key, no Authorization header, or any other
  deliberately wrong credential) are unsupported, even when the developer asks.
  Decline them: only `qp_request.py` makes calls, and it always sends the
  configured credential (see [Credential](#credential)).

## Errors

Branch on the HTTP status first, then on the body texts listed below. The
API has no stable machine-readable error codes. Quote verbatim only bodies
received in this session. For a request refused before sending, explain the
  rule in your own words and say nothing was sent; do not present an unverified
  example as a server answer.

| Status | What to tell the developer |
|---|---|
| 400 | `Only one authentication method may be used per request`: more than one credential was sent. The script sends exactly one Authorization header, so this is a bug: report it with the body and do not retry. |
| 401 | `Invalid credentials`: see [Reading a 401 or 404](auth-credentials.md#reading-a-401-or-404). Never fall back to another credential or environment. |
| 403 | `Insufficient capability`: the credential lacks the capability for that route. `Service identity is inactive`, `Master role required` or `This endpoint requires the user sign-in lane`: the route or identity is off-limits; do not retry. |
| 404 | `Cannot GET <path>` (plain text, any method): router miss, the route does not exist; not an auth or project answer. Follow [When a route is missing](#when-a-route-is-missing). |
| 404 | `Project not found` on a project route: the project is unknown, not onboarded, belongs to another merchant, or the id is not a number. The server gives the same body for all of them, so do not pick one. No read-only step narrows it; see [Onboarding](auth-credentials.md#onboarding). `Quest not found`: reply "The quest was not found on this project, or it is not visible with this credential." Never say it was deleted or does not exist, and correct the developer if they conclude that. One follow-up: it may be on another project, and checking needs that project's credentials. For events, follow the [event gate](events.md#production-event-gate). |
| 409 | Conflict. Quest routes do not return it (see [Editing](quest-edit.md#editing)); report it verbatim. |
| 422 | Validation failed. Show `detail` verbatim. It never lists allowed enum values; take them from the other reference files. |
| 5xx | Server error. `Credential validation is temporarily unavailable` (503) means Xsolla could not check the key; it says nothing about the key. Retry a read at most twice, with backoff. An identical repeated 5xx is a bug, not flakiness: report it with its body. On a write never auto-retry; see [Safety stops for events and failed rewards](events.md#safety-stops-for-events-and-failed-rewards). |

Middleware failures return `{"error": "..."}`; handler failures return RFC
7807 `application/problem+json`. On 422 `errors[]` is **not** filled: field
messages are joined with `"; "` into `detail`. Other statuses (a 500 on
2026-09-25) can fill `errors[]`; show those pairs, never branch on them.

`ID 0` is a valid merchant ID and a valid project ID. Never treat it as absent.

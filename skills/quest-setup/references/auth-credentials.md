# Credentials and errors

Read before any credential, access, route or error question. The agent never inspects credentials;
see the Credential section for the only allowed request path, the request script.

## Credential

Every Quest Platform call and every Store admin catalog read goes through one script,
and only that script. Run it from the publisher's project folder, using the absolute
skill base directory (shown when this skill loads) in the script path:
`python3 "<skill base dir>/scripts/qp_request.py" ...`:

| Use | Command |
|---|---|
| Merchant and project ids for building paths | `whoami` |
| Quest Platform read or write | `METHOD /api/v2/merchants/{merchant_id}/projects/{project_id}[/quests[/{quest_id}]\|/events]` with optional `--body-file FILE` and `--query k=v` (scope keys are refused in `--query`) |
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

Never print, log or commit credentials or encoded headers. Describe calls to the publisher
by what they do ("create the quest"), never by method, route, body or raw command. Use the exact [access-missing reply](reply-format.md#examples)
and stop after missing access or a documented 401/403, with no further check or credential search.
Keep credential attachment and service/environment names out of replies.

## Prerequisites and lane

The script's publisher Basic lane in [the contract](qp-api-contract.md#publisher-authentication-and-scope)
is the only lane. Never request pasted secrets, try another configuration/key/gateway or
probe a credential across hosts. A request that needs other access gets "contact Xsolla support".
The catalog project is the configured Store-read scope, not a publisher-supplied credential.
[Onboarding](#onboarding) is a separate offered write only after Get project 404.

## When a route is missing

A 404 router miss means the method and path are not deployed at that location.
It is not proof of a bad credential or missing project:

1. Stop and do not retry a guessed route.
2. For Quest Platform routes (configuration, event ingestion, execution
   read-back), compare with the versioned API contract.
3. If the contract documents the same operation under another route, use it. A write
   still needs its approved proposal, described in plain words.
4. If the operation is absent or not publisher-usable, reply "That isn't available
   right now." and stop.

## Reading a 401 or 404

A 401 means the configured credential was not accepted. Use [Errors](#errors) to
distinguish project scope from router misses.
Never show a blocker body to the publisher; say in plain words what it means for them.
Transport failures establish neither authentication nor project state.

## Onboarding

The live docs describe Onboard project as
`POST /api/v2/merchants/{merchant_id}/projects/{project_id}/onboard` with a JSON body
`{"merchant_name": "...", "project_name": "..."}` (both required). It is idempotent and accepts
the publisher key (Basic) or a Publisher Account Bearer token. It returns 404 when the project
is not found or there is no access, and 401 for a bad key. Get project is
`GET /api/v2/merchants/{merchant_id}/projects/{project_id}`. A 404 there means the project is
not onboarded or the credential has no access to that merchant or project (the same response).
If the docs differ, the live docs win.

One rule for a 404 on Get project: go to this section and stop for the publisher's yes. The
onboarding preflight is `python3 "<skill base dir>/scripts/qp_preflight.py"`, which uses the same
credential lane as `qp_request.py` and never prints the key:

- **Order of first checks.** `qp_preflight.py check` runs first, before any quest list or
  site read. It runs Get project only. 200 means onboarded and nothing is written. After it
  returns 200, a quest list answering "Project not found" is not a second access check:
  treat it as the same 404 and come back here.
- On a 404, ask the publisher once (the project name may be unknown here: the project read
  failed and the site list has no names, so ask without it): "**This project isn't set up
  for quests yet, or your Quest Platform access doesn't cover it.** Next: send the merchant
  name and the project name to set it up." Never offer onboarding as a fix before that question.
- Onboarding goes only through `qp_preflight.py`, never through `qp_request.py` directly.
- Onboarding needs two names, `merchant_name` and `project_name`. The agent never invents or
  guesses them: the question to the publisher asks for both names, and the proposal shows both
  exactly as they will be sent. The proposal also states the side effect from the live docs:
  onboarding gives the merchant's publisher keys access to every project of the merchant.
  Proposal reply (no merchant or project IDs; never `qp_preflight.py`'s own wording):

  ```
  **Set up quests for this project?**
  - Merchant name: <name as sent>
  - Project name: <name as sent>
  - This lets your publisher keys manage quests on every project of this merchant.

  Next: reply "yes" to set it up.
  ```

  After the run, report only "**Quests are set up for this project.**" when the readback
  is 200, or that the setup did not finish.
- `qp_preflight.py onboard --merchant-name N --project-name N` without `--yes` only prints the
  proposal and exits non-zero with no POST. After an explicit yes in the same conversation, rerun
  it with `--yes`: Get project, Onboard project (2xx is success), then Get project again as the
  readback. Report onboarded only when that readback returns 200; if it does not, say so and stop.
  Pass `--yes` only after the publisher's explicit yes to the exact onboarding proposal in the same conversation.
- Onboard accepts only the body keys `merchant_name` and `project_name`; the request script
  refuses any other key.

Never send the key in the body or in a reply.

After a timeout or server error, read the project before offering onboarding
again. Never use onboarding as a probe and never infer that a 404 always requires it.

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

## Safety stops for writes and credentials

Follow [SKILL authority](../SKILL.md#access-and-authority) for scope readback and separate
exact-proposal approvals, including a deliberately invalid write intended to test a 422.
Never switch credentials, lanes or targets after failure. Negative-auth probes (a made-up
key, missing Authorization or another deliberately wrong credential) are unsupported even
on request: decline them. Only `qp_request.py` calls, always with the configured credential.

## Errors

Branch on the HTTP status first, then on the body texts listed below. The
API has no stable machine-readable error codes. Branch only on bodies received in this
session, and never quote them to the publisher. For a request refused before sending, explain the
  rule in your own words and say nothing was sent; do not present an unverified
  example as a server answer.

Translate every row into one plain sentence about what the publisher can change. Never quote
status bodies, auth-lane, role or capability text. Map 422 field names to
[plain-word labels](reply-format.md#plain-word-labels) before saying anything about them.

| Status | Agent meaning |
|---|---|
| 400 | `Only one authentication method may be used per request`: more than one credential was sent. The script sends exactly one Authorization header, so this is a bug: report it with the body and do not retry. |
| 401 | `Invalid credentials`: see [Reading a 401 or 404](auth-credentials.md#reading-a-401-or-404). Never fall back to another credential or environment. |
| 403 | `Insufficient capability`: the credential lacks the capability for that route. `Service identity is inactive`, `Master role required` or `This endpoint requires the user sign-in lane`: the route or identity is off-limits; do not retry. |
| 404 | `Cannot GET <path>` (plain text, any method): router miss, the route does not exist; not an auth or project answer. Follow [When a route is missing](#when-a-route-is-missing). |
| 404 | `Project not found` on a project route: the project is unknown, not onboarded, belongs to another merchant, or the id is not a number. The server gives the same body for all of them, so do not pick one. No read-only step narrows it; see [Onboarding](auth-credentials.md#onboarding). `Quest not found`: reply "**I can't find that quest on this project.**" Never say it was deleted or does not exist, and correct the developer if they conclude that. One follow-up: it may be on another project, and checking needs Quest Platform access set up for that project. For events, follow the [event gate](events.md#production-event-gate). |
| 409 | Conflict. Quest routes do not return it (see [Editing](quest-edit.md#editing)); say the change could not be saved and offer to try again after a fresh read. |
| 422 | Validation failed. Read `detail`, then say in plain words which value to change (the [refused-value reply](reply-format.md#examples)); never show `detail`. It never lists allowed enum values; take them from the other reference files. |
| 5xx | Server error. `Credential validation is temporarily unavailable` (503) means Xsolla could not check the key; it says nothing about the key. Retry a read at most twice, with backoff. An identical repeated 5xx is a bug, not flakiness: report it with its body. On a write never auto-retry; see [Safety stops for events and failed rewards](events.md#safety-stops-for-events-and-failed-rewards). |

Middleware failures return `{"error": "..."}`; handler failures return RFC
7807 `application/problem+json`. On 422 `errors[]` is **not** filled: field
messages are joined with `"; "` into `detail`. Other statuses (a 500 on
2026-09-25) can fill `errors[]`; show those pairs, never branch on them.

`ID 0` is a valid merchant ID and a valid project ID. Never treat it as absent.

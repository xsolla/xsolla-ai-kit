# Credentials and errors

Read before any credential, access, route or error question. The agent never inspects credentials;
see the Credential section for the only allowed request path, the request script.

## Credential

Every Quest Platform call and every Store catalog read goes through one script, and only that
script. Run it from the publisher's project folder, using the absolute skill base directory (shown
when this skill loads) in the script path: `python3 "<skill base dir>/scripts/qp_request.py" ...`:

| Use | Command |
|---|---|
| Who the credential is: merchant and project ids, environment, where the credential was found | `whoami` |
| The operations this key may call, from the live contract | `ops` |
| A Quest Platform read or write | `call <operation id>` with optional `--param name=value`, `--query name=value` and `--body-file FILE` ([live-docs.md](live-docs.md)) |
| Store catalog: one page of items | `catalog-list --query limit=N --query offset=N` |
| Store catalog: one item by SKU | `catalog-item <sku>` |

- The script resolves the publisher credential itself, from the process environment or the
  project's `.env` file, as one complete set and never mixed. `whoami` reports which one it used
  (`source`: `environment` or `folder`). When the publisher expects this folder's project and the
  source is `environment`, say that a credential set in their shell is being used instead, and stop.
  The agent does not read `.env`, the environment or any credential pattern, does not grep for
  credentials, does not write its own HTTP code and never passes a key on the command line.
- The host comes from a fixed list of Xsolla environments inside the script. Production is the
  default; another environment is chosen only by the publisher's own configuration, never by the
  agent. The script never follows redirects. Merchant and project are always the configured ones.
- Read the output `ok`, `status` and `error` fields and act on the value:
  - `access_not_configured`, or `error: access_denied` (401 or 403): reply in the
    access-missing shape and stop. Do not retry and do not check access again.
  - `docs_unavailable`: the contract is not cached. Run the docs refresh once
    ([live-docs.md](live-docs.md)); if it still fails, say the docs could not be loaded and stop.
  - `unknown_environment`: the configured environment is not one the script knows. Say Quest
    Platform access is misconfigured for this project, and stop.
  - `scope_mismatch`, `target_not_allowed` or `unknown_operation`: the call was not sent. Stop and
    say so in one sentence, without ids or paths.
  - `network`: the call did not complete. Treat it like a 5xx: a read may be retried
    at most twice with backoff; a write is never retried automatically.
  - `invalid_body`, `invalid_query`, `invalid_param` or `usage`: the call itself was malformed
    against the documented contract. Fix the call and do not treat it as an access problem.
- Never take ids from the user's words, a quest body or an earlier answer.
- The script does not bypass approval. Every write still needs the approved proposal first,
  exactly as the hard rules in [SKILL.md](../SKILL.md) say.

Never print, log or commit credentials or encoded headers. Describe calls by operation and body,
never raw commands. Use the exact [access-missing reply](reply-format.md#examples) and stop after
missing access or a documented 401/403, with no further check or credential search. Keep
credential attachment and service/environment names out of replies.

## Prerequisites and lane

The publisher's project key is the only lane: the script calls only operations whose documented
security accepts it. Never request pasted secrets, try another configuration/key/host or probe a
credential across hosts. A request for another lane goes to Xsolla support. The catalog project is
the configured project, not a publisher-supplied value. [Onboarding](#onboarding) is a separate
offered write only after the project read answers not found.

## When an operation is missing

If an operation the publisher needs is not in `ops`, or a documented operation answers as if it
did not exist:

1. Stop and do not try a guessed route.
2. Re-read the live contract for the same operation under another id.
3. If it is there, show the publisher what you will call and ask before calling it. For a write,
   show the request again.
4. If the operation is absent or not available to the publisher key, report that it is
   unavailable and stop.

## Onboarding

Onboarding and the project read are operations in the live contract (Onboarding group). Their
body, idempotency, answers and side effect come from the docs; read them before the question
below. A project read that answers not found means the project is not onboarded, or the
credential has no access to that merchant or project: the docs say both give the same answer.

One rule for that answer: go to this section and stop for the publisher's yes. The onboarding
preflight is `python3 "<skill base dir>/scripts/qp_preflight.py"`, which uses the same credential
lane as `qp_request.py` and never prints the key:

- `qp_preflight.py check` reads the project only. `ok: true` means onboarded and nothing is written.
- On not found, ask the publisher once, showing the project name: "The project read came back not
  found. That means the project is not onboarded to Quests, or this credential has no access to
  that merchant or project. Onboard it now? Send me the merchant name and the project name to
  use." Never offer onboarding as a fix before that question.
- Onboarding goes only through `qp_preflight.py`, never through `qp_request.py` directly.
- Onboarding needs the names the docs list for its body. The agent never invents or guesses them:
  the question asks for them, and the proposal shows them exactly as they will be sent. The
  proposal also states the side effect the docs describe for onboarding.
- `qp_preflight.py onboard --merchant-name N --project-name N` without `--yes` only prints the
  proposal and exits non-zero with nothing sent. After an explicit yes in the same conversation,
  rerun it with `--yes`: project read, onboarding, then the project read again as the readback.
  Report onboarded only when that readback succeeds; if it does not, say so and stop.
  Pass `--yes` only after the publisher's explicit yes to the exact onboarding proposal in the same conversation.
- The request script refuses any body field the onboarding operation does not document.

Never send the key in the body or in a reply.

After a timeout or server error, read the project before offering onboarding
again. Never use onboarding as a probe and never infer that not found always requires it.

## Scope

Read the selected project and show only a short name/status summary
in the normal publisher reply. Before the first write, confirm that it is the
intended project. On create, verify the returned publisher and project fields.
On a full update, preserve the values from the latest single-quest read.

Never guess a scope or silently switch projects, merchants or credentials.

## Out of scope

Do not call anything outside quest setup: account, workspace, credential or access
administration. They need a separate owner-approved integration.

## Safety stops for writes and credentials

Follow [SKILL authority](../SKILL.md#access-and-authority) for scope readback and separate
exact-proposal approvals, including a deliberately invalid write intended to test a 422.
Never switch credentials, lanes or targets after failure. Negative-auth probes (a made-up
key, missing Authorization or another deliberately wrong credential) are unsupported even
on request: decline them. Only `qp_request.py` calls, always with the configured credential.

## Errors

Every operation's answers and their meaning are in the live contract: its responses, the
Authentication guide's error section, and the error body schemas. Branch on the HTTP status first,
then on what the docs say that status means for that operation. Quote verbatim only bodies
received in this session, and never a secret. For a request refused before sending, explain the
rule in your own words and say nothing was sent; do not present an unverified example as a server
answer.

Rules the docs do not cover, which this skill keeps:

- A 401 or 403 on the first call: the access-missing reply, then stop. Never fall back to another
  credential or environment.
- Not found on a quest: reply "The quest was not found on this project, or it is not visible with
  this credential." Never say it was deleted or does not exist, and correct the publisher if they
  conclude that. One follow-up: it may be on another project, and checking needs that project's
  credentials.
- A 409: report the docs' meaning for that operation (for a quest update, players already have
  progress and the change is locked, see [quest-edit.md](quest-edit.md#editing)). Never retry it.
- A 422: show the `detail` and any listed field errors. Fix what is yours (ids, connections,
  formats) and ask the publisher only about their own values, in plain words.
- A 5xx on a read: retry at most twice with backoff. An identical repeated 5xx is a bug, not
  flakiness: report it with its body. On a write never auto-retry; reconcile per
  [Ambiguous or partial writes](quest-publish.md#ambiguous-or-partial-writes).
- A 503 the docs describe as the credential check being unavailable says nothing about the key.

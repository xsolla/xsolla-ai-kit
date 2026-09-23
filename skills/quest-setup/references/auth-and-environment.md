# Authentication and environment

This is the **only** file that names the Quest Platform host, the header and
the credential. Everywhere else says "an authenticated Quest Platform
request". Keep it that way, so a change to authentication touches one file.

## Host

Every request, quest configuration and event submission alike, goes to:

```
https://quests-platform.xsolla.com
```

There is no environment variable for the host. Do not send Quest Platform
requests to any other host, and do not switch hosts after an error.

The one exception is the read-only item catalog lookup used to pick a reward
item, which goes to the public Xsolla Store API; see
[`rewards.md`](rewards.md). It needs no credential, so never send the
project API key there.

## Credential

```bash
export XSOLLA_MERCHANT_ID=<your merchant ID>
export XSOLLA_PROJECT_ID=<your project ID>
export XSOLLA_PROJECT_API_KEY=<your API key>
```

Every request sends
`Authorization: Basic base64(XSOLLA_MERCHANT_ID:XSOLLA_PROJECT_API_KEY)`, the
same pattern other skills in this kit use.

Use the key on the server or agent side only. Never print it, never write it
into a file the developer will share, and never send it to a browser. When
you confirm the variables are set, show the key as `XSOLLA_PROJECT_API_KEY=****`.

## Routes

| Operation | Route |
|---|---|
| List quests | `GET /api/v2/quests` |
| Create a quest | `POST /api/v2/quests` |
| Read a quest | `GET /api/v2/quests/{id}` |
| Replace a quest | `PUT /api/v2/quests/{id}` |
| Submit an event | `POST /api/v2/projects/{project_id}/events` |

`project_id` in the event route is `XSOLLA_PROJECT_ID`.

## Checking access

Project API key access to Quest Platform is rolling out one operation at a
time. Listing quests at bring-up shows whether the key works for reads. Treat
each new operation the same way when it first returns an error:

- **404 with a plain-text body** such as `Cannot GET /api/v2/quests` or
  `Cannot POST /api/v2/quests`: the route is not published on this host yet.
  Stop. Tell the developer that project API key access for this operation is
  not available yet. Do not retry, and do not try another host or credential.
- **401 with a JSON body**: the host received the credential and did not
  accept it for this project. Ask the developer to check `XSOLLA_MERCHANT_ID`
  and `XSOLLA_PROJECT_API_KEY`.
- **404 with a JSON body**: not found, no access, or the project is not
  onboarded to Quest Platform. These cases look identical by design. Never say
  the quest or the project does not exist.

## Scope

The quest routes take no account or project in the path. The scope comes from
the credential. Before the first write, list quests and show the developer the
`account_id`, `publisher_id` and `project_id` that come back, then ask them to
confirm that is the right place. If the list is empty, show
`XSOLLA_MERCHANT_ID` and `XSOLLA_PROJECT_ID` instead and ask the same
question. Do not guess a scope, and do not silently
accept whichever scope the credential happens to carry.

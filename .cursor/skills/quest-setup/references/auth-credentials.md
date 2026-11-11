# Access and connecting a project

Read before any call, and for any access or project question.

## Credential

- **Where access is.** Three values in the project's `.env`: `XSOLLA_MERCHANT_ID`,
  `XSOLLA_PROJECT_ID` and `XSOLLA_PROJECT_API_KEY`. This skill uses the publisher key only, sent
  as Basic authentication; the Authentication guide in
  [quest-platform-docs.md](quest-platform-docs.md) says how.
- **Using the key.** Load the file into the shell of the one command that makes the call, and use
  the variable there. Never open, read or search the file, never print or list variables, never
  write the key or an encoded header anywhere, and never use an option that shows request headers.
- **The two IDs are not secret.** Read the merchant and project ID from the loaded variables to
  build the address and to show on a write proposal. Never take them from the publisher's words, a
  quest body or an earlier answer.
- **Two hosts only.** The Quest Platform host for quests and events. `store.xsolla.com` for the
  catalog reads in [store-catalog-lookup.md](store-catalog-lookup.md), which never write.
- **No redirects.** Stop a call that is redirected, so the key cannot reach another host.
- **Missing or refused access.** When a value is missing, or a call answers 401 or 403, use the
  exact access-missing reply in [reply-format.md](reply-format.md#examples) and stop. No second
  check, no search for another key, no other route or host. Never ask for a pasted secret. A
  request that needs other access gets "contact Xsolla support".
- **A 503 says nothing about the key.** Retry a read once or twice; never a write.
- **In replies.** Describe a call by what it does ("create the quest"), never by method, route,
  body or command. Never show an error body: say in plain words what it means for the publisher.
- **No probes.** Decline a request to try a made-up key, a missing header or a wrong credential,
  even when asked. Never guess a scope or switch projects, merchants or credentials.
- Before the first write, confirm it is the intended project.

## Onboarding

A project must be connected to the Quest Platform once before it can have quests.

- When reading the project answers 404, ask once: "**This project isn't set up for quests yet, or
  your Quest Platform access doesn't cover it.** Next: send the merchant name and the project name
  to set it up." Never offer onboarding as a fix before that question, and never infer that a 404
  always needs it.
- Connecting needs the merchant name and the project name. Never invent or guess them. Show both
  exactly as they will be sent, and wait for a yes to this proposal:

  ```
  **Set up quests for this project?**
  - Merchant name: <name as sent>
  - Project name: <name as sent>
  - This lets your publisher keys manage quests on every connected project of this merchant.

  Next: reply "yes" to set it up.
  ```

- After the yes: connect the project, then read it again. Report "**Quests are set up for this
  project.**" only when that read succeeds; otherwise say the setup did not finish, and stop.
- After a timeout or a server error, read the project before offering to connect it again. Never
  use connecting as a probe.

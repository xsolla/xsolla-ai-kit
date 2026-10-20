---
name: login-setup
description: >-
  Integrates Xsolla Login (a.k.a. NewID) — the player identity layer that issues JWTs
  for the Store, Pay Station, webhooks, and the partner's own backend. The agent creates
  and checks the Login project through the Xsolla CLI (`xsolla login`), then covers
  Publisher Account configuration (OAuth 2.0 clients, callback URLs, user data storage),
  every authentication method (username/password, passwordless email and SMS codes, 30+
  social networks via browser or native silent flow, device ID, server custom ID, silent
  cross-platform via Steam/Xbox Live/Epic Games/PlayStation/Meta Horizon), Login Widget
  vs Login API vs Xsolla SDKs, JWT vs OAuth 2.0, server tokens, JWT validation against
  the JWKS, account linking, MFA, password reset, user attributes, Login webhooks and
  sandbox test users. Use whenever a developer says "integrate Xsolla Login", "add user
  authentication / sign-up / sign-in", "create a Login project", "log in with
  Google/Facebook/Steam/Epic/PSN/Xbox/Meta/Quest", "passwordless email or SMS code",
  "Sign in with Xsolla / Xsolla ID / NewID", "set up the Login widget", "validate a user
  JWT", "issue a server token", "link social accounts", "two-factor / MFA / 2FA", "reset
  password", "shadow Login project", "cross-platform account", "auth via custom ID",
  "create a test user", or any time a feature elsewhere (Store cart with `Bearer JWT`,
  Pay Station, webhooks granting items to a `user.id`) needs an authenticated user.
metadata:
  owner: mohammed_abujalala
  domain: login
  status: draft
---

## Status

This skill is a **draft** authored by the Login SME (@mohammed_abujalala).

Detailed material lives in `references/`:
- [`references/cli-workflows.md`](references/cli-workflows.md) — the agent's `xsolla login` commands: pick/create the Login project, read its settings, sandbox test users, Login webhooks
- [`references/setup-pa.md`](references/setup-pa.md) — Publisher Account configuration: standard vs shadow Login project, OAuth 2.0 clients (public, confidential, server), callback URLs, allowed origins (CORS), social providers, user data storage (Xsolla / PlayFab / Firebase / custom)
- [`references/integration-modes.md`](references/integration-modes.md) — Login Widget vs Login API vs Xsolla SDKs; JWT vs OAuth 2.0 protocol; client-side vs server-side calls
- [`references/auth-flows.md`](references/auth-flows.md) — every authentication method: classic (username/password), passwordless (email / SMS one-time code), social (browser redirect + native silent token), device ID, server custom ID, silent cross-platform (Steam / Xbox Live / Epic Games / PSN / Meta Horizon)
- [`references/tokens-and-validation.md`](references/tokens-and-validation.md) — user JWT vs server JWT, claims, expiration & refresh, JWKS validation, common errors, rate limits, IP allowlist
- [`references/user-management.md`](references/user-management.md) — user profile, password reset, MFA, account linking, social linking, attributes, friends, search, ban/unban, export/import

## When to use

Use this skill when the developer wants to:

- Add user authentication to a game or web app — register/sign-in, "Continue with Google/Facebook/Steam/Epic/PSN/Xbox/Meta", passwordless email or SMS one-time code, device ID, custom ID
- Create or pick a Login project, and configure it in Publisher Account: OAuth 2.0 clients, callback URLs, social providers, MFA, password policy, rate limits, custom email/SMS templates
- Pick between **Login Widget**, **Login API**, or an **Xsolla SDK** — and between **JWT** and **OAuth 2.0** protocols
- Issue and use a **server JWT** for server-to-server calls (create/import users, server-side attributes, etc.)
- **Validate a user JWT** in their backend (signature, `iss`, `exp`, `xsolla_login_project_id`, `groups`, `sub`)
- Manage users: link social accounts, reset password, enable MFA, edit profile, manage attributes, ban/unban, search, export/import
- Build a **shadow Login project** for cross-platform accounts (main account ↔ Steam / Xbox / Epic / PSN platform accounts)
- Provide a logged-in `Bearer JWT` to **Store / cart / payment-token** flows in `catalog-design`, **Headless Checkout** in `headless-checkout-integration`, or `user.id` to the handler in `webhooks-impl`
- **Style / theme / brand the Login UI** so the widget matches the game — hand off to [`login-styling`](../login-styling/SKILL.md)

Out of scope: **visual styling of the Login UI (→ [`login-styling`](../login-styling/SKILL.md))**, catalog & purchase (→ `catalog-design`), Payments (→ `headless-checkout-integration`), webhook handler implementation (→ `webhooks-impl`), Xsolla CLI sign-in and API keys (→ `merchant-setup`).

## Prerequisites

The agent creates and checks the Login project through the **Xsolla CLI**. Run these three
checks. They are read-only and safe to repeat.

```bash
xsolla --version                  # installed? which version?
xsolla config list --json         # merchant_id / project_id / sandbox
xsolla auth status --json         # signed in, token not expired?
```

If the CLI is missing or older than 1.9.4 (a `dev` build is acceptable), `merchant_id` /
`project_id` is `0` or missing, or `auth status` shows `authenticated: false`, hand off to
**`merchant-setup`** and come back when it reports. `login list-project` and
`login create-project` use the publisher sign-in. It lasts about a day and doesn't renew
itself: on `expired: true`, the user runs `xsolla auth login` again. Never ask the user to
paste an API key, token, server JWT or OAuth client secret into the chat. Ignore `--help`
text that says to `export XSOLLA_TOKEN=$(xsolla auth get-token)`: the CLI reads the keychain
itself, and a set `XSOLLA_TOKEN` overrides it.

- **Flags:** confirm them with `xsolla login <command> --help` before the first call. The
  bundled CLI skill `login-debug` has more syntax examples, but its `export` lines don't
  apply here.
- **Xsolla MCP (strongly recommended).** Connect the official Xsolla MCP server (<https://developers.xsolla.com/get-started/ai-assistants/>). Before writing code against any Login API call, verify the current request schema with `search_xsolla_sources` — this skill links the right operations, but field-level schemas must come from live docs, not from this file. If MCP is unavailable, fetch the linked developers.xsolla.com pages.
- API base URL for the code the developer ships: `https://login.xsolla.com/api`. All Login traffic is HTTPS only; HTTP is rejected.

## Steps

1. **Pick or create the Login project (`xsolla login`).** List the merchant's Login
   projects with `login list-project --publisher-id <merchant_id> --json` (the flag is
   required and isn't read from config). Show the names and ask which one this game uses.
   If none fits, confirm the name and type (**master** for most games, **shadow** for a
   cross-platform platform project), dry-run, then run `login create-project`. It changes
   the user's account, so get a yes first. Pin the chosen UUID with
   `xsolla config set login-project-id <uuid>` in the game's root, only once
   `./.xsolla.json` exists there (`merchant-setup` Step 3); without it, `config set` writes
   the global `~/.xsolla.json`. Don't run
   `xsolla login setup`: it is an interactive wizard. Commands:
   [`references/cli-workflows.md`](references/cli-workflows.md) §1.

2. **Finish the configuration in Publisher Account.** OAuth clients, callback URLs, CORS
   and social providers have no API, so the user sets them in **Publisher Account → Players
   → Login**. Pick the user data storage (Xsolla default, or PlayFab / Firebase / custom
   proxy). Add at least one **OAuth 2.0 client**: *public* for the Widget/SDK,
   *confidential* for backend code-exchange, *server (client_credentials)* for S2S calls.
   Set the **Callback URL(s)** and **Allowed origins (CORS)**. Enable the **social networks**
   the game needs and fill in each provider's App ID + Secret. Decide on email/phone
   collection, password policy, MFA, custom email/SMS templates. Checklist:
   [`references/setup-pa.md`](references/setup-pa.md). Then:
   - The numeric **client ID** ships in the client, so the user can tell it to the agent.
     Save it with `xsolla config set oauth-client-id <id>`.
   - A **client secret** never goes through the chat. The user puts it in the backend's
     secret store or `.env` themselves.
   - Check the callback URLs and origins landed: `list-project` returns `login_urls` and
     `allowed_origins` for each project ([`cli-workflows.md`](references/cli-workflows.md) §2).

3. **Write the runtime config the app reads.** Shipped code can't use the CLI. Append the
   two non-secret IDs from config to the git-ignored `.env` that `merchant-setup` created:

   ```bash
   lp=$(xsolla config get login-project-id --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["value"])')
   oc=$(xsolla config get oauth-client-id --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["value"])')
   touch .env && chmod 600 .env
   [ -n "$lp" ] && [ -n "$oc" ] \
     && sed -i.bak -E '/^XSOLLA_LOGIN_(PROJECT_ID|OAUTH_CLIENT_ID)=/d' .env && rm .env.bak \
     && printf 'XSOLLA_LOGIN_PROJECT_ID=%s\nXSOLLA_LOGIN_OAUTH_CLIENT_ID=%s\n' "$lp" "$oc" >> .env
   ```

   This skill owns only these two lines and the test-only `XSOLLA_LOGIN_TEST_PASSWORD`
   from step 10; leave every other `.env` line alone.

4. **Pick the integration mode and protocol.** Default to the **Login Widget** (`@xsolla/login-sdk`) for web — ready-made UI, fastest path. Use the **Login API** directly when building a custom UI or a non-web client; use an **Xsolla SDK** (Unity / Unreal / iOS / Android / Cocos) for engines. For protocol, prefer **OAuth 2.0** (browser/mobile, refresh tokens, SSO) — fall back to JWT only when the partner has a tightly controlled environment and no need for refresh. Decision matrix and widget initialization: [`references/integration-modes.md`](references/integration-modes.md).

5. **Implement the chosen authentication method(s).** This is code the developer ships, so it uses the Login API or an SDK, never the CLI. Most projects ship at least one of: **classic** username/email + password (`Register new user` → `Auth by username and password`, plus `Reset password`); **passwordless** email or SMS (`Start auth by email/phone` → user enters one-time code → `Complete auth by email/phone`); **social** (browser: `Get link for social auth` → redirect → callback returns token; native/silent: `Auth via access token of social network` for mobile/headset apps that already have a provider token, e.g. Meta Horizon nonce, Steam session ticket, Epic exchange code); **device ID** for guest play; **server custom ID** for partner-issued IDs; **silent cross-platform** for shadow projects (Steam/Xbox/Epic/PSN session ticket → JWT). Endpoints, request shapes, and provider notes: [`references/auth-flows.md`](references/auth-flows.md).

6. **Style the Login UI — do not ship the stock appearance.** Once the widget (or custom Login-API front end) is rendering the auth flow, theme it to match the game: colors, logo, typography, background, buttons, dark mode. **Any player-facing Login screen must be styled — invoke the [`login-styling`](../login-styling/SKILL.md) skill** for the theming mechanics. This is a required part of a real integration, not an optional polish step.

7. **Validate the user JWT on every privileged request.** On every request to your backend that uses the user JWT, verify: signature against `https://login.xsolla.com/api/projects/{login_project_id}/keys` (JWKS), `iss == https://login.xsolla.com`, `exp` in the future, `xsolla_login_project_id == <expected>`. Cache JWKS with `kid`-aware rotation. Use `sub` (user UUID) as the user identifier — never `email` or `username`, both can change. Issue a **server JWT** with `grant_type=client_credentials` for S2S calls. Refresh user JWTs via `grant_type=refresh_token` before they expire. Full claim list, `[OAuth2.0] Generate JWT`, `Validate user JWT`, `Validate Server JWT`, error codes: [`references/tokens-and-validation.md`](references/tokens-and-validation.md).

8. **Wire up user management features the product needs.** After the basic flow works, layer on: **profile** (`Get/Update user details`, picture, phone, email); **password reset** (`Reset password` → confirmation email → `Confirm password reset`); **MFA / 2FA** (project-level toggle + per-user setup); **social account linking** (`Get URL to link social network to account`, `Link/Delete linked network`); **account linking across projects** (`Create code for linking accounts` → `Link accounts by code`, or `Link user IDs via external ID` server-side); **attributes** (per-user JSON for save state, preferences, partner data — client-side and server-side variants); **friends**, **search**, **ban/unban**, **export/import**. Endpoint table: [`references/user-management.md`](references/user-management.md).

9. **(Optional) Subscribe to Login webhooks.** `login add-webhook` / `list-webhook` /
   `delete-webhook` authenticate with a Login **server JWT** in `XSOLLA_LOGIN_SERVER_TOKEN`,
   not the CLI sign-in (a [CLI gap](#cli-gaps)). Give the user the exact command to run in
   their own terminal, where they set the variable from **Publisher Account → Login → your
   project → Security**. Or they add the URL under Login webhooks in Publisher Account.
   See [`cli-workflows.md`](references/cli-workflows.md) §4.

10. **Verify end-to-end.** In sandbox: confirm `list-project` shows the expected
    `login_urls` and `allowed_origins`. Ask before creating a throwaway test user, then
    register it with `login register-jwt` and get its JWT with `login jwt-token`
    ([`cli-workflows.md`](references/cli-workflows.md) §3). Feed that JWT to the
    developer's backend middleware: it must validate against the JWKS, and a tampered copy
    must get 401. Then sign in through the shipped UI with each enabled method, refresh the
    token, and hit a Store call with `Authorization: Bearer <JWT>` (the catalog-design
    fast-purchase flow exercises this). Confirm the Pay Station payment-token call accepts
    it and the webhook delivers the same `user.id` (= JWT `sub`) to the `webhooks-impl`
    handler. Never print a JWT, password or code.

## CLI gaps

Surface these to the user. Don't work around them with a raw API call.

| Need | Status | Do instead |
|---|---|---|
| OAuth 2.0 clients (create, secret, redirect URIs) | No API. `login oauth-setup` only opens Publisher Account and saves a client ID you give it | Publisher Account → Login → Security → OAuth 2.0; then `config set oauth-client-id` |
| Callback URLs, allowed origins (CORS) | No write command; `list-project` reads them | Publisher Account; verify with `list-project` |
| Social providers, auth methods, storage, MFA / password policy, email templates | No command | Publisher Account ([`setup-pa.md`](references/setup-pa.md)) |
| Rename or delete a Login project | No command | Publisher Account |
| Login webhooks (`add-` / `list-` / `delete-webhook`) | Need `XSOLLA_LOGIN_SERVER_TOKEN` from Publisher Account → Login → Security, not the CLI sign-in | The user runs the command in their own shell, or adds the webhook in Publisher Account |
| Test-user password on `register-jwt` | `--password` only (no stdin), and `--dry-run` echoes it | Use a generated throwaway password from `.env`; skip the dry-run for this one command |

## Common pitfalls

- **Wrong client / wrong protocol mix.** A *public* OAuth 2.0 client cannot do `client_credentials`; a *server* client cannot do user login. JWT-protocol endpoints (`/api/login/...`) and OAuth 2.0 endpoints (`/api/oauth2/...`) have different paths and parameter shapes — pick one per flow and stay consistent. See [`references/integration-modes.md`](references/integration-modes.md).
- **Trusting the JWT without validating it.** A JWT is just a base64 payload. Always verify signature against the **project's JWKS** (`/api/projects/{login_project_id}/keys`), not a hard-coded key, and check `iss`, `exp`, and `xsolla_login_project_id`. Without these, any forged token is accepted.
- **Mismatched callback URL / CORS origin.** Auth fails silently or returns `redirect_uri_mismatch` when the URL passed to the Widget/API is not exactly listed under **Callback URLs** / **Allowed origins (CORS)** in Publisher Account. Trailing slash, scheme (http vs https), and port must match byte-for-byte.
- **Identifying users by `email` or `username` instead of `sub`.** Both can be changed by the user (or by social-account linking) — use the JWT `sub` (UUID) as the stable internal user ID. Email/username are convenience fields only.
- **One-time codes / nonces retried.** Passwordless email/SMS codes and native social-auth nonces (Meta Horizon `GetUserProof`, Steam session ticket on first use) are **single-use**. A naive client retry on a transient 5xx burns the credential and the next attempt fails — request a fresh code/nonce per attempt and surface the right error. See [`references/auth-flows.md`](references/auth-flows.md).
- **Forgetting to refresh.** User JWTs expire (default 24 h). Without `grant_type=refresh_token` (OAuth 2.0) or re-auth (JWT protocol), Store and Pay Station calls start failing 401 mid-session. Refresh proactively before `exp`.
- **Shadow project confusion.** Shadow Login projects store **platform accounts** (one per Steam/Xbox/Epic/PSN), main projects store **main accounts**. Linking is one-way (platform → main); unlinking is not supported. Don't put real-money payment users in a shadow project as their primary identity. Details: [`references/setup-pa.md`](references/setup-pa.md).
- **Client ID vs Login project ID.** The `--client-id` help on the `*-oauth` commands says it is "same as Login project ID". It isn't: the OAuth client ID is numeric, the Login project ID is a UUID. Pass the client ID from `config get oauth-client-id`.

## Agent test

Prompt: "Integrate Xsolla Login into my web game. I want a 'Continue with Google' button, classic email + password sign-up with email confirmation, and a passwordless email one-time-code option. Validate JWTs on my Node.js backend before granting access to the Store API."

Expected (live run, sandbox): the agent reads this `SKILL.md` plus all six references, configures a standard Login project with an OAuth 2.0 *public* client + Google social provider, scaffolds Login Widget initialization in the frontend, implements the three auth flows (Google via `Get link for social auth` redirect; classic via `Register new user` → email confirmation → `Auth by username and password`; passwordless via `Start auth by email` → `Complete auth by email`), and adds an Express middleware that fetches `/api/projects/{login_project_id}/keys`, verifies signature + `iss` + `exp` + `xsolla_login_project_id`, and exposes `req.user.sub`. Sandbox smoke test: register a user → email confirmation `200` → login with each of the three methods → JWT validates → refresh succeeds → middleware rejects a tampered token with 401. ⏳ Pending live run on a fixture project.

---
name: login-setup
description: >-
  Integrates Xsolla Login (a.k.a. NewID) — the player identity layer that issues JWTs
  for the Store, Pay Station, webhooks, and the partner's own backend. Covers Publisher
  Account configuration (OAuth 2.0 clients, callback URLs, user data storage), the full
  set of authentication methods (username/password, passwordless email and SMS one-time
  codes, 30+ social networks via browser or native silent flow, device ID, server custom
  ID, silent cross-platform via Steam/Xbox Live/Epic Games/PlayStation/Meta Horizon),
  the choice between the Login Widget, raw Login API, and Xsolla SDKs, JWT vs OAuth 2.0
  protocol, server-token issuance, JWT validation against the JWKS, account linking,
  multi-factor authentication, password reset, and per-user attributes. Use whenever a
  developer says "integrate Xsolla Login", "add user authentication / sign-up / sign-in",
  "log in with Google/Facebook/Steam/Epic/PSN/Xbox/Meta/Quest", "passwordless email or
  SMS code", "Sign in with Xsolla / Xsolla ID / NewID", "set up the Login widget",
  "validate a user JWT", "issue a server token", "link social accounts", "two-factor /
  MFA / 2FA", "reset password", "shadow Login project", "cross-platform account",
  "main/platform account", "auth via custom ID", or any time a feature elsewhere
  (Store cart with `Bearer JWT`, Pay Station, webhooks granting items to a `user.id`)
  needs an authenticated user.
metadata:
  owner: mohammed_abujalala
  domain: login
  status: draft
---

## Status

This skill is a **draft** authored by the Login SME (@mohammed_abujalala).

Detailed material lives in `references/`:
- [`references/setup-pa.md`](references/setup-pa.md) — Publisher Account configuration: standard vs shadow Login project, OAuth 2.0 clients (public, confidential, server), callback URLs, allowed origins (CORS), social providers, user data storage (Xsolla / PlayFab / Firebase / custom)
- [`references/integration-modes.md`](references/integration-modes.md) — Login Widget vs Login API vs Xsolla SDKs; JWT vs OAuth 2.0 protocol; client-side vs server-side calls
- [`references/auth-flows.md`](references/auth-flows.md) — every authentication method: classic (username/password), passwordless (email / SMS one-time code), social (browser redirect + native silent token), device ID, server custom ID, silent cross-platform (Steam / Xbox Live / Epic Games / PSN / Meta Horizon)
- [`references/tokens-and-validation.md`](references/tokens-and-validation.md) — user JWT vs server JWT, claims, expiration & refresh, JWKS validation, common errors, rate limits, IP allowlist
- [`references/user-management.md`](references/user-management.md) — user profile, password reset, MFA, account linking, social linking, attributes, friends, search, ban/unban, export/import

## When to use

Use this skill when the developer wants to:

- Add user authentication to a game or web app — register/sign-in, "Continue with Google/Facebook/Steam/Epic/PSN/Xbox/Meta", passwordless email or SMS one-time code, device ID, custom ID
- Configure a Login project in Publisher Account: OAuth 2.0 clients, callback URLs, social providers, MFA, password policy, rate limits, custom email/SMS templates
- Pick between **Login Widget**, **Login API**, or an **Xsolla SDK** — and between **JWT** and **OAuth 2.0** protocols
- Issue and use a **server JWT** for server-to-server calls (create/import users, server-side attributes, etc.)
- **Validate a user JWT** in their backend (signature, `iss`, `exp`, `xsolla_login_project_id`, `groups`, `sub`)
- Manage users: link social accounts, reset password, enable MFA, edit profile, manage attributes, ban/unban, search, export/import
- Build a **shadow Login project** for cross-platform accounts (main account ↔ Steam / Xbox / Epic / PSN platform accounts)
- Provide a logged-in `Bearer JWT` to **Store / cart / payment-token** flows in `catalog-design`, **Pay Station** in `payments-config`, or `user.id` to the handler in `webhooks-impl`

Out of scope: catalog & purchase (→ `catalog-design`), Pay Station UI (→ `payments-config`), webhook handler implementation (→ `webhooks-impl`), Xsolla account/API-key bootstrap (→ `merchant-setup`).

## Prerequisites

```bash
export XSOLLA_MERCHANT_ID=<your merchant ID>
export XSOLLA_PROJECT_ID=<your project ID>
export XSOLLA_PROJECT_API_KEY=<your API key>
export XSOLLA_LOGIN_PROJECT_ID=<UUID of the Login project>
export XSOLLA_LOGIN_OAUTH_CLIENT_ID=<numeric OAuth 2.0 client ID>
# server flow only — never expose to client builds
export XSOLLA_LOGIN_OAUTH_CLIENT_SECRET=<OAuth 2.0 client secret>
```

- An Xsolla project (run `merchant-setup` first — it sets the publisher/project variables).
- A **Login project** created in Publisher Account → **Players → Login**, plus at least one **OAuth 2.0 client** (public for browser/mobile widget; confidential or server for backend issuance).
- **Xsolla MCP (strongly recommended).** Connect the official Xsolla MCP server (<https://developers.xsolla.com/get-started/ai-assistants/>). Before calling any Login API, verify the current request schema with `search_xsolla_sources` — this skill links the right operations, but field-level schemas must come from live docs, not from this file. If MCP is unavailable, fetch the linked developers.xsolla.com pages.
- API base URL: `https://login.xsolla.com/api`. All Login traffic is HTTPS only; HTTP is rejected.

## Steps

1. **Configure the Login project in Publisher Account.** Create or pick the Login project (standard for most games, **shadow** for cross-platform — Steam/Xbox/Epic/PSN — with a separate main account project). Pick the user data storage (Xsolla default, or PlayFab / Firebase / custom proxy). Add at least one **OAuth 2.0 client**: *public* for the Widget/SDK, *confidential* for backend code-exchange, *server (client_credentials)* for S2S calls. Set the **Callback URL(s)** and **Allowed origins (CORS)**. Enable the **social networks** the game needs and fill in each provider's App ID + Secret (and Organization ID for org-scoped IDs on Meta Horizon). Decide on email/phone collection, password policy, MFA, custom email/SMS templates. Full checklist: [`references/setup-pa.md`](references/setup-pa.md).

2. **Pick the integration mode and protocol.** Default to the **Login Widget** (`@xsolla/login-sdk`) for web — ready-made UI, fastest path. Use the **Login API** directly when building a custom UI or a non-web client; use an **Xsolla SDK** (Unity / Unreal / iOS / Android / Cocos) for engines. For protocol, prefer **OAuth 2.0** (browser/mobile, refresh tokens, SSO) — fall back to JWT only when the partner has a tightly controlled environment and no need for refresh. Decision matrix and widget initialization: [`references/integration-modes.md`](references/integration-modes.md).

3. **Implement the chosen authentication method(s).** Most projects ship at least one of: **classic** username/email + password (`Register new user` → `Auth by username and password`, plus `Reset password`); **passwordless** email or SMS (`Start auth by email/phone` → user enters one-time code → `Complete auth by email/phone`); **social** (browser: `Get link for social auth` → redirect → callback returns token; native/silent: `Auth via access token of social network` for mobile/headset apps that already have a provider token, e.g. Meta Horizon nonce, Steam session ticket, Epic exchange code); **device ID** for guest play; **server custom ID** for partner-issued IDs; **silent cross-platform** for shadow projects (Steam/Xbox/Epic/PSN session ticket → JWT). Endpoints, request shapes, and provider notes: [`references/auth-flows.md`](references/auth-flows.md).

4. **Validate the user JWT on every privileged request.** On every request to your backend that uses the user JWT, verify: signature against `https://login.xsolla.com/api/projects/{login_project_id}/keys` (JWKS), `iss == https://login.xsolla.com`, `exp` in the future, `xsolla_login_project_id == <expected>`. Cache JWKS with `kid`-aware rotation. Use `sub` (user UUID) as the user identifier — never `email` or `username`, both can change. Issue a **server JWT** with `grant_type=client_credentials` for S2S calls. Refresh user JWTs via `grant_type=refresh_token` before they expire. Full claim list, `[OAuth2.0] Generate JWT`, `Validate user JWT`, `Validate Server JWT`, error codes: [`references/tokens-and-validation.md`](references/tokens-and-validation.md).

5. **Wire up user management features the product needs.** After the basic flow works, layer on: **profile** (`Get/Update user details`, picture, phone, email); **password reset** (`Reset password` → confirmation email → `Confirm password reset`); **MFA / 2FA** (project-level toggle + per-user setup); **social account linking** (`Get URL to link social network to account`, `Link/Delete linked network`); **account linking across projects** (`Create code for linking accounts` → `Link accounts by code`, or `Link user IDs via external ID` server-side); **attributes** (per-user JSON for save state, preferences, partner data — client-side and server-side variants); **friends**, **search**, **ban/unban**, **export/import**. Endpoint table: [`references/user-management.md`](references/user-management.md).

6. **Verify end-to-end.** In a sandbox project: register a test user, log in with each enabled method, decode the returned JWT, verify it against the JWKS, refresh it, hit a Store call with `Authorization: Bearer <JWT>` (the catalog-design fast-purchase flow exercises this), confirm the Pay Station payment-token call accepts it, and confirm the webhook delivers the same `user.id` (= JWT `sub`) so the `webhooks-impl` handler can grant items.

## Common pitfalls

- **Wrong client / wrong protocol mix.** A *public* OAuth 2.0 client cannot do `client_credentials`; a *server* client cannot do user login. JWT-protocol endpoints (`/api/login/...`) and OAuth 2.0 endpoints (`/api/oauth2/...`) have different paths and parameter shapes — pick one per flow and stay consistent. See [`references/integration-modes.md`](references/integration-modes.md).
- **Trusting the JWT without validating it.** A JWT is just a base64 payload. Always verify signature against the **project's JWKS** (`/api/projects/{login_project_id}/keys`), not a hard-coded key, and check `iss`, `exp`, and `xsolla_login_project_id`. Without these, any forged token is accepted.
- **Mismatched callback URL / CORS origin.** Auth fails silently or returns `redirect_uri_mismatch` when the URL passed to the Widget/API is not exactly listed under **Callback URLs** / **Allowed origins (CORS)** in Publisher Account. Trailing slash, scheme (http vs https), and port must match byte-for-byte.
- **Identifying users by `email` or `username` instead of `sub`.** Both can be changed by the user (or by social-account linking) — use the JWT `sub` (UUID) as the stable internal user ID. Email/username are convenience fields only.
- **One-time codes / nonces retried.** Passwordless email/SMS codes and native social-auth nonces (Meta Horizon `GetUserProof`, Steam session ticket on first use) are **single-use**. A naive client retry on a transient 5xx burns the credential and the next attempt fails — request a fresh code/nonce per attempt and surface the right error. See [`references/auth-flows.md`](references/auth-flows.md).
- **Forgetting to refresh.** User JWTs expire (default 24 h). Without `grant_type=refresh_token` (OAuth 2.0) or re-auth (JWT protocol), Store and Pay Station calls start failing 401 mid-session. Refresh proactively before `exp`.
- **Shadow project confusion.** Shadow Login projects store **platform accounts** (one per Steam/Xbox/Epic/PSN), main projects store **main accounts**. Linking is one-way (platform → main); unlinking is not supported. Don't put real-money payment users in a shadow project as their primary identity. Details: [`references/setup-pa.md`](references/setup-pa.md).

## Agent test

Prompt: "Integrate Xsolla Login into my web game. I want a 'Continue with Google' button, classic email + password sign-up with email confirmation, and a passwordless email one-time-code option. Validate JWTs on my Node.js backend before granting access to the Store API."

Expected (live run, sandbox): the agent reads this `SKILL.md` plus all five references, configures a standard Login project with an OAuth 2.0 *public* client + Google social provider, scaffolds Login Widget initialization in the frontend, implements the three auth flows (Google via `Get link for social auth` redirect; classic via `Register new user` → email confirmation → `Auth by username and password`; passwordless via `Start auth by email` → `Complete auth by email`), and adds an Express middleware that fetches `/api/projects/{login_project_id}/keys`, verifies signature + `iss` + `exp` + `xsolla_login_project_id`, and exposes `req.user.sub`. Sandbox smoke test: register a user → email confirmation `200` → login with each of the three methods → JWT validates → refresh succeeds → middleware rejects a tampered token with 401. ⏳ Pending live run on a fixture project.

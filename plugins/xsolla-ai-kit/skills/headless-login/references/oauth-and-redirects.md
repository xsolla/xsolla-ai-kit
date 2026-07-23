# OAuth 2.0 clients and redirect/CORS config (headless)

The Publisher Account settings a **custom frontend** needs on top of the shared Login
project config (`login-setup` → `references/setup-pa.md`). Shop Builder does not need any
of this — its hosted domain provisions its own OAuth client — so this file is headless-only.

Lives at: **Players → Login → \<your project\> → Configure → Security → OAuth 2.0**, plus
the Login project's top **Callback URLs** block.

## 1. Add OAuth 2.0 client(s)

**Add OAuth 2.0 client.** A project can have many; pick the right authentication type per
use case.

| Client type | Choose when | Used by | Grant types |
|-------------|-------------|---------|-------------|
| **Public** (no secret) | Browser SPA, mobile/desktop app, Login Widget | Frontend / SDK | `authorization_code`, `refresh_token` |
| **Confidential** (secret) | Backend can keep a secret and exchanges `code` for token | Partner backend | `authorization_code`, `refresh_token` |
| **Server** (server-to-server) | Issue **server JWTs** for S2S calls | Backend only | `client_credentials` |

Per-client fields:

- **OAuth 2.0 redirect URIs** — the URL(s) the user is redirected to after auth, email
  confirmation, password reset. Must match byte-for-byte (scheme, host, port, path,
  trailing slash). For iOS apps: `app://xlogin.<bundle-id>`.
- **Token lifetime** — for server clients only. Default 1 h.
- **Scopes** — `email`, `offline` (issues `refresh_token`), `phone`, `playfab`, …
- **Client ID** is numeric, surfaced in the list. **Secret** is shown **once** at creation
  for confidential/server clients — copy it immediately.

Setup: [Connecting OAuth 2.0](https://developers.xsolla.com/authenticate-users/login/security/connecting-oauth2/).

## 2. Set Callback URLs and Allowed origins (CORS)

**Login project → top settings block → Callback URLs.**

- **Callback URL** — destination after successful auth, email confirmation, password
  reset. Multiple values allowed.
- **Error callback URL** — destination on auth error. Falls back to Callback URL if empty.
- **Allowed origins (CORS)** — the *origins* (scheme + host + port) the browser may call
  the Login API from. Required for raw Login API calls from the browser (Widget bypasses
  this because it lives on `login.xsolla.com`).

The Callback URL passed to the Widget/API in `redirect_uri` (OAuth 2.0) or `login_url`
(JWT) **must exactly match** one of the registered values. Trailing slash, scheme (http
vs https), and port must match byte-for-byte — a mismatch is the most common cause of a
silent auth failure or `redirect_uri_mismatch`.

## 3. Identifiers checklist

These are contributed by this file, on top of the shared `XSOLLA_LOGIN_PROJECT_ID`:

```bash
XSOLLA_LOGIN_OAUTH_CLIENT_ID=<numeric>
# confidential/server clients only — never expose to client builds
XSOLLA_LOGIN_OAUTH_CLIENT_SECRET=<shown once at creation>
```

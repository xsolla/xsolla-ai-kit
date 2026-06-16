# Publisher Account configuration for Login

Everything that must be configured **before** any client/server code can authenticate
users. Lives at: **Publisher Account → Players → Login**.

All identifiers below are surfaced through the Login project page and the OAuth 2.0
client list — copy them into the agent's environment as the variables documented in the
parent `SKILL.md` Prerequisites.

## 1. Pick the Login project type

| Type | Use for | What it stores |
|------|---------|----------------|
| **Standard Login project** | Web/PC/mobile games where the player has one Xsolla identity | Main accounts (email, social, device, custom ID, …) |
| **Shadow Login project** | Cross-platform games where the player also has Steam/Xbox/Epic/PSN identities and you want the platform identity to silently resolve to the same Xsolla user | **Platform accounts only**. Each shadow project is bound to one publishing platform. Linked to a parent standard project. |

Cross-platform overview: [Cross-platform account](https://developers.xsolla.com/doc/login/features/cross-platform-account/).
You can have **one standard project + N shadow projects**, one shadow project per
publishing platform (e.g. one for Steam, one for Epic).

## 2. Connect a user data storage

Default: **Xsolla**. Other supported options affect token claims and the auth call shape.

| Storage | Notes | Token marker |
|---------|-------|--------------|
| Xsolla (default) | Users are stored in Xsolla. No extra setup. | (no extra claim) |
| PlayFab | Users are stored in PlayFab. Login proxies auth, returns PlayFab session ticket / entity token in the JWT. | `external_account_id`, `session_ticket`, `entity_token`, `entity_type`, `entity_id` |
| Firebase | Users are stored in Firebase. | (Firebase claims) |
| Custom (proxy) | Login forwards requests to **your** identity backend. You implement the proxy contract. | `provider`, `external_account_id`, optional `partner_data` |

Comparison: [Comparison of user data storage options](https://developers.xsolla.com/authenticate-users/login/user-data-storage/users-storages-comparison/).

## 3. Add OAuth 2.0 client(s)

**Players → Login → \<your project\> → Configure → Security → OAuth 2.0 → Add OAuth 2.0
client.** A project can have many; pick the right authentication type per use case.

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

## 4. Set Callback URLs and Allowed origins (CORS)

**Login project → top settings block → Callback URLs.**

- **Callback URL** — destination after successful auth, email confirmation, password
  reset. Multiple values allowed.
- **Error callback URL** — destination on auth error. Falls back to Callback URL if empty.
- **Allowed origins (CORS)** — the *origins* (scheme + host + port) the browser may call
  the Login API from. Required for raw Login API calls from the browser (Widget bypasses
  this because it lives on `login.xsolla.com`).

The Callback URL passed to the Widget/API in `redirect_uri` (OAuth 2.0) or `login_url`
(JWT) **must exactly match** one of the registered values.

## 5. Enable social networks

**Login project → Configure → Authentication → Social login.** 30+ providers are
available. Per provider:

1. Enable the toggle.
2. Click **Settings**, paste the App ID + App Secret you got from the provider's
   developer dashboard.
3. For platform-scoped IDs (Meta Horizon `org_scoped_id`, Apple `team_id`, etc.),
   provide the extra fields the form asks for.
4. **Xsolla ID / NewID** is just another social provider — enable it to give players the
   "Sign in with Xsolla" button.

Reference for the silent / native-app variants of Steam, Xbox Live, Epic Games, PSN, and
Meta Horizon: see [`auth-flows.md`](auth-flows.md) and the `[social] Auth via access
token of social network` API call.

## 6. Authentication method toggles

Same Authentication block — flip on what the game needs. Each adds API endpoints (see
[`auth-flows.md`](auth-flows.md)) and, for the Widget, a button:

- Username/email + password (`Username and password`)
- One-time password by email or SMS (`Passwordless`)
- Device ID (guest / quick-start)
- Server custom ID (partner-issued IDs)
- Social login (the providers from §5)
- Publishing platforms (only on **shadow** projects: Steam, Xbox Live, Epic Games)

Other useful toggles in the same panel:

- **Miscellaneous data form** — collect email and/or phone after social login that didn't
  return them.
- **Welcome email**, **email confirmation**, **password recovery** — built-in templates,
  override per project under **Communication providers → Custom email templates**.
- **MFA / 2FA** — project-level on/off; per-user setup happens via the API or Widget.

Custom email and SMS templates (full localization, branding): see the API section
"Custom email templates" and Communication providers settings.

## 7. Security & compliance

- **Password policy**: min length, char classes, max age — set under **Security →
  Password policy**.
- **Brute-force protection**: per-IP and per-user lockouts, captcha thresholds — under
  **Security → Brute force protection**. The default is sane; lower thresholds for
  high-risk regions.
- **Rate limits**: per-method, per-IP, per-token. Documented in [`tokens-and-validation.md`](tokens-and-validation.md).
- **Allowed IP addresses** for server-side calls — optional allowlist.
- **Age restrictions** by country — `Manage age restrictions for countries` (admin API).
- **Regional laws**: GDPR consent capture, age gating, CCPA — toggles + custom consent
  texts under **Legal settings**.

## 8. Webhooks (Login-specific)

Login emits its own webhooks (separate from Pay Station / Store webhooks): user
registered, user signed in, user banned, MFA challenged, etc. Configure URL + secret under
**Communication providers → Webhooks**, or via the API (`Get/Add/Delete webhook for
event`). Verification format and reliability rules are the same family as the
`webhooks-impl` skill — re-use it.

## 9. Identifiers checklist

After the steps above, the agent should record:

```bash
XSOLLA_LOGIN_PROJECT_ID=<UUID, copied from Login project page>
XSOLLA_LOGIN_OAUTH_CLIENT_ID=<numeric>
XSOLLA_LOGIN_OAUTH_CLIENT_SECRET=<only for confidential/server clients>
```

`XSOLLA_LOGIN_PROJECT_ID` is the same value as the JWT `xsolla_login_project_id` claim
and the `projectId` parameter in every Login API call. Both must agree.

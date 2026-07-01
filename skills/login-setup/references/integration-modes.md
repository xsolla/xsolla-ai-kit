# Integration modes — Widget vs Login API vs SDKs, JWT vs OAuth 2.0

Two orthogonal choices: **how** to call Xsolla Login (Widget / API / SDK) and **which
protocol** to use (JWT or OAuth 2.0).

## How to call Login

| Option | Best for | Pros | Cons |
|--------|----------|------|------|
| **Login Widget** (`@xsolla/login-sdk`) | Web apps, fastest UX | Ready-made UI, themable, all auth methods exposed via toggles, MFA / passwordless / social handled for you | Web only |
| **Login API** (raw HTTPS) | Custom UI, non-web clients, headless flows, server-side | Full control of the UI and request shape, language-agnostic | You build every screen and handle every error |
| **Xsolla SDK** (Unity / Unreal / iOS / Android / Cocos / …) | Engine integrations | Idiomatic per engine, wraps the API + token storage + refresh | Platform-specific quirks; one SDK version per platform |

Decision flow:

```
Web app, ship fast?                  → Login Widget
Web app, custom UI?                  → Login API (browser) + Widget for social pop-ups
Mobile/desktop game, has an engine?  → Xsolla SDK for that engine
Mobile/desktop game, custom engine?  → Login API + native social SDKs
Server-side only (S2S)?              → Login API with server OAuth 2.0 client
```

## Which protocol — JWT vs OAuth 2.0

Both protocols ultimately deliver a JWT to your client. The difference is how it is
issued and renewed.

| | JWT (legacy) | OAuth 2.0 (preferred) |
|---|---|---|
| Endpoint family | `/api/login/...`, `/api/social/...` | `/api/oauth2/...` |
| Token returned | User JWT directly | `code` → exchange via `Generate JWT` for `access_token` (+ optional `refresh_token`) |
| Refresh | Re-authenticate | `grant_type=refresh_token` |
| Server JWT (S2S) | Not supported | `grant_type=client_credentials` |
| SSO | Limited | Full (`OAuth 2.0 authorize`, `Check user authentication`, `Log user out`, `Clear SSO`) |
| Recommended? | Only when locked-in to legacy | **Yes — default** |

**Default to OAuth 2.0 unless the partner explicitly needs the JWT-protocol shape.** Most
new integrations have refresh-token requirements that make JWT-protocol painful.

OAuth 2.0 reference: [Connecting OAuth 2.0](https://developers.xsolla.com/authenticate-users/login/security/connecting-oauth2/).

## Login Widget initialization

Minimal Widget config (copy the values from Publisher Account, see [`setup-pa.md`](setup-pa.md)):

```js
import { Widget } from '@xsolla/login-sdk';

const xl = new Widget({
  projectId:       'XSOLLA_LOGIN_PROJECT_ID',     // Login project UUID
  preferredLocale: 'en_US',
  clientId:        'XSOLLA_LOGIN_OAUTH_CLIENT_ID', // OAuth 2.0 public client
  responseType:    'code',
  state:           'CSRF-RANDOM-STRING',           // anti-CSRF, verify on callback
  redirectUri:     'https://your.site/callback',   // must be in Callback URLs
  scope:           'offline email',                // offline → issues refresh_token
});

xl.open(document.getElementById('login-button'));
```

After redirect, exchange the `code` query parameter for a JWT via `[OAuth2.0] Generate
JWT` (see [`tokens-and-validation.md`](tokens-and-validation.md)).

For the Widget to display the right buttons, the matching toggles must be enabled in
Publisher Account first — Widget is purely a UI layer over the same auth methods.

## Login API call shape

**Base URL**: `https://login.xsolla.com/api`. All requests use HTTPS, JSON in/out.

Auth headers:

| Caller | Header |
|--------|--------|
| Anonymous (registration, login start) | none |
| Authenticated user (profile, etc.) | `Authorization: Bearer <user_JWT>` |
| Server (S2S, e.g. import users, server attributes) | `X-SERVER-AUTHORIZATION: <server_JWT>` |

Project / client identifiers in query parameters:

- JWT-protocol calls: `?projectId=<XSOLLA_LOGIN_PROJECT_ID>`
- OAuth 2.0 calls: `?client_id=<XSOLLA_LOGIN_OAUTH_CLIENT_ID>` (+ `redirect_uri`,
  `state`, `response_type`, `scope` on flows that start the auth)

Always pass through the user's IP for rate-limit / geolocation correctness — the
Login service uses it for brute-force scoring and for resolving country-specific rules.

## Where Login fits in the broader integration

Login issues the JWT that the rest of the stack consumes:

```
                     ┌────────────────────┐
   user JWT (Bearer) │                    │  same JWT used by:
   ──────────────────►   Store API        │  · catalog-design (cart, fast purchase)
                     │  Payments          │  · headless-checkout-integration (payment-token call)
                     │  Webhooks          │  · webhooks-impl (user.id == JWT.sub)
                     │  Partner backend   │
                     └────────────────────┘
```

Refresh proactively before `exp` so Store/Pay-Station calls don't 401 mid-checkout.

## When to mix

It is normal to combine modes — for example, the Widget for the auth UI, raw Login API
on your backend for `Validate user JWT` and server-side user management, and SDK calls
on a mobile companion app. They share the same Login project, the same OAuth 2.0
clients, and the same user database — there is no per-mode account silo.

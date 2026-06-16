# Authentication flows

All authentication methods exposed by Xsolla Login, with the Login API operations to
invoke. Each method has a JWT-protocol variant and an OAuth 2.0 variant — prefer OAuth
2.0 (see [`integration-modes.md`](integration-modes.md)). Schemas vary by data storage
(Xsolla / PlayFab / Firebase / custom) — verify the request body via the Xsolla MCP
before calling.

URL slugs below are the live `operationId`s from `xsolla-login@941da4eff` (`swagger/**/*.yaml`).

## 1. Classic — username/email + password

The bread-and-butter flow. Two operations: register, then sign in.

| Task | API call |
|------|----------|
| Register | [\[OAuth2.0\] Register new user](https://developers.xsolla.com/api/login/operation/oauth-20-register-new-user) / [\[JWT\] Register new user](https://developers.xsolla.com/api/login/operation/jwt-register-new-user) |
| Sign in | [\[OAuth 2.0\] Auth by username and password](https://developers.xsolla.com/api/login/operation/oauth-20-auth-by-username-and-password) (`POST /oauth2/login`) / [\[JWT\] Auth by username and password](https://developers.xsolla.com/api/login/operation/auth-by-username-and-password) (`POST /login`) / [\[OAuth 2.0\] JWT auth by username and password](https://developers.xsolla.com/api/login/operation/jwt-auth-by-username-and-password) (`POST /oauth2/login/token`) |
| Confirm email (resend link) | [\[OAuth2.0\] Resend account confirmation email](https://developers.xsolla.com/api/login/operation/oauth-20-resend-account-confirmation-email) / [\[JWT\] Resend account confirmation email](https://developers.xsolla.com/api/login/operation/jwt-resend-account-confirmation-email) |
| Reset password | [Reset password](https://developers.xsolla.com/api/login/operation/reset-password) → user clicks email link → [Confirm password reset](https://developers.xsolla.com/api/login/operation/confirm-password-reset) |

Notes:

- Register sends a **welcome email** if the project has it on; it can also require email
  confirmation before the first login.
- Password policy (min length, complexity, history) is enforced by the project — see
  [`setup-pa.md`](setup-pa.md) §7.
- Brute-force protection on `Auth by username and password` is on by default (per IP +
  per username); after the threshold, captcha is required.

## 2. Passwordless — email or SMS one-time code

Two-step: start the auth (server sends a code), complete the auth (user submits the
code).

| Task | API call |
|------|----------|
| Email — start | [\[OAuth2.0\] Start auth by email](https://developers.xsolla.com/api/login/operation/oauth-20-start-auth-by-email) / [\[JWT\] Start auth by email](https://developers.xsolla.com/api/login/operation/jwt-start-auth-by-email) |
| Email — complete | [\[OAuth2.0\] Complete auth by email](https://developers.xsolla.com/api/login/operation/oauth-20-complete-auth-by-email) / [\[JWT\] Complete auth by email](https://developers.xsolla.com/api/login/operation/jwt-complete-auth-by-email) |
| SMS — start | [\[OAuth2.0\] Start auth by phone number](https://developers.xsolla.com/api/login/operation/oauth-20-start-auth-by-phone-number) / [\[JWT\] Start auth by phone number](https://developers.xsolla.com/api/login/operation/jwt-start-auth-by-phone-number) |
| SMS — complete | [\[OAuth2.0\] Complete auth by phone number](https://developers.xsolla.com/api/login/operation/oauth-20-complete-auth-by-phone-number) / [\[JWT\] Complete auth by phone number](https://developers.xsolla.com/api/login/operation/jwt-complete-auth-by-phone-number) |
| Server-side variant | [Get confirmation code](https://developers.xsolla.com/api/login/operation/get-confirmation-code) (server uses the code itself, e.g. test fixtures) |
| Server-only register | [Register new user from server](https://developers.xsolla.com/api/login/operation/register-new-user-from-server) |

Notes:

- The code is **single-use and short-lived**. Naive retries on a transient 5xx burn the
  code — request a fresh one per attempt and surface the right error. Exact TTLs and
  resend cooldowns are project-configurable; check Publisher Account or your project's
  email/SMS template settings rather than hard-coding values.
- The same `operation_id` returned by `Start auth` must be passed to `Complete auth`.
- SMS templates and senders configured under **Communication providers** in PA.

## 3. Social — browser flow (`Get link` → redirect → callback)

Used by the Login Widget and any browser-based custom UI. The user is redirected to the
provider, signs in there, and the provider redirects back with a code.

| Task | API call |
|------|----------|
| Build the redirect URL | [\[OAuth 2.0\] Get link for social auth](https://developers.xsolla.com/api/login/operation/oauth-20-get-link-for-social-auth) / [\[JWT\] Get link for social auth](https://developers.xsolla.com/api/login/operation/jwt-get-link-for-social-auth) |
| (Widget does this internally) | `GET /social/{providerName}/login_redirect` (JWT) — same shape under `/oauth2/social/...` |
| Auth callback | [\[OAuth 2.0\] Auth via social network](https://developers.xsolla.com/api/login/operation/oauth-20-auth-via-social-network) / [\[JWT\] Auth via social network](https://developers.xsolla.com/api/login/operation/jwt-auth-via-social-network) |
| Refresh provider tokens (when supported) | [\[JWT\] Refresh social tokens in JWT](https://developers.xsolla.com/api/login/operation/jwt-refresh-social-token) |

Provider list: 30+ social networks are supported, configured per project. Common ones
include Google, Facebook, Apple, Twitter, Discord, Microsoft, Twitch, Steam, Epic Games,
PlayStation Network, Xbox Live, Meta Horizon (Oculus), Naver, Baidu, QQ, WeChat, VK,
Yandex, KakaoTalk, LINE, Amazon, GitHub, Mail.Ru, Odnoklassniki, Xsolla / NewID, plus
custom OIDC / OAuth 2.0 providers via the project-level `customidentityprovider` and
`oidc` features. **Confirm what's currently enabled in your project's PA before relying
on a specific provider** — the available list evolves and varies by region.

To collect missing email/phone after social login (some providers don't return them),
either enable the **Miscellaneous data form** in PA (Widget shows a follow-up form), or
add `fields=email`/`scope=email` to `Get link for social auth`.

## 4. Social — native silent flow (mobile / headset / launcher)

Used when the client app already has a provider token (e.g. obtained from the platform
SDK on Quest, mobile, or PC launcher) and wants to skip the browser bounce.

| Task | API call |
|------|----------|
| Native social token → Xsolla JWT | [\[JWT\] Auth via access token of social network](https://developers.xsolla.com/api/login/operation/jwt-auth-via-access-token-of-social-network) (`POST /social/{provider_name}/login_with_token`) / [\[OAuth 2.0\] Auth via access token of social network](https://developers.xsolla.com/api/login/operation/oauth-20-auth-via-access-token-of-social-network) (`POST /oauth2/social/{provider_name}/login_with_token`) |

Request body across providers (verify exact shape per provider):

```json
{ "access_token": "<provider token / nonce / session ticket>",
  "openid":       "<provider user_id, when needed (e.g. Meta Horizon)>",
  "access_token_secret": "<for OAuth 1 providers like Twitter v1>" }
```

Provider-specific notes:

- **Steam** — `access_token` = session ticket from Steamworks SDK. Single-use; treat
  5xx as fatal and re-acquire from Steam.
- **Epic Games** — `access_token` = exchange code from the Epic launcher.
- **Xbox Live** — `access_token` = `XBLToken` formatted as `<XUID>;<userhash>;<XSTSToken>`.
- **PlayStation Network** — `access_token` = PSN auth code from the platform SDK.
- **Meta Horizon (Oculus / Quest)** — `access_token` = nonce from `Users.GetUserProof()`,
  `openid` = App-Scoped User ID. The Xsolla backend validates server-side via
  `graph.oculus.com/user_nonce_validate`. See ADR
  [`docs/adr/0001-silent-auth-via-meta-horizon-oculus.md`](https://github.com/xsolla/xsolla-login/blob/master/docs/adr/0001-silent-auth-via-meta-horizon-oculus.md)
  in the `xsolla-login` repo.
- **Apple / Google / Facebook** — `access_token` = native SDK token (Sign in with Apple
  identity token, Google ID token, FB access token).

These calls do all the same things as the browser flow on the Xsolla side (issue JWT,
trigger event flow, MFA, ASK fields, attribute population) — the only difference is the
identity-proof comes from the client.

## 5. Device ID — guest / quick-start

Sign the user in by a stable per-device identifier (no email needed). Useful for "play
without account" intros that can later be upgraded to a full account via account linking.

| Task | API call |
|------|----------|
| Sign in by device ID | [\[JWT\] Auth via device ID](https://developers.xsolla.com/api/login/operation/jwt-auth-via-device-id) / [\[OAuth 2.0\] Auth via device ID](https://developers.xsolla.com/api/login/operation/oauth-20-auth-via-device-id) |
| List devices linked to a user | [Get user devices](https://developers.xsolla.com/api/login/operation/get-users-devices) |
| Link a device | [Link device to account](https://developers.xsolla.com/api/login/operation/link-device-to-account) |
| Unlink a device | [Unlink device from account](https://developers.xsolla.com/api/login/operation/unlink-device-from-account) |

Notes: `device_id` should be a stable UUID generated by the client. The first call
creates the user; subsequent calls return the same `sub`.

## 6. Server custom ID — partner-issued IDs

For partners who already have their own user database and want Xsolla Login as a token
broker without touching their identity store. Signs in / creates a Login user keyed on
your `external_account_id`.

| Task | API call |
|------|----------|
| Auth by custom ID | [\[JWT\] Auth by custom ID](https://developers.xsolla.com/api/login/operation/auth-by-custom-id) (server-side, requires server JWT) |
| Update server custom ID for an existing user | [Update server custom ID for user](https://developers.xsolla.com/api/login/operation/put-user-custom-id) |
| Get attributes by server custom IDs | [Get attributes by server custom IDs](https://developers.xsolla.com/api/login/operation/get-attributes-by-server-custom-id) |
| Link existing Xsolla user to external ID | [Link user IDs via external ID](https://developers.xsolla.com/api/login/operation/link-user-ids-via-external-id) |

`auth-by-custom-id` is a **server call** (`X-SERVER-AUTHORIZATION` header). Never expose
the server JWT to the client.

## 7. Silent cross-platform — shadow Login project

For cross-platform games, the platform identity (Steam/Xbox/Epic) is stored in a
**shadow** Login project; the standard project still owns the main account. Same client
calls as §4, but issued against the shadow project ID; the result is then linked to the
main account via `Link accounts by code` (see [`user-management.md`](user-management.md)
§ "Account linking").

| Task | API call |
|------|----------|
| Silent auth (cross-auth between projects) | [\[OAuth 2.0\] Silent authentication](https://developers.xsolla.com/api/login/operation/oauth-20-silent-authentication) / [\[JWT\] Silent authentication](https://developers.xsolla.com/api/login/operation/jwt-silent-authentication) |
| Platform-specific session ticket → JWT | `Auth via access token of social network` (same as §4) |
| Create cross-project link code | [Create code for linking accounts](https://developers.xsolla.com/api/login/operation/create-code-for-linking-accounts) |
| Consume the link code | [Link accounts by code](https://developers.xsolla.com/api/login/operation/link-accounts-by-code) |

Setup flow per platform: see "How to set up a shadow Login project" in
[How-tos](https://developers.xsolla.com/authenticate-users/login/how-to/) — Steam needs an
AppID + Web API Key; Epic needs Client ID + Secret; Xbox Live can run with Xsolla's keys
or your own.

## 8. SSO and logout

Once OAuth 2.0 is wired:

| Task | API call |
|------|----------|
| Authorize (start SSO) | [OAuth 2.0 authorize](https://developers.xsolla.com/api/login/operation/oauth2-authorize) (`GET /oauth2/auth`) |
| Check user authentication | [\[OAuth 2.0\] Check user authentication](https://developers.xsolla.com/api/login/operation/check-user-authentication) (`GET /oauth2/sso`) |
| Log out (revoke session) | [\[OAuth 2.0\] Log user out](https://developers.xsolla.com/api/login/operation/log-user-out) (`GET /oauth2/logout`) |
| Clear SSO cookies | [\[OAuth 2.0\] Clear SSO](https://developers.xsolla.com/api/login/operation/clear-sso-cookie) (`GET /oauth2/clear_sso`) |
| Revoke a token (refresh or access) | [\[OAuth2.0\] Revoke Token](https://developers.xsolla.com/api/login/operation/revoke-jwt) (`POST /oauth2/token/revoke`) |
| Save OAuth 2.0 consent | [\[OAuth 2.0\] Save consent](https://developers.xsolla.com/api/login/operation/oauth2-save-consent) (`POST /oauth2/consent`) |
| Check OAuth 2.0 consent | [\[OAuth 2.0\] Check consent](https://developers.xsolla.com/api/login/operation/oauth2-check-consent) (`POST /oauth2/consent/validate`) |

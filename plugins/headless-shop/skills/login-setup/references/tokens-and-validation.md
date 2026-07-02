# Tokens, validation, errors, rate limits

How user JWTs and server JWTs are issued, what they contain, how to validate them, and
the operational guard-rails (errors, rate limits, IP allowlist).

## User JWT — issuance & refresh

Every successful auth (any method in [`auth-flows.md`](auth-flows.md)) returns a user JWT.

- **JWT protocol**: returned directly in the response or in the `?token=<JWT>` query of
  the redirect URL.
- **OAuth 2.0**: returns a `code` first; exchange it for `access_token` (+ optional
  `refresh_token`) via [\[OAuth2.0\] Generate JWT](https://developers.xsolla.com/api/login/operation/generate-jwt) (operationId `generate-jwt`):

  ```http
  POST https://login.xsolla.com/api/oauth2/token
  Content-Type: application/x-www-form-urlencoded

  grant_type=authorization_code
  client_id=<XSOLLA_LOGIN_OAUTH_CLIENT_ID>
  client_secret=<only for confidential clients>
  redirect_uri=<exact match of the URL used to start auth>
  code=<one-time authorization code>
  ```

- **Refresh** before expiry:

  ```
  grant_type=refresh_token
  client_id=…
  refresh_token=<from previous Generate JWT>
  ```

- **Revoke** the access or refresh token: [\[OAuth2.0\] Revoke Token](https://developers.xsolla.com/api/login/operation/revoke-jwt) (`POST /oauth2/token/revoke`, operationId `revoke-jwt`).

Default lifetime: 24 h (configurable per Login project). Refresh tokens last longer
(set on the OAuth 2.0 client). The Widget refreshes for you; raw clients must implement
it.

## User JWT — claims

Every claim the agent should care about. Full list in
[`xsolla-login/docs/login-api.md`](https://github.com/xsolla/xsolla-login/blob/master/docs/login-api.md)
JWT structure section.

| Claim | Type | Meaning |
|-------|------|---------|
| `sub` | UUID string | **Stable user ID. Use this in your DB** — never email or username. |
| `iss` | string | Always `https://login.xsolla.com`. |
| `iat`, `exp` | unix timestamp | Issue / expiry. Validate `exp > now`. |
| `xsolla_login_project_id` | UUID | Must equal `XSOLLA_LOGIN_PROJECT_ID`. |
| `publisher_id` | int | Merchant who owns the project. |
| `type` | string | `xsolla_login` / `social` / `email` / `phone` / `firebase` / `playfab` / `proxy` / `device` / `server_custom_id`. Use to know how the user authenticated. |
| `groups` | array | `[{id, name, is_default}]` — your custom user groups. |
| `email`, `username`, `avatar` | string | Profile snapshot. Don't trust as identity. |
| `provider`, `id`, `social_access_token`, `picture` | various | Present on `type=social`; `provider` is the network name, `id` is the user's ID inside that network. |
| `external_account_id`, `session_ticket`, `entity_token`, … | string | Present when storage = PlayFab. |
| `provider`, `external_account_id`, `partner_data` | various | Present when storage = custom proxy. |
| `payload` | string | Free-form value passed by the client during auth. Echoed back here. |
| `connection_information` | string | Birth-date confirmation status (e.g. okname for KR). |
| `promo_email_agreement` | bool | Newsletter opt-in. |

## Validating a user JWT (mandatory)

In **every** server-side handler that accepts a user JWT:

1. **Fetch the JWKS** for the project: [Get JSON Web Key Set](https://developers.xsolla.com/api/login/operation/json-web-key-set):
   `GET https://login.xsolla.com/api/projects/{XSOLLA_LOGIN_PROJECT_ID}/keys`. Cache the
   result, key by `kid`. Honor `Cache-Control` / refresh on `kid` miss to handle key
   rotation.
2. **Verify signature** with the key whose `kid` matches the JWT header. Algorithm:
   `RS256`.
3. **Verify claims**:
   - `iss === "https://login.xsolla.com"`
   - `exp > now`
   - `nbf <= now` (if present)
   - `xsolla_login_project_id === XSOLLA_LOGIN_PROJECT_ID`
   - For OAuth 2.0 access tokens: `client_id` matches an expected one.
4. **Extract `sub` as the user ID**. Use it as the foreign key in your DB.
5. (Optional, defence-in-depth) call [Validate user JWT](https://developers.xsolla.com/api/login/operation/validate-jwt)
   (`POST /token/validate`, operationId `validate-jwt`) for a server-side liveness check
   (rejects revoked tokens). Don't call this on every request — too costly; use it on
   session establishment or risk decisions only.

The same `/projects/{project_id}/keys` endpoint ([Get project keys](https://developers.xsolla.com/api/login/operation/get-projects-keys), operationId `get-projects-keys`) is the canonical RSA-keys resource — JWKS is just one representation.

Standard libraries (`jsonwebtoken` for Node, `jwt-go` for Go, `python-jose` for Python,
`Microsoft.IdentityModel.Tokens` for .NET) all accept a JWKS URL — pass the project's
JWKS URL and the rest is mechanical.

## Server JWT — S2S auth

For server-side calls that use `X-SERVER-AUTHORIZATION: <server_JWT>`:

1. Create a **server OAuth 2.0 client** (see [`setup-pa.md`](setup-pa.md) §3).
2. Issue a server token:

   ```
   POST https://login.xsolla.com/api/oauth2/token
   grant_type=client_credentials
   client_id=<server client ID>
   client_secret=<server client secret>
   ```

3. Use the returned `access_token` in `X-SERVER-AUTHORIZATION`.
4. Cache + auto-refresh on expiry. Same `Generate JWT` endpoint, no user context.

Server JWT is required for, e.g.:

- [Auth by custom ID](https://developers.xsolla.com/api/login/operation/auth-by-custom-id)
- [Get users IDs by social ID and platform](https://developers.xsolla.com/api/login/operation/get-users-ids-by-social-id-and-platform)
- [Link accounts by code](https://developers.xsolla.com/api/login/operation/link-accounts-by-code)
- [Link user IDs via external ID](https://developers.xsolla.com/api/login/operation/link-user-ids-via-external-id)
- All `Server-side` attribute calls
- [Validate Server JWT](https://developers.xsolla.com/api/login/operation/validate-server-jwt) (`POST /server/token/validate`)

Server JWT claims: `iss`, `exp`, `iat`, `client_id`, `publisher_id`, `xsolla_login_project_id`.

## Errors

Error envelope:

```json
{
  "error": {
    "code": "LongIdentifierNotFound",
    "description": "User not found",
    "details": null
  }
}
```

Frequently encountered codes:

| Code | Cause | Fix |
|------|-------|-----|
| `InvalidParameter` | Bad request shape | Check schema via Xsolla MCP. |
| `Unauthorized` | Bad / missing JWT or server JWT | Re-issue token. |
| `TokenExpired` | `exp < now` | Refresh, then retry. |
| `InvalidClient` / `ClientNotFound` | OAuth 2.0 `client_id` wrong or disabled | Verify in PA, check public/confidential/server type matches the grant. |
| `InvalidGrant` | `code` / `refresh_token` consumed or expired | Restart auth or refresh earlier. |
| `RedirectUriMismatch` | `redirect_uri` doesn't match a registered Callback URL | Add the URL byte-for-byte in PA. |
| `BruteForceLimit` | Too many failed attempts | Show captcha; back off. |
| `CaptchaRequired` | Threshold reached | Render captcha widget; resubmit with token. |
| `EmailAlreadyExists` / `UsernameAlreadyExists` | Account exists | Switch to login flow / suggest password reset. |
| `EmailNotConfirmed` | Project requires email confirmation | Resend confirmation email. |
| `OneTimeCodeExpired` / `OneTimeCodeInvalid` | Email/SMS code stale | Request a fresh code. |
| `MfaRequired` | 2FA challenge | Walk the user through the per-user MFA flow. |
| `SocialTokenInvalid` | Provider token rejected by Xsolla / by the provider | Acquire a fresh token from the provider; for native nonces (Meta Horizon, Steam ticket), call the platform SDK again. |
| `SocialProviderNotEnabled` | Provider not configured for the project | Enable + fill credentials in PA. |
| `DependencyServiceUnavailable` | Upstream provider (graph.oculus.com, Steam Web API, …) failed | Retry with backoff; surface 503 to client. |
| `RateLimitExceeded` (HTTP 429) | Too many requests | Honor `Retry-After`. |

## Rate limits

- **Per IP, per method** is always on; values vary by method. The hardest limits sit on
  classic auth (anti brute-force) and passwordless start (anti SMS abuse).
- **Server-side methods** (`X-SERVER-AUTHORIZATION`) have higher ceilings than
  client-side. If you proxy client traffic through your server you'll spend the
  client-side budget on the server — keep the IP forwarded so per-user limits apply.
- **429** responses include `Retry-After` (seconds). Implement exponential backoff with
  jitter; don't tight-loop.
- Increases are possible by request — contact your CSM (`csm@xsolla.com`).

Reference: [Rate limits](https://developers.xsolla.com/api/login/#section/Rate-limits).

## IP allowlist

`login.xsolla.com` calls outbound from a fixed set of IP addresses (current list in
[`docs/login-api.md`](https://github.com/xsolla/xsolla-login/blob/master/docs/login-api.md#ip-addresses)).
Allowlist them on:

- Your custom-storage proxy backend.
- Your custom-email / SMS provider, if configured.
- Webhook endpoints subscribed to Login events.

## TLS, headers, body

- HTTPS only — HTTP returns 400.
- Always send `Content-Type: application/json` for POST/PATCH/PUT bodies.
- Forward the user's IP via `X-Forwarded-For` from your edge so per-user rate limits and
  geo rules behave correctly.
- Don't log the JWT, the server JWT, the OAuth 2.0 secret, or one-time codes / nonces.
- For confidential / server clients, store the secret in a secrets manager (Vault,
  AWS Secrets Manager, etc.) — never in source control or `.env` committed to git.

# Publisher Account configuration for Login (shared)

Project-level Login configuration that **both** storefront paths need — headless and Shop
Builder alike. Lives at: **Publisher Account → Players → Login**.

> **Scope.** This file covers the storefront-agnostic setup: the Login project, user-data
> storage, which social networks and auth methods are enabled, and security/compliance.
> The **OAuth 2.0 client + redirect/CORS** configuration a custom frontend needs is a
> headless concern — see `headless-login` (`references/oauth-and-redirects.md`). Shop
> Builder provisions its own OAuth client for the hosted domain, so a Shop Builder build
> stops after this file.

All identifiers below are surfaced through the Login project page — copy them into the
agent's environment as the variables in the parent `SKILL.md` Prerequisites.

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

## 3. Enable social networks

**Login project → Configure → Authentication → Social login.** 30+ providers are
available. Per provider:

1. Enable the toggle.
2. Click **Settings**, paste the App ID + App Secret you got from the provider's
   developer dashboard.
3. For platform-scoped IDs (Meta Horizon `org_scoped_id`, Apple `team_id`, etc.),
   provide the extra fields the form asks for.
4. **Xsolla ID / NewID** is just another social provider — enable it to give players the
   "Sign in with Xsolla" button.

The silent / native-app variants of Steam, Xbox Live, Epic Games, PSN, and Meta Horizon
require frontend code — that lives in `headless-login` (`references/auth-flows.md`). Here
you only decide which providers are **on**.

## 4. Authentication method toggles

Same Authentication block — flip on what the game needs. Enabling a method here is what
both storefront paths depend on; the code that drives each method is a headless concern
(`headless-login`), and Shop Builder's hosted UI renders whatever is toggled on.

- Username/email + password (`Username and password`)
- One-time password by email or SMS (`Passwordless`)
- Device ID (guest / quick-start)
- Server custom ID (partner-issued IDs)
- Social login (the providers from §3)
- Publishing platforms (only on **shadow** projects: Steam, Xbox Live, Epic Games)

Other useful toggles in the same panel:

- **Miscellaneous data form** — collect email and/or phone after social login that didn't
  return them.
- **Welcome email**, **email confirmation**, **password recovery** — built-in templates,
  override per project under **Communication providers → Custom email templates**.
- **MFA / 2FA** — project-level on/off; per-user setup happens via the API or Widget.

## 5. Security & compliance

- **Password policy**: min length, char classes, max age — set under **Security →
  Password policy**.
- **Brute-force protection**: per-IP and per-user lockouts, captcha thresholds — under
  **Security → Brute force protection**. The default is sane; lower thresholds for
  high-risk regions.
- **Allowed IP addresses** for server-side calls — optional allowlist.
- **Age restrictions** by country — `Manage age restrictions for countries` (admin API).
- **Regional laws**: GDPR consent capture, age gating, CCPA — toggles + custom consent
  texts under **Legal settings**.

Per-method / per-IP / per-token rate limits are documented alongside token validation in
`headless-login` (`references/tokens-and-validation.md`).

## 6. Webhooks (Login-specific)

Login emits its own webhooks (separate from Pay Station / Store webhooks): user
registered, user signed in, user banned, MFA challenged, etc. Configure URL + secret under
**Communication providers → Webhooks**, or via the API (`Get/Add/Delete webhook for
event`). Verification format and reliability rules are the same family as the
`webhooks-impl` skill — re-use it.

## 7. Identifiers checklist

After the steps above, the agent should record the project id (needed by every path):

```bash
XSOLLA_LOGIN_PROJECT_ID=<UUID, copied from Login project page>
```

`XSOLLA_LOGIN_PROJECT_ID` is the same value as the JWT `xsolla_login_project_id` claim
and the `projectId` parameter in every Login API call. Both must agree.

For a **headless** build, continue to `headless-login` to add an OAuth 2.0 client and the
redirect/CORS settings, which contribute `XSOLLA_LOGIN_OAUTH_CLIENT_ID` /
`_CLIENT_SECRET`. A **Shop Builder** build needs nothing further here.

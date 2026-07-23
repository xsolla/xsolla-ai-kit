---
name: login-setup
description: >-
  Shared, storefront-agnostic setup of Xsolla Login (a.k.a. NewID) — the player identity
  layer whose JWT `sub` becomes the `user.id` that flows into the Store cart, the payment
  token, and webhook fulfillment. Covers the project-level Publisher Account configuration
  both the headless and Shop Builder paths depend on: creating or choosing the Login project
  (standard vs shadow for cross-platform), linking it to the Store project, picking the user
  data storage (Xsolla / PlayFab / Firebase / custom), enabling authentication methods
  (username/password, passwordless email & SMS codes, 30+ social networks, device ID, server
  custom ID, silent cross-platform), MFA and password policy, and the identity model. Use
  whenever a developer says "set up Xsolla Login", "create/link a Login project", "enable
  Google/Facebook/Steam/Epic/PSN/Xbox/Meta login", "turn on passwordless / MFA", "choose
  user data storage", "shadow Login project", "cross-platform account", or needs the Login
  project that catalog-design, headless-login, and webhooks-impl all build on. For the
  headless code integration (OAuth client, Login Widget/API/SDK, JWT validation, cart Bearer
  switch) use `headless-login`; for a Shop Builder storefront the hosted site renders login
  itself and only needs the methods enabled here.
metadata:
  owner: mohammed_abujalala
  domain: login
  status: draft
---

## Status

This skill is a **draft** authored by the Login SME (@mohammed_abujalala).

## Scope

This is the **shared Login foundation** — the Publisher Account configuration that is the
same whether the storefront is headless or Shop Builder. It sets up the Login project and
decides what identity the shop runs on; it does **not** write frontend or backend code.

- **Headless build** → after this, run `headless-login` for the OAuth 2.0 client, the Login
  Widget/API/SDK integration, JWT validation, and the guest→Bearer cart switch.
- **Shop Builder build** → after this, nothing more is needed for login. The hosted
  storefront renders the login UI and manages tokens itself; it only surfaces the auth
  methods you enable here.

Detailed material:
- [`references/setup-pa.md`](references/setup-pa.md) — the full project-level checklist:
  project type, user data storage, social providers, method toggles, security/compliance,
  Login webhooks, the project-id checklist.

## The identity model (why every path needs this)

Login issues a JWT whose `sub` claim is the stable user UUID. That `sub`:

- authenticates the **Store cart** and personal-store calls (`catalog-design`),
- is embedded in the **payment token** (`headless-checkout-integration`), and
- arrives as `user.id` in the **payment webhook**, so `webhooks-impl` knows who to grant to.

Get the project and its identity right here and the rest of the shop lines up. Use `sub`
(UUID) as the internal user id everywhere — never `email` or `username`, both can change.

## When to use

- Create or choose a Login project and link it to the Store project (`XSOLLA_PROJECT_ID`).
- Decide standard vs **shadow** project (shadow = cross-platform Steam/Xbox/Epic/PSN).
- Pick user data storage (Xsolla default, or PlayFab / Firebase / custom proxy).
- Enable the authentication methods and social providers the game needs.
- Set MFA, password policy, brute-force protection, and legal/age settings.
- Configure Login-specific webhooks (user registered / signed in / banned).

Out of scope (each has its own skill): OAuth client + code integration + JWT validation
(→ `headless-login`), catalog & purchase (→ `catalog-design`), payments
(→ `headless-checkout-integration`), payment/webhook handler (→ `webhooks-impl`), Xsolla
account/API-key bootstrap (→ `merchant-setup`).

## Prerequisites

```bash
export XSOLLA_MERCHANT_ID=<your merchant ID>
export XSOLLA_PROJECT_ID=<your project ID>
export XSOLLA_PROJECT_API_KEY=<your API key>
# produced by this skill:
export XSOLLA_LOGIN_PROJECT_ID=<UUID of the Login project>
```

- An Xsolla project (run `merchant-setup` first — it sets the publisher/project variables).
- **Xsolla MCP (strongly recommended).** Connect the official Xsolla MCP server
  (<https://developers.xsolla.com/get-started/ai-assistants/>) and verify current request
  schemas with `search_xsolla_sources` before any API call. If MCP is unavailable, fetch
  the linked developers.xsolla.com pages.
- API base URL: `https://login.xsolla.com/api`. All Login traffic is HTTPS only.

## Steps

1. **Create or choose the Login project.** Standard for most games; **shadow** for
   cross-platform (a separate main-account project + one shadow per platform). Link the
   project to the Store project so the same identity powers the catalog and payments.

2. **Pick the user data storage.** Xsolla default, or PlayFab / Firebase / custom proxy —
   this affects token claims and the auth call shape downstream.

3. **Enable authentication methods and social providers.** Turn on only what the game
   needs: classic username/password, passwordless email/SMS, social networks (paste each
   provider's App ID + Secret), device ID, server custom ID, and — on shadow projects —
   publishing platforms. The hosted Shop Builder UI and a headless custom UI both render
   only what is toggled on here.

4. **Set security and compliance.** Password policy, brute-force protection, MFA toggle,
   allowed IPs, age restrictions, and GDPR/CCPA consent.

5. **Record `XSOLLA_LOGIN_PROJECT_ID`.** It equals the JWT `xsolla_login_project_id` claim
   and the `projectId` in every Login API call.

Full field-level checklist for every step: [`references/setup-pa.md`](references/setup-pa.md).

## Common pitfalls

- **Not linking the Login project to the Store project.** Cart and payment-token calls
  reject a JWT from an unlinked Login project.
- **Enabling a method in code without toggling it on here.** A headless build calling a
  disabled method (or a Shop Builder site expecting a button that was never enabled) fails
  silently — the toggle is the source of truth.
- **Identifying users by `email`/`username` instead of `sub`.** Both change; `sub` (UUID)
  is the only stable id, and it is the value that must match the webhook `user.id`.
- **Shadow project confusion.** Shadow projects store **platform** accounts (one per
  Steam/Xbox/Epic/PSN); main projects store **main** accounts. Linking is one-way. Don't
  make a shadow project a real-money buyer's primary identity.

## Agent test

Prompt: "Set up an Xsolla Login project for my cross-platform game. I want Google and Steam
sign-in plus passwordless email codes, MFA on, and it linked to my Store project. I'll wire
the actual login UI later."

Expected (live run, sandbox): the agent reads this `SKILL.md` and `references/setup-pa.md`,
creates a standard Login project linked to `XSOLLA_PROJECT_ID` (and notes a shadow project
is needed for silent Steam), keeps Xsolla user-data storage, enables Google + Steam social
providers and passwordless-email, turns on MFA and a sane password policy, and records
`XSOLLA_LOGIN_PROJECT_ID` — then points the developer at `headless-login` for the code, or
confirms nothing more is needed if they are building on Shop Builder. ⏳ Pending live run.

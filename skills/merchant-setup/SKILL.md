---
name: merchant-setup
description: Guide for setting up a new Xsolla merchant account and obtaining API credentials. Use this skill whenever a user needs to create an Xsolla Publisher Account, get API keys, understand the difference between merchant-level and project-level API keys, set up sandbox mode for testing, or asks how to start integrating with Xsolla Pay Station. Also trigger when a user says they want to accept payments via Xsolla, start an Xsolla integration, or test Xsolla payments. Claude Code cannot create the account on behalf of the user — this skill provides the exact steps the user must complete manually before integration can begin.
metadata:
  owner: y-klochikhin
  domain: orchestrator
---

# Merchant Setup

AI Agent **cannot** create an Xsolla account automatically. The user must complete the registration steps manually.

## Step 0: Check for Existing Credentials

**Before anything else**, check the project root's `.env` with the skill's script, run from
that folder. It parses `.env` as text, never sources it, and never prints the key:

```bash
python3 "<skill base dir>/scripts/env_credentials.py" check
```

It prints the merchant ID and project ID (they are not secrets, and they show which project is
configured) and only `set` or `missing` for `XSOLLA_PROJECT_API_KEY`. Show the user those three
lines and confirm the IDs are the intended project. If all three are set and the project is the
right one, continue with the integration. Never print, echo or show the key, even masked or
encoded.

If the file is missing or any value is missing, continue with the steps below. For a coded shop,
tell the user which value is missing. Do not ask them to paste the project API key into chat.

**Where the key lives:**

- A shop the user codes (`shop-setup`) has a project directory. Write the merchant id, project id, and project API key to `.env` ([Step 5](#step-5-write-credentials-to-env)). That file is for the application.
- A shop created on Xsolla's side (`nocode-shop-setup`) has no project directory. Use the
  project key held by the signed-in Xsolla CLI; do not create `.env` unless the recovery
  below needs one.
- When `xsolla auth login` reports that it created a Store API key for the project and
  saved it to the keychain, CLI commands use that key. Do not ask for a key or copy it
  into `.env` or chat. Check it with one read-only catalog command for this project. If
  that read returns 401 (seen after switching projects), run `xsolla auth login` for the
  intended project and repeat the read once.
- If it still returns 401, `auth login` made no key for this project. Creating one is a
  write: propose it and wait for the user's yes (for `nocode-shop-setup`, in its one batch).
  Then create one project key with `xsolla publisher create-api-key` (confirm the command
  with `xsolla publisher --help`) and pipe its output straight into
  `python3 "<skill base dir>/scripts/env_credentials.py" write --merchant-id <id> --project-id <id> --key-stdin`,
  run from the folder the CLI runs from, so the key is saved to `.env` there (the CLI reads
  it) and never appears in the output or the chat. Create one key per project, not one per
  run. If the key cannot be saved this way, stop and report the credential blocker.
- Never ask the user to paste a key or a session token into chat.

---

## Step 1: Create a Publisher Account

Direct the user to: **https://publisher.xsolla.com/signup**

### Individual vs. Company account

| | Individual | Company |
|---|---|---|
| **When to use** | Just testing, evaluating Xsolla, quick sandbox setup | Committed to going live, need a contract |
| **Registration** | Simple — email, Google, or social login | Requires company details for the licensing agreement |
| **Contract** | Still needed for live payments, but can skip for sandbox | Submit from the Agreements tab once ready |

For pure exploration and sandbox testing, an individual account is the fastest path. The user can always add company details later when submitting the licensing agreement.

> Publisher Account uses two-factor authentication. Confirmation code is sent to the registered email.

---

## Step 2: Extract IDs from a Publisher Account URL

The user doesn't need to hunt for IDs — they're embedded in every Publisher Account URL. Parse them directly if the user shares a link.

URL pattern:
```
https://publisher.xsolla.com/{merchant_id}/projects/{project_id}/...
```

Examples:
- `https://publisher.xsolla.com/{merchant_id}/settings/api_key` → merchant ID is in the URL
- `https://publisher.xsolla.com/{merchant_id}/projects/{project_id}/edit/api_key` → both IDs are in the URL

If the user doesn't share a URL, tell them:
- **Merchant ID**: visible in the URL on any Publisher Account page, or under `Company settings → Company`
- **Project ID**: visible in the sidebar next to the project name, or in the URL when inside a project

---

## Step 3: Generate a Project-Level API Key

> ⚠️ **Critical**: The API key is shown **only once** at creation time. It is never sent by email. The user must copy and save it immediately — it cannot be recovered.

For standard integration, the **project-level key** is sufficient.

- Location: `Project settings → API key`
- Direct URL: `https://publisher.xsolla.com/{merchant_id}/projects/{project_id}/edit/api_key`
- Scope: this project only
- General project-level API auth format: `Authorization: Basic Base64({project_id}:{api_key})`.
  Use this only for endpoints whose contract specifies project-level Basic auth.

To generate:
1. Open the URL above (with the real IDs)
2. Click **Create**
3. Copy and store the value immediately

### Merchant-level API key (optional)

Only needed for Xsolla CLI or API calls where the endpoint URL has **no `project_id`** path parameter.

- Location: `Company settings → API keys` → `https://publisher.xsolla.com/{merchant_id}/settings/api_key`
- Auth format: `Authorization: Basic Base64({merchant_id}:{api_key})`

**Rule of thumb**: follow the authentication contract for the specific API.
Some APIs use project-level credentials and others require a merchant-level
key. Quest Platform publisher routes are an API-specific exception: they use
the configured merchant ID as the HTTP Basic username with the project API key
as password, as the live Quests docs describe (see
[`live-docs.md`](../quest-setup/references/live-docs.md)). Do not
apply that Quest Platform format to Catalog, Store, or unrelated APIs.

---

## Step 4: Sandbox Mode — No Contract Needed

> ℹ️ Development can start **immediately** after account creation — no signed contract required.

A project-level API key is all that's needed to run a full sandbox integration: create tokens, test the payment UI, configure the catalog.

When going live, the only change needed is switching the mode from `sandbox` to production in the integration. Everything else stays the same.

What requires a **signed licensing agreement** (submit from the **Agreements** tab in Publisher Account):
- Accepting real payments from end users
- Completing the Tax Interview (W-8 for non-US / W-9 for US)

Contract review typically takes a few business days — submit it well before the planned launch date.
Full go-live checklist (utils probe, flip sandbox flags, deploy, live payment tests): **`production`**.

---

## Quick Reference

| Resource | URL |
|----------|-----|
| Sign up | https://publisher.xsolla.com/signup |
| Publisher Account | https://publisher.xsolla.com |
| API Reference | https://developers.xsolla.com/api |
| Getting started guide | https://developers.xsolla.com/get-started/work-in-pa/create-first-project/ |
| FAQ — API keys | https://developers.xsolla.com/dev-resources/faq/general/#faq_project_settings |

---

## Step 5: Write Credentials to .env

For a coded shop, write the confirmed credentials to the project-local `.env` with the skill's
script, run from the project root. It first makes sure `.env` is ignored by Git, then sets
`XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID` and `XSOLLA_PROJECT_API_KEY` in place (existing lines,
including `export NAME=` lines, are updated without duplicates; every other line is kept) and
leaves the file at mode `600`:

```bash
python3 "<skill base dir>/scripts/env_credentials.py" write --merchant-id <merchant_id> --project-id <project_id>
```

This writes the two IDs and keeps a key already in the file. To add the key, give the user this
command to run in their own terminal; it asks for the key with hidden input, so the key never
reaches the chat:

```bash
python3 "<skill base dir>/scripts/env_credentials.py" write --merchant-id <merchant_id> --project-id <project_id> --key-prompt
```

Both print the same result as `check`: the two IDs and `set` or `missing` for the key. For a Shop
Builder shop without a code repository, do not create `.env`; the signed-in Xsolla CLI holds the
project key (see [Where the key lives](#step-0-check-for-existing-credentials)). Never source,
execute or interpolate `.env`, and never print or echo the key, even masked or encoded.

## Checklist

- [ ] `.env` checked for existing credentials (Step 0)
- [ ] Publisher Account created (individual or company)
- [ ] Merchant ID known
- [ ] Project ID known
- [ ] Project-level API key securely available in `.env` for a coded shop or the signed-in CLI for Shop Builder
- [ ] For a coded shop, `.env` written with the skill's script: mode 600 and ignored by Git
- [ ] *(Optional)* Merchant-level API key saved — only needed for CLI or cross-project API calls

Once credentials are available from `.env` or the signed-in CLI, proceed with the integration.

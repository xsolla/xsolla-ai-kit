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

**Before anything else**, check for a `.env` file in the project root. Parse it
as text and inspect only whether the expected names have non-empty values.
Never run `source`, `eval`, or shell interpolation on `.env`. Do not print the
file, values, or encoded headers.

```bash
python3 - <<'PY'
from pathlib import Path

expected = (
    "XSOLLA_MERCHANT_ID",
    "XSOLLA_PROJECT_ID",
    "XSOLLA_PROJECT_API_KEY",
)
values = {}
path = Path(".env")
for line in path.read_text().splitlines() if path.is_file() else ():
    line = line.rstrip("\r\n").strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    name, _, value = line.partition("=")
    name = name.strip()
    if name.startswith("export "):
        name = name[7:].strip()
    if name not in expected:
        continue
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    values[name] = value
for name in expected:
    print(f"{name}: {'set' if values.get(name) else 'missing'}")
PY
```

Report only `XSOLLA_MERCHANT_ID: set/missing`,
`XSOLLA_PROJECT_ID: set/missing`, and `XSOLLA_PROJECT_API_KEY: set/missing`.
If all three are set, continue with the integration without showing any values.

If the file is missing or any variable is absent, continue with the steps below.
For a coded shop, tell the user which required key is missing from the
project-local `.env`. Do not ask them to paste the project API key into chat.

**Where the key lives:**

- A shop the user codes (`shop-setup`) has a project directory. Write the merchant id, project id, and project API key to `.env` ([Step 5](#step-5-write-credentials-to-env)). That file is for the application.
- A shop created on Xsolla's side (`nocode-shop-setup`) has no project directory. Do
  not create `.env`; use the project key held by the signed-in Xsolla CLI instead.
- When `xsolla auth login` reports that it created a Store API key for the project and
  saved it to the keychain, CLI commands use that key. Do not ask for a key or copy it
  into `.env` or chat. Check it with one read-only catalog command for this project. If
  that read returns 401 after a project switch, run `xsolla auth login` for the intended
  project and repeat the read once. If it still returns 401, stop and report the secure
  credential setup blocker; do not create or request a key as a chat fallback. Never ask
  the user to paste a session token.

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

For a coded shop, write confirmed credentials to the project-local `.env` using
`XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID`, and `XSOLLA_PROJECT_API_KEY`. For a
Shop Builder shop without a code repository, do not create `.env`; the signed-in
Xsolla CLI holds the project key.

Before saving any values, verify `.env` is ignored by Git. Add it to `.gitignore`
before creating a new file. Create the file with only the required settings and
set its mode to `600`. For an existing file, update required assignments in place,
including lines that start with `export NAME=`, without adding duplicates. Preserve
all unrelated lines and settings.

Never source, execute, or interpolate `.env`. After writing, confirm only the
set/missing state of each key. Never print or echo saved values, even masked or
encoded.

## Checklist

- [ ] `.env` checked for existing credentials (Step 0)
- [ ] Publisher Account created (individual or company)
- [ ] Merchant ID known
- [ ] Project ID known
- [ ] Project-level API key securely available in `.env` for a coded shop or the signed-in CLI for Shop Builder
- [ ] For a coded shop, `.env` has mode 600 and is ignored by Git
- [ ] *(Optional)* Merchant-level API key saved — only needed for CLI or cross-project API calls

Once credentials are available from `.env` or the signed-in CLI, proceed with the integration.

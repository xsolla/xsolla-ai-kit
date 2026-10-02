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
When a value is missing, tell the user to save the required key in the
project-local `.env`: `XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID`, or
`XSOLLA_PROJECT_API_KEY`. Do not ask them to paste the project API key into
chat.

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
- `https://publisher.xsolla.com/887981/settings/api_key` → **merchant_id = 887981**
- `https://publisher.xsolla.com/887981/projects/308077/edit/api_key` → **merchant_id = 887981**, **project_id = 308077**

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
as password, as documented in
[`qp-api-contract.md`](../quest-setup/references/qp-api-contract.md). Do not
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

Once all credentials are confirmed, write them to the project-local `.env`.
Use the `XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID`, and
`XSOLLA_PROJECT_API_KEY` names. Update only those three assignments and retain
every other line and setting, including `XSOLLA_QP_ENV`.

If `.env` does not exist, add `.env` to the repository's `.gitignore` before
saving any credential values, then create the file with only the required
settings. Treat `.env` as text; never source, execute, or interpolate it.

After writing, confirm only the set/missing state of each required key. Never
repeat any saved value, even in masked or encoded form.

For an existing `.env`, update each of those three keys in place when already
present, including a line that starts with `export NAME=`. Do not add a
second assignment for the same key. Preserve all unrelated content and verify
that the file is ignored by Git before saving new credential values.

---

## Checklist

- [ ] `.env` checked for existing credentials (Step 0)
- [ ] Publisher Account created (individual or company)
- [ ] Merchant ID known
- [ ] Project ID known
- [ ] Project-level API key generated and saved securely
- [ ] Credentials written to `.env`
- [ ] `.env` added to `.gitignore`
- [ ] *(Optional)* Merchant-level API key saved — only needed for CLI or cross-project API calls

Once credentials are in `.env`, proceed with the integration.

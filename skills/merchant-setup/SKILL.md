---
name: merchant-setup
description: Sets up the Xsolla CLI as the agent's way into Xsolla — install it, sign in, pick the merchant and project, and get the API key into the keychain without the user ever copying a key from Publisher Account. Use this skill whenever a user needs to create an Xsolla Publisher Account, sign in to Xsolla, install or authenticate the Xsolla CLI (`xsolla auth login`), get or rotate an API key, choose or create a project, set up sandbox mode for testing, or start any Xsolla integration (Pay Station, Store, catalog, Login, webhooks, Shop Builder). Also trigger when another skill's preflight fails (CLI missing, not logged in, no project, 401/403 from a CLI command), or when the user says they want to accept payments via Xsolla or test Xsolla payments.
metadata:
  owner: y-klochikhin
  domain: orchestrator
---

# Merchant Setup

Every other skill reaches Xsolla through the **Xsolla CLI** (`xsolla`). This skill gets it
installed and signed in, with a merchant and a project selected. It also stores a Store API
key in the OS keychain.

Never ask the user to copy an API key or token out of Publisher Account and paste it into
the chat or into `.env`. The CLI mints and stores keys itself.

## Step 0: Preflight

Run these three checks. They are read-only and safe to repeat.

```bash
xsolla --version                  # installed? which version?
xsolla auth status --json         # signed in, token not expired?
xsolla config list --json         # merchant_id / project_id / sandbox
```

| Result | Go to |
|---|---|
| `command not found` | Step 1 |
| `authenticated: false` or `expired: true` | Step 2 |
| `merchant_id` or `project_id` is `0` or missing | Step 3 |
| All present | Step 3's project confirmation, then Steps 4–6 |

Ignore `xsolla publisher status`: it can say "not configured" when the config is fine.

## Step 1: Install the CLI

The minimum is **1.9.4**. A `dev` build is acceptable. Ask before installing, because this
changes the user's machine:

```bash
brew install xsolla/xsolla-cli/xsolla      # macOS / Linux with Homebrew
brew update && brew upgrade xsolla         # when below 1.9.4
```

Without Homebrew, point the user to the signed release archives for their OS. Do not pipe
a remote script into a shell.

## Step 2: Sign in

**The user already has a Publisher Account.** Run `xsolla auth login`. It opens a browser
for OAuth2 + PKCE. The user completes the sign-in there, and the CLI never sees a password.
Tokens go to the OS keychain and refresh automatically.

- If login fails with *audience required*, retry with
  `--audience https://api.xsolla.com`.

**The user has no account yet.** The user runs `xsolla publisher signup` themselves, in
their own terminal (`! xsolla publisher signup` in Claude Code). It asks for a password and
an emailed 6-digit code, and the agent must never type or see either one.

- Signup creates the merchant, tries to create a project, and saves both IDs to
  `.xsolla.json`.
- Then run `xsolla auth login`.
- Signup prints an API key. Tell the user they don't need to save it, because Step 4
  mints the key the agent uses.
- An individual account is the fastest way to evaluate Xsolla in sandbox. Company
  details are needed later, for the licensing agreement.

## Step 3: Select the merchant and project

- **`merchant_id` is still 0 after login.** Ask the user for it. Every Publisher Account
  URL contains it: `publisher.xsolla.com/{merchant_id}/projects/{project_id}/...`.
- **No `project_id`.** Let the user choose one from
  `xsolla publisher list-projects --json` (`data[].id`, `data[].name`).

- **No projects exist.** Confirm a name with the user, then:

  ```bash
  xsolla publisher create-project --name "<Game name>" --url "<game site>"
  ```

  It saves the new `project_id` to the active config; pin it below. If the user gives a short descriptor, add
  `--descriptor <≤12 letters/digits>`. If creation is refused, send the user to
  Publisher Account → **Projects → Create project**, then return to the list step.
- **A project is already set.** Confirm it before building on it, because the IDs may come
  from `~/.xsolla.json` and belong to an earlier game. Show its name from
  `publisher list-projects --json` and ask: *"Use project `<name>` (`<id>`) for this
  game?"* If the user says no, use the list step above.
- **Pin the confirmed project to this game.** The CLI reads `./.xsolla.json` before
  `~/.xsolla.json`, so a local file keeps another game's `config set` from switching this
  one. The file holds no secrets. Run this in the game's root:

  ```bash
  [ -f .xsolla.json ] || xsolla config init
  xsolla config set merchant-id <id> && xsolla config set project-id <id>
  xsolla config set sandbox true     # while building; see "Sandbox and going live"
  ```

## Step 4: Store API key (agent side)

Catalog, payments and other Basic-auth commands need a Store API key. They read it from the
keychain. Recent CLI builds create one automatically during `xsolla auth login` when a
project is set. Probe for it; this is a read-only call:

```bash
xsolla catalog admin-list-currency --json >/dev/null; echo "exit=$?"
```

| Exit | Meaning | Action |
|---|---|---|
| `0` | The key works | Done |
| `10` | No key, or a rejected key | Run the command below, then probe again |
| other | Not a key problem | See [Troubleshooting](#troubleshooting) |

```bash
xsolla publisher create-api-key --title "xsolla-cli (agent)" >/dev/null
```

`create-api-key` saves every key it creates to the keychain, and the newest one replaces
the previous one there. Stdout goes to `/dev/null`, so the key never appears in the
transcript. Keys expire after 365 days by default; set the lifetime with `--days 1-3650`.

## Step 5: Runtime config in `.env` (the developer's app)

Code the developer ships cannot use the CLI or the keychain. Their backend reads its own
`.env`. Write the non-secret IDs from config:

```bash
touch .env && chmod 600 .env   # the CLI ignores a group/world-readable .env, with a warning
grep -qxF '.env' .gitignore 2>/dev/null || echo ".env" >> .gitignore
ids=$(xsolla config list --json | python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; print("XSOLLA_MERCHANT_ID=%s\nXSOLLA_PROJECT_ID=%s" % (d["merchant_id"], d["project_id"]))') \
  && sed -i.bak -E '/^XSOLLA_(MERCHANT_ID|PROJECT_ID)=/d' .env && rm .env.bak \
  && printf '%s\n' "$ids" >> .env
```

Do not mint a **backend API key** up front. Mint it only when the app's server code needs
one, for payment tokens or server-side Store admin calls, or when a later skill asks for
`XSOLLA_PROJECT_API_KEY` at the point it uses it. The agent's own CLI calls never need it.

The key goes straight into `.env`; never print it or echo it back. The old line is removed
only after the new key arrives:

```bash
key=$(xsolla publisher create-api-key --title "backend: $(basename "$PWD")" --json \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print((d.get("data") or d)["key"])') \
  && [ -n "$key" ] \
  && sed -i.bak -E '/^XSOLLA_PROJECT_API_KEY=/d' .env && rm .env.bak \
  && printf 'XSOLLA_PROJECT_API_KEY=%s\n' "$key" >> .env
unset key
```

Each run creates a new key, and that key also becomes the CLI's keychain key. To rotate,
run it again. Then revoke only **older** keys: `xsolla publisher list-api-keys --json`, then
`xsolla publisher revoke-api-key --key-id <id> --force`. Without `--force` it waits for a
y/N prompt. Never write `XSOLLA_API_KEY` or `XSOLLA_TOKEN` anywhere: they override the keychain.

Never delete lines from `.env` other than the ones this skill owns. Other skills keep keys
there, such as `XSOLLA_BUILD_PATH` from `shop-plan`.

## Step 6: Report

```
✅ Xsolla CLI <version> — signed in as <login> (<context>)
   merchant_id=<id>  project_id=<id> ("<project name>")  sandbox=true   (./.xsolla.json)
   Store API key: in keychain ✓
   .env: XSOLLA_MERCHANT_ID, XSOLLA_PROJECT_ID[, XSOLLA_PROJECT_API_KEY=****]
```

`<login>` and `<context>` come from the active entry in `xsolla auth list-account --json`.
`auth status` doesn't include them.

## Sandbox and going live

You can build without a signed contract. Sandbox covers catalog setup, payment tokens, the
payment UI and webhooks. Live payments and the tax interview (W-8/W-9) need the
**licensing agreement**. Submit it from **Agreements** in Publisher Account; review takes a
few business days. No CLI command signs the agreement or switches the project live.
**`production`** covers the full go-live checklist.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Exit `10` (401/403) after a working login | `XSOLLA_API_KEY` or `XSOLLA_TOKEN` is set in the env | `unset XSOLLA_API_KEY XSOLLA_TOKEN`, then probe again |
| Exit `10` on a webshop or cart command | It needs a player JWT, not a publisher login | See the bundled CLI skill `auth-accounts` (`--auth-context xsolla-id`) |
| 403 *roles for user… merchant* | The project belongs to another merchant | Run `publisher list-projects` and pick one from that list |
| `merchant_id not set` | The token carried no merchant | Step 3 |
| CI or a headless box with no browser | OAuth needs a browser | Set `XSOLLA_API_KEY` from the CI secret store and `merchant_id` in config. This is the one exception to "no env keys". |

Exit codes: `0` ok · `1` usage · `10` auth · `20` network · `30` validation · `40` not found
· `50` conflict · `70` 5xx · `75` transient (retry). `--json` gives `{"ok":…,"data"|"error":…}`.

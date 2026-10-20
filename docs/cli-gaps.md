# What the Xsolla CLI can't do yet

The kit's skills reach Xsolla through the Xsolla CLI. Where the CLI has no command, or behaves
differently from what an agent needs, the skill says so in its **CLI gaps** table and falls back
to Publisher Account or a named REST step that takes its bearer from `xsolla auth get-token`.
Nothing on this list asks the user to paste a key.

This page collects every gap in one place, so each can be filed once and closed once. Checked
against CLI `dev` 379d24a (built 2026-09-04) on 2026-10-20. The **Ticket** column is empty
until the gap is filed.

## Missing commands

| Area | Need | Today | Skill | Ticket |
|---|---|---|---|---|
| Payments | Mint a **sandbox** payment token | `webshop admin-create-payment-token` ignores `--sandbox` and has no flag for the body's `sandbox` field, so every token is live | `headless-checkout-integration`, `shop-setup` | |
| Payments | `payments create-token` with the CLI sign-in | Reads only an exported `XSOLLA_API_KEY`, never the keychain | `headless-checkout-integration`, `production` | |
| Payments | Pay Station utils check (is the contract signed?) | No command | `production` | |
| Webhooks | Set the project's webhook URL and secret, enable webhooks | No command | `webhooks-impl` | |
| Webhooks | `order_paid` / `order_canceled` / subscription payloads in `webhook trigger` | `trigger --list` has only `payment`, `refund`, `user_validation`; no custom-body flag | `webhooks-impl` | |
| Webhooks | Forward live Xsolla deliveries to a local handler | `listen` / `trigger` are offline only | `webhooks-impl` | |
| Login | OAuth 2.0 clients: create, secret, redirect URIs | No API; `login oauth-setup` only opens Publisher Account | `login-setup` | |
| Login | Callback URLs, allowed origins (CORS), social providers, MFA, email templates | No write command | `login-setup` | |
| Login | Rename or delete a Login project; delete a test user | No command | `login-setup` | |
| Login | Upload a CSS / font / image file to Xsolla storage | No command (`shopbuilder upload-asset` is for Shop Builder landings) | `login-styling` | |
| Login | Read or set the Login `custom_style_url`; read `disallow_external_style` | No command | `login-styling` | |
| Catalog | Consumable / non-consumable type, availability window (`periods`) | No flag on `create-items` / `update-items` | `catalog-design` | |
| Catalog | Delete or update an item group | No command | `catalog-design` | |
| Catalog | Regions / reglocks, per-user limits, attributes | 403 on a standard Store key | `catalog-design` | |
| Catalog | Price or show a virtual currency directly | `admin-create-currency` has no `--prices` / `--is-show-in-store` | `catalog-design` | |
| Go-live | Sign the licensing agreement, tax interview, switch live | No command (`shopbuilder list-agreements` reads the status) | `production` | |

## Behaviour that trips an agent

| Behaviour | Effect | Skill that works around it |
|---|---|---|
| The publisher sign-in lasts about a day and doesn't renew itself | `publisher` and `login` commands fail until the user runs `xsolla auth login` again; the Store key keeps working | `merchant-setup` |
| A 401 on a `publisher` command exits `1` with plain text on stderr, even with `--json` | An agent checking for exit `10` or a JSON error misses it | `merchant-setup` |
| With `--json`, every failure leaves stdout empty and puts the error JSON on stderr | Parsing stdout alone gets nothing | `merchant-setup`, `catalog-design` |
| `xsolla config init` prompts for IDs | Hangs a non-interactive agent unless stdin is closed | `merchant-setup` |
| `login list-project` / `create-project` don't read `merchant_id` from config | `--publisher-id` is required every time | `login-setup` |
| `login register-jwt` takes the password only as a flag, and `--dry-run` prints it | The test password ends up in the process list and the transcript | `login-setup` |
| The `*-oauth` commands' `--client-id` help says it's "the same as the Login project ID" | It isn't | `login-setup` |
| `login add-webhook` needs `XSOLLA_LOGIN_SERVER_TOKEN` from Publisher Account | The CLI sign-in isn't enough | `login-setup` |
| The CLI ignores `XSOLLA_WEBHOOK_SECRET` in a project `.env` | `webhook trigger` signs with an empty secret, without a warning | `webhooks-impl` |
| `create-api-key` saves every new key to the keychain, replacing the previous one | Revoking the newest key breaks the CLI's own Store access | `merchant-setup` |

## Release questions

- Is keychain storage of the Store API key, and its automatic creation during `xsolla auth
  login` (`ensureStoreAPIKey`), in a released build? Every test ran on a `dev` build of CLI
  `main`. The kit's minimum is 1.9.4; if 1.9.4 lacks this, the minimum has to go up.
- `https://cdn.xsolla.net/xsolla-cli/latest/version.json` is missing, so `xsolla update` can't
  find new releases.

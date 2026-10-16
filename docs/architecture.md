# Architecture

```
shop-setup (orchestrator)
    ├── merchant-setup                   → Merchant and Project setup
    ├── login-setup                      → Xsolla Login API
    ├── catalog-design                   → `xsolla catalog` (admin); Catalog API in shipped client code
    ├── headless-checkout-integration    → Payments via Headless Checkout
    ├── webhooks-impl                    → Webhook configuration + handler code generation
    └── production                       → Sandbox → live (contract, flags, deploy, live tests)
```

## How skills reach Xsolla

The agent works through the **Xsolla CLI** (`xsolla` 1.9.4 or later,
`brew install xsolla/xsolla-cli/xsolla`) on both build paths.

| Concern | Where it lives |
|---|---|
| Sign-in | `xsolla auth login` (browser OAuth2 + PKCE). The token is in the OS keychain. |
| Store API key | Minted by the CLI, in the OS keychain, and loaded automatically by Basic-auth commands |
| Merchant and project | `.xsolla.json` (`xsolla config list` / `config set`) |
| Developer's runtime config | `.env`, written by `merchant-setup`. The backend API key is written only when the app needs one. |

`merchant-setup` owns all of this. Other skills run a three-command preflight
(`xsolla --version`, `xsolla auth status`, `xsolla config list`) and hand off to
`merchant-setup` when it fails.

REST stays in two places:

- **Code the developer ships**: client catalog and cart calls, the Headless Checkout SDK, the
  backend payment-token endpoint, and webhook handlers. A shipped game must not depend on the
  CLI.
- **CLI gaps**: operations with no command yet. Examples are project webhook settings, the
  Login OAuth client, and the Login custom-style upload. A skill that hits a gap says so and
  gets its bearer token from `xsolla auth get-token`, never from a pasted value.

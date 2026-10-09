# Architecture

```
shop-setup (orchestrator)
    ├── merchant-setup                   → Merchant and Project setup
    ├── login-setup                      → Xsolla Login API
    ├── catalog-design                   → IGS API: /merchant/v2/projects/{id}/items/*
    ├── headless-checkout-integration    → Payments via Headless Checkout
    ├── webhooks-impl                    → Webhook configuration + handler code generation
    └── production                       → Sandbox → live (contract, flags, deploy, live tests)
```

On the headless path, skills call Xsolla REST APIs directly. The Shop Builder path needs the Xsolla CLI 1.9.4 or later (`brew install xsolla/xsolla-cli/xsolla`).

# Architecture

```
shop-setup (orchestrator)
    ├── merchant-setup                   → Merchant and Project setup
    ├── login-setup                      → Xsolla Login API
    ├── catalog-design                   → IGS API: /merchant/v2/projects/{id}/items/*
    ├── headless-checkout-integration    → Payments via Headless Checkout
    └── webhooks-impl                    → Webhook configuration + handler code generation
```

Skills call Xsolla REST APIs directly. The CLI (`xsolla/xsolla-cli`) is an optional shortcut once it ships.

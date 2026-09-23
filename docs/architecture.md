# Architecture

```
shop-plan                                → Headless vs Shop Builder, decided and recorded first
    ↓  (XSOLLA_BUILD_PATH in .env)
shop-setup (orchestrator)            → builds the recorded path
    ├── merchant-setup                   → Merchant and Project setup
    ├── login-setup                      → Xsolla Login API
    ├── catalog-design                   → IGS API: /merchant/v2/projects/{id}/items/*
    ├── headless-checkout-integration    → Payments via Headless Checkout
    ├── webhooks-impl                    → Webhook configuration + handler code generation
    ├── shopbuilder-storefront           → Shop Builder path: site → page → blocks → customize
    └── production                       → Sandbox → live (contract, flags, deploy, live tests)
```

Skills call Xsolla REST APIs directly. The CLI (`xsolla/xsolla-cli`) is an optional shortcut once it ships.

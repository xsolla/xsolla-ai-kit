# Architecture

```
shop-plan                                → Headless vs Shop Builder, decided and recorded first
    ↓  (XSOLLA_BUILD_PATH in .env)
shop-setup (orchestrator)            → headless path below; shopbuilder path →
    │                                     shopbuilder-storefront → site → page → blocks → customize
    ├── merchant-setup                   → Merchant and Project setup
    ├── login-setup                      → Xsolla Login API
    ├── catalog-design                   → IGS API: /merchant/v2/projects/{id}/items/*
    ├── headless-checkout-integration    → Payments via Headless Checkout
    ├── webhooks-impl                    → Webhook configuration + handler code generation
    └── production                       → Sandbox → live (contract, flags, deploy, live tests)
```

Skills call Xsolla REST APIs directly. The CLI (`xsolla/xsolla-cli`) is an optional shortcut once it ships.

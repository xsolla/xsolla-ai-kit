# Architecture

```
shop-setup (orchestrator)
    ├── project-init       → Xsolla REST API: /merchant/v2/merchants/{id}/projects
    ├── login-setup        → Xsolla Login API
    ├── catalog-design     → IGS API: /merchant/v2/projects/{id}/items/*
    ├── payments-config    → Pay Station API
    └── webhooks-impl      → Webhook configuration + handler code generation
```

Skills call Xsolla REST APIs directly. The CLI (`xsolla/xsolla-cli`) is an optional shortcut once it ships.

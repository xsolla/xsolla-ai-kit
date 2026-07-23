# Skills

Each subdirectory contains a `SKILL.md` — a structured workflow file for an Xsolla integration domain. One entry point (`shop-setup`) runs a shared foundation, then routes to one of two build paths (headless or Shop Builder).

## Entry

| Skill                               | Domain                                        | Owner         | Status |
|-------------------------------------|-----------------------------------------------|---------------|--------|
| [`shop-setup`](shop-setup/SKILL.md) | Single entry point — foundation + path router | @y.klochikhin | Done   |

## Shared foundation (both paths)

| Skill                                       | Domain                                | Owner               | Status |
|---------------------------------------------|---------------------------------------|---------------------|--------|
| [`merchant-setup`](merchant-setup/SKILL.md) | Merchant and Project setup            | @y.klochikhin       | Done   |
| [`catalog-design`](catalog-design/SKILL.md) | Items, purchase & order tracking      | @p.sanachev         | Draft  |
| [`login-setup`](login-setup/SKILL.md)       | Shared Login / NewID project config   | @mohammed_abujalala | Draft  |
| [`webhooks-impl`](webhooks-impl/SKILL.md)   | Webhook handler generation            | @e.chernykh         | Draft  |

## Headless branch

| Skill                                                                     | Domain                              | Owner               | Status |
|---------------------------------------------------------------------------|-------------------------------------|---------------------|--------|
| [`headless-storefront`](headless-storefront/SKILL.md)                     | Headless path orchestrator          | @y.klochikhin       | Draft  |
| [`headless-login`](headless-login/SKILL.md)                               | Headless Login code integration     | @mohammed_abujalala | Draft  |
| [`login-styling`](login-styling/SKILL.md)                                 | Theme/brand the Login widget (CSS)  | @elnur_khalilov     | Draft  |
| [`headless-checkout-integration`](headless-checkout-integration/SKILL.md) | Payments via Headless Checkout      | @y.klochikhin       | Draft  |

## Shop Builder branch

| Skill                                                             | Domain                          | Owner | Status |
|------------------------------------------------------------------|---------------------------------|-------|--------|
| [`shopbuilder-storefront`](shopbuilder-storefront/SKILL.md)      | Shop Builder path orchestrator  | —     | Draft  |
| [`shopbuilder-site`](shopbuilder-site/SKILL.md)                  | Level 1 — site container        | —     | Draft  |
| [`shopbuilder-page`](shopbuilder-page/SKILL.md)                  | Level 2 — page                  | —     | Draft  |
| [`shopbuilder-blocks`](shopbuilder-blocks/SKILL.md)             | Level 3 — blocks                | —     | Draft  |
| [`shopbuilder-customize`](shopbuilder-customize/SKILL.md)        | Level 4 — block customization   | —     | Draft  |
| [`shopbuilder-custom-block`](shopbuilder-custom-block/SKILL.md) | Advanced escape hatch           | —     | Draft  |

## Adding a skill

See [../../../CONTRIBUTING-skills.md](../../../CONTRIBUTING-skills.md).

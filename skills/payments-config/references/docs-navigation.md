# Docs navigation — Headless Checkout

Where the authoritative material lives, and how to fetch it. Always prefer the **Xsolla
MCP** (`search_xsolla_sources`) for current schemas; the links below are stable entry
points but field-level detail changes.

## Map of the docs

| Topic | Page |
|-------|------|
| Headless Checkout overview (what it is vs. hosted Pay Station) | <https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/> |
| Get started / how it works (flow diagram) | <https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/integration-guide/get-started/> |
| Install + initialize SDK | <https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/integration-guide/install-sdk/> |
| Integrate on the application side (form, components, events) | <https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/integration-guide/integrate-on-app-side/> |
| **SDK components reference** (`psdk-*` tags) | <https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/references/sdk-components/> |
| Receiving payment method data | <https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/references/payment-method-data/> |
| Payment methods (bank cards, e-wallets, Apple/Google Pay, saved) | <https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/payment-methods/> |
| Styling secured components | <https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/references/styles/> |
| Supported languages | <https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/references/supported-languages/> |
| Test payments in sandbox | <https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/integration-guide/test-payments/> |
| Go live (licensing, real-payment test) | <https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/integration-guide/go-live/> |
| **Pay Station Create token API** | <https://developers.xsolla.com/api/pay-station/token/create-token/> |
| Test bank cards (incl. 3DS) | <https://developers.xsolla.com/dev-resources/testing/test-cards/> |
| PayRank (top payment methods) | <https://developers.xsolla.com/payment-ui-and-flow/payment-methods/how-to-manage-top-payment-methods/> |
| Order life cycle | <https://developers.xsolla.com/api/catalog/payment-client-side/create-order#section/Error-response-format> |

## Code samples

- Live demo (React): <https://headless-checkout-demo-react.web.app/start-page>
- Sample scripts (bank cards, PayPal, Apple/Google Pay): <https://github.com/xsolla/pay-station-sdk/tree/main/examples>

## How to fetch with the MCP

The SDK signatures, event payloads, and token fields are the parts most likely to drift.
Before writing integration code, query the MCP for the specific piece, e.g.:

- "headless checkout form.init parameters and onNextAction event types"
- "psdk-payment-methods component attributes and selectionChange payload"
- "Pay Station create-token request body settings.ui parameters"

## Scope note

This is the **headless SDK** path. Adjacent docs you may land on but that are *not* this
skill: hosted Pay Station / Pay Station Embed (`doc/pay-station/`), Site Builder webshops,
and the legacy `paystation-embed` repo (deprecated). If the developer wants a ready-made
hosted UI rather than a custom one, they don't need this SDK — they open
`https://secure.xsolla.com/paystation4/?token={token}` (or the `sandbox-secure` host).

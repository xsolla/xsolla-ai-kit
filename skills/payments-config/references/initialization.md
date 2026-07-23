# Initialization — SDK + payment token

The dev-environment entry point: install the SDK, initialize it, and feed it a payment
token. Verify exact signatures via the Xsolla MCP before coding.

Docs: [Install SDK](https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/integration-guide/install-sdk/) ·
[Create token API](https://developers.xsolla.com/api/pay-station/token/create-token/)

## 1. Install

```bash
npm install --save @xsolla/pay-station-sdk
```

## 2. Initialize the SDK

```ts
import { headlessCheckout } from '@xsolla/pay-station-sdk';

await headlessCheckout.init({
  sandbox: true,          // false in production
  // language: 'en',      // must match the token's settings.language
});
```

## 3. Get a payment token

The token is a **Pay Station access token** — encrypted user + project + order data that
authorizes the payment session. Generate it **on your backend** (it needs the secret API
key); never mint it in frontend code.

- Endpoint: `POST` Create token (`merchant_id` path param, **basic auth**
  `XSOLLA_MERCHANT_ID:XSOLLA_PROJECT_API_KEY` Base64-encoded).
- The call has no `project_id` path param → pass `settings.project_id` in the body and use a
  company-wide API key.
- Default lifetime **24h**; regenerate (ideally in the background) rather than reuse a stale
  one.

Minimal body shape (verify current fields via the MCP):

```jsonc
{
  "settings": {
    "project_id": 000000,
    "currency": "USD",
    "language": "en",
    "ui": { "size": "medium" }
  },
  "user": {
    "id":    { "value": "<stable user id>" },   // required
    "email": { "value": "user@example.com" }     // recommended (anti-fraud, receipt)
  }
}
```

### Reuse the catalog order token

If you arrived here from `catalog-design`'s purchase flow, the **"create order" call
already returned a payment `token`** alongside `order_id`. Reuse that token directly — do
**not** mint a second one. Generating a standalone token (above) is only for flows that
don't create a catalog order first. This catalog→checkout handoff is the seam most likely to
break "on the first try," so confirm which token you're holding.

## 4. Set the token on the SDK

```ts
await headlessCheckout.setToken(accessToken);
```

## Notes

- **Localization:** pass the same `language` to `headlessCheckout.init()` *and* the token's
  `settings.language`. Supported languages:
  <https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/references/supported-languages/>.
  Japanese IPs must be served a Japanese UI regardless (legal requirement).
- **Attribution:** to attribute the sale, put `tracking_id` in `user.tracking_id.value` of
  the token before `setToken` — it can't be passed as an SDK parameter.
- The token alone could open the **hosted** UI at `secure.xsolla.com/paystation4`. Headless
  Checkout instead consumes it via `setToken` and renders your own components. Next:
  `payment-methods.md`.

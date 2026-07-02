# Headless Checkout Documentation

## Purpose
Navigation guide for the Xsolla Pay Station SDK (Headless Checkout) knowledge base. Use this skill to identify which source to load for the current task — load only what's needed, not everything at once.

---

## What is Headless Checkout

A fully customizable payment acceptance solution based on headless architecture. The client controls the entire UI; payments are processed through Xsolla without using the standard Pay Station. The JavaScript SDK loads a hidden `0px iframe` with a Core Library that isolates all sensitive data (tokens, card details). Client code communicates with it only via `public postMessage`. Card input fields are also isolated in iframes — the client has no direct access to their values.

**Install:** `npm install --save @xsolla/pay-station-sdk`

---

## Primary SDK reference (README)
`https://raw.githubusercontent.com/xsolla/pay-station-sdk/refs/heads/main/README.md`
Load when: full API reference, complete component list, events table, or general SDK understanding needed.

---

## General integration flow

```
1. headlessCheckout.init({ sandbox, isWebView, theme, language })
2. headlessCheckout.setToken(accessToken)
3. form.init({ paymentMethodId, returnUrl })  +  subscribe to onNextAction
4. Render components in HTML
5. form.activate()  →  user fills form  →  form.submit()
6. Handle NextAction:
   show_fields | show_errors | redirect | 3DS |
   show_qr_code | show_mobile_payment_screen | check_status | hide_form | special_button
```

> Only one form can exist on a page at a time. `psdk-legal` and `psdk-total` are **required** on every page by contract.

---

## Components reference

Full table: `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/references/sdk-components/index.md`

| Component | Secure | Notes |
|-----------|--------|-------|
| `psdk-payment-methods` | | List of available payment methods |
| `psdk-saved-methods` | | List of saved methods; supports `delete-mode="true"` |
| `psdk-payment-form` | | Auto-renders all required form fields |
| `psdk-payment-form-messages` | | System messages during payment |
| `psdk-submit-button` | | Purchase button; contains embedded `psdk-apple-pay` |
| `psdk-default-submit-button` | | Purchase button without Apple Pay logic |
| `psdk-text` | ✅ | Additional data input (email, ZIP, etc.) |
| `psdk-card-number` | ✅ | Card number input |
| `psdk-phone` | ✅ | Phone number input |
| `psdk-google-pay-button` | ✅ | Google Pay button |
| `psdk-apple-pay` | ✅ | Apple Pay button (embedded in `psdk-submit-button`) |
| `psdk-qr-code` | ✅ | QR code display |
| `psdk-3ds` | | 3-D Secure verification via WebSocket |
| `psdk-redirect` | | Handles GET/POST redirects automatically |
| `psdk-status` | | Payment status display |
| `psdk-finance-details` | | Purchase details |
| `psdk-total` | | **Required.** Total purchase amount |
| `psdk-legal` | | **Required** (or use all 5 sub-components) |
| `psdk-select` | | Dropdown (e.g., installments, country) |
| `psdk-checkbox` | | Checkbox (e.g., save card) |
| `psdk-coupon` | | Coupon input with apply/remove/discount display |
| `psdk-user-balance` | | User virtual balance display |
| `psdk-secure-connection` | | Xsolla logo + secure connection text |

---

## Official documentation pages

All readable via `web_fetch` with `/index.md` suffix.

### Integration guide

| Topic | URL | Load when |
|-------|-----|-----------|
| Overview | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/index.md` | General concept explanation needed |
| Get started | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/integration-guide/get-started/index.md` | Integration flow overview needed |
| Install SDK | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/integration-guide/install-sdk/index.md` | npm install, `init()`, `setToken()` |
| Integrate on app side | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/integration-guide/integrate-on-app-side/index.md` | Basic form setup, mandatory components, `check_status` |
| Test in sandbox | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/integration-guide/test-payments/index.md` | Sandbox mode, test cards, transaction registry |
| Go live | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/integration-guide/go-live/index.md` | Licensing agreement, real payment testing, refunds |

### Payment methods

| Topic | URL | Load when |
|-------|-----|-----------|
| Available payment methods | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/payment-methods/available-payment-methods/index.md` | `psdk-payment-methods`, `selectionChange`, SDK methods |
| Saved methods | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/payment-methods/pay-with-saved-methods/index.md` | `psdk-saved-methods`, `savedMethodSelected`, `paymentWithSavedMethod` |
| Bank cards | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/payment-methods/bank-cards/index.md` | `show_fields`, dynamic fields, 3DS via acquirer or MPI |
| E-wallets (redirect) | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/payment-methods/e-wallet/index.md` | PayPal, Klarna, Skrill — redirect flow |
| Google Pay | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/payment-methods/google-pay/index.md` | `special_button` NextAction, one-click, `isGooglePayInstantFlowEnabled` |
| Apple Pay | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/payment-methods/apple-pay/index.md` | `psdk-apple-pay`, domain setup, one-click, `isApplePayInstantFlowEnabled` |
| QR code | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/payment-methods/qr-code/index.md` | `show_qr_code` NextAction, WeChat Pay, Alipay |
| Mobile payments | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/payment-methods/mobile-payment/index.md` | `show_mobile_payment_screen` NextAction, carrier billing |

### References

| Topic | URL | Load when |
|-------|-----|-----------|
| SDK components | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/references/sdk-components/index.md` | Full component table with secure flags |
| Payment method data | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/references/payment-method-data/index.md` | `getRegularMethods`, `getQuickMethods`, `getSavedMethods` |
| Errors | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/references/errors/index.md` | `show_errors` NextAction handling |
| Styles | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/references/styles/index.md` | `dist/style.css`, `setSecureComponentStyles()` |
| Supported languages | `https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/references/supported-languages/index.md` | Localization, language codes, Japanese IP rule |

---

## Code examples (GitHub)

All readable via `web_fetch` on `raw.githubusercontent.com`.

### URL
`https://raw.githubusercontent.com/xsolla/pay-station-sdk/refs/heads/main/examples/{Example}/{File}`

### Examples index

| Example | Files | Load when |
|---------|-------|-----------|
| `select-method` | `index.html` | Starting point for any integration; display payment methods list |
| `events` | `index.html` | Custom UI without `psdk-*` components; raw `onCoreEvent` / `events.send` API |
| `credit-card` | `index.html`, `init-payment-flow.js` | Card payments; all NextAction branches; 3DS; dynamic fields by type; `cardBinCountryChanged` |
| `paypal` | `index.html` | Basic redirect flow; `isMandatory` fields filter; URL builder |
| `paypal-external-page` | `index.html`, `return.html`, `status.html` | Redirect in popup (`window.open`); form stays open in background; `postMessage` bridge |
| `paypal-custom-status` | `index.html`, `return.html` | Custom status UI via `headlessCheckout.getStatus()` instead of `psdk-status` |
| `sdk-payment-methods` | `index.html` | Generic redirect template (Barzahlen, Naver, Venmo, etc.); includes `psdk-payment-form-messages` |
| `google-pay` | `index.html` | `special_button` NextAction; `GooglePayButtonComponent`; `show_errors` handling |
| `apple-pay` | `index.html` | Apple Pay lifecycle events; `hide_form` NextAction; fullscreen QR iframe |
| `qr-code` | `index.html` | `show_qr_code` NextAction; `QrCodeComponent` inline |
| `mobile-payment` | `index.html` | `show_mobile_payment_screen` NextAction; waiting screen with status button |
| `save-payment-method` | `index.html` | `save-method-mode="true"`; `form.init({ savePaymentMethod: true })` |
| `saved-methods` | `index.html` | `psdk-saved-methods`; `delete-mode="true"`; `deletedSavedMethodStatus` event |
| `payment-via-saved-method` | `index.html` | `form.init({ paymentWithSavedMethod: true, savedMethodId })`; `TotalComponent` |
| `changing-country` | `index.html` | `psdk-select type="country"`; `userCountryChanged` event |
| `unsupported-country` | `index.html` | `show_errors` NextAction with error code + message display |
| `default-styles` | `index.html` | `dist/style.css` + `theme: 'default'` in `init()` |
| `secure-component-styles` | `index.html` | Two-level styling: wrapper CSS + `setSecureComponentStyles()` string into iframe |
| `return` | `return.html` | Universal return page; token from `?token=` URL param; `psdk-status` auto-loads |

---

## Quick task → source mapping

| Task | Load |
|------|------|
| Starting a new integration | `select-method/index.html` |
| Bank card payment with 3DS | `credit-card/index.html` + `init-payment-flow.js` + docs: bank-cards |
| PayPal / e-wallet redirect | `paypal/index.html` + docs: e-wallet |
| PayPal in popup (form stays open) | `paypal-external-page` (all 3 files) |
| Custom payment status page | `paypal-custom-status` (both files) |
| Google Pay | `google-pay/index.html` + docs: google-pay |
| Apple Pay | `apple-pay/index.html` + docs: apple-pay |
| Alipay / WeChat QR code | `qr-code/index.html` + docs: qr-code |
| Carrier billing / mobile payment | `mobile-payment/index.html` + docs: mobile-payment |
| Barzahlen / Naver / Venmo | `sdk-payment-methods/index.html` |
| Save a payment method | `save-payment-method/index.html` |
| List / delete saved methods | `saved-methods/index.html` |
| Pay with saved method (one-click) | `payment-via-saved-method/index.html` + docs: saved-methods |
| Country selector | `changing-country/index.html` |
| Server-side validation errors | `unsupported-country/index.html` + docs: errors |
| Custom UI without SDK components | `events/index.html` + README (events table) |
| Style secure fields (card input) | `secure-component-styles/index.html` + docs: styles |
| Default styles | `default-styles/index.html` + docs: styles |
| Return page after redirect | `return.html` |
| Full API reference | README |
| All components with attributes | docs: sdk-components |
| `getRegularMethods` / `getQuickMethods` | docs: payment-method-data |
| Sandbox testing | docs: test-payments |
| Go live / licensing | docs: go-live |
| Localization / language codes | docs: supported-languages |

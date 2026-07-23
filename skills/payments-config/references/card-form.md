# Credit card form + 3-D Secure

Build the bank-card payment form, handle methods that need extra fields, and clear 3-D
Secure. Verify component tags / event payloads via the Xsolla MCP before coding.

Docs: [Bank cards](https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/payment-methods/bank-cards/) ·
[SDK components](https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/references/sdk-components/) ·
[Test cards](https://developers.xsolla.com/dev-resources/testing/test-cards/)

## 1. Initialize the form

```ts
const form = await headlessCheckout.form.init({
  paymentMethodId: 1380,                 // bank card (from the method list)
  returnUrl: 'https://example.com/return-page.html',  // where 3DS/redirect returns the user
});
```

`returnUrl` must be a real page in your app that re-mounts the SDK and shows status — it's
where the user lands after an external 3DS or redirect. A `isFormAutoSubmitted: true`
response means no input was needed (e.g. QR methods) and the step was skipped.

## 2. Mandatory + form components

```html
<psdk-legal></psdk-legal>     <!-- REQUIRED (or its sub-parts) -->
<psdk-total></psdk-total>     <!-- REQUIRED -->

<psdk-payment-form></psdk-payment-form>   <!-- built-in: all card fields -->
<psdk-submit-button text="Pay"></psdk-submit-button>
```

`psdk-payment-form` renders the full card form for you. Use `psdk-default-submit-button` if
you do **not** want the embedded Apple Pay logic; `psdk-submit-button` includes it.

### Hand-built fields (instead of `psdk-payment-form`)

Secured field components for a custom layout: `psdk-card-number`, `psdk-text` (cardholder /
extra fields), `psdk-phone`, `psdk-select` (e.g. installments), `psdk-checkbox` (e.g. "save
card"). "Secured" components isolate sensitive input — style them per the
[styles reference](https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/references/styles/).

## 3. Additional fields — `show_fields`

Some methods/countries need extra data (e.g. Brazilian cards need a cardholder name / tax
ID). Subscribe and render the fields the SDK asks for:

```ts
headlessCheckout.form.onNextAction((nextAction) => {
  switch (nextAction.type) {
    case 'show_fields':
      // nextAction.data.fields → build inputs (card_number → psdk-card-number,
      // phone → psdk-phone, select → psdk-select, check → psdk-checkbox, else psdk-text)
      // nextAction.data.submitButtonText → relabel the button (e.g. "Continue")
      break;
  }
});
```

## 4. 3-D Secure

Subscribe to `onNextAction` — the flow depends on the user's bank:

- **Acquirer built-in (redirect):** a `redirect` action. Build the URL from
  `redirectAction.data.redirect.redirectUrl` + `.data` params and navigate there; the user
  returns to `returnUrl`.
- **External MPI (challenge):** a `3DS` action. Set a flag, stash
  `nextAction.data.data`, and render:

```html
<psdk-3ds [attr.data-challenge]="challenge" text="Continue"></psdk-3ds>
```

```ts
headlessCheckout.form.onNextAction((nextAction) => {
  switch (nextAction.type) {
    case 'redirect': handleRedirect(nextAction); break;       // acquirer 3DS / e-wallets
    case '3DS':      showChallenge(nextAction.data.data); break; // MPI challenge
  }
});
```

The `3DS` event fires only for the challenge flow (frictionless needs no UI). Under a strict
CSP, set `is_three_ds_independent_windows` in the token so 3DS opens in its own window.

## 5. Test cards (sandbox)

Full list: <https://developers.xsolla.com/dev-resources/testing/test-cards/>. Examples:

| Purpose | Card | Exp | CVV |
|---------|------|-----|-----|
| 3DS challenge (acquirer) | `4111 1111 1111 1152` | 12/40 | any 3 |
| 3DS frictionless (MPI) | `4026 5100 0000 0000` | 12/40 | any 3 |
| 3DS challenge (MPI) | `4423 6100 0000 0007` | 12/40 | any 3 |

The list also includes cards that simulate declines — test at least one success, one
decline, and one 3DS challenge.

## Related

- E-wallets with redirect (PayPal, Klarna, Skrill) reuse the same `redirect` action →
  `payment-methods.md` and the [e-wallet docs](https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/payment-methods/e-wallet/).
- Apple Pay (`psdk-apple-pay`) / Google Pay (`psdk-google-pay-button`) are quick methods;
  the `psdk-submit-button` embeds Apple Pay. Full wallet setup (certificates, instant flow)
  is a later-phase topic.

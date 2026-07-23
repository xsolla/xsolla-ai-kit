# Payment method list component

Render the list of methods available to the user and capture their choice. Two approaches:
the ready-made component, or SDK methods if you build your own list UI.

Docs: [Receiving payment method data](https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/references/payment-method-data/) ·
[PayRank](https://developers.xsolla.com/payment-ui-and-flow/payment-methods/how-to-manage-top-payment-methods/)

## Option A — `psdk-payment-methods` component

```html
<psdk-payment-methods country="US"></psdk-payment-methods>
```

```ts
const paymentMethods = document.querySelector('psdk-payment-methods');
paymentMethods?.addEventListener('selectionChange', (event) => {
  const { paymentMethodId } = event.detail;   // pass this to form.init (see card-form.md)
});
```

## Option B — SDK methods (custom list UI)

| Method | Returns |
|--------|---------|
| `headlessCheckout.getRegularMethods()` | regular methods (cards, e-wallets, …) |
| `headlessCheckout.getQuickMethods()` | quick methods (Apple Pay, Google Pay) |
| `headlessCheckout.getSavedMethods()` | the user's previously saved methods |

```ts
const methods = await headlessCheckout.getRegularMethods();
// render your own list, then call form.init with the chosen paymentMethodId
```

## Ordering — PayRank

The default order of methods is set by **PayRank**, which ranks by popularity in the user's
country and their prior usage. Adjust it per-project in Publisher Account under
**Payments > PayRank settings** (choose country → drag the top 4 → optionally **Pin** →
**Save**; **Reset PayRank order** returns to automatic). Limit which methods appear at all
under **Payments > Payment methods**.

## Choice-presentation approaches

Depending on the storefront you can present methods as:

- **Full list** up front (`psdk-payment-methods`) — simplest, lets the user scan options.
- **Quick-pay first** — surface Apple Pay / Google Pay buttons (`getQuickMethods`) above a
  "more methods" link to the full list. See `card-form.md` for the wallet buttons.
- **Saved methods first** — show `psdk-saved-methods` for returning users, falling back to
  the full list. Returning-user flow uses `form.init({ paymentWithSavedMethod: true,
  savedMethodId, paymentMethodId })`.
- **Standalone single method** — skip the list and `form.init` a fixed `paymentMethodId`
  directly (e.g. a card-only checkout).

## Notes

- You **can't initialize multiple methods on one page**. The list captures the choice; the
  form (`card-form.md`) initializes exactly one method at a time.
- Apple Pay is hidden on devices that don't support it regardless of settings.
- Method IDs are stable integers (e.g. bank card `1380`, PayPal `24`, Apple Pay `3175` in
  doc examples) — but confirm the IDs for a given project via `getRegularMethods` rather
  than hardcoding.

# Payment Methods List

Guide for an AI agent. Goal: let the user pick a payment method before `form.init()`.

**Prerequisite:** `initialization` completed — SDK installed, `init()` + `setToken()` work.

---

## Choose Integration Approach

```
Need full control over layout, icons, "show more", inline expand?
└── Custom UI via SDK API (headless-checkout-demo pattern)

Want fastest result with built-in search?
└── psdk-payment-methods component (select-method example)
```

| Approach                    | Best for                                   | Trade-off                   |
|-----------------------------|--------------------------------------------|-----------------------------|
| **`psdk-payment-methods`**  | MVP, standard list + search                | Fixed UI                    |
| **SDK API + custom markup** | Branded checkout, accordion, quick methods | More code; full flexibility |

---

## SDK Data Model

Three API methods — understand before building UI:

| Method                                               | Returns                                                 | Includes                                                |
|------------------------------------------------------|---------------------------------------------------------|---------------------------------------------------------|
| `getRegularMethods({ country?, isSaveMethodMode? })` | `PaymentMethod[]`                                       | Cards, PayPal, wallets, etc. **Excludes** quick methods |
| `getQuickMethods(country?)`                          | `PaymentMethod[]`                                       | Apple Pay, Google Pay                                   |
| `getCombinedPaymentMethods(country?)`                | `{ paymentMethods: { quick, remained }, savedMethods }` | All groups + saved methods                              |

`PaymentMethod` fields used in UI: `id`, `name`, `iconName`, `recommended`, `rank`.

**Load order:** always `await headlessCheckout.init()` → `await setToken()` **before** fetching methods.
`psdk-payment-methods` waits for init internally; API calls fail without token.

---

## Option A: `psdk-payment-methods` Component

Reference: [select-method example](https://github.com/xsolla/pay-station-sdk/blob/main/examples/select-method/index.md),
`headless-sdk-testing` route `/methods`.

```html

<psdk-payment-methods
        country="US"
        search-placeholder="Search payment methods"
        not-found="No methods found"
></psdk-payment-methods>
```

**Attributes:**

| Attribute                 | Purpose                                                                    |
|---------------------------|----------------------------------------------------------------------------|
| `country`                 | ISO country code — filters available methods. Changing it reloads the list |
| `search-placeholder`      | Search input placeholder                                                   |
| `not-found`               | Text when list is empty                                                    |
| `skipPaymentMethodsCount` | Skip first N methods (e.g. hide top recommendations)                       |
| `save-method-mode`        | `"true"` — show only methods that support saving (card vault flow)         |

**Event — method selected:**

```typescript
const el = document.querySelector('psdk-payment-methods');
el?.addEventListener('selectionChange', (event) => {
    const {paymentMethodId} = event.detail; // string from attribute
    onMethodSelected(Number(paymentMethodId));
});
```

Event bubbles (`composed: true`) — can listen on `window` (see `save-payment-method` example).

**Styling:** component ships default styles. Override via CSS targeting `.payment-methods`, `.payment-method` inside the
shadow host, or use API approach for full control.

---

## Option B: Custom UI via API

Reference: [headless-checkout-demo](https://github.com/xsolla/headless-checkout-demo) — `src/sdk/payment-methods`,
`src/pages/store-page/ui/payment-methods`.

```typescript
// Merge quick + regular — both omit Apple/Google Pay alone
const [quick, regular] = await Promise.all([
    headlessCheckout.getQuickMethods(country),
    headlessCheckout.getRegularMethods({country}),
]);
const allMethods = [...quick, ...regular];
```

**Demo UX:** show first N methods + "More", accordion expand with inline form, reset form on switch, filter by allowed
IDs, skeleton while loading.

---

## Country Handling

Available methods depend on country. Two ways to set it:

1. `psdk-payment-methods country="DE"` attribute
2. `getRegularMethods({ country: 'DE' })` / `getQuickMethods('DE')`

**Dynamic country change** (user picks country):

```html

<psdk-select type="country"></psdk-select>
```

```typescript
document.querySelector('psdk-select')?.addEventListener('userCountryChanged', (e) => {
    const country = e.detail.country;
    document.querySelector('psdk-payment-methods')?.setAttribute('country', country);
    // or re-fetch via API for custom UI
});
```

See [changing-country](https://raw.githubusercontent.com/xsolla/pay-station-sdk/refs/heads/main/examples/changing-country/index.html)
and [unsupported-country](https://raw.githubusercontent.com/xsolla/pay-station-sdk/refs/heads/main/examples/unsupported-country/index.html)
examples.

---

## After Selection: Hand Off to Payment Form

Selecting a method is step 1. Step 2 is `form.init()` — only **one form per page**.

```typescript
async function onMethodSelected(paymentMethodId: number) {
    // Hide methods list or collapse to selected method (demo pattern)
    await headlessCheckout.form.init({
        paymentMethodId,
        returnUrl: 'https://yoursite.com/payment/return',
        country: 'US', // optional, if not set via psdk-payment-methods
    });

    headlessCheckout.form.onNextAction((action) => { /* show_fields, redirect, ... */
    });
}
```

**Save-card flow:** use `save-method-mode="true"` on list + `form.init({ savePaymentMethod: true })`.
Reference: [save-payment-method example](https://raw.githubusercontent.com/xsolla/pay-station-sdk/refs/heads/main/examples/save-payment-method/index.html).

**Skip selection when method is known:** hardcode `paymentMethodId` (e.g. `1380` for cards in sandbox). Used in
`credit-card`, `paypal` examples — valid when checkout has a single method.

---

## Sandbox Method IDs

Common IDs from demo (vary by project/country): card `1380`, PayPal `24`, Apple Pay `3175`, Google Pay `3431`, Venmo
`3636`. Log `getRegularMethods()` to discover methods for the partner's project.

---

## Anti-Patterns

1. **Do not** call `getRegularMethods` before `setToken()` — empty list or error.
2. **Do not** expect Apple Pay / Google Pay in `psdk-payment-methods` — fetch `getQuickMethods` separately.
3. **Do not** call `form.init()` twice without understanding — only one active form per page.
4. **Do not** forget to remove/replace UI on `selectionChange` — stale listeners cause double init (demo resets form on
   switch).

---

## Checklist

- [ ] `init()` + `setToken()` before loading methods
- [ ] Component or custom API approach chosen; quick methods included if needed
- [ ] Country set; `selectionChange` / click → `form.init({ paymentMethodId })`
- [ ] One active form; reset on method switch; list renders correctly

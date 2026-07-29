# Payment Methods List

Guide for an AI agent. Goal: let the user pick a payment method before `form.init()`.

**Prerequisite:** `initialization` completed — SDK installed, `init()` + `setToken()` work.

> **Show saved methods first.** If the user already has saved payment methods, present *those* as the
> first step (faster, higher conversion) and offer this regular list only as "pay another way." See
> `saved-methods`; come back here for the fallback selector.

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
| `getRegularMethods({ country? })`                    | `PaymentMethod[]`                                       | Cards, PayPal, wallets, etc. **Excludes** quick methods |
| `getQuickMethods(country?)`                          | `PaymentMethod[]`                                       | Apple Pay, Google Pay                                   |
| `getCombinedPaymentMethods(country?)`                | `{ paymentMethods: { quick, remained }, savedMethods }` | All groups + saved methods                              |

`PaymentMethod` fields used in UI: `id`, `name`, `iconName`, `recommended`, `rank`.

**Load order:** always `await headlessCheckout.init()` → `await setToken()` **before** fetching methods.
`psdk-payment-methods` waits for init internally; API calls fail without token.

---

## Layout Patterns (UX)

Headless Checkout ships **no layout** for the method list — you decide how methods are presented.
Because the SDK renders **only one form at a time**, every pattern is "pick a method → its form
appears." Pick by how many methods you have and how integrated it should feel. **For the first
integration, start with Pattern 1** (simplest, hardest to get wrong); switch later on request.

| # | Pattern              | How it behaves                                                                                          | Switch method | Best for                          | Seen on |
|---|----------------------|--------------------------------------------------------------------------------------------------------|---------------|-----------------------------------|---------|
| 1 | **List / tile grid** | All methods as a list or tiles; tapping one opens its form (replacing the list).                        | Go **back** to the list | Any count; **recommended to start** | Pay Station 3 |
| 2 | **Accordion**        | Tapping a method expands it in place and shows its form inline; the other methods stay visible.         | Pick another right away | Short lists, branded checkout     | Headless Checkout demo |
| 3 | **Tabs + form below**| Methods as tabs with the form under them; fits only ~3–4, so add a **"More methods"** tab that opens a full list (Pattern 1). First tab's form can render pre-selected. | Tap another tab | Few headline methods + long tail  | Pay Station 4 |

**Back navigation.** Patterns 1 and 3-more nearly always need a designed way for the user to
return to the previous step — to pick another method or retry after a failure. This is a
**whole-checkout** concern, not the selector's: depending on the store, the browser's built-in
page navigation may be enough, or you build your own / reuse the store's navigation.

**Quick-pay wallets (Apple Pay / Google Pay).** These are *quick methods* (`getQuickMethods`),
but the SDK still can't show several forms at once — so a wallet is really "select this method →
its form." Present each as a **branded button** that leads to the wallet's form:

- Pattern 1 → branded buttons **above** the tile list.
- Pattern 2 → at the **top of the accordion**.
- Pattern 3 → branded buttons **above the tabs**; tapping opens the form (with the real pay
  button) under the tabs.

Wallet mechanics live in `google-pay` / `apple-pay`.

**Icons are mandatory.** Always render each method's payment-system icon (`PaymentMethod.iconName`)
— the **icon takes priority over the name** for fast recognition. Building the list yourself?
See **Method icons in custom UI** (Option B) for the CDN path (the `brand-logos/` gotcha).

### View the patterns live (for the developer / agent)

Open the Buy button, then **wait ~5s for the token to generate** before the methods appear
(especially PS3):

| Pattern | URL                                                                                                   |
|---------|-------------------------------------------------------------------------------------------------------|
| 1 (variant) | https://livedemo.xsolla.com/paystation — click Buy, and **choose the virtual-currency purchase** to reach the methods page |
| 2       | https://headless-checkout-demo-react.web.app/start-page                                                |
| 3       | https://livedemo.xsolla.com/pay-station — click Buy                                                    |

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

### Method icons in custom UI

`psdk-payment-methods` renders icons for you; building the list yourself, resolve
`PaymentMethod.iconName` against the CDN. Base:
`https://cdn.xsolla.net/headless-checkout-prod/assets/icons`

- **Brand logo:** `<base>/brand-logos/<iconName>` (`iconName` includes the `.svg`).
- **Fallback** (no `iconName`, or the logo 404s): `<base>/default-payment-icons/default.svg`.

The SVGs are served `image/svg+xml` with open CORS, so a normal image element loads them: point
it at the brand logo, swap to `default.svg` on error, hide only if that fails too — every method
then shows something. If you need to **recolor/resize** the icon, fetch the SVG markup and inline
it instead.

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

**Saving / reusing a method:** the user saves a method by ticking the save checkbox during a normal
payment, and reuses it next time. See `saved-methods`.

**Skip selection when method is known:** hardcode `paymentMethodId` (e.g. `1380` for cards in sandbox). Used in
`credit-card`, `paypal` examples — valid when checkout has a single method.

---

## Sandbox Method IDs

Common IDs from demo (vary by project/country): card `1380`, PayPal `24`, Apple Pay `3175`, Google Pay `3431`, Venmo
`3636`. Log `getRegularMethods()` to discover methods for the store’s project.

---

## Anti-Patterns

1. **Do not** call `getRegularMethods` before `setToken()` — empty list or error.
2. **Do not** expect Apple Pay / Google Pay in `psdk-payment-methods` — fetch `getQuickMethods` separately.
3. **Do not** call `form.init()` twice without understanding — only one active form per page.
4. **Do not** forget to remove/replace UI on `selectionChange` — stale listeners cause double init (demo resets form on
   switch).
5. **Do not** try to render several method forms at once — the SDK shows one form at a time; wallets are branded
   buttons that open their form (see Layout Patterns).
6. **Do not** list methods by name only — always show the icon; it is the primary recognizer.
7. **Do not** ship a selector with no way back — design the return-to-list / retry navigation.

---

## Checklist

- [ ] `init()` + `setToken()` before loading methods
- [ ] Component or custom API approach chosen; quick methods included if needed
- [ ] Layout pattern chosen (start with Pattern 1); method icons shown; wallets as branded buttons
- [ ] Back / retry navigation designed (return to the method list)
- [ ] Country set; `selectionChange` / click → `form.init({ paymentMethodId })`
- [ ] One active form; reset on method switch; list renders correctly

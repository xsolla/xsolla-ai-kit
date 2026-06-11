# Credit Card Form

Guide for an AI agent. The most complex Headless Checkout integration — dynamic fields, multi-step flows, two 3DS paths,
secure iframes.

**Prerequisites:** `initialization` + `payment-methods-list` (or hardcode `paymentMethodId: 1380` for sandbox cards).

---

## Required Page Structure

Every checkout page (by contract):

```html

<psdk-total></psdk-total>
<psdk-legal></psdk-legal>
```

Recommended: `psdk-payment-form-messages` for server messages. Optional: `psdk-finance-details`.

**Return page** (`returnUrl`) — user lands here after 3DS redirect. Must re-run `init()` + `setToken(tokenFromUrl)` +
render `psdk-status`.

---

## Step 1: Initialize Card Form

```typescript
const form = await headlessCheckout.form.init({
    paymentMethodId: 1380,           // sandbox card PID; use selectionChange id in production
    returnUrl: `${origin}/payment/return?token=${token}`,
    country: 'US',                   // optional; affects visible fields
    paymentMethodSettings: {
        useSingleExpirationDateField: true,  // single MM/YY field instead of month+year
    },
    overrideFormFields: {
        allowSubscription: {initialValue: '1'},  // pre-check save-card checkbox
    },
});

headlessCheckout.form.onNextAction(handleNextAction);
```

`form.init()` returns `{ fields, submitButtonText, isFormAutoSubmitted }`. Field set is **server-driven** — never
hardcode which fields exist; always read `form.fields` or react to `show_fields`.

---

## Step 2: Map Fields to Components

Server returns `Field[]` with `type`, `name`, `isMandatory`. Map each field:

| Field condition          | Component          | Attributes                 |
|--------------------------|--------------------|----------------------------|
| `name === 'card_number'` | `psdk-card-number` | `name`, `icon="true"`      |
| `name === 'phone'`       | `psdk-phone`       | `name`, `showFlags="true"` |
| `type === 'text'`        | `psdk-text`        | `name`                     |
| `type === 'select'`      | `psdk-select`      | `name`                     |
| `type === 'check'`       | `psdk-checkbox`    | `name`                     |
| `type === 'label'`       | **none — skip it** | —                          |

**Match on `type` explicitly — do NOT use a catch-all `else → psdk-text`.** The card
flow also returns `type: 'label'` fields (e.g. `description`, `termsAndConditions`)
that are **informational, not inputs**. Rendering a label as `psdk-text` tries to
mount a secure iframe with no server config and throws **`Could not load control
component config`**. Skip `label` fields — legal/terms text is already shown by
`psdk-legal`. Only map the input types above; ignore anything else.

**Short form**: fixed
`card_number`, `card_month`, `card_year`, `cvv`, `zip`, `allowSubscription` — only if present in `form.fields`. Filter:
`isMandatory === '1'` for minimal UI; all fields for BR/regional flows.

Then add `psdk-submit-button` and call **`form.activate()`**. `activate()` is
**mandatory, not optional** — it wires up the mounted secure fields and enables
submit. **Without it the form renders fine but clicking submit does nothing** (no
NextAction fires, no error) — a silent dead end that is easy to misread as "the SDK
is broken." Call it once, after the field components and the submit button are in
the DOM. The canonical `examples/credit-card/init-payment-flow.js` omits this call;
do not treat that example as complete on this point.

---

## Step 3: Wait for Secure Fields (Loading State)

Card fields load inside secure iframes. This step is **optional** — only for showing
a loading state while the iframes initialize.

```typescript
// Map + APPEND the field components to the DOM first (Step 2), THEN:
const mandatory = form.fields.filter(f => f.isMandatory === '1');
await headlessCheckout.form.setupAndAwaitFieldsLoading(mandatory);
// now reveal the form — see headless-sdk-testing /wait-fields-loading
```

**Order matters: the field components must already be mounted in the DOM before you
call this.** Calling `setupAndAwaitFieldsLoading` *before* rendering the components
(e.g. to "preload, then render") **never resolves** — the promise waits for iframes
that do not exist yet, so the form hangs on the loader forever with no error. If you
are not showing a loading state, you can skip this entirely and just render →
`activate()`. `psdk-payment-form` calls this internally. For custom UI — call
explicitly. Use `AbortSignal` when the user switches methods mid-load.

---

## Step 4: Handle NextActions (Critical)

Subscribe **before or right after** `form.init()`. Card flow uses these actions:

| Action         | Meaning                                                | Handler                                                                                                                |
|----------------|--------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| `show_fields`  | New/replacement fields (BR 2nd step, validation retry) | **Clear container**, set `form.fields = nextAction.data.fields`, re-render. Update button text from `submitButtonText` |
| `show_errors`  | Validation/server error                                | Display `nextAction.data.errors[0].message`                                                                            |
| `redirect`     | 3DS via acquirer / external MPI                        | Redirect to bank; use `psdk-redirect` or manual form submit                                                            |
| `3DS`          | MPI challenge flow                                     | Show `psdk-3ds` with `data-challenge={JSON.stringify(action.data.data)}` — payload is **nested** under `.data.data`   |
| `check_status` | Payment done                                           | Show `psdk-status`                                                                                                     |

On `show_fields`: **clear container** → `form.fields = nextAction.data.fields` → re-render → update `submitButtonText`.
See `credit-card/init-payment-flow.js`, `/card-second-step`.

**Quirk:** `show_errors` + `show_fields` may fire in sequence on failed submit. Use `AbortSignal` with
`setupAndAwaitFieldsLoading` if awaiting on each `show_fields`.

---

## Step 5: 3-D Secure (Two Paths)

Bank chooses verification type — handle **both**:

**`redirect`** — acquirer / external MPI. Prefer `psdk-redirect` with `data-redirect={JSON.stringify(redirect)}` —
handles GET/POST + new tab. If `isNewWindowRequired` — open only on user click. Full redirect mechanics (GET/POST + 414,
`isNewWindowRequired` / `isSameWindowRequired`, the new-tab gesture rule, return page) live in
[`redirect-flow.md`](redirect-flow.md) — the same `redirect` action also drives e-wallets / APMs and extra
verification, so it's documented once there. Refs: `/card` (step machine), `/card-3ds-custom-status` (popup +
`status_updated`).

**`3DS`** — MPI challenge: `psdk-3ds` + `data-challenge={JSON.stringify(action.data.data)}` (payload is **nested** in
`.data.data`, not `.data`). On `threeDsWindowClosed` → re-init form (`/card`). User returns via `returnUrl` →
`psdk-status`.

---

## Step 6: Secure Field Styling

Card inputs live in iframes — **two layers**:

1. **Wrapper CSS** — size/position of `psdk-card-number`, `psdk-text` host elements
2. **Iframe styles** — `setSecureComponentStyles(cssString)` **before** `setToken()`

Call `setSecureComponentStyles(css)` **before** `setToken()`. Ref: `secure-component-styles` example. Wrapper sizing on
`psdk-*` hosts; iframe styles via `setSecureComponentStyles`.

**Also:** `cardBinCountryChanged` on `psdk-card-number` (hide fields by BIN country); `psdk-payment-form` auto-creates
missing fields (watch console); reset form on method switch (
demo); [test cards](https://developers.xsolla.com/doc/pay-station/testing/test-cards/) for 3DS/success/decline.

---

## Testing (Sandbox)

Use these test cards in **sandbox mode** to confirm the integration works end-to-end. For all cards: **Exp. date
`12/40`**, **CVV2 any 3 digits**. Verifying these three cards is enough to confirm the integration is functional.

| Card number        | Flow                                          | Behavior                                                                          |
|--------------------|-----------------------------------------------|-----------------------------------------------------------------------------------|
| `4111111111111111` | Plain payment, **no 3DS**                     | Charges directly → `check_status` → `psdk-status` shows success                   |
| `4111111111111152` | 3DS — **acquirer's built-in mechanism**       | Redirects to the Xsolla verification page, then back to `returnUrl`               |
| `4423610000000007` | 3DS — **external MPI**                        | Redirects to the Xsolla verification page, then back to `returnUrl`               |

**3DS flow (last two cards):** the form triggers a `redirect` NextAction to the Xsolla verification page. The password
field is **pre-filled** — just click the confirmation button. After confirmation the user is redirected back to the
**return page** (`returnUrl`), where `init()` + `setToken(tokenFromUrl)` + `psdk-status` report the final status.

**Testing the `failed` status:** on the verification page, enter a **wrong password** (e.g. `123456`) instead of
confirming the pre-filled one. The payment fails and the return page reports the failed status.

---

## Anti-Patterns

1. **Do not** hardcode field list without checking `form.fields` — BR/JP cards need extra steps.
2. **Do not** append fields on `show_fields` — **clear and re-render** the container.
3. **Do not** skip `returnUrl` — 3DS redirect fails without it.
4. **Do not** auto-redirect when `isNewWindowRequired` — use button + `psdk-redirect`.
5. **Do not** style card inputs only with outer CSS — use `setSecureComponentStyles`.
6. **Do not** ignore `show_errors` — user sees silent failure.
7. **Do not** call `form.init()` twice on same page without cleanup.

---

## Checklist

- [ ] `psdk-total` + `psdk-legal`; `form.init` + all five NextActions handled
- [ ] `card_number` → `psdk-card-number`; `show_fields` clears + re-renders
- [ ] 3DS path (`psdk-redirect` / `psdk-3ds`); return page with `psdk-status`

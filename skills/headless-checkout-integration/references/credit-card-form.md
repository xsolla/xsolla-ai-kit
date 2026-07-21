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

**Render `psdk-payment-form-messages`** (see **Form Messages** below — it carries real
server text like the sandbox "no redirect" notice; render it *visibly*, not hidden).
Optional: `psdk-finance-details`.

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

`form.fields` is **already the visible set** (the SDK drops hidden `fix_*` / `signature`
fields) — render all of it, mapping **by `type`**. The one rule: **skip `type: 'label'`;
never fall through to a catch-all `else → psdk-text`** — a label has no secure config, so
`psdk-text` throws `Could not load control component config`, and a rendered
`termsAndConditions` is the "EULA on every step" bug. Labels are shown elsewhere: legal by
`psdk-legal`, status/info text (e.g. the sandbox "no redirect" notice) by
`psdk-payment-form-messages` (**Form Messages** below) — not as fields. Filtering to
`isMandatory === '1'` is an optional minimal-UI choice, not required.

Then add `psdk-submit-button` and call **`form.activate()`**. `activate()` is
**mandatory, not optional** — it wires up the mounted secure fields and enables
submit. **Without it the form renders fine but clicking submit does nothing** (no
NextAction fires, no error) — a silent dead end that is easy to misread as "the SDK
is broken." Call it once, after the field components and the submit button are in
the DOM. The canonical `examples/credit-card/init-payment-flow.js` omits this call;
do not treat that example as complete on this point.

---

## Step 3: Show a loader (there is no "loading" event)

**Trap:** `onNextAction` reports *outcomes*, not loading — the SDK gives you **no
"request in flight" event**. If you don't drive loaders yourself, the buyer stares at a blank
area during every round-trip. Two gaps:

- **Form fetch + field load** (`form.init`, and each `show_fields` step): show a loader from
  the moment you start until the fields are ready. Readiness = the
  **`setupAndAwaitFieldsLoading(fields)` promise resolving**. Hide the form area meanwhile and
  reveal on resolve (mount the fields behind the loader so they load while hidden).
- **Submit → next action:** `psdk-submit-button` shows its **own** in-button loader — leave
  that gap to it.

```typescript
// mount the field components FIRST (Step 2), then:
await headlessCheckout.form.setupAndAwaitFieldsLoading(tracked); // resolve → hide loader, reveal form
```

`psdk-payment-form` does this internally; render fields manually → you call it. **Mount the
components before calling, and pass only the ones you mounted as secure inputs** (never a
`label`/hidden field) — otherwise the promise **hangs forever** on an iframe that never
appears. (`activate()`, not this, enables submit — Step 2.) `AbortSignal` on method switch.

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
demo); [test cards](https://developers.xsolla.com/doc/pay-station/testing/test-cards/) for 3DS/success/decline. The
**"save this card" checkbox** is the server-driven `allowSave` field (present only for savable methods) — see
`saved-methods` for saving/reusing a method.

---

## Form Messages (server status / info text)

Some server responses carry a **`messages`** block — free-text status/info **not** in
`form.fields` and **not** a NextAction (e.g. sandbox: *"Unlike with real payment… no
redirect to the payment system"*). Surface it by mounting **`psdk-payment-form-messages`**
(it auto-subscribes to `formMessagesChanged` and renders the text — just mount it):

```html
<psdk-payment-form-messages></psdk-payment-form-messages>
```

**Render it visibly and keep it mounted through the whole form flow** — not `sr-only`, and
not only on step 1 (the message often arrives after the first submit). Hiding it is why a
step looks empty for no reason. Ref: `demo-install` → `.../checkout/form-container`.

---

## Testing (Sandbox) — you are NOT done until a real transaction lands on `psdk-status`

Rendering the form is **not** "done." "The form renders" / "it should work" does not count — drive an actual sandbox
payment and observe the terminal screen. Run **all three** cards below and report the result of each. For all cards:
**Exp. date `12/40`**, **CVV2 any 3 digits**.

| # | Card number        | Path exercised                          | Expected terminal state                                              |
|---|--------------------|-----------------------------------------|---------------------------------------------------------------------|
| 1 | `4111111111111111` | plain card, **no 3DS**                  | `check_status` → `psdk-status` shows **success**                    |
| 2 | `4111111111111152` | 3DS — acquirer's built-in mechanism     | `redirect` → Xsolla verify page → **return page** → success        |
| 3 | `4423610000000007` | 3DS — external MPI                      | `redirect` → Xsolla verify page → **return page** → success        |

**Card 1 alone does NOT prove the integration** — it skips `redirect` and the **return page** entirely, which is the
part most likely to be broken (wrong `returnUrl`, SDK not loaded on the return route, stripped query params). Cards 2
and 3 are **mandatory**.

**3DS flow (cards 2 & 3):** the form triggers a `redirect` to the Xsolla verify page
(`sandbox-secure.xsolla.com/pages/sandbox`); the password is **pre-filled** — just confirm. The user is then redirected
to the **return page** (`returnUrl`), where `init()` + `setToken(tokenFromUrl)` + `psdk-status` report the final status.
To test the **`failed`** status, enter a **wrong password** (e.g. `123456`) instead of confirming the pre-filled one.

**Driving it headlessly.** The card inputs live in cross-origin secure iframes, but Playwright/Puppeteer can drive them:

- Locate each input via `frameLocator('iframe[src*="text-input/<field>"]').locator('input')`.
- **Type with real key presses, not `fill()`.** `fill()` sets the value in one shot and the secure field's listeners
  never fire, so the field stays `INVALID` and **submit silently hangs** (no NextAction, no error). Use
  `pressSequentially(value)` / character-by-character `type()` so each keystroke registers and the field goes `VALID`.
- Then click the button inside `psdk-submit-button`.
- On the verify page: a **GDPR overlay** intercepts clicks — dismiss it first (`button.gdpr-accept-all-button`); the
  code is pre-filled, so click `#xps-submit-button` to confirm (or replace it with a wrong code for the `failed` path).
- Finally, assert the return page renders `psdk-status` with the expected terminal state and capture the screen.

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
- [ ] Map `form.fields` by `type`; **skip `label`** (no catch-all `else → psdk-text`) — labels are `psdk-legal` / form-messages, not inputs
- [ ] `psdk-payment-form-messages` rendered **visibly** + kept mounted (server status/info text)
- [ ] Loader on form fetch + each `show_fields` step (driven by `setupAndAwaitFieldsLoading`); submit gap left to the button
- [ ] 3DS path (`psdk-redirect` / `psdk-3ds`); return page with `psdk-status`

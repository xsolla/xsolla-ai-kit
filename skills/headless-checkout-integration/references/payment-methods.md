# Additional Payment Methods

Guide for an AI agent. Covers the payment methods **beyond the bank card**: redirect-based
systems (PayPal, e-wallets, APMs), **QR code**, and **mobile / carrier billing**. Each is
driven through the *same* `onNextAction` dispatcher you already wired for cards — only the
action the server emits differs.

**Prerequisites:** `credit-card-form` (`form.init()` + `onNextAction` working) and
`payment-status` (status rendering). **All redirect *mechanics* — the window strategies
(same-tab / new-tab / WebView), the iframe caveat, the `isNewWindowRequired` /
`isSameWindowRequired` flags, GET/POST + 414, the new-tab gesture, `returnUrl`, and the return
page — live in `redirect-flow`.** This doc covers *which* method emits *which* NextAction and
the method-specific handling, and does **not** repeat the redirect mechanics.

> **General form mechanics live in [`credit-card-form`](credit-card-form.md) and apply to every
> method** — field mapping by `type` (skip `label`), server `messages` via
> `psdk-payment-form-messages`, `setupAndAwaitFieldsLoading`, `form.activate()`. Read it first;
> this doc only adds the per-method NextActions.

---

## One dispatcher, many methods

Do **not** build a separate flow per payment method. You call `form.init({ paymentMethodId,
returnUrl })`, render the server-driven fields (as for cards), the user submits, and the
server tells you what to do next. The flow can change with the user's environment and the
project/payment settings, so **always react to the action** — never assume a method's shape.

> How the method list is **presented and selected** (layout patterns — list / accordion / tabs,
> method icons, wallet-button placement, back navigation) lives in `payment-methods-list`. This
> doc picks up *after* a method is chosen.

| Method family                         | Distinguishing NextAction         | Component to mount              |
|---------------------------------------|-----------------------------------|--------------------------------|
| Redirect PS (PayPal, e-wallets, APMs) | `redirect`                        | `psdk-redirect` (see `redirect-flow`) |
| QR code (Alipay, PIX, etc.)           | `show_qr_code`                    | `psdk-qr-code` (`QrCodeComponent`) |
| Mobile / carrier billing              | `show_mobile_payment_screen`      | `psdk-submit-button` (`SubmitButtonComponent`) |

All three still terminate on `check_status` → status view, exactly like the card flow.

---

## Sandbox can't exercise these flows — that's production

Only Card / PayPal / Google Pay / Apple Pay run their real UI in sandbox. Every other method collapses to one
generic flow: form → a step showing only the sandbox notice (*"…no redirect in sandbox mode"*) →
success. So a real QR, SMS/carrier charge, or cash voucher never appears in sandbox — verify
those **only in production**. In sandbox, drive **PayPal** (+ **Venmo**) to status: same shared
wiring QR/mobile/cash reuse, and it confirms `psdk-payment-form-messages`. Code their handlers to
spec (below); don't claim a sandbox pass for them.

---

## Redirect-based payment systems (PayPal and others)

Most alternative payment systems finish on an **external page**. Typical flow:

1. A form renders with a few fields (often `zip`, `email`; sometimes none) plus a **submit**
   button.
2. User submits.
3. The server responds with a `redirect` NextAction — the SDK sends the user to the
   provider's page, passing a **`returnUrl`** so the provider knows where to send them back.
4. User pays on the external page.
5. The provider redirects the user back to `returnUrl`.

**All the redirect mechanics live in `redirect-flow`** — the action shape (`redirectUrl`,
`data`, `method`, GET/POST + 414); the same-tab / new-tab / WebView window strategies and the
**iframe caveat**; the `isNewWindowRequired` / `isSameWindowRequired` server flags; the new-tab
gesture rule; `is_independent_windows` for WebView; and the return page. Do **not** re-implement
any of it — use `psdk-redirect` and obey the server flag. This section only covers what is
*method-specific*: how to test in sandbox.

### Sandbox test recipe — PayPal

Redirect methods are best exercised on **PayPal** in sandbox, and an AI agent can drive it:

- Leave the **Mock** field in the form **empty**.
- **Uncheck the "save this method" checkbox** — it routes to a one-time payment
  (`/checkoutnow`, plain email+password login). Left checked, PayPal goes into a billing
  agreement (`/agreements/approve`) with a **different page** your login steps won't match.
- On the PayPal login page use:
  - login: `sb-fjnsq14644046@business.example.com`
  - password: `MvUrho6?`
- Full guide:
  https://developers.xsolla.com/dev-resources/testing/sandbox-mode/test-paypal-in-sandbox/index.md

**Also drive Venmo** — same-window/APM, no external login, so it's the quickest confirm of the
shared dispatcher + `psdk-payment-form-messages`. PayPal + Venmo = what sandbox can verify.

---

## SDK payment methods (same-window-required systems)

A distinct group of payment systems — **Barzahlen, Naver, Venmo, Paytm, Alipay, PIX**, and
similar — **must open in the same top-level window** and cannot survive a new tab or an iframe.
You do **not** detect them yourself: the server marks their `redirect` action with
**`isSameWindowRequired`**, and `psdk-redirect` obeys it. The mechanics and the iframe
consequences are in `redirect-flow` ("Server-forced same-window methods"); only the
method-specific rules are below.

The SDK repo's **`sdk-payment-methods`** example handles this group — its handler is just the
same-window branch of a `redirect` (a bare `window.location.href`); prefer `psdk-redirect` in
real code so the same dispatcher also covers the new-tab group.

- **Switch on `nextAction.type`, never on the payment method id.** A single method can come back
  as `redirect`, `show_qr_code`, or a cash instruction depending on context — one dispatcher keyed
  on the action type covers them all.
- **`isWebView` matters.** `init({ isWebView })` is a required init flag; a WebView build needs the
  independent-window handling (`redirect-flow`), not a same-tab navigation.
- Example:
  https://raw.githubusercontent.com/xsolla/pay-station-sdk/refs/heads/main/examples/sdk-payment-methods/index.html

> **The full NextAction set** the dispatcher may receive: `check_status`, `show_fields`,
> `show_errors`, `show_init_form`, `redirect`, `3DS`, `special_button`, `show_qr_code`,
> `show_mobile_payment_screen`, `show_cash_payment_instruction`, `hide_form`, `status_updated`,
> `server_error`. Cards/3DS → `credit-card-form`; `redirect` → `redirect-flow`; status/
> `status_updated` → `payment-status`; `show_qr_code` / `show_mobile_payment_screen` below.

---

## QR code

Some methods (Alipay, PIX, …) ask the user to scan a QR code. The only difference from the
card flow is that you handle the **`show_qr_code`** NextAction and mount the dedicated
QR component.

```typescript
headlessCheckout.form.onNextAction((nextAction) => {
  if (nextAction.type === 'show_qr_code') {
    formElement.innerHTML = '';                       // clear the collected fields
    const qrCodeComponent = new PayStationSdk.QrCodeComponent();
    formElement.append(qrCodeComponent);              // <psdk-qr-code> renders the code
    const submitButtonText = nextAction.data.submitButtonText;
    renderSubmitButton(formElement, submitButtonText); // "I've paid" style button under the QR
  }
  // ... 'check_status' → mount psdk-status as usual
});
```

The submit button below the QR carries `nextAction.data.submitButtonText`; pressing it after
scanning takes the user to the status view.

Example: https://raw.githubusercontent.com/xsolla/pay-station-sdk/refs/heads/main/examples/qr-code/index.html

**Sandbox:** the real QR does **not** render in sandbox — the method collapses to the generic
sandbox flow (form → sandbox notice → success), so there's nothing to scan. This is by design,
not a setup bug. Verify the actual QR flow only in **production**.

---

## Mobile / carrier billing

The user enters a phone number (plus any other server-requested fields) and submits. The
carrier then sends an **SMS invoice** to that number, and the server emits
**`show_mobile_payment_screen`**.

```typescript
headlessCheckout.form.onNextAction((nextAction) => {
  if (nextAction.type === 'show_mobile_payment_screen') {
    formElement.innerHTML = '';
    const submitButtonText = nextAction.data.submitButtonText;
    // Show a message: "An invoice was sent by SMS to your number — pay it, then tap below."
    const submitButton = new PayStationSdk.SubmitButtonComponent();
    submitButton.setAttribute('text', submitButtonText);
    formElement.append(submitButton);                 // "Show payment status" button
  }
  // ... 'check_status' → mount psdk-status
});
```

On this screen you show the user that an invoice was sent and a **"Show payment status"**
button; after they pay the SMS invoice and tap it, they land on status, and the status flips
once the carrier confirms.

You may **skip** this intermediate screen and jump straight to the status view on
`show_mobile_payment_screen`. If you do, the **status page** must explain (for the
`processing` state only) that an invoice was sent by SMS to the entered number and to pay it —
that message is meaningless for `success`/`failed`, so gate it on `processing`.

Example: https://raw.githubusercontent.com/xsolla/pay-station-sdk/refs/heads/main/examples/mobile-payment/index.html

**Sandbox:** there is **no** real carrier/SMS flow in sandbox — the method collapses to the
generic sandbox flow (form → sandbox notice → success), no SMS is sent. Reaching `success` there
proves your wiring, **not** the mobile-billing flow itself; verify that only in **production**.

---

## Anti-patterns

1. **Do not** build a separate integration per payment method, and **do not switch on the payment
   method id** — one `form.init` + one `onNextAction` dispatcher that switches on
   `nextAction.type` handles cards, redirect PS, SDK/same-window PS, QR, and mobile.
2. **Do not** copy the `sdk-payment-methods` example's bare `window.location.href` as your redirect
   pattern — it is only the same-window branch; use `psdk-redirect` and let it read the flag.
3. **Do not** show the "invoice sent by SMS" message on `success`/`failed` — only on `processing`.

The redirect-specific anti-patterns (iframe + same-tab, new-tab gesture, honoring `method`,
WebView `is_independent_windows`, return page) live in `redirect-flow`.

---

## Quick reference

| Resource                     | Path / URL                                                                                     |
|------------------------------|------------------------------------------------------------------------------------------------|
| Redirect mechanics           | `references/redirect-flow.md`                                                                   |
| Status rendering             | `references/payment-status.md`                                                                  |
| SDK / same-window methods    | https://raw.githubusercontent.com/xsolla/pay-station-sdk/refs/heads/main/examples/sdk-payment-methods/index.html |
| QR code example              | https://raw.githubusercontent.com/xsolla/pay-station-sdk/refs/heads/main/examples/qr-code/index.html |
| Mobile payment example       | https://raw.githubusercontent.com/xsolla/pay-station-sdk/refs/heads/main/examples/mobile-payment/index.html |
| PayPal sandbox testing       | https://developers.xsolla.com/dev-resources/testing/sandbox-mode/test-paypal-in-sandbox/index.md |

---

## Checklist

- [ ] One `onNextAction` dispatcher, keyed on `nextAction.type` — never on the payment method id
- [ ] Redirect PS handled via `psdk-redirect` (window strategy, flags, iframe, WebView → `redirect-flow`)
- [ ] SDK / same-window methods (Venmo, Naver, Paytm, Alipay, PIX, Barzahlen…) covered by the same dispatcher
- [ ] `show_qr_code` handled with `QrCodeComponent` + submit button (`submitButtonText`) — real QR verified in **production**
- [ ] `show_mobile_payment_screen` handled (dedicated screen or jump to status with a `processing` message) — real flow in **production**
- [ ] Every method still terminates on `check_status` → `psdk-status`
- [ ] **Sandbox test = PayPal (+ Venmo)** driven to a terminal status; confirms the shared wiring + `psdk-payment-form-messages`. QR/mobile/cash real flows are **production-only**.

**Done?** Redirect internals → `redirect-flow`. Status display → `payment-status`. Go-live → `docs`.

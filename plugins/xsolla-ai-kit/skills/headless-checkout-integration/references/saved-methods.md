# Saved Methods

Guide for an AI agent. Covers **saved payment methods**: letting a user save a method while paying,
then showing and reusing it on the next checkout, plus managing (deleting) saved methods.

**Prerequisites:** `credit-card-form` (you need a working payment form to *save* a method and to
handle the NextActions when *paying* with one), `payment-methods-list` (the regular selector you fall
back to), and `payment-status` (terminal status). All of it still runs through the one
`form.init()` + `onNextAction` dispatcher.

---

## Why bother

Paying with a saved method is **faster** (no re-entering card data, often no redirect) and
**converts better**. So: **if the user has saved methods, show them as the *first* step** — instead
of the regular method list from `payment-methods-list` — while always keeping a
path back to the full payment methods list.

There are four parts: **(1) save** a method during payment, **(2) detect + show** saved methods,
**(3) pay** with one, **(4) manage** (delete / add).

---

## 1. Save a method during payment

This is the normal path: the user pays as usual, and the method is **saved automatically as part of
that payment** when the save checkbox is ticked — no separate step.

The "save this card" **checkbox is a server-driven form field** (`allowSave`) that the SDK includes
in `form.fields` **only for methods that support saving**. Render it like any other field — do not
hardcode it. If it is absent, the method can't be saved.

- To pre-tick / force it, pass `savePaymentMethod: true` to `form.init({ paymentMethodId, returnUrl,
  savePaymentMethod: true })`.
- After a **successful** payment with it ticked, the method is saved automatically. You can confirm
  from the `status_updated` action: `isSavePaymentMethodMode` and `savePaymentMethodStatus`
  (`'success'` / `'failed'`).

Example: `examples/save-payment-method/index.html`.

---

## 2. Detect and show saved methods (make them the first step)

**Detect** what the user already has:

```typescript
const saved = await headlessCheckout.getSavedMethods();               // SavedMethod[]
// or, in one call with the regular + quick lists:
const { paymentMethods, savedMethods } = await headlessCheckout.getCombinedPaymentMethods();
```

If `saved.length > 0`, render the saved list **first**; otherwise fall through to the normal
`payment-methods-list` selector. Keep a **"pay another way"** control that routes to that selector.

**Display** — component or custom UI:

- **Component:** `<psdk-saved-methods not-found="No saved methods"></psdk-saved-methods>` — renders the
  list itself (icon + name + expiry) and emits the events below.
- **Custom UI:** build from `getSavedMethods()`. Each `SavedMethod` has `id`, `pid`, `name`,
  `iconName`, `cardExpiryDate {month, year}`, `type`, `psName`. Show the **icon first** (same rule as
  the method list — see `payment-methods-list`), then name + expiry.

**Selection event** (`psdk-saved-methods` or your own click): `savedMethodSelected`, with
`detail = { paymentMethodId, savedMethodId, type }`. It bubbles (`composed: true`), so you can listen
on `window`.

Example: `examples/saved-methods/index.html`.

---

## 3. Pay with a saved method — still NextAction-driven

On `savedMethodSelected`, init the form in saved-method mode and handle actions **exactly like a
normal payment**:

```typescript
window.addEventListener('savedMethodSelected', async ({ detail }) => {
  await headlessCheckout.form.init({
    paymentMethodId: Number(detail.paymentMethodId),
    paymentWithSavedMethod: true,
    savedMethodId: Number(detail.savedMethodId),
    returnUrl,
  });
  headlessCheckout.form.onNextAction((action) => { /* same dispatcher as always */ });
});
```

**Paying with a saved method is NOT always one click.** Depending on the method, acquirer, amount,
and risk rules the server may still ask for **CVV re-entry** (`show_fields`), **3DS**
(`3DS` or `redirect`), or return `show_errors` before it reaches `check_status`. **Do not shortcut
straight to the status view** — run the full `onNextAction` chain (`credit-card-form`,
`redirect-flow`), then show status (`payment-status`).

Example: `examples/payment-via-saved-method/index.html`.

---

## 4. Manage saved methods (delete / add)

**Delete** — through the component's delete mode, not a bespoke API call:

```typescript
// toggle a trash button on each item
savedMethods.setAttribute('delete-mode', 'true');   // remove the attribute to leave delete mode
savedMethods.addEventListener('deletedSavedMethodStatus', ({ detail }) => {
  // detail.isDeleteSuccessful — the component already removed the row on success
});
```

Clicking the trash icon deletes via the SDK, fires `deletedSavedMethodStatus`
(`{ isDeleteSuccessful }`), and drops the row from the list. There is **no separate public delete
method** — the `psdk-saved-methods` component owns it.

**Add / "edit"** — there is no edit. Adding a method means running the **save flow again** (Part 1):
make another payment with the `allowSave` checkbox ticked.

---

## Sandbox testing — full round trip

Requires the card form from `credit-card-form`. Do the whole loop and report each step:

1. Pay with a sandbox **test card** and **tick the save checkbox** → complete the payment.
2. Reopen the checkout → the saved method appears as the **first step**.
3. **Pay with it** — drive any `show_fields` (CVV) / `3DS` / `redirect` NextActions it raises, to a
   terminal status.
4. **Delete it** (delete mode) → back to the initial state.

---

## Anti-patterns

1. **Do not** assume paying with a saved method is a single click — handle CVV / 3DS / errors via
   `onNextAction` before status.
2. **Do not** hardcode the save checkbox — it's the server-driven `allowSave` field; render it only
   when present.
3. **Do not** hide the regular methods — always offer "pay another way" alongside saved methods.
4. **Do not** roll your own delete request — use `psdk-saved-methods` `delete-mode` (+ its events).
5. **Do not** list saved methods without icons — icon-first, same as the method list.
6. **Do not** show saved methods when there are none — gate on `getSavedMethods().length`.

---

## Quick reference

| Thing                         | API / event / field                                                                 |
|-------------------------------|-------------------------------------------------------------------------------------|
| Detect saved methods          | `getSavedMethods()` → `SavedMethod[]`; `getCombinedPaymentMethods()` → `.savedMethods` |
| Save while paying             | `allowSave` form field (server-driven) + `form.init({ savePaymentMethod: true })`   |
| Save result                   | `status_updated` → `isSavePaymentMethodMode`, `savePaymentMethodStatus`              |
| Show saved methods            | `<psdk-saved-methods not-found delete-mode>` or custom UI from `getSavedMethods()`   |
| Pay with saved method         | `form.init({ paymentWithSavedMethod: true, savedMethodId, paymentMethodId, returnUrl })` |
| Selection event               | `savedMethodSelected` → `{ paymentMethodId, savedMethodId, type }` (bubbles/composed) |
| Delete                        | `psdk-saved-methods` `delete-mode="true"` → `deletedSavedMethodStatus { isDeleteSuccessful }` |
| `SavedMethod` display fields  | `id`, `pid`, `name`, `iconName`, `cardExpiryDate`, `type`, `psName`                  |
| Examples                      | `save-payment-method`, `saved-methods`, `payment-via-saved-method`                   |

---

## Checklist

- [ ] `getSavedMethods()` / `getCombinedPaymentMethods()` checked; saved methods shown **first** when present
- [ ] "Pay another way" falls back to the regular `payment-methods-list`
- [ ] Save checkbox rendered from the `allowSave` field (not hardcoded); save result read from `status_updated`
- [ ] Paying with a saved method goes through `onNextAction` (CVV / 3DS / redirect handled), then status
- [ ] Delete via `psdk-saved-methods delete-mode`; icons shown on every saved item
- [ ] Sandbox round trip passes: save → see it → pay with it → delete it

**Done?** Regular selection → `payment-methods-list`. Form fields / 3DS → `credit-card-form`. Redirect
mechanics → `redirect-flow`. Status → `payment-status`.

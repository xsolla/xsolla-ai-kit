# Status component, order life cycle, confirmation

Show the user the result, and confirm the purchase the *right* way (server-side).

Docs: [Integrate on app side](https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/integration-guide/integrate-on-app-side/) ·
[Order life cycle](https://developers.xsolla.com/api/catalog/payment-client-side/create-order#section/Error-response-format)

## Status component

When processing reaches a terminal/await state the SDK emits a `check_status` action.
Render `psdk-status`:

```ts
let showStatus = false;
headlessCheckout.form.onNextAction((nextAction) => {
  if (nextAction.type === 'check_status') showStatus = true;
});
```

```html
<!-- render once showStatus is true -->
<psdk-status></psdk-status>
```

`psdk-status` displays the payment outcome (success / failure / pending) to the user. After
an external 3DS or redirect the user lands on your `returnUrl` page — that page must
re-mount the SDK and render `psdk-status` so the returning user sees the result.

## Order life cycle

| Status | Meaning |
|--------|---------|
| `new` | Order created; awaiting payment confirmation |
| `paid` | Transaction confirmed; item can be granted |
| `done` | Item granted to the user |
| `canceled` | Payment refunded |
| `expired` | Superseded by a newer order for a limited item/promo; only the most recent order is payable (paying an expired order shows error `2002`) |

A successful payment moves `new → paid → done`. `psdk-status` reflects the payment, but
**`done` (item granted) is driven by your server**, not the client.

## Confirm server-side (source of truth)

The status component is **UX, not fulfillment**. Grant entitlements when your server
receives and verifies the `order_paid` webhook — never on the client status alone (the page
can be closed, reloaded, or spoofed). Webhook handling (signature verification, idempotency,
granting items) is the `webhooks-impl` skill.

Client-side order tracking (WebSocket order status + short-polling `Get order` as a
fallback) exists for flows with **no server**, and is covered by `catalog-design`'s
purchase-and-tracking reference — use it for UX only, still confirm server-side where you
can.

## Verify the full flow (sandbox)

With `sandbox: true` and a [test card](https://developers.xsolla.com/dev-resources/testing/test-cards/):

1. Methods render (`psdk-payment-methods`) and a selection fires `selectionChange`.
2. `form.init` for the chosen method; mandatory `psdk-legal` + `psdk-total` present.
3. Submit a success test card → 3DS challenge card clears via `psdk-3ds` or `redirect`.
4. `check_status` fires; `psdk-status` shows success.
5. The order reaches `done` and your `order_paid` webhook fired.
6. Repeat with a declined card (status shows failure) and confirm a refund moves the order
   to `canceled`.

See sandbox transaction history under **Accounting > Transaction registry** (check
**Show test transactions**).

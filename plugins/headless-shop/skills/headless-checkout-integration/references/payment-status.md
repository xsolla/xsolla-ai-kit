# Payment Status

Guide for an AI agent. Shows payment result: success, processing, error, canceled.

**Prerequisites:** `credit-card-form` or other payment flow skill — `form.init()` + submit working.

---

## How Status Works Under the Hood

```
submit → check_status → partner shows status UI
              ↓
    [one getStatus() OR psdk-status mount] → HTTP + WebSocket if processing
              ↓
         status_updated (push) → update UI from action.data
              ↓
         final state (success / fail / canceled)
```

**Three pieces — do not mix responsibilities:**

| Piece            | Role                                                                                                                           |
|------------------|--------------------------------------------------------------------------------------------------------------------------------|
| `check_status`   | Signal: switch UI to status view                                                                                               |
| `getStatus()`    | **One-shot** HTTP fetch; starts WebSocket when status is still processing. **Call at most once** per payment session on a page |
| `status_updated` | Push when status changes; update UI from `action.data` — **do not call `getStatus()` here**                                    |

`psdk-status` calls `getStatus()` internally and listens `status_updated` — partner must **not** call `getStatus()`
alongside it.

---

## Status States

| UI state       | `statusState` / flags             | Partner action                              |
|----------------|-----------------------------------|---------------------------------------------|
| **Processing** | `processing`, `created`, `held`   | Spinner; wait for `status_updated`          |
| **Success**    | `done`, `authorized`, `isSuccess` | Confirmation; `action.data.email` available |
| **Failed**     | `error`                           | Show error, offer retry                     |
| **Canceled**   | `canceled`, `isCanceled`          | User cancelled                              |

`status_updated` payload: `statusState`, `isSuccess`, `isCanceled`, `email`, `invoice`, `group`.

Full `Status` object (`statusMessage`, `financeInfo`, `order`) — only from the **single** `getStatus()` call when
needed.

---

## Approach A: `psdk-status` (Recommended)

Component owns WebSocket lifecycle. Partner only reacts to `check_status`.

> **Never put `<psdk-status>` in static markup** — not even inside a hidden/`display:none`
> container. On its `connectedCallback` the component immediately calls `getStatus()`,
> and if it mounts before there is a payment context it fails on page load with
> **`Could not get payment status`**. **Create the element dynamically** only when you
> actually have a payment to show — i.e. on `check_status`, or on the return page
> **after** `setToken()`. Toggling visibility on an already-present element is **not**
> enough; the element must not exist in the DOM until that moment.

```typescript
// Subscribe ONCE after form.init(), before submit
headlessCheckout.form.onNextAction((action) => {
    if (action.type === 'check_status') {
        showStatus = true;  // mount <psdk-status> — nothing else
    }
});
```

```html
@if (showStatus) {
<psdk-status></psdk-status>
}
```

**Do not call `getStatus()` manually** when `psdk-status` is mounted.

Refs: `headless-sdk-testing` `/basic`, `/card` — on `check_status` only toggle `showStatus`, no `getStatus()`.

### Return page

```html
<div id="status-container"></div>
<psdk-legal></psdk-legal>
```

```typescript
const token = new URLSearchParams(location.search).get('token');
await headlessCheckout.init({sandbox: true, isWebView: false});
await headlessCheckout.setToken(token);
// Create psdk-status only AFTER setToken — never static in the HTML, or its
// connectedCallback runs getStatus() before the token is set → "Could not get
// payment status". It calls getStatus() once on mount.
document.querySelector('#status-container')
    .appendChild(document.createElement('psdk-status'));
```

No `form.init()` on return page. URL needs: `token`, `locale`, `signature`, `pid`, `invoice`.

> **The return page must be a page that actually loads the SDK + this code.** On
> multi-page/CMS sites a wrong `returnUrl` lands the user on a page without your
> bundle and nothing happens — `getStatus()` is never called. If the return page
> does nothing, see the **"Troubleshooting: the return page does nothing"** checklist
> in [`redirect-flow.md`](redirect-flow.md).

Refs: `examples/return.html`, `headless-sdk-testing` `/status`, `/paypal/return`.

---

## Approach B: Custom Status UI

Partner renders own success/fail screen. **One `getStatus()` to enter polling; all further updates via `status_updated`.**

```typescript
let statusPollingStarted = false;

// Subscribe ONCE after form.init(), before submit
headlessCheckout.form.onNextAction((action) => {
    switch (action.type) {
        case 'check_status':
            showStatusView();
            startStatusPollingOnce();
            break;
        case 'status_updated':
            updateUI(action.data);  // isSuccess, isCanceled, statusState, email
            break;
    }
});

function startStatusPollingOnce() {
    if (statusPollingStarted) return;
    statusPollingStarted = true;
    void headlessCheckout.getStatus().then(mapInitialStatus);
}
```

**Never call `getStatus()` inside `status_updated`** — duplicates WebSocket, events get lost.

### Popup redirect (checkout page stays open)

One `getStatus()` on `redirect` to prime WebSocket before popup closes — then only `status_updated`:

```typescript
case
'redirect'
:
openPaymentPopup(url);
if (!statusPollingStarted) {
    statusPollingStarted = true;
    void headlessCheckout.getStatus();
}
break;
case
'status_updated'
:
updateUI(action.data);
break;
```

Ref: `headless-sdk-testing` `/card-3ds-custom-status` — `getStatus()` on `redirect`, UI from `status_updated` only.

### Return page — custom UI

One `getStatus()` after `init` + `setToken` — final read, no polling loop:

```typescript
const status = await headlessCheckout.getStatus();
renderCustomStatus(status.statusMessage, status.isSuccess, status.email);
```

Ref: `paypal-custom-status/return.html`.

---

## WebSocket Pitfalls (Critical)

1. **Multiple `getStatus()` calls** — each call can restart status listener / WebSocket (`ListenStatusService` calls
   `stopListening()` before new `listen()`). Second call = missed `status_updated`. **Max one `getStatus()` per page
   session** for live polling; use `status_updated` after that.

2. **`psdk-status` + manual `getStatus()`** — double WebSocket. Pick one: component OR manual, never both.

3. **`getStatus()` on `status_updated`** — wrong pattern (even though `psdk-status` does this internally — partners must
   not replicate). Use `action.data`.

4. **Late `onNextAction` subscription** — register once after `form.init()`, before submit. Never subscribe inside
   `check_status` or after `await getStatus()`. Anti-pattern: subscribing only when status is `processing` (race with
   WebSocket).

5. **Unsubscribe + re-subscribe** — gap loses events. One listener for entire payment session.

6. **Multiple `onNextAction` calls** — each adds a listener (not replace). One per page.

7. **Unmount `psdk-status` while processing** — component unsubscribes on destroy. Keep mounted until final state.

8. **`psdk-status` in static markup** — its `connectedCallback` calls `getStatus()` the moment it mounts. If it exists
   in the page before there is a payment context (e.g. a hidden `<psdk-status>` on the checkout page, or static on the
   return page before `setToken()`), it fails on load with **`Could not get payment status`**. Create it dynamically
   only at `check_status` / after `setToken()`; a hidden-then-shown static element is **not** a fix.

---

**Layouts:** same-page → `check_status` + `psdk-status` (`/card`); redirect return → `return.html`; popup flow → one
`getStatus()` on `redirect` + `status_updated` (`/card-3ds-custom-status`).

**Return URL:** redirect appends `token`, `signature`, `pid`, `invoice`, `locale`; return page = `init` + `setToken` +
`psdk-legal`.

**Refs:
** [integrate-on-app-side](https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/integration-guide/integrate-on-app-side/index.md), [return.html](https://github.com/xsolla/pay-station-sdk/blob/main/examples/return.html), [paypal-custom-status/return.html](https://github.com/xsolla/pay-station-sdk/blob/main/examples/paypal-custom-status/return.html).

---

## Checklist

- [ ] `onNextAction` registered once before submit
- [ ] `check_status` → status UI; **no extra `getStatus()` if `psdk-status` mounted**
- [ ] Custom UI: **one** `getStatus()` to start polling; updates via `status_updated` only
- [ ] Return page: `init` + `setToken`; sandbox success/decline tested

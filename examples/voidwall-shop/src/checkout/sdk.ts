import { headlessCheckout, type Lang } from '@xsolla/pay-station-sdk';

export interface CheckoutUi {
  fieldsEl: HTMLElement;
  statusEl: HTMLElement;
  errorEl: HTMLElement;
  setLoading(on: boolean): void;
}

type Field = Parameters<typeof headlessCheckout.form.setupAndAwaitFieldsLoading>[0][number];

/** Shop language codes (see PAY_LANGUAGE) are a subset of the SDK's Lang enum values. */
export const asLang = (code: string) => code as Lang;

// Styles for the cross-origin secure card iframes. Must be set before setToken().
const SECURE_CSS = `
  input { background:#0a0e14; color:#eaf6ff; border:1px solid #2a3242; border-radius:6px; padding:10px; font-size:16px; }
  input:focus { border-color:#35e0ff; outline:none; }
`;

let currentUi: CheckoutUi | null = null;
let unsubscribeActions: (() => void) | null = null;
let initialized = false;
let initGeneration = 0;

function teardown() {
  // The listener lives on the core iframe's message client, so it dies with the iframe: drop it explicitly
  // and register a fresh one on the next open.
  unsubscribeActions?.();
  unsubscribeActions = null;
  if (!initialized) return;
  headlessCheckout.destroy(); // removes the core iframe; init() appends a new one each time
  initialized = false;
}

export async function initCheckout(token: string, language: string, sandbox: boolean) {
  const generation = ++initGeneration;
  await headlessCheckout.init({ sandbox, isWebview: false, language: asLang(language) });
  initialized = true;
  if (generation !== initGeneration) { teardown(); return; } // closed (or superseded) while init was in flight
  headlessCheckout.setSecureComponentStyles(SECURE_CSS);
  await headlessCheckout.setToken(token);
}

export function detachUi() {
  currentUi = null;
  initGeneration++;
  teardown();
}

function fieldElement(f: Field): HTMLElement | null {
  let el: HTMLElement;
  if (f.name === 'card_number') { el = document.createElement('psdk-card-number'); el.setAttribute('icon', 'true'); }
  else if (f.name === 'phone') { el = document.createElement('psdk-phone'); el.setAttribute('showFlags', 'true'); }
  else if (f.type === 'text') el = document.createElement('psdk-text');
  else if (f.type === 'select') el = document.createElement('psdk-select');
  else if (f.type === 'check') el = document.createElement('psdk-checkbox');
  else return null; // labels (and anything unknown) are never rendered as inputs
  el.setAttribute('name', f.name);
  return el;
}

async function renderFields(ui: CheckoutUi, fields: Field[]) {
  ui.setLoading(true);
  // Do not clear errorEl here: show_errors is often followed by show_fields, which would wipe the message.
  ui.fieldsEl.replaceChildren(); // replace, never append, on show_fields
  const mounted: Field[] = [];
  for (const f of fields) {
    const el = fieldElement(f);
    if (el) { ui.fieldsEl.appendChild(el); mounted.push(f); }
  }
  ui.fieldsEl.appendChild(document.createElement('psdk-submit-button'));
  await headlessCheckout.form.setupAndAwaitFieldsLoading(mounted);
  headlessCheckout.form.activate(); // without this, submit silently does nothing
  ui.setLoading(false);
}

interface Redirect {
  redirectUrl: string; method?: string; data?: Record<string, unknown>;
  isNewWindowRequired?: boolean; isSameWindowRequired?: boolean;
}

/** New tab: let psdk-redirect render the gesture button. Otherwise (same-window flag OR no flag) submit in this tab. */
function handleRedirect(ui: CheckoutUi, redirect: Redirect) {
  if (redirect.isNewWindowRequired) {
    const el = document.createElement('psdk-redirect');
    el.setAttribute('data-redirect', JSON.stringify(redirect));
    el.setAttribute('text', 'Continue');
    ui.fieldsEl.replaceChildren();
    ui.statusEl.replaceChildren(el);
    return;
  }
  const form = document.createElement('form');
  form.method = redirect.method?.toUpperCase() === 'POST' ? 'POST' : 'GET'; // POST avoids 414 on long parameter sets
  form.action = redirect.redirectUrl;
  for (const [name, value] of Object.entries(redirect.data ?? {})) {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = name;
    input.value = String(value);
    form.appendChild(input);
  }
  document.body.appendChild(form);
  form.submit();
}

function dispatch(action: any) {
  const ui = currentUi;
  if (!ui) return;
  switch (action.type) {
    case 'show_fields':
      void renderFields(ui, action.data.fields);
      break;
    case 'show_errors':
      ui.errorEl.textContent = action.data.errors?.[0]?.message ?? 'Payment error';
      break;
    case 'redirect':
      handleRedirect(ui, action.data.redirect);
      break;
    case '3DS': {
      const el = document.createElement('psdk-3ds');
      el.setAttribute('data-challenge', JSON.stringify(action.data.data)); // payload is nested one level down
      ui.statusEl.replaceChildren(el);
      break;
    }
    case 'check_status': {
      ui.fieldsEl.replaceChildren();
      // Created dynamically on purpose: a static <psdk-status> calls getStatus() before a token exists.
      ui.statusEl.replaceChildren(document.createElement('psdk-status'));
      break;
    }
  }
}

export async function openMethod(ui: CheckoutUi, paymentMethodId: number, returnUrl: string) {
  currentUi = ui;
  ui.errorEl.textContent = '';
  ui.statusEl.replaceChildren();
  ui.setLoading(true);
  // paymentMethodSettings is only valid for the card method (1380); other methods must omit it.
  const form = await headlessCheckout.form.init(
    paymentMethodId === 1380
      ? { paymentMethodId: 1380, returnUrl, paymentMethodSettings: { useSingleExpirationDateField: true } }
      : { paymentMethodId, returnUrl },
  );
  if (!unsubscribeActions) { // exactly one listener per live SDK session
    unsubscribeActions = headlessCheckout.form.onNextAction(dispatch);
  }
  await renderFields(ui, form.fields);
}

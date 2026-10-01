// @vitest-environment jsdom
import { beforeEach, describe, expect, test, vi } from 'vitest';

const sdk = vi.hoisted(() => {
  const handlers: ((a: any) => void)[] = [];
  const fields = [
    { name: 'card_number', type: 'text' },
    { name: 'cvv', type: 'text' },
    { name: 'terms', type: 'label' },
  ];
  const unsubscribe = vi.fn();
  return {
    handlers,
    fields,
    unsubscribe,
    headlessCheckout: {
      init: vi.fn(async () => {}),
      setSecureComponentStyles: vi.fn(async () => {}),
      setToken: vi.fn(async () => {}),
      destroy: vi.fn(),
      form: {
        init: vi.fn(async () => ({ fields })),
        onNextAction: vi.fn((h: (a: any) => void) => { handlers.push(h); return unsubscribe; }),
        setupAndAwaitFieldsLoading: vi.fn(async () => {}),
        activate: vi.fn(),
      },
    },
  };
});
vi.mock('@xsolla/pay-station-sdk', () => ({ headlessCheckout: sdk.headlessCheckout }));

import { detachUi, initCheckout, openMethod, type CheckoutUi } from '../src/checkout/sdk';

function makeUi(): CheckoutUi {
  return {
    fieldsEl: document.createElement('div'),
    statusEl: document.createElement('div'),
    errorEl: document.createElement('p'),
    setLoading: vi.fn(),
  };
}
const fire = (a: unknown) => sdk.handlers.at(-1)!(a);
const flush = () => new Promise((r) => setTimeout(r, 0));

describe('checkout dispatcher', () => {
  let ui: CheckoutUi;
  beforeEach(async () => {
    detachUi();
    vi.clearAllMocks();
    ui = makeUi();
    await openMethod(ui, 1380, 'http://x/return');
  });

  test('labels are never rendered as inputs; a submit button is added and the form is activated', () => {
    expect(ui.fieldsEl.querySelectorAll('psdk-card-number')).toHaveLength(1);
    expect(ui.fieldsEl.querySelectorAll('psdk-text')).toHaveLength(1);
    expect(ui.fieldsEl.querySelector('[name="terms"]')).toBeNull();
    expect(ui.fieldsEl.querySelectorAll('psdk-submit-button')).toHaveLength(1);
    expect(sdk.headlessCheckout.form.activate).toHaveBeenCalledTimes(1);
  });

  test('show_fields replaces the fields instead of appending', async () => {
    fire({ type: 'show_fields', data: { fields: [{ name: 'zip', type: 'text' }] } });
    await flush();
    expect(ui.fieldsEl.querySelectorAll('psdk-text')).toHaveLength(1);
    expect(ui.fieldsEl.querySelectorAll('psdk-card-number')).toHaveLength(0);
  });

  test('a card error survives the show_fields that follows it', async () => {
    fire({ type: 'show_errors', data: { errors: [{ message: 'Card declined' }] } });
    fire({ type: 'show_fields', data: { fields: [{ name: 'card_number', type: 'text' }] } });
    await flush();
    expect(ui.errorEl.textContent).toBe('Card declined');
  });

  test('check_status mounts psdk-status dynamically and clears the form', () => {
    fire({ type: 'check_status' });
    expect(ui.statusEl.querySelectorAll('psdk-status')).toHaveLength(1);
    expect(ui.fieldsEl.children).toHaveLength(0);
  });

  test('3DS passes the nested challenge payload', () => {
    fire({ type: '3DS', data: { data: { acs: 'x' } } });
    expect(ui.statusEl.querySelector('psdk-3ds')!.getAttribute('data-challenge')).toBe(JSON.stringify({ acs: 'x' }));
  });

  test('redirect without a window flag submits a same-tab form', () => {
    const submit = vi.spyOn(HTMLFormElement.prototype, 'submit').mockImplementation(() => {});
    fire({ type: 'redirect', data: { redirect: { redirectUrl: 'https://bank/x', method: 'POST', data: { a: 1 } } } });
    expect(submit).toHaveBeenCalledTimes(1);
    expect(ui.statusEl.querySelector('psdk-redirect')).toBeNull();
  });

  test('redirect with isNewWindowRequired renders psdk-redirect for the click gesture', () => {
    const submit = vi.spyOn(HTMLFormElement.prototype, 'submit').mockImplementation(() => {});
    submit.mockClear();
    fire({ type: 'redirect', data: { redirect: { redirectUrl: 'https://bank/x', isNewWindowRequired: true, data: {} } } });
    expect(ui.statusEl.querySelector('psdk-redirect')).not.toBeNull();
    expect(submit).not.toHaveBeenCalled();
  });
});

describe('checkout SDK lifecycle', () => {
  beforeEach(() => { detachUi(); vi.clearAllMocks(); });

  test('closing after a method was opened destroys the SDK so a reopen does not stack core iframes', async () => {
    await initCheckout('tok', 'en', true);
    await openMethod(makeUi(), 1380, 'http://x/return');
    detachUi();
    expect(sdk.headlessCheckout.destroy).toHaveBeenCalledTimes(1);
  });

  test('closing before any method was chosen still destroys the SDK', async () => {
    await initCheckout('tok', 'en', true);
    detachUi();
    expect(sdk.headlessCheckout.destroy).toHaveBeenCalledTimes(1);
  });

  test('closing while init is still in flight destroys the SDK once init lands', async () => {
    let release!: () => void;
    sdk.headlessCheckout.init.mockImplementationOnce(() => new Promise<void>((r) => { release = r; }));
    const pending = initCheckout('tok', 'en', true);
    detachUi();
    release();
    await pending;
    expect(sdk.headlessCheckout.destroy).toHaveBeenCalledTimes(1);
    expect(sdk.headlessCheckout.setToken).not.toHaveBeenCalled();
  });

  test('teardown unsubscribes the form listener and the next open registers a fresh one', async () => {
    await initCheckout('tok', 'en', true);
    await openMethod(makeUi(), 1380, 'http://x/return');
    detachUi();
    expect(sdk.unsubscribe).toHaveBeenCalledTimes(1);
    await initCheckout('tok', 'en', true);
    await openMethod(makeUi(), 1380, 'http://x/return');
    expect(sdk.headlessCheckout.form.onNextAction).toHaveBeenCalledTimes(2);
  });

  test('detachUi without a live SDK does not call destroy', () => {
    detachUi();
    expect(sdk.headlessCheckout.destroy).not.toHaveBeenCalled();
  });

  test('init passes the shop language and sandbox flag and sets secure styles before the token', async () => {
    await initCheckout('tok', 'fr', true);
    expect(sdk.headlessCheckout.init).toHaveBeenCalledWith({ sandbox: true, isWebview: false, language: 'fr' });
    const styleOrder = sdk.headlessCheckout.setSecureComponentStyles.mock.invocationCallOrder[0]!;
    const tokenOrder = sdk.headlessCheckout.setToken.mock.invocationCallOrder[0]!;
    expect(styleOrder).toBeLessThan(tokenOrder);
  });
});

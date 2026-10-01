import { describe, expect, test } from 'vitest';
import { authHeaders, guestId } from '../src/cart/headers';
import { createCartApi, type Cart, type CartApi } from '../src/cart/cartApi';
import { mergeGuestCart } from '../src/cart/merge';

const mem = () => {
  const m = new Map<string, string>();
  return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v) };
};

test('guestId is stable across calls and reloads', () => {
  const s = mem();
  const a = guestId(s, () => 'uuid-1');
  expect(guestId(s, () => 'uuid-2')).toBe(a);
});

test('authHeaders: Bearer when logged in, guest id otherwise', () => {
  expect(authHeaders(null, 'g1')).toEqual({ 'x-unauthorized-id': 'g1' });
  expect(authHeaders({ accessToken: 'T', expiresAt: 1 }, 'g1')).toEqual({ Authorization: 'Bearer T' });
});

test('cart api: get normalizes, PUT item sends quantity, headers always attached', async () => {
  const calls: { url: string; method: string; body?: string; h: Record<string, string> }[] = [];
  const f = (async (url: string, init: RequestInit = {}) => {
    calls.push({ url, method: init.method ?? 'GET', body: init.body as string | undefined, h: init.headers as Record<string, string> });
    if ((init.method ?? 'GET') === 'GET') {
      return new Response(JSON.stringify({
        cart_id: 'c1',
        items: [{ sku: 'cores_500', name: 'Core Cache', quantity: 2, price: { amount: '4.99', amount_without_discount: '4.99', currency: 'USD' }, image_url: 'u' }],
        price: { amount: '9.98', amount_without_discount: '9.98', currency: 'USD' },
      }), { status: 200 });
    }
    return new Response(null, { status: 204 });
  }) as unknown as typeof fetch;
  const api = createCartApi('316665', () => ({ 'x-unauthorized-id': 'g1' }), f);
  const cart = await api.get();
  expect(cart.cartId).toBe('c1');
  expect(cart.items[0]).toMatchObject({ sku: 'cores_500', quantity: 2 });
  expect(cart.total?.amount).toBe(9.98);
  await api.setQuantity('cores_500', 3);
  expect(calls[1]).toMatchObject({ method: 'PUT', body: JSON.stringify({ quantity: 3 }) });
  expect(calls[1]!.url).toContain('/cart/item/cores_500');
  expect(calls.every((c) => c.h['x-unauthorized-id'] === 'g1')).toBe(true);
});

describe('mergeGuestCart', () => {
  const line = (sku: string, quantity: number) => ({ sku, name: sku, quantity });
  const fake = (items: ReturnType<typeof line>[], failOn?: string) => {
    const ctl = { failOn };
    const log: string[] = [];
    const state = new Map(items.map((i) => [i.sku, i.quantity]));
    const api: CartApi = {
      async get(): Promise<Cart> { return { cartId: 'c', items: [...state].map(([sku, q]) => line(sku, q)) }; },
      async setQuantity(sku, q) { if (sku === ctl.failOn) throw new Error('boom'); state.set(sku, q); log.push(`set ${sku}=${q}`); },
      async remove(sku) { state.delete(sku); },
      async clear() { state.clear(); log.push('clear'); },
    };
    return { api, log, state, ctl };
  };

  test('adds guest lines on top of the account cart and clears the guest cart', async () => {
    const guest = fake([line('cores_500', 1), line('bundle_rime_hunter', 1)]);
    const user = fake([line('cores_500', 2)]);
    await mergeGuestCart(guest.api, user.api);
    expect(user.state.get('cores_500')).toBe(3);
    expect(user.state.get('bundle_rime_hunter')).toBe(1);
    expect(guest.state.size).toBe(0);
  });

  test('an empty guest cart is a no-op', async () => {
    const guest = fake([]);
    const user = fake([line('cores_500', 2)]);
    await mergeGuestCart(guest.api, user.api);
    expect(user.log).toEqual([]);
    expect(guest.log).toEqual([]);
  });

  test('a failure midway loses nothing: every line is in the account cart or still in the guest cart', async () => {
    const guest = fake([line('cores_500', 1), line('bundle_rime_hunter', 1)]);
    const failingUser = fake([], 'bundle_rime_hunter');
    await expect(mergeGuestCart(guest.api, failingUser.api)).rejects.toThrow('boom');
    expect(failingUser.state.get('cores_500')).toBe(1);
    expect([...guest.state.keys()]).toEqual(['bundle_rime_hunter']);
  });

  test('a retry after a midway failure does not double lines that already landed', async () => {
    const guest = fake([line('cores_500', 2), line('bundle_rime_hunter', 1)]);
    const user = fake([], 'bundle_rime_hunter');
    await expect(mergeGuestCart(guest.api, user.api)).rejects.toThrow('boom');
    user.ctl.failOn = undefined;
    await mergeGuestCart(guest.api, user.api);
    expect(user.state.get('cores_500')).toBe(2);
    expect(user.state.get('bundle_rime_hunter')).toBe(1);
    expect(guest.state.size).toBe(0);
  });
});

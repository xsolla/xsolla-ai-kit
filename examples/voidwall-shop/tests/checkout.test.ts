import { describe, expect, test } from 'vitest';
import { InsufficientCoresError, buyWithCores, createCartPaymentToken, fetchCoresBalance } from '../src/checkout/api';

const session = { accessToken: 'JWT', expiresAt: Date.now() + 1e6 };
const json = (o: unknown, status = 200) => new Response(JSON.stringify(o), { status });
type Seen = { url: string; init: RequestInit };
const spy = (res: Response) => {
  const seen: Seen[] = [];
  const f = (async (url: string, init: RequestInit) => { seen.push({ url, init }); return res.clone(); }) as unknown as typeof fetch;
  return { f, seen };
};

describe('createCartPaymentToken (Method 1)', () => {
  test('posts to the cart payment endpoint with Bearer, sandbox and language', async () => {
    const { f, seen } = spy(json({ token: 'TKN', order_id: 42 }));
    const r = await createCartPaymentToken({ projectId: '316665', cartId: 'c1', session, language: 'ja', sandbox: true }, f);
    expect(r).toEqual({ token: 'TKN', orderId: 42 });
    expect(seen[0]!.url).toBe('https://store.xsolla.com/api/v2/project/316665/payment/cart/c1');
    expect((seen[0]!.init.headers as Record<string, string>).Authorization).toBe('Bearer JWT');
    const body = JSON.parse(String(seen[0]!.init.body));
    expect(body.sandbox).toBe(true);
    expect(body.settings.language).toBe('ja');
    expect(body.promo_code).toBeUndefined();
  });

  test('never sends an API key header', async () => {
    const { f, seen } = spy(json({ token: 'T', order_id: 1 }));
    await createCartPaymentToken({ projectId: '1', cartId: 'c', session, language: 'en', sandbox: true }, f);
    expect(JSON.stringify(seen[0]!.init.headers).toLowerCase()).not.toContain('basic');
  });

  test('non-2xx throws with status', async () => {
    const { f } = spy(json({}, 422));
    await expect(createCartPaymentToken({ projectId: '1', cartId: 'c', session, language: 'en', sandbox: true }, f)).rejects.toThrow(/422/);
  });
});

describe('buyWithCores', () => {
  test('posts to the virtual-currency purchase endpoint', async () => {
    const { f, seen } = spy(json({ order_id: 7 }));
    expect(await buyWithCores({ projectId: '316665', sku: 'tether_skin_anchor', session }, f)).toEqual({ orderId: 7 });
    expect(seen[0]!.url).toBe('https://store.xsolla.com/api/v2/project/316665/payment/item/tether_skin_anchor/virtual/cores');
    expect(seen[0]!.init.method).toBe('POST');
  });
  test('a 422 maps to InsufficientCoresError', async () => {
    const { f } = spy(json({ errorCode: 4003 }, 422));
    await expect(buyWithCores({ projectId: '1', sku: 'x', session }, f)).rejects.toBeInstanceOf(InsufficientCoresError);
  });
});

test('fetchCoresBalance reads the cores line, 0 when absent', async () => {
  expect(await fetchCoresBalance('1', session, spy(json({ items: [{ sku: 'cores', amount: 1200 }] })).f)).toBe(1200);
  expect(await fetchCoresBalance('1', session, spy(json({ items: [] })).f)).toBe(0);
});

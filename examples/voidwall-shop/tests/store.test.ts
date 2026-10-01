import { expect, test } from 'vitest';
import { fetchCatalog, formatMoney, normalizeItem } from '../src/api/store';

const rawSkin = {
  sku: 'lancer_skin_deadeye', name: 'Deadeye', description: 'd', image_url: 'https://cdn/x.jpg',
  groups: [{ external_id: 'turret_skins' }],
  attributes: [{ external_id: 'rarity', values: [{ external_id: 'legendary', value: 'Legendary' }] }],
  price: null,
  virtual_prices: [{ sku: 'cores', amount: 2400, is_default: true }],
};
const rawPack = {
  sku: 'cores_1200', name: 'Core Stack', description: 'd', groups: [],
  price: { amount: '9.99', amount_without_discount: '9.99', currency: 'USD' },
};

test('normalizeItem: Cores price, null price, attributes', () => {
  const it = normalizeItem(rawSkin, 'item');
  expect(it.coresPrice).toBe(2400);
  expect(it.price).toBeUndefined();
  expect(it.attributes).toEqual({ rarity: 'legendary' });
  expect(it.groups).toEqual(['turret_skins']);
});

test('normalizeItem: money strings become numbers', () => {
  const it = normalizeItem(rawPack, 'package');
  expect(it.price).toEqual({ amount: 9.99, amountWithoutDiscount: 9.99, currency: 'USD' });
});

test('formatMoney: undefined price is an empty string, not NaN', () => {
  expect(formatMoney(undefined, 'en')).toBe('');
  expect(formatMoney({ amount: 9.99, amountWithoutDiscount: 9.99, currency: 'USD' }, 'en')).toBe('$9.99');
  expect(formatMoney({ amount: 1500, amountWithoutDiscount: 1500, currency: 'JPY' }, 'ja')).toMatch(/1,500/);
});

test('fetchCatalog paginates, passes locale, never sends country', async () => {
  const urls: string[] = [];
  const page = (items: unknown[], more: boolean) => new Response(JSON.stringify({ items, has_more: more }), { status: 200 });
  const f = (async (url: string) => {
    urls.push(url);
    if (url.includes('/items/virtual_items') && !url.includes('offset=50')) return page([rawSkin], true);
    if (url.includes('/items/virtual_items')) return page([], false);
    if (url.includes('/package')) return page([rawPack], false);
    return page([], false);
  }) as unknown as typeof fetch;
  const items = await fetchCatalog('316665', 'pt-BR', f);
  expect(items.map((i) => i.sku).sort()).toEqual(['cores_1200', 'lancer_skin_deadeye']);
  expect(urls.every((u) => u.includes('locale=pt&'))).toBe(true);
  expect(urls.some((u) => u.includes('country='))).toBe(false);
  expect(urls.filter((u) => u.includes('/items/virtual_items'))).toHaveLength(2);
});

test('fetchCatalog throws on a non-2xx response', async () => {
  const f = (async () => new Response('{}', { status: 500 })) as unknown as typeof fetch;
  await expect(fetchCatalog('316665', 'en', f)).rejects.toThrow(/500/);
});

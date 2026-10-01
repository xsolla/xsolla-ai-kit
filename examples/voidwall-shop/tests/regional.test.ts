import { expect, test } from 'vitest';
import { CURRENCIES } from '../catalog/types';
import { pricesFor, regionalPrice } from '../catalog/regional';

test('Core Stack matches the worked example in CONTEXT.md', () => {
  expect(regionalPrice('cores_1200', 9.99, 'USD')).toBe(9.99);
  expect(regionalPrice('cores_1200', 9.99, 'EUR')).toBe(9.99);
  expect(regionalPrice('cores_1200', 9.99, 'GBP')).toBe(8.99);
  expect(regionalPrice('cores_1200', 9.99, 'BRL')).toBe(49.9);
  expect(regionalPrice('cores_1200', 9.99, 'JPY')).toBe(1500);
});

test('other tiers use multipliers; JPY rounds to 10', () => {
  expect(regionalPrice('cores_500', 4.99, 'GBP')).toBe(4.49);
  expect(regionalPrice('cores_500', 4.99, 'JPY')).toBe(750);
});

test('pricesFor returns the full currency set with USD default', () => {
  const p = pricesFor('cores_500', 4.99);
  expect(p.map((x) => x.currency)).toEqual(CURRENCIES);
  expect(p.filter((x) => x.is_default).map((x) => x.currency)).toEqual(['USD']);
});

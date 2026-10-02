import { expect, test } from 'vitest';
import { LOCALES } from '../catalog/types';
import { UI } from '../src/i18n/ui';

test('every locale defines exactly the same keys, with no empty values or em dashes', () => {
  const keys = Object.keys(UI.en).sort();
  for (const l of LOCALES) {
    expect(Object.keys(UI[l]).sort(), l).toEqual(keys);
    for (const [k, v] of Object.entries(UI[l])) {
      expect(v.length, `${l}.${k}`).toBeGreaterThan(0);
      expect(v).not.toContain(String.fromCharCode(0x2014));
    }
  }
});

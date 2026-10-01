import { existsSync } from 'node:fs';
import { describe, expect, test } from 'vitest';
import {
  BOOSTERS, BUNDLES, GEAR, GROUPS, IMAGES, PACKS, PASS, SKINS, coresValue,
} from '../catalog/catalog';

describe('catalog definitions', () => {
  test('counts match CONTEXT.md (+ hidden title)', () => {
    expect(GROUPS).toHaveLength(6);
    expect(PACKS).toHaveLength(5);
    expect(SKINS).toHaveLength(11);
    expect(GEAR).toHaveLength(5);
    expect(BOOSTERS).toHaveLength(3);
    expect(BUNDLES).toHaveLength(4);
    expect(PASS.sku).toBe('pass_s1_frontier');
  });

  test('SKUs are unique and valid', () => {
    const skus = [
      ...PACKS, ...SKINS, ...GEAR, ...BOOSTERS, ...BUNDLES, PASS,
    ].map((d) => d.sku);
    expect(new Set(skus).size).toBe(skus.length);
    for (const s of skus) expect(s).toMatch(/^[A-Za-z0-9._-]{1,255}$/);
  });

  test('every image resolves to a file in public/assets', () => {
    for (const [sku, rel] of Object.entries(IMAGES)) {
      expect(existsSync(`public/assets/${rel}`), `${sku} -> ${rel}`).toBe(true);
    }
  });

  test('bundle contents reference known SKUs or cores', () => {
    const known = new Set([
      'cores', ...SKINS.map((s) => s.sku), ...GEAR.map((g) => g.sku), ...BOOSTERS.map((b) => b.sku),
    ]);
    for (const b of BUNDLES) for (const c of b.contents) expect(known.has(c.sku), `${b.sku}:${c.sku}`).toBe(true);
  });

  test('Warden\'s Arsenal individual value is 3900 Cores, not the 4700 in CONTEXT.md', () => {
    const arsenal = BUNDLES.find((b) => b.sku === 'bundle_wardens_arsenal')!;
    expect(coresValue(arsenal)).toBe(3900);
  });

  test('pack totals', () => {
    const totals = Object.fromEntries(PACKS.map((p) => [p.sku, p.base + p.bonus]));
    expect(totals).toEqual({
      cores_500: 500, cores_1200: 1200, cores_2600: 2600, cores_7000: 7000, cores_15000: 15000,
    });
  });
});

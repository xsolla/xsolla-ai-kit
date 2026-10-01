import { expect, test } from 'vitest';
import { byGroup, groupOf, knownItems, visibleGroups } from '../src/api/view';
import type { ShopItem } from '../src/api/store';

const mk = (sku: string, kind: ShopItem['kind'] = 'item', groups: string[] = []): ShopItem => ({
  sku, kind, name: sku, description: '', groups, attributes: {},
});

test('knownItems drops foreign quest fixtures', () => {
  const out = knownItems([mk('quest_demo_r1h_20260930t1910z'), mk('qp_fire_sword_1'), mk('tether_skin_anchor')]);
  expect(out.map((i) => i.sku)).toEqual(['tether_skin_anchor']);
});

test('packages land in currency, bundles in bundles, items by group', () => {
  expect(groupOf(mk('cores_500', 'package'))).toBe('currency');
  expect(groupOf(mk('bundle_rime_hunter', 'bundle'))).toBe('bundles');
  expect(groupOf(mk('booster_xp_24h', 'item'))).toBe('boosters');
  expect(groupOf(mk('arclight_skin_voltaic'))).toBe('turret_skins');
});

test('visibleGroups hides empty sections (windowed pass hidden before Season 1)', () => {
  const items = knownItems([mk('cores_500', 'package'), mk('tether_skin_anchor')]);
  expect(visibleGroups(items).map((g) => g.id)).toEqual(['currency', 'turret_skins']);
  expect(byGroup(items, 'passes')).toEqual([]);
});

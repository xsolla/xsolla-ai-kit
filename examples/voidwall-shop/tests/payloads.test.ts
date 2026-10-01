import { describe, expect, test } from 'vitest';
import { LOCALES } from '../catalog/types';
import { buildPlan } from '../catalog/plan';

const plan = buildPlan();
const byKey = (k: string) => plan.find((s) => s.key === k)!;

describe('seed plan', () => {
  test('order: groups, currencies, items, packages, bundles', () => {
    const kinds = plan.map((s) => s.kind);
    const firstIndex = (k: string) => kinds.indexOf(k as never);
    expect(firstIndex('group')).toBe(0);
    expect(firstIndex('currency')).toBeGreaterThan(kinds.lastIndexOf('group'));
    expect(firstIndex('item')).toBeGreaterThan(kinds.lastIndexOf('currency'));
    expect(firstIndex('package')).toBeGreaterThan(kinds.lastIndexOf('item'));
    expect(firstIndex('bundle')).toBeGreaterThan(kinds.lastIndexOf('package'));
  });

  test('37 steps: 6 groups, 2 currencies, 20 items, 5 packages, 4 bundles', () => {
    const count = (k: string) => plan.filter((s) => s.kind === k).length;
    expect([count('group'), count('currency'), count('item'), count('package'), count('bundle')]).toEqual([6, 2, 20, 5, 4]);
  });

  test('every name and description has all five locales', () => {
    for (const s of plan.filter((p) => p.kind !== 'group')) {
      for (const field of ['name', 'description']) {
        for (const l of LOCALES) {
          expect(s.payload[field]?.[l], `${s.key}.${field}.${l}`).toBeTruthy();
        }
      }
    }
  });

  test('no step touches quest fixtures', () => {
    for (const s of plan) expect(s.key).not.toMatch(/^quest_|^qp_/);
  });

  test('skin: Cores price, group and attributes', () => {
    const p = byKey('arclight_skin_solarflare').payload;
    expect(p.vc_prices).toEqual([{ sku: 'cores', amount: 2400, is_default: true, is_enabled: true }]);
    expect(p.groups).toEqual(['turret_skins']);
    const attr = Object.fromEntries(p.attributes.map((a: any) => [a.external_id, a.values[0].external_id]));
    expect(attr).toEqual({ rarity: 'legendary', turret_class: 'arclight' });
    expect(p.virtual_item_type).toBe('non_consumable');
  });

  test('boosters are consumable (boolean) with daily limit on 24h only', () => {
    const day = byKey('booster_xp_24h').payload;
    expect(day.virtual_item_type).toBe('consumable');
    expect(day.inventory_options.consumable).toBe(true);
    expect(day.limits.per_user).toBe(5);
    expect(day.limits.recurrent_schedule.per_user.interval_type).toBe('daily');
    expect(byKey('booster_salvage_7d').payload.limits).toBeUndefined();
  });

  test('packs grant base + bonus and carry five currencies', () => {
    const p = byKey('cores_1200').payload;
    expect(p.content).toEqual([{ sku: 'cores', quantity: 1200 }]);
    expect(p.prices.map((x: any) => x.currency)).toEqual(['USD', 'EUR', 'GBP', 'BRL', 'JPY']);
    expect(p.prices[0]).toMatchObject({ currency: 'USD', amount: 9.99, is_default: true });
  });

  test('bundles: money price only, limits and window', () => {
    for (const k of ['bundle_frontier_starter', 'bundle_wardens_arsenal', 'bundle_rime_hunter', 'bundle_founders']) {
      expect(byKey(k).payload.vc_prices).toBeUndefined();
      expect(byKey(k).payload.prices).toHaveLength(5);
    }
    expect(byKey('bundle_frontier_starter').payload.limits.per_user).toBe(1);
    expect(byKey('bundle_founders').payload.periods).toEqual([
      { date_from: '2026-10-14T00:00:00+00:00', date_until: '2027-01-13T23:59:59+00:00' },
    ]);
    expect(byKey('bundle_wardens_arsenal').payload.periods).toBeUndefined();
  });

  test('hidden title, Cores currency hidden, windowed items not expected in store', () => {
    expect(byKey('warden_title_plankowner').payload.is_show_in_store).toBe(false);
    expect(byKey('cores').payload.is_show_in_store).toBe(false);
    expect(byKey('pass_s1_frontier').expectInStore).toBe(false);
    expect(byKey('bundle_founders').expectInStore).toBe(false);
    expect(byKey('bundle_rime_hunter').expectInStore).toBe(true);
    expect(byKey('cores_500').expectInStore).toBe(true);
  });
});

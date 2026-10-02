import { CORES_SKU, PASS } from './catalog';
import { allLocales, descFor, nameFor, type CopyKind, type Vars } from './copy';
import { pricesFor } from './regional';
import type { BoosterDef, BundleDef, GearDef, GroupDef, PackDef, SkinDef, Window } from './types';

const lower = (s: string) => s.toLowerCase();
const vcPrice = (amount: number) => [{ sku: CORES_SKU, amount, is_default: true, is_enabled: true }];
const periods = (w?: Window) => (w ? [{ date_from: w.from, date_until: w.until }] : undefined);
const text = (sku: string, enName: string, kind: CopyKind, vars: Vars = {}) => ({
  name: allLocales((l) => nameFor(sku, enName, l)),
  description: allLocales((l) => descFor(sku, kind, vars, l)),
});
const attribute = (id: string, label: string, value: string, shown: string) => ({
  external_id: id, name: { en: label }, values: [{ external_id: lower(value).replace(/\s+/g, '_'), value: { en: shown } }],
});

export const buildGroup = (g: GroupDef) => ({ external_id: g.id, name: g.names, order: g.order });

export const buildCurrency = (sku: string, enName: string, kind: 'cores' | 'scrap') => ({
  sku, ...text(sku, enName, kind), is_enabled: true, is_show_in_store: false,
});

export const buildPack = (p: PackDef) => ({
  sku: p.sku, ...text(p.sku, p.name, 'pack', { total: p.base + p.bonus, bonus: p.bonus }),
  is_enabled: true, is_show_in_store: true, prices: pricesFor(p.sku, p.usd),
  content: [{ sku: CORES_SKU, quantity: p.base + p.bonus }],
});

export const buildSkin = (s: SkinDef) => ({
  sku: s.sku, ...text(s.sku, s.name, 'skin', { rarity: s.rarity, cls: s.turretClass }),
  groups: ['turret_skins'], is_enabled: true, is_show_in_store: true,
  virtual_item_type: 'non_consumable', vc_prices: vcPrice(s.cores),
  attributes: [
    attribute('rarity', 'Rarity', s.rarity, s.rarity),
    attribute('turret_class', 'Turret class', s.turretClass, s.turretClass),
  ],
});

export const buildGear = (g: GearDef) => ({
  sku: g.sku, ...text(g.sku, g.name, g.kind),
  groups: ['warden_gear'], is_enabled: true, is_show_in_store: !g.hidden,
  virtual_item_type: 'non_consumable', vc_prices: vcPrice(g.cores),
  attributes: [attribute('rarity', 'Rarity', g.rarity, g.rarity)],
});

export const buildBooster = (b: BoosterDef) => ({
  sku: b.sku, ...text(b.sku, b.name, 'booster', { effect: b.effect, duration: b.duration }),
  groups: ['boosters'], is_enabled: true, is_show_in_store: true,
  virtual_item_type: 'consumable', inventory_options: { consumable: true }, vc_prices: vcPrice(b.cores),
  ...(b.dailyLimit
    ? { limits: { per_user: b.dailyLimit, recurrent_schedule: { per_user: { interval_type: 'daily', time: '00:00:00+00:00' } } } }
    : {}),
});

export const buildBundle = (b: BundleDef, itemNames: Record<string, string>) => {
  const list = b.contents
    .map((c) => (c.sku === CORES_SKU ? `${new Intl.NumberFormat('en').format(c.quantity)} Cores` : itemNames[c.sku] ?? c.sku))
    .join(', ');
  return {
    sku: b.sku, ...text(b.sku, b.name, 'bundle', { list }),
    groups: ['bundles'], is_enabled: true, is_show_in_store: true,
    prices: pricesFor(b.sku, b.usd), content: b.contents,
    ...(b.limitPerUser ? { limits: { per_user: b.limitPerUser } } : {}),
    ...(b.window ? { periods: periods(b.window) } : {}),
  };
};

export const buildPass = () => ({
  sku: PASS.sku, ...text(PASS.sku, PASS.name, 'pass'),
  groups: ['passes'], is_enabled: true, is_show_in_store: true,
  virtual_item_type: 'non_consumable', prices: pricesFor(PASS.sku, PASS.usd), periods: periods(PASS.window),
});

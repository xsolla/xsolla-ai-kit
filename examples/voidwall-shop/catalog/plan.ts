import { BUNDLES, BOOSTERS, CORES_SKU, GEAR, GROUPS, PACKS, SCRAP_SKU, SKINS } from './catalog';
import {
  buildBooster, buildBundle, buildCurrency, buildGear, buildGroup, buildPack, buildPass, buildSkin,
} from './payloads';

export type Kind = 'group' | 'currency' | 'package' | 'item' | 'bundle';
export interface PlanStep {
  kind: Kind;
  key: string;
  payload: Record<string, any>;
  /** True if the public catalog should return it today (shown, enabled, not date-windowed). */
  expectInStore: boolean;
}

const step = (kind: Kind, key: string, payload: Record<string, any>): PlanStep => ({
  kind, key, payload,
  expectInStore: kind !== 'group' && payload.is_show_in_store === true && !payload.periods,
});

export function buildPlan(): PlanStep[] {
  const itemNames = Object.fromEntries([...SKINS, ...GEAR, ...BOOSTERS].map((i) => [i.sku, i.name]));
  return [
    ...GROUPS.map((g) => step('group', g.id, buildGroup(g))),
    step('currency', CORES_SKU, buildCurrency(CORES_SKU, 'Cores', 'cores')),
    step('currency', SCRAP_SKU, buildCurrency(SCRAP_SKU, 'Scrap', 'scrap')),
    ...SKINS.map((s) => step('item', s.sku, buildSkin(s))),
    ...GEAR.map((g) => step('item', g.sku, buildGear(g))),
    ...BOOSTERS.map((b) => step('item', b.sku, buildBooster(b))),
    step('item', 'pass_s1_frontier', buildPass()),
    ...PACKS.map((p) => step('package', p.sku, buildPack(p))),
    ...BUNDLES.map((b) => step('bundle', b.sku, buildBundle(b, itemNames))),
  ];
}

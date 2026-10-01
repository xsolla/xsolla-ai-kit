import { BOOSTERS, BUNDLES, GEAR, GROUPS, PACKS, PASS, SKINS } from '../../catalog/catalog';
import type { GroupDef, GroupId } from '../../catalog/types';
import type { ShopItem } from './store';

const KNOWN = new Set<string>([
  ...PACKS, ...SKINS, ...GEAR, ...BOOSTERS, ...BUNDLES, PASS,
].map((d) => d.sku));

const GROUP_BY_SKU = new Map<string, GroupId>([
  ...SKINS.map((s) => [s.sku, 'turret_skins'] as const),
  ...GEAR.map((g) => [g.sku, 'warden_gear'] as const),
  ...BOOSTERS.map((b) => [b.sku, 'boosters'] as const),
  [PASS.sku, 'passes'] as const,
]);

/** The project also holds unrelated quest fixtures; only Voidwall SKUs are rendered. */
export const knownItems = (items: ShopItem[]) => items.filter((i) => KNOWN.has(i.sku));

export function groupOf(item: ShopItem): GroupId {
  if (item.kind === 'package') return 'currency';
  if (item.kind === 'bundle') return 'bundles';
  return GROUP_BY_SKU.get(item.sku) ?? 'turret_skins';
}

export const byGroup = (items: ShopItem[], id: GroupId) => items.filter((i) => groupOf(i) === id);

export const visibleGroups = (items: ShopItem[]): GroupDef[] =>
  GROUPS.filter((g) => byGroup(items, g.id).length > 0);

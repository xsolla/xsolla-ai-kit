import type {
  BoosterDef, BundleDef, GearDef, GroupDef, PackDef, PassDef, SkinDef,
} from './types';

export const CORES_SKU = 'cores';
export const SCRAP_SKU = 'scrap';
export const SEASON_ONE = { from: '2026-10-14T00:00:00+00:00', until: '2027-01-13T23:59:59+00:00' };

export const GROUPS: GroupDef[] = [
  { id: 'currency', order: 1, names: { en: 'Currency', fr: 'Monnaie', de: 'Währung', ja: '通貨', 'pt-BR': 'Moeda' } },
  { id: 'turret_skins', order: 2, names: { en: 'Turret Skins', fr: 'Skins de tourelle', de: 'Geschützskins', ja: 'タレットスキン', 'pt-BR': 'Skins de torre' } },
  { id: 'warden_gear', order: 3, names: { en: 'Warden Gear', fr: 'Équipement de Gardien', de: 'Wächter-Ausrüstung', ja: 'ウォーデンギア', 'pt-BR': 'Equipamento de Guardião' } },
  { id: 'boosters', order: 4, names: { en: 'Boosters', fr: 'Boosters', de: 'Booster', ja: 'ブースター', 'pt-BR': 'Boosters' } },
  { id: 'bundles', order: 5, names: { en: 'Bundles', fr: 'Packs', de: 'Bundles', ja: 'バンドル', 'pt-BR': 'Pacotes' } },
  { id: 'passes', order: 6, names: { en: 'Passes and Subscriptions', fr: 'Passes et abonnements', de: 'Pässe und Abos', ja: 'パスとサブスクリプション', 'pt-BR': 'Passes e assinaturas' } },
];

export const PACKS: PackDef[] = [
  { sku: 'cores_500', name: 'Core Cache', base: 500, bonus: 0, usd: 4.99, image: 'currency/pack_cache.jpg' },
  { sku: 'cores_1200', name: 'Core Stack', base: 1100, bonus: 100, usd: 9.99, image: 'currency/pack_stack.jpg' },
  { sku: 'cores_2600', name: 'Core Crate', base: 2300, bonus: 300, usd: 19.99, image: 'currency/pack_crate.jpg' },
  { sku: 'cores_7000', name: 'Core Vault', base: 5800, bonus: 1200, usd: 49.99, image: 'currency/pack_vault.jpg' },
  // pack_reactor.jpg does not exist in the asset pack; reuse the generated core icon (known gap 5).
  { sku: 'cores_15000', name: 'Core Reactor', base: 11500, bonus: 3500, usd: 99.99, image: 'currency/cores_svg.jpg' },
];

export const SKINS: SkinDef[] = [
  { sku: 'spitter_skin_obsidian', name: 'Obsidian', turretClass: 'Spitter', rarity: 'Rare', cores: 800 },
  { sku: 'spitter_skin_huntsman', name: 'Huntsman', turretClass: 'Spitter', rarity: 'Epic', cores: 1500 },
  { sku: 'arclight_skin_voltaic', name: 'Voltaic', turretClass: 'Arclight', rarity: 'Rare', cores: 800 },
  { sku: 'arclight_skin_solarflare', name: 'Solar Flare', turretClass: 'Arclight', rarity: 'Legendary', cores: 2400 },
  { sku: 'bulwark_skin_ironclad', name: 'Ironclad', turretClass: 'Bulwark', rarity: 'Rare', cores: 800 },
  { sku: 'bulwark_skin_warlord', name: 'Warlord', turretClass: 'Bulwark', rarity: 'Epic', cores: 1500 },
  { sku: 'hailstorm_skin_frostbite', name: 'Frostbite', turretClass: 'Hailstorm', rarity: 'Epic', cores: 1500 },
  { sku: 'hailstorm_skin_tempest', name: 'Tempest', turretClass: 'Hailstorm', rarity: 'Legendary', cores: 2400 },
  { sku: 'lancer_skin_longshot', name: 'Longshot', turretClass: 'Lancer', rarity: 'Rare', cores: 800 },
  { sku: 'lancer_skin_deadeye', name: 'Deadeye', turretClass: 'Lancer', rarity: 'Legendary', cores: 2400 },
  { sku: 'tether_skin_anchor', name: 'Anchor', turretClass: 'Tether', rarity: 'Rare', cores: 800 },
];

export const GEAR: GearDef[] = [
  { sku: 'warden_armor_frontier', name: 'Frontier Issue', kind: 'armor', rarity: 'Common', cores: 400 },
  { sku: 'warden_armor_vanguard', name: 'Vanguard Plate', kind: 'armor', rarity: 'Epic', cores: 1200 },
  { sku: 'warden_emote_salute', name: 'Salute', kind: 'emote', rarity: 'Common', cores: 250 },
  { sku: 'warden_decal_rimehunter', name: 'Rime Hunter', kind: 'decal', rarity: 'Common', cores: 300 },
  // Bundle-only title. Price is an assumption (known gap 4). Hidden from the store.
  { sku: 'warden_title_plankowner', name: 'Plank Owner', kind: 'title', rarity: 'Legendary', cores: 1500, hidden: true },
];

export const BOOSTERS: BoosterDef[] = [
  { sku: 'booster_salvage_24h', name: 'Salvage Surge (24h)', effect: 'salvage', duration: '24h', cores: 300, dailyLimit: 5 },
  { sku: 'booster_xp_24h', name: 'Field Promotion (24h)', effect: 'xp', duration: '24h', cores: 300, dailyLimit: 5 },
  { sku: 'booster_salvage_7d', name: 'Salvage Surge (7 days)', effect: 'salvage', duration: '7d', cores: 1200 },
];

export const BUNDLES: BundleDef[] = [
  {
    sku: 'bundle_frontier_starter', name: 'Frontier Starter Pack', usd: 9.99, limitPerUser: 1,
    contents: [{ sku: 'cores', quantity: 1200 }, { sku: 'spitter_skin_obsidian', quantity: 1 }, { sku: 'booster_salvage_24h', quantity: 1 }],
    image: 'bundles/starter.jpg',
  },
  {
    // Priced in USD because the bundle Admin endpoint drops vc_prices (known gap 3).
    sku: 'bundle_wardens_arsenal', name: "Warden's Arsenal", usd: 29.99,
    contents: [
      { sku: 'spitter_skin_huntsman', quantity: 1 }, { sku: 'arclight_skin_voltaic', quantity: 1 },
      { sku: 'bulwark_skin_ironclad', quantity: 1 }, { sku: 'lancer_skin_longshot', quantity: 1 },
    ],
    image: 'bundles/arsenal.jpg',
  },
  {
    sku: 'bundle_rime_hunter', name: 'Rime Hunter Bundle', usd: 14.99,
    contents: [{ sku: 'lancer_skin_deadeye', quantity: 1 }, { sku: 'warden_emote_salute', quantity: 1 }, { sku: 'warden_decal_rimehunter', quantity: 1 }],
    image: 'bundles/rime_hunter.jpg',
  },
  {
    // 30 days of Warden's Charter is omitted (known gap 2).
    sku: 'bundle_founders', name: "Founder's Pack", usd: 49.99, limitPerUser: 1, window: SEASON_ONE,
    contents: [
      { sku: 'warden_armor_vanguard', quantity: 1 }, { sku: 'arclight_skin_solarflare', quantity: 1 },
      { sku: 'hailstorm_skin_tempest', quantity: 1 }, { sku: 'cores', quantity: 7000 },
      { sku: 'warden_title_plankowner', quantity: 1 },
    ],
    image: 'bundles/founders.jpg',
  },
];

export const PASS: PassDef = {
  sku: 'pass_s1_frontier', name: 'Frontier Pass, Season 1: Cold Open', usd: 9.99,
  window: SEASON_ONE, image: 'passes/frontier_pass_s1.jpg',
};

/** Display-only. Not seeded (known gap 1). */
export const CHARTER = { sku: 'sub_wardens_charter', name: "Warden's Charter", usd: 7.99, image: 'passes/wardens_charter.jpg' };

const cores = (sku: string): number | undefined =>
  SKINS.find((s) => s.sku === sku)?.cores ?? GEAR.find((g) => g.sku === sku)?.cores ?? BOOSTERS.find((b) => b.sku === sku)?.cores;

/** Sum of what the contents would cost individually, in Cores. */
export function coresValue(b: BundleDef): number {
  return b.contents.reduce((sum, c) => sum + (c.sku === CORES_SKU ? c.quantity : (cores(c.sku) ?? 0) * c.quantity), 0);
}

export const IMAGES: Record<string, string> = {
  [CORES_SKU]: 'currency/cores.jpg',
  [SCRAP_SKU]: 'currency/scrap.jpg',
  ...Object.fromEntries(PACKS.map((p) => [p.sku, p.image])),
  ...Object.fromEntries(SKINS.map((s) => [s.sku, `skins/${s.sku}.jpg`])),
  ...Object.fromEntries(GEAR.filter((g) => g.kind !== 'title').map((g) => [g.sku, `gear/${g.sku}.jpg`])),
  ...Object.fromEntries(BOOSTERS.map((b) => [b.sku, `boosters/${b.sku}.jpg`])),
  ...Object.fromEntries(BUNDLES.map((b) => [b.sku, b.image])),
  [PASS.sku]: PASS.image,
  [CHARTER.sku]: CHARTER.image,
};

export const LOCALES = ['en', 'fr', 'de', 'ja', 'pt-BR'] as const;
export type Locale = (typeof LOCALES)[number];
export type L10n = Record<Locale, string>;

export const CURRENCIES = ['USD', 'EUR', 'GBP', 'BRL', 'JPY'] as const;
export type Currency = (typeof CURRENCIES)[number];

export type Rarity = 'Common' | 'Rare' | 'Epic' | 'Legendary';
export type TurretClass = 'Spitter' | 'Arclight' | 'Bulwark' | 'Hailstorm' | 'Lancer' | 'Tether';
export type GroupId = 'currency' | 'turret_skins' | 'warden_gear' | 'boosters' | 'bundles' | 'passes';

export interface Window { from: string; until: string }

export interface GroupDef { id: GroupId; order: number; names: L10n }
export interface PackDef { sku: string; name: string; base: number; bonus: number; usd: number; image: string }
export interface SkinDef { sku: string; name: string; turretClass: TurretClass; rarity: Rarity; cores: number }
export interface GearDef {
  sku: string; name: string; kind: 'armor' | 'emote' | 'decal' | 'title'; rarity: Rarity; cores: number;
  hidden?: boolean;
}
export interface BoosterDef {
  sku: string; name: string; effect: 'salvage' | 'xp'; duration: '24h' | '7d'; cores: number; dailyLimit?: number;
}
export interface BundleDef {
  sku: string; name: string; usd: number; contents: { sku: string; quantity: number }[];
  image: string; limitPerUser?: number; window?: Window;
}
export interface PassDef { sku: string; name: string; usd: number; window: Window; image: string }

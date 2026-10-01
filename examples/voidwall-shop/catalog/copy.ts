import { LOCALES, type L10n, type Locale } from './types';

export type CopyKind =
  | 'skin' | 'armor' | 'emote' | 'decal' | 'title' | 'booster' | 'pack' | 'bundle' | 'pass' | 'cores' | 'scrap';

export interface Vars {
  rarity?: string; cls?: string; effect?: 'salvage' | 'xp'; duration?: '24h' | '7d';
  total?: number; bonus?: number; list?: string;
}

const RARITY: Record<string, L10n> = {
  Common: { en: 'Common', fr: 'Commun', de: 'Gewöhnlich', ja: 'コモン', 'pt-BR': 'Comum' },
  Rare: { en: 'Rare', fr: 'Rare', de: 'Selten', ja: 'レア', 'pt-BR': 'Raro' },
  Epic: { en: 'Epic', fr: 'Épique', de: 'Episch', ja: 'エピック', 'pt-BR': 'Épico' },
  Legendary: { en: 'Legendary', fr: 'Légendaire', de: 'Legendär', ja: 'レジェンダリー', 'pt-BR': 'Lendário' },
};
const EFFECT: Record<string, L10n> = {
  salvage: { en: '2× Scrap', fr: '2× Scrap', de: '2× Scrap', ja: 'Scrap 2倍', 'pt-BR': '2× Scrap' },
  xp: { en: '2× Warden XP', fr: '2× XP de Gardien', de: '2× Wächter-XP', ja: 'ウォーデンXP 2倍', 'pt-BR': '2× XP de Guardião' },
};
const DURATION: Record<string, L10n> = {
  '24h': { en: '24 hours', fr: '24 heures', de: '24 Stunden', ja: '24時間', 'pt-BR': '24 horas' },
  '7d': { en: '7 days', fr: '7 jours', de: '7 Tage', ja: '7日間', 'pt-BR': '7 dias' },
};

type Tpl = Record<Locale, (v: Vars, l: Locale) => string>;
const n = (x: number | undefined, l: Locale) => new Intl.NumberFormat(l).format(x ?? 0);
const r = (v: Vars, l: Locale) => RARITY[v.rarity ?? 'Common']![l];

const TEMPLATES: Record<CopyKind, Tpl> = {
  skin: {
    en: (v, l) => `${v.cls} skin (${r(v, l)}). Cosmetic only, no stat changes.`,
    fr: (v, l) => `Skin ${v.cls} (${r(v, l)}). Cosmétique uniquement, aucun effet sur les stats.`,
    de: (v, l) => `${v.cls}-Skin (${r(v, l)}). Nur kosmetisch, keine Werteänderungen.`,
    ja: (v, l) => `${v.cls}スキン(${r(v, l)})。見た目のみで、性能は変わりません。`,
    'pt-BR': (v, l) => `Skin de ${v.cls} (${r(v, l)}). Apenas cosmético, sem alterar atributos.`,
  },
  armor: {
    en: () => 'Warden armor set. Cosmetic only.', fr: () => 'Armure de Gardien. Cosmétique uniquement.',
    de: () => 'Wächter-Rüstung. Nur kosmetisch.', ja: () => 'ウォーデン用アーマー。見た目のみ。',
    'pt-BR': () => 'Armadura de Guardião. Apenas cosmética.',
  },
  emote: {
    en: () => 'A Warden emote. Cosmetic only.', fr: () => 'Une emote de Gardien. Cosmétique uniquement.',
    de: () => 'Eine Wächter-Emote. Nur kosmetisch.', ja: () => 'ウォーデン用エモート。見た目のみ。',
    'pt-BR': () => 'Um emote de Guardião. Apenas cosmético.',
  },
  decal: {
    en: () => 'A decal for your Warden gear. Cosmetic only.', fr: () => "Un décalque pour l'équipement de Gardien. Cosmétique uniquement.",
    de: () => 'Ein Decal für die Wächter-Ausrüstung. Nur kosmetisch.', ja: () => 'ウォーデンギア用デカール。見た目のみ。',
    'pt-BR': () => 'Um decalque para o equipamento de Guardião. Apenas cosmético.',
  },
  title: {
    en: () => 'An exclusive profile title.', fr: () => 'Un titre de profil exclusif.',
    de: () => 'Ein exklusiver Profiltitel.', ja: () => '限定プロフィールタイトル。', 'pt-BR': () => 'Um título de perfil exclusivo.',
  },
  booster: {
    en: (v, l) => `${EFFECT[v.effect!]![l]} for ${DURATION[v.duration!]![l]}.`,
    fr: (v, l) => `${EFFECT[v.effect!]![l]} pendant ${DURATION[v.duration!]![l]}.`,
    de: (v, l) => `${EFFECT[v.effect!]![l]} für ${DURATION[v.duration!]![l]}.`,
    ja: (v, l) => `${DURATION[v.duration!]![l]}、${EFFECT[v.effect!]![l]}。`,
    'pt-BR': (v, l) => `${EFFECT[v.effect!]![l]} por ${DURATION[v.duration!]![l]}.`,
  },
  pack: {
    en: (v, l) => (v.bonus ? `${n(v.total, l)} Cores (includes ${n(v.bonus, l)} bonus).` : `${n(v.total, l)} Cores.`),
    fr: (v, l) => (v.bonus ? `${n(v.total, l)} Cores (dont ${n(v.bonus, l)} bonus).` : `${n(v.total, l)} Cores.`),
    de: (v, l) => (v.bonus ? `${n(v.total, l)} Cores (inkl. ${n(v.bonus, l)} Bonus).` : `${n(v.total, l)} Cores.`),
    ja: (v, l) => (v.bonus ? `${n(v.total, l)} Cores(ボーナス${n(v.bonus, l)}含む)。` : `${n(v.total, l)} Cores。`),
    'pt-BR': (v, l) => (v.bonus ? `${n(v.total, l)} Cores (inclui ${n(v.bonus, l)} de bônus).` : `${n(v.total, l)} Cores.`),
  },
  bundle: {
    en: (v) => `Includes: ${v.list}.`, fr: (v) => `Contient : ${v.list}.`, de: (v) => `Enthält: ${v.list}.`,
    ja: (v) => `内容: ${v.list}。`, 'pt-BR': (v) => `Inclui: ${v.list}.`,
  },
  pass: {
    en: () => 'Season 1: Cold Open. Unlocks the premium reward track.',
    fr: () => 'Saison 1 : Cold Open. Débloque la piste de récompenses premium.',
    de: () => 'Saison 1: Cold Open. Schaltet die Premium-Belohnungsleiste frei.',
    ja: () => 'シーズン1「Cold Open」。プレミアム報酬トラックを解放します。',
    'pt-BR': () => 'Temporada 1: Cold Open. Libera a trilha de recompensas premium.',
  },
  cores: {
    en: () => 'Premium currency of Voidwall.', fr: () => 'La monnaie premium de Voidwall.',
    de: () => 'Die Premium-Währung von Voidwall.', ja: () => 'Voidwallのプレミアム通貨。', 'pt-BR': () => 'A moeda premium de Voidwall.',
  },
  scrap: {
    en: () => 'Soft currency earned in play.', fr: () => 'Monnaie gratuite gagnée en jouant.',
    de: () => 'Weiche Währung, die du im Spiel verdienst.', ja: () => 'プレイで手に入るソフトカレンシー。',
    'pt-BR': () => 'Moeda comum ganha jogando.',
  },
};

const NAME_OVERRIDES: Record<string, Partial<L10n>> = {
  spitter_skin_obsidian: { fr: 'Obsidienne', ja: 'オブシディアン', 'pt-BR': 'Obsidiana' },
};
const DESC_OVERRIDES: Record<string, L10n> = {
  spitter_skin_obsidian: {
    en: 'A matte-black Spitter chassis cut from salvaged Well plating.',
    fr: "Un châssis de Spitter noir mat, taillé dans le blindage récupéré d'un Puits.",
    de: 'Ein mattschwarzes Spitter-Chassis aus geborgener Well-Panzerung.',
    ja: 'ウェルの装甲を再利用した、つや消しブラックのスピッター機体。',
    'pt-BR': 'Um chassi Spitter preto fosco forjado com blindagem recuperada de um Poço.',
  },
};

export function nameFor(sku: string, enName: string, locale: Locale): string {
  return NAME_OVERRIDES[sku]?.[locale] ?? enName;
}

export function descFor(sku: string, kind: CopyKind, vars: Vars, locale: Locale): string {
  return DESC_OVERRIDES[sku]?.[locale] ?? TEMPLATES[kind][locale](vars, locale);
}

export const allLocales = (f: (l: Locale) => string): L10n =>
  Object.fromEntries(LOCALES.map((l) => [l, f(l)])) as L10n;

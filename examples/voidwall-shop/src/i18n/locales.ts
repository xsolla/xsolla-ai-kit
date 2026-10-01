import { LOCALES, type Locale } from '../../catalog/types';

export { LOCALES };
export type { Locale };

/** Store API `locale` query value. Brazilian Portuguese is stored under `pt`; `pt_BR` silently returns English. */
export const STORE_LOCALE: Record<Locale, string> = { en: 'en', fr: 'fr', de: 'de', ja: 'ja', 'pt-BR': 'pt' };
/** Headless Checkout / token `settings.language`. Unsupported shop locales must map to 'en'. */
export const PAY_LANGUAGE: Record<Locale, string> = { en: 'en', fr: 'fr', de: 'de', ja: 'ja', 'pt-BR': 'pt' };
/** Login widget `preferredLocale`. */
export const LOGIN_LOCALE: Record<Locale, string> = { en: 'en_US', fr: 'fr_FR', de: 'de_DE', ja: 'ja_JP', 'pt-BR': 'pt_BR' };

export const LOCALE_LABEL: Record<Locale, string> = { en: 'EN', fr: 'FR', de: 'DE', ja: '日本語', 'pt-BR': 'PT-BR' };

export function resolveLocale(raw: string | null | undefined): Locale {
  return (LOCALES as readonly string[]).includes(raw ?? '') ? (raw as Locale) : 'en';
}

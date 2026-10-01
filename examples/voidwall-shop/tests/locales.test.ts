import { expect, test } from 'vitest';
import { PAY_LANGUAGE, STORE_LOCALE, resolveLocale } from '../src/i18n/locales';

test('resolveLocale falls back to en for junk', () => {
  expect(resolveLocale('fr')).toBe('fr');
  expect(resolveLocale('pt-BR')).toBe('pt-BR');
  for (const bad of [null, undefined, '', 'xx', 'FR', '{"a":1}']) expect(resolveLocale(bad)).toBe('en');
});

test('code maps cover every locale', () => {
  for (const l of ['en', 'fr', 'de', 'ja', 'pt-BR'] as const) {
    expect(STORE_LOCALE[l]).toBeTruthy();
    expect(PAY_LANGUAGE[l]).toBeTruthy();
  }
});

test('Store API stores Brazilian Portuguese under pt (locale=pt_BR silently returns English)', () => {
  expect(STORE_LOCALE['pt-BR']).toBe('pt');
});

import { expect, test } from 'vitest';
import { LOCALES } from '../catalog/types';
import { descFor, nameFor } from '../catalog/copy';

test('Obsidian worked example from CONTEXT.md', () => {
  expect(nameFor('spitter_skin_obsidian', 'Obsidian', 'fr')).toBe('Obsidienne');
  expect(nameFor('spitter_skin_obsidian', 'Obsidian', 'ja')).toBe('オブシディアン');
  expect(nameFor('spitter_skin_obsidian', 'Obsidian', 'pt-BR')).toBe('Obsidiana');
  expect(descFor('spitter_skin_obsidian', 'skin', { rarity: 'Rare', cls: 'Spitter' }, 'en'))
    .toBe('A matte-black Spitter chassis cut from salvaged Well plating.');
});

test('every kind has non-empty copy in all five locales and no em dash', () => {
  const kinds = ['skin', 'armor', 'emote', 'decal', 'title', 'booster', 'pack', 'bundle', 'pass', 'cores', 'scrap'] as const;
  for (const kind of kinds) {
    for (const l of LOCALES) {
      const text = descFor('x', kind, {
        rarity: 'Rare', cls: 'Lancer', effect: 'salvage', duration: '24h', total: 1200, bonus: 100, list: 'A, B',
      }, l);
      expect(text.length, `${kind}/${l}`).toBeGreaterThan(5);
      expect(text).not.toContain(String.fromCharCode(0x2014));
    }
  }
});

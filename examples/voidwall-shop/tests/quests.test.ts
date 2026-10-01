import { expect, test } from 'vitest';
import { normalizeQuests, questsUrl, safeImageUrl } from '../src/quests/api';

test('questsUrl defaults to the production public host and honours an override', () => {
  expect(questsUrl('1', '2')).toBe('https://quests-platform.xsolla.com/api/v2/public/merchants/1/projects/2/quests?page=1&limit=100');
  expect(questsUrl('1', '2', 'https://example.test/')).toBe('https://example.test/api/v2/public/merchants/1/projects/2/quests?page=1&limit=100');
});

test('safeImageUrl keeps only absolute http(s) URLs', () => {
  expect(safeImageUrl('https://cdn.test/a.png')).toBe('https://cdn.test/a.png');
  for (const bad of ['/a.png', 'javascript:alert(1)', 'data:image/png;base64,AA', null, undefined, 5]) expect(safeImageUrl(bad)).toBeUndefined();
});

test('normalizeQuests skips nulls, bad images and malformed quests', () => {
  const quests = normalizeQuests({ data: [
    { id: 'a', name: 'Slay', description: null, rewards: [{ name: null, description: null, image_url: 'javascript:x', quantity: 2, type: 'web3_item' }] },
    { id: 'b', name: 'No rewards' },
    { name: 'no id' },
  ] });
  expect(quests.map((q) => q.id)).toEqual(['a', 'b']);
  expect(quests[0].description).toBeUndefined();
  expect(quests[0].rewards[0]).toEqual({ name: undefined, description: undefined, imageUrl: undefined, quantity: 2, type: 'web3_item' });
  expect(quests[1].rewards).toEqual([]);
});

test('normalizeQuests accepts an empty page and rejects a bad envelope', () => {
  expect(normalizeQuests({ page: 1, limit: 100, total: 0, data: [] })).toEqual([]);
  expect(() => normalizeQuests({})).toThrow();
});

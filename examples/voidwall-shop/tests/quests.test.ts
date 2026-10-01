import { expect, test, vi } from 'vitest';
import { QP_PRODUCTION_BASE, fetchQuests, parseQuests, questsUrl, safeImageUrl } from '../src/quests/api';

const scope = { merchantId: '1', projectId: '2' };

test('builds the public list URL on the production host by default', () => {
  expect(questsUrl(scope)).toBe(`${QP_PRODUCTION_BASE}/api/v2/public/merchants/1/projects/2/quests?page=1&limit=100`);
  expect(questsUrl({ ...scope, baseUrl: 'https://example.test/' })).toMatch(/^https:\/\/example\.test\/api\/v2\/public\//);
});

test('missing scope yields no URL and fetch rejects instead of returning empty', async () => {
  expect(questsUrl({ merchantId: '', projectId: '2' })).toBeNull();
  await expect(fetchQuests({ merchantId: '', projectId: '' })).rejects.toThrow();
});

test('only absolute http(s) image URLs are accepted', () => {
  expect(safeImageUrl('https://cdn.test/a.png')).toBe('https://cdn.test/a.png');
  for (const bad of ['/a.png', 'javascript:alert(1)', 'data:image/png;base64,AA', null, 5]) expect(safeImageUrl(bad)).toBeNull();
});

test('parse skips null reward fields and bad images, keeps empty data as empty', () => {
  const quests = parseQuests({ data: [{ id: 'q1', name: 'Q', description: null, rewards: [
    { name: null, description: null, image_url: 'javascript:x', quantity: 2, type: 'web3_item' }] }] });
  expect(quests[0]).toMatchObject({ id: 'q1', description: null });
  expect(quests[0].rewards[0]).toMatchObject({ name: null, imageUrl: null, quantity: 2 });
  expect(parseQuests({ data: [] })).toEqual([]);
  expect(() => parseQuests({})).toThrow();
});

test('non-200 and network failures reject; request sends no credentials', async () => {
  const f = vi.fn().mockResolvedValue({ status: 404, json: async () => ({}) });
  vi.stubGlobal('fetch', f);
  await expect(fetchQuests(scope)).rejects.toThrow('404');
  expect(f.mock.calls[0][1]).toMatchObject({ credentials: 'omit' });
  f.mockRejectedValue(new TypeError('cors'));
  await expect(fetchQuests(scope)).rejects.toThrow();
  vi.unstubAllGlobals();
});

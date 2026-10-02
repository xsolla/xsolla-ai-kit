import { expect, test } from 'vitest';
import { questSource } from '../src/config';
import { fetchQuests, parsePage, questsUrl, safeImageUrl, type QuestSource } from '../src/quests/api';

const src: QuestSource = { baseUrl: 'https://quests-platform.xsolla.com/', merchantId: '1', projectId: '2' };
const reward = { name: 'Ice Sword', description: null, image_url: 'https://cdn.example/a.png', quantity: 1, type: 'web3_item' };

test('questsUrl targets the public list, trims the base, no credentials in the url', () => {
  expect(questsUrl(src, 1)).toBe('https://quests-platform.xsolla.com/api/v2/public/merchants/1/projects/2/quests?page=1&limit=100');
});

test('safeImageUrl keeps only absolute http(s)', () => {
  expect(safeImageUrl('https://a.b/c.png')).toBe('https://a.b/c.png');
  for (const bad of ['/rel.png', 'javascript:alert(1)', 'data:image/png;base64,AA', null, undefined, 5]) expect(safeImageUrl(bad)).toBeNull();
});

test('parsePage skips null reward fields and unsafe images, omits an absent description', () => {
  const { quests } = parsePage({ total: 1, data: [{ id: 'q1', name: 'Q', rewards: [{ ...reward, name: null, image_url: 'javascript:x' }, reward] }] });
  expect(quests[0]).not.toHaveProperty('description');
  expect(quests[0].rewards[0]).toMatchObject({ name: null, imageUrl: null, quantity: 1 });
  expect(quests[0].rewards[1].imageUrl).toBe('https://cdn.example/a.png');
});

test('parsePage rejects a malformed body instead of returning an empty list', () => {
  expect(() => parsePage({})).toThrow();
  expect(() => parsePage(null)).toThrow();
});

const respond = (body: unknown, status = 200) => (async () => new Response(JSON.stringify(body), { status })) as unknown as typeof fetch;

test('fetchQuests returns an empty list only for a 200 with data: []', async () => {
  expect(await fetchQuests(src, respond({ page: 1, limit: 100, total: 0, data: [] }))).toEqual([]);
});

test('fetchQuests throws on HTTP errors and never sends credentials', async () => {
  await expect(fetchQuests(src, respond({ error: 'Project not found' }, 404))).rejects.toThrow();
  let init: RequestInit | undefined;
  const spy = (async (_u: unknown, i?: RequestInit) => { init = i; return new Response(JSON.stringify({ total: 0, data: [] })); }) as unknown as typeof fetch;
  await fetchQuests(src, spy);
  expect(init?.credentials).toBe('omit');
});

test('fetchQuests pages until total is covered', async () => {
  const urls: string[] = [];
  const f = (async (u: string) => {
    urls.push(u);
    const page = Number(new URL(u).searchParams.get('page'));
    const data = Array.from({ length: page === 1 ? 100 : 1 }, (_, i) => ({ id: `q${page}-${i}`, name: 'Q', rewards: [] }));
    return new Response(JSON.stringify({ total: 101, data }));
  }) as unknown as typeof fetch;
  expect(await fetchQuests(src, f)).toHaveLength(101);
  expect(urls).toHaveLength(2);
});

test('questSource needs both ids, defaults to the production host, accepts only an http(s) override', () => {
  expect(questSource({ qpMerchantId: '', qpProjectId: '2', qpBaseUrl: '' })).toBeNull();
  expect(questSource({ qpMerchantId: '1', qpProjectId: '', qpBaseUrl: '' })).toBeNull();
  expect(questSource({ qpMerchantId: '1', qpProjectId: '2', qpBaseUrl: '' })?.baseUrl).toBe('https://quests-platform.xsolla.com');
  expect(questSource({ qpMerchantId: '1', qpProjectId: '2', qpBaseUrl: 'javascript:1' })?.baseUrl).toBe('https://quests-platform.xsolla.com');
  expect(questSource({ qpMerchantId: '1', qpProjectId: '2', qpBaseUrl: 'https://x.example/path' })?.baseUrl).toBe('https://x.example');
});

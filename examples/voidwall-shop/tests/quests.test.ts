import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { expect, test, vi } from 'vitest';
import { QUEST_COPY, QuestsUnavailableError, fetchQuests, parseQuests, questsUrl, safeImageUrl } from '../src/quests/api';
import { QuestModuleView, type QuestState } from '../src/quests/XsollaQuestModule';

const cfg = { baseUrl: 'https://quests-platform.xsolla.com/', merchantId: '1', projectId: '2' };
const view = (state: QuestState) => renderToStaticMarkup(createElement(QuestModuleView, { state, locale: 'en' }));

test('url targets the public list with the max page size', () => {
  expect(questsUrl(cfg)).toBe('https://quests-platform.xsolla.com/api/v2/public/merchants/1/projects/2/quests?page=1&limit=100');
});

test('images: only absolute http(s)', () => {
  expect(safeImageUrl('https://x.test/a.png')).toBe('https://x.test/a.png');
  for (const bad of ['javascript:alert(1)', 'data:image/png;base64,AA', '/rel.png', 'rel.png', null, '']) expect(safeImageUrl(bad)).toBeNull();
});

test('parse keeps null reward fields as null and drops malformed quests', () => {
  const q = parseQuests({ data: [
    { id: 'a', name: 'Q', rewards: [{ name: null, description: null, image_url: null, quantity: 1, type: 'web3_item' }] },
    { name: 'no id', rewards: [] },
  ] });
  expect(q).toHaveLength(1);
  expect(q[0].rewards[0]).toMatchObject({ name: null, imageUrl: null, quantity: 1 });
});

test('fetch sends no credentials and treats failures as unavailable, not empty', async () => {
  const ok = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ data: [] }) });
  expect(await fetchQuests(cfg, ok as any)).toEqual([]);
  expect(ok.mock.calls[0][1]).toMatchObject({ credentials: 'omit' });
  expect(ok.mock.calls[0][1].headers).toBeUndefined();
  const bad = vi.fn().mockResolvedValue({ ok: false, status: 404 });
  await expect(fetchQuests(cfg, bad as any)).rejects.toBeInstanceOf(QuestsUnavailableError);
  await expect(fetchQuests({ ...cfg, projectId: '' }, ok as any)).rejects.toBeInstanceOf(QuestsUnavailableError);
});

test('every state renders the marked section; empty and error stay visible', () => {
  for (const s of [{ status: 'loading' }, { status: 'error' }, { status: 'ready', quests: [] }] as QuestState[])
    expect(view(s)).toContain('data-xsolla-quest-module="1"');
  expect(view({ status: 'ready', quests: [] })).toContain(QUEST_COPY.empty);
  expect(view({ status: 'error' })).toContain(QUEST_COPY.unavailable);
  expect(view({ status: 'loading' })).toContain(QUEST_COPY.disclaimer);
});

test('API strings are escaped and unsafe images are replaced by a placeholder', () => {
  const html = view({ status: 'ready', quests: [{ id: 'a', name: '<img src=x onerror=1>', rewards: [
    { name: 'Sword', description: null, imageUrl: null, quantity: 2, type: 'web3_item' }] }] });
  expect(html).not.toContain('<img src=x');
  expect(html).toContain('&lt;img src=x onerror=1&gt;');
  expect(html).toContain('quest-reward-media');
  expect(html).toContain('x2');
});

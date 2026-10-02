export interface QuestReward {
  name: string | null;
  description: string | null;
  imageUrl: string | null;
  quantity: number;
  type: string;
}

export interface Quest {
  id: string;
  name: string;
  description?: string;
  rewards: QuestReward[];
}

export interface QuestSource {
  baseUrl: string;
  merchantId: string;
  projectId: string;
}

const PAGE_LIMIT = 100;
const MAX_PAGES = 10;

export function questsUrl(src: QuestSource, page: number): string {
  const path = `/api/v2/public/merchants/${encodeURIComponent(src.merchantId)}/projects/${encodeURIComponent(src.projectId)}/quests`;
  return `${src.baseUrl.replace(/\/+$/, '')}${path}?page=${page}&limit=${PAGE_LIMIT}`;
}

/** Only absolute http(s) URLs may reach an <img>. Everything else is dropped. */
export function safeImageUrl(raw: unknown): string | null {
  if (typeof raw !== 'string') return null;
  try {
    const u = new URL(raw);
    return u.protocol === 'http:' || u.protocol === 'https:' ? u.toString() : null;
  } catch { return null; }
}

const str = (v: unknown): string | null => (typeof v === 'string' && v.trim() ? v : null);

function parseReward(r: unknown): QuestReward | null {
  if (!r || typeof r !== 'object') return null;
  const o = r as Record<string, unknown>;
  if (typeof o.quantity !== 'number' || typeof o.type !== 'string') return null;
  return { name: str(o.name), description: str(o.description), imageUrl: safeImageUrl(o.image_url), quantity: o.quantity, type: o.type };
}

export function parseQuest(q: unknown): Quest | null {
  if (!q || typeof q !== 'object') return null;
  const o = q as Record<string, unknown>;
  if (typeof o.id !== 'string' || typeof o.name !== 'string' || !Array.isArray(o.rewards)) return null;
  const description = str(o.description);
  return {
    id: o.id, name: o.name, ...(description ? { description } : {}),
    rewards: o.rewards.map(parseReward).filter((r): r is QuestReward => r !== null),
  };
}

export interface QuestPage { quests: Quest[]; total: number }

export function parsePage(json: unknown): QuestPage {
  const o = json as Record<string, unknown> | null;
  if (!o || !Array.isArray(o.data) || typeof o.total !== 'number') throw new Error('Unexpected quest list response');
  return { quests: o.data.map(parseQuest).filter((q): q is Quest => q !== null), total: o.total };
}

/** A failed request is never reported as an empty list: it throws. No credentials are sent. */
export async function fetchQuests(src: QuestSource, fetchImpl: typeof fetch = fetch, signal?: AbortSignal): Promise<Quest[]> {
  const all: Quest[] = [];
  for (let page = 1; page <= MAX_PAGES; page++) {
    const res = await fetchImpl(questsUrl(src, page), { credentials: 'omit', signal });
    if (!res.ok) throw new Error(`Quest list request failed (${res.status})`);
    const { quests, total } = parsePage(await res.json());
    all.push(...quests);
    if (quests.length === 0 || page * PAGE_LIMIT >= total) break;
  }
  return all;
}

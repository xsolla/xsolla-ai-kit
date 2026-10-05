export const QUEST_COPY = {
  disclaimer: 'Quests are configured by the publisher. Rewards are delivered to your Backpack.',
  empty: 'No active quests right now.',
  unavailable: 'Quests are temporarily unavailable.',
  loading: 'Loading quests...',
} as const;

export const QP_PRODUCTION_BASE = 'https://quests-platform.xsolla.com';

export interface QuestReward {
  name: string | null; description: string | null; imageUrl: string | null; quantity: number; type: string;
}
export interface Quest { id: string; name: string; description?: string; rewards: QuestReward[] }

export interface QuestConfig { baseUrl: string; merchantId: string; projectId: string }

export class QuestsUnavailableError extends Error {}

export function questsUrl(c: QuestConfig): string {
  const base = c.baseUrl.replace(/\/+$/, '');
  return `${base}/api/v2/public/merchants/${encodeURIComponent(c.merchantId)}/projects/${encodeURIComponent(c.projectId)}/quests?page=1&limit=100`;
}

/** Only absolute http(s) URLs may reach an <img>. */
export function safeImageUrl(raw: string | null | undefined): string | null {
  if (!raw) return null;
  try {
    const u = new URL(raw);
    return u.protocol === 'http:' || u.protocol === 'https:' ? u.toString() : null;
  } catch { return null; }
}

const str = (v: unknown): string | null => (typeof v === 'string' && v.length > 0 ? v : null);

export function parseQuests(body: unknown): Quest[] {
  const data = (body as { data?: unknown } | null)?.data;
  if (!Array.isArray(data)) throw new QuestsUnavailableError('malformed quest list');
  return data.flatMap((q: any): Quest[] => {
    const id = str(q?.id), name = str(q?.name);
    if (!id || !name) return [];
    const rewards: QuestReward[] = (Array.isArray(q.rewards) ? q.rewards : []).map((r: any) => ({
      name: str(r?.name), description: str(r?.description), imageUrl: safeImageUrl(str(r?.image_url)),
      quantity: Number.isFinite(Number(r?.quantity)) ? Number(r.quantity) : 1, type: str(r?.type) ?? '',
    }));
    const description = str(q.description);
    return [{ id, name, ...(description ? { description } : {}), rewards }];
  });
}

/** No auth header and no credentials: the public list is anonymous. */
export async function fetchQuests(c: QuestConfig, f: typeof fetch = fetch, signal?: AbortSignal): Promise<Quest[]> {
  if (!c.merchantId || !c.projectId) throw new QuestsUnavailableError('quest scope is not configured');
  const res = await f(questsUrl(c), { signal, credentials: 'omit' });
  if (!res.ok) throw new QuestsUnavailableError(`quests ${res.status}`);
  return parseQuests(await res.json());
}

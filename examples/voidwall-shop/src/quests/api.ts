export const QP_PRODUCTION_BASE = 'https://quests-platform.xsolla.com';

export const QUEST_COPY = {
  disclaimer: 'Quests are configured by the publisher. Rewards are delivered to your Backpack.',
  empty: 'No active quests right now.',
  error: 'Quests are temporarily unavailable.',
} as const;

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
  description: string | null;
  rewards: QuestReward[];
}

export interface QuestScope { merchantId: string; projectId: string; baseUrl?: string }

export function questsUrl(scope: QuestScope): string | null {
  if (!scope.merchantId || !scope.projectId) return null;
  const base = (scope.baseUrl || QP_PRODUCTION_BASE).replace(/\/+$/, '');
  return `${base}/api/v2/public/merchants/${encodeURIComponent(scope.merchantId)}/projects/${encodeURIComponent(scope.projectId)}/quests?page=1&limit=100`;
}

/** Only absolute http(s) URLs may reach an <img src>. */
export function safeImageUrl(raw: unknown): string | null {
  if (typeof raw !== 'string') return null;
  try {
    const u = new URL(raw);
    return u.protocol === 'http:' || u.protocol === 'https:' ? u.href : null;
  } catch { return null; }
}

const text = (v: unknown): string | null => (typeof v === 'string' && v.trim() ? v : null);

export function parseQuests(body: unknown): Quest[] {
  const data = (body as { data?: unknown } | null)?.data;
  if (!Array.isArray(data)) throw new Error('Malformed quest list');
  return data.flatMap((q): Quest[] => {
    if (!q || typeof q.id !== 'string' || typeof q.name !== 'string') return [];
    const rewards: unknown[] = Array.isArray(q.rewards) ? q.rewards : [];
    return [{
      id: q.id,
      name: q.name,
      description: text(q.description),
      rewards: rewards.flatMap((r: any): QuestReward[] => r && typeof r === 'object' ? [{
        name: text(r.name),
        description: text(r.description),
        imageUrl: safeImageUrl(r.image_url),
        quantity: Number.isFinite(r.quantity) ? r.quantity : 1,
        type: typeof r.type === 'string' ? r.type : '',
      }] : []),
    }];
  });
}

/** Throws on any non-200, network or parse failure: a failed request is never an empty list. */
export async function fetchQuests(scope: QuestScope, signal?: AbortSignal): Promise<Quest[]> {
  const url = questsUrl(scope);
  if (!url) throw new Error('Quest scope is not configured');
  const res = await fetch(url, { signal, credentials: 'omit' });
  if (res.status !== 200) throw new Error(`Quest list failed: ${res.status}`);
  return parseQuests(await res.json());
}

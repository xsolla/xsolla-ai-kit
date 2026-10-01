export interface QuestReward { name?: string; description?: string; imageUrl?: string; quantity: number; type: string }
export interface Quest { id: string; name: string; description?: string; rewards: QuestReward[] }

const PUBLIC_BASE = 'https://quests-platform.xsolla.com';

export function questsUrl(merchantId: string, projectId: string, baseOverride = ''): string {
  const base = (baseOverride || PUBLIC_BASE).replace(/\/+$/, '');
  return `${base}/api/v2/public/merchants/${encodeURIComponent(merchantId)}/projects/${encodeURIComponent(projectId)}/quests?page=1&limit=100`;
}

/** Only absolute http(s) image URLs are rendered. */
export function safeImageUrl(raw: unknown): string | undefined {
  if (typeof raw !== 'string') return undefined;
  try {
    const u = new URL(raw);
    return u.protocol === 'http:' || u.protocol === 'https:' ? u.href : undefined;
  } catch { return undefined; }
}

const text = (v: unknown): string | undefined => (typeof v === 'string' && v.length > 0 ? v : undefined);

export function normalizeQuests(body: any): Quest[] {
  if (!body || !Array.isArray(body.data)) throw new Error('Unexpected quests response');
  return body.data
    .filter((q: any) => q && typeof q.id === 'string' && typeof q.name === 'string')
    .map((q: any): Quest => ({
      id: q.id, name: q.name, description: text(q.description),
      rewards: (Array.isArray(q.rewards) ? q.rewards : []).map((r: any): QuestReward => ({
        name: text(r?.name), description: text(r?.description), imageUrl: safeImageUrl(r?.image_url),
        quantity: Number.isInteger(r?.quantity) ? r.quantity : 1, type: typeof r?.type === 'string' ? r.type : '',
      })),
    }));
}

export async function fetchQuests(merchantId: string, projectId: string, baseOverride = ''): Promise<Quest[]> {
  const res = await fetch(questsUrl(merchantId, projectId, baseOverride));
  if (!res.ok) throw new Error(`Quests API ${res.status}`);
  return normalizeQuests(await res.json());
}

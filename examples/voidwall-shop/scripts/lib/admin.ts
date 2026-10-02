import type { Kind, PlanStep } from '../../catalog/plan';

export interface AdminResponse { status: number; body: unknown }
export interface Admin {
  call(method: 'GET' | 'POST' | 'PUT', path: string, body?: unknown): Promise<AdminResponse>;
}

export class SeedError extends Error {
  constructor(public step: PlanStep, public res: AdminResponse) {
    super(`${step.kind} ${step.key}: HTTP ${res.status} ${JSON.stringify(res.body)}`);
  }
}

const PATHS: Record<Kind, { collection: string; one: (key: string) => string }> = {
  group: { collection: '/items/groups', one: (k) => `/items/groups/${k}` },
  currency: { collection: '/items/virtual_currency', one: (k) => `/items/virtual_currency/sku/${k}` },
  package: { collection: '/items/virtual_currency/package', one: (k) => `/items/virtual_currency/package/sku/${k}` },
  item: { collection: '/items/virtual_items', one: (k) => `/items/virtual_items/sku/${k}` },
  bundle: { collection: '/items/bundle', one: (k) => `/items/bundle/sku/${k}` },
};

export function createAdmin(cfg: { merchantId: string; projectId: string; apiKey: string }, f: typeof fetch = fetch): Admin {
  const base = `https://store.xsolla.com/api/v2/project/${cfg.projectId}/admin`;
  const auth = `Basic ${Buffer.from(`${cfg.merchantId}:${cfg.apiKey}`).toString('base64')}`;
  return {
    async call(method, path, body) {
      const res = await f(base + path, {
        method,
        headers: { Authorization: auth, 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const text = await res.text();
      let parsed: unknown = undefined;
      try { parsed = text ? JSON.parse(text) : undefined; } catch { parsed = text; }
      return { status: res.status, body: parsed };
    },
  };
}

const ok = (s: number) => s >= 200 && s < 300;

export async function upsert(admin: Admin, step: PlanStep, apply: boolean): Promise<'create' | 'update'> {
  const paths = PATHS[step.kind];
  const existing = await admin.call('GET', paths.one(step.key));
  if (existing.status !== 200 && existing.status !== 404) throw new SeedError(step, existing);
  const exists = existing.status === 200;
  if (!apply) return exists ? 'update' : 'create';
  const res = exists
    ? await admin.call('PUT', paths.one(step.key), step.payload)
    : await admin.call('POST', paths.collection, step.payload);
  if (!ok(res.status)) throw new SeedError(step, res);
  return exists ? 'update' : 'create';
}

export const missingSkus = (expected: string[], found: string[]) => {
  const have = new Set(found);
  return expected.filter((s) => !have.has(s));
};

import { storeBase } from '../api/store';
import type { Session } from '../auth/types';

export class InsufficientCoresError extends Error {
  constructor() { super('Not enough Cores'); }
}

const bearer = (s: Session) => ({ Authorization: `Bearer ${s.accessToken}`, 'Content-Type': 'application/json' });

/** Token Method 1: the browser asks the Store API, so the API key is never involved. */
export async function createCartPaymentToken(
  p: { projectId: string; cartId: string; session: Session; language: string; sandbox: boolean },
  f: typeof fetch = fetch,
): Promise<{ token: string; orderId: number }> {
  const res = await f(`${storeBase(p.projectId)}/payment/cart/${p.cartId}`, {
    method: 'POST',
    headers: bearer(p.session),
    body: JSON.stringify({ sandbox: p.sandbox, settings: { language: p.language } }),
  });
  if (!res.ok) throw new Error(`Payment token request failed: ${res.status}`);
  const j = await res.json();
  return { token: j.token, orderId: j.order_id };
}

export async function buyWithCores(
  p: { projectId: string; sku: string; session: Session }, f: typeof fetch = fetch,
): Promise<{ orderId: number }> {
  const res = await f(`${storeBase(p.projectId)}/payment/item/${encodeURIComponent(p.sku)}/virtual/cores`, {
    method: 'POST', headers: bearer(p.session), body: JSON.stringify({}),
  });
  if (res.status === 422) throw new InsufficientCoresError();
  if (!res.ok) throw new Error(`Cores purchase failed: ${res.status}`);
  const j = await res.json();
  return { orderId: j.order_id };
}

export async function fetchCoresBalance(projectId: string, session: Session, f: typeof fetch = fetch): Promise<number> {
  const res = await f(`${storeBase(projectId)}/user/virtual_currency_balance`, { headers: bearer(session) });
  if (!res.ok) throw new Error(`Balance request failed: ${res.status}`);
  const j = await res.json();
  return Number((j.items ?? []).find((i: any) => i.sku === 'cores')?.amount ?? 0);
}

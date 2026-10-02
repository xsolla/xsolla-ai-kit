import { storeBase, type Money } from '../api/store';

export interface CartLine { sku: string; name: string; quantity: number; price?: Money; imageUrl?: string }
export interface Cart { cartId: string; items: CartLine[]; total?: Money }
export interface CartApi {
  get(): Promise<Cart>;
  setQuantity(sku: string, quantity: number): Promise<void>;
  remove(sku: string): Promise<void>;
  clear(): Promise<void>;
}

const money = (p: any): Money | undefined =>
  p ? { amount: Number(p.amount), amountWithoutDiscount: Number(p.amount_without_discount ?? p.amount), currency: p.currency } : undefined;

export function createCartApi(projectId: string, getHeaders: () => Record<string, string>, f: typeof fetch = fetch): CartApi {
  const base = `${storeBase(projectId)}/cart`;
  const send = async (method: string, path: string, body?: unknown) => {
    const res = await f(`${base}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', ...getHeaders() },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`Cart ${method} ${path} failed: ${res.status}`);
    return res;
  };
  return {
    async get() {
      const j = await (await send('GET', '')).json();
      return {
        cartId: j.cart_id,
        items: (j.items ?? []).map((i: any) => ({
          sku: i.sku, name: i.name, quantity: i.quantity, price: money(i.price), imageUrl: i.image_url ?? undefined,
        })),
        total: money(j.price),
      };
    },
    async setQuantity(sku, quantity) { await send('PUT', `/item/${encodeURIComponent(sku)}`, { quantity }); },
    async remove(sku) { await send('DELETE', `/item/${encodeURIComponent(sku)}`); },
    async clear() { await send('PUT', '/clear'); },
  };
}

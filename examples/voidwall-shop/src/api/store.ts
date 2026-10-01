import type { Locale } from '../../catalog/types';
import { STORE_LOCALE } from '../i18n/locales';

export interface Money { amount: number; amountWithoutDiscount: number; currency: string }
export type ItemKind = 'item' | 'package' | 'bundle';
export interface ShopItem {
  sku: string; kind: ItemKind; name: string; description: string; imageUrl?: string;
  groups: string[]; attributes: Record<string, string>; price?: Money; coresPrice?: number;
}

export class StoreApiError extends Error {
  constructor(public status: number, public url: string) {
    super(`Store API ${status} for ${url}`);
  }
}

export const storeBase = (projectId: string) => `https://store.xsolla.com/api/v2/project/${projectId}`;

export function normalizeItem(raw: any, kind: ItemKind): ShopItem {
  const cores = (raw.virtual_prices ?? []).find((p: any) => p.sku === 'cores');
  const p = raw.price;
  return {
    sku: raw.sku, kind, name: raw.name ?? raw.sku, description: raw.description ?? '',
    imageUrl: raw.image_url ?? undefined,
    groups: (raw.groups ?? []).map((g: any) => g.external_id),
    attributes: Object.fromEntries(
      (raw.attributes ?? []).map((a: any) => [a.external_id, a.values?.[0]?.external_id ?? '']),
    ),
    price: p ? { amount: Number(p.amount), amountWithoutDiscount: Number(p.amount_without_discount ?? p.amount), currency: p.currency } : undefined,
    coresPrice: cores ? Number(cores.amount) : undefined,
  };
}

async function fetchAll(url: string, f: typeof fetch): Promise<any[]> {
  const out: any[] = [];
  for (let offset = 0; ; offset += 50) {
    const sep = url.includes('?') ? '&' : '?';
    const full = `${url}${sep}limit=50&offset=${offset}`;
    const res = await f(full);
    if (!res.ok) throw new StoreApiError(res.status, full);
    const body = await res.json();
    out.push(...(body.items ?? []));
    if (!body.has_more) return out;
  }
}

/** Catalog is read from the browser with no `country`, so Xsolla resolves prices from the buyer's IP. */
export async function fetchCatalog(projectId: string, locale: Locale, f: typeof fetch = fetch): Promise<ShopItem[]> {
  const base = storeBase(projectId);
  const q = `locale=${STORE_LOCALE[locale]}`;
  const [items, packs, bundles] = await Promise.all([
    fetchAll(`${base}/items/virtual_items?${q}`, f),
    fetchAll(`${base}/items/virtual_currency/package?${q}`, f),
    fetchAll(`${base}/items/bundle?${q}`, f),
  ]);
  return [
    ...items.map((r) => normalizeItem(r, 'item')),
    ...packs.map((r) => normalizeItem(r, 'package')),
    ...bundles.map((r) => normalizeItem(r, 'bundle')),
  ];
}

export function formatMoney(m: Money | undefined, locale: Locale): string {
  if (!m || Number.isNaN(m.amount)) return '';
  return new Intl.NumberFormat(locale, { style: 'currency', currency: m.currency }).format(m.amount);
}

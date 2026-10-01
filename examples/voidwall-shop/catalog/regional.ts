import { CURRENCIES, type Currency } from './types';

const MULTIPLIER: Record<Currency, number> = { USD: 1, EUR: 1, GBP: 0.9, BRL: 5, JPY: 150 };

// Hand-set prices from CONTEXT.md's worked example.
const OVERRIDES: Record<string, Partial<Record<Currency, number>>> = {
  cores_1200: { BRL: 49.9, JPY: 1500 },
};

export function regionalPrice(sku: string, usd: number, currency: Currency): number {
  const fixed = OVERRIDES[sku]?.[currency];
  if (fixed !== undefined) return fixed;
  const raw = usd * MULTIPLIER[currency];
  return currency === 'JPY' ? Math.round(raw / 10) * 10 : Math.round(raw * 100) / 100;
}

export function pricesFor(sku: string, usd: number) {
  return CURRENCIES.map((currency) => ({
    currency,
    amount: regionalPrice(sku, usd, currency),
    is_default: currency === 'USD',
    is_enabled: true,
  }));
}

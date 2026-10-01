import type { CartApi } from './cartApi';

/**
 * Carry guest lines into the account cart. Each guest line is removed right after it lands, so a failure
 * midway loses nothing (a line is in the account cart or still in the guest cart) and a retry only
 * merges what is left instead of adding landed lines twice.
 */
export async function mergeGuestCart(guest: CartApi, user: CartApi): Promise<void> {
  const guestCart = await guest.get();
  if (guestCart.items.length === 0) return;
  const existing = new Map((await user.get()).items.map((i) => [i.sku, i.quantity]));
  for (const line of guestCart.items) {
    await user.setQuantity(line.sku, (existing.get(line.sku) ?? 0) + line.quantity);
    await guest.remove(line.sku);
  }
}

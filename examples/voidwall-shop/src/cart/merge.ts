import type { CartApi } from './cartApi';

/**
 * Carry guest lines into the account cart. The guest cart is cleared only after every line landed,
 * so a failure midway loses nothing and a retry re-reads the account cart before adding.
 */
export async function mergeGuestCart(guest: CartApi, user: CartApi): Promise<void> {
  const guestCart = await guest.get();
  if (guestCart.items.length === 0) return;
  const existing = new Map((await user.get()).items.map((i) => [i.sku, i.quantity]));
  for (const line of guestCart.items) {
    await user.setQuantity(line.sku, (existing.get(line.sku) ?? 0) + line.quantity);
  }
  await guest.clear();
}

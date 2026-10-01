import type { Session } from '../auth/types';

export function guestId(storage: Pick<Storage, 'getItem' | 'setItem'>, uuid: () => string = () => crypto.randomUUID()): string {
  const KEY = 'voidwall.guestId';
  const existing = storage.getItem(KEY);
  if (existing) return existing;
  const fresh = uuid();
  storage.setItem(KEY, fresh);
  return fresh;
}

export const authHeaders = (session: Session | null, guest: string): Record<string, string> =>
  session ? { Authorization: `Bearer ${session.accessToken}` } : { 'x-unauthorized-id': guest };

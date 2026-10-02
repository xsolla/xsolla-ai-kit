import type { Session } from './types';

const KEY = 'voidwall.session';
export const STATE_KEY = 'voidwall.oauthState';

export function loadSession(storage: Storage = sessionStorage): Session | null {
  try {
    const raw = storage.getItem(KEY);
    const s = raw ? (JSON.parse(raw) as Session) : null;
    return s && typeof s.accessToken === 'string' && typeof s.expiresAt === 'number' ? s : null;
  } catch {
    return null;
  }
}
export const saveSession = (s: Session | null, storage: Storage = sessionStorage) =>
  s ? storage.setItem(KEY, JSON.stringify(s)) : storage.removeItem(KEY);

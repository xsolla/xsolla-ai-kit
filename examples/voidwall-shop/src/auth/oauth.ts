import type { Session } from './types';

const TOKEN_URL = 'https://login.xsolla.com/api/oauth2/token';

export function newState(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}

/** Returns the authorization code, or throws. `expectedState` is what we stored before opening the widget. */
export function parseCallback(search: string, expectedState: string | null): string {
  const p = new URLSearchParams(search);
  const error = p.get('error');
  if (error) throw new Error(`Login failed: ${error}`);
  if (!expectedState || p.get('state') !== expectedState) throw new Error('Login failed: state mismatch');
  const code = p.get('code');
  if (!code) throw new Error('Login failed: missing code');
  return code;
}

async function tokenRequest(params: Record<string, string>, f: typeof fetch, now: () => number, prevRefresh?: string): Promise<Session> {
  const res = await f(TOKEN_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(params),
  });
  if (!res.ok) throw new Error(`Login token request failed: ${res.status}`);
  const j = await res.json();
  return {
    accessToken: j.access_token,
    refreshToken: j.refresh_token ?? prevRefresh,
    expiresAt: now() + Number(j.expires_in) * 1000,
  };
}

export const exchangeCode = (
  p: { clientId: string; code: string; redirectUri: string }, f: typeof fetch = fetch, now = Date.now,
) => tokenRequest({ grant_type: 'authorization_code', client_id: p.clientId, code: p.code, redirect_uri: p.redirectUri }, f, now);

export const refreshSession = (
  p: { clientId: string; refreshToken: string }, f: typeof fetch = fetch, now = Date.now,
) => tokenRequest({ grant_type: 'refresh_token', client_id: p.clientId, refresh_token: p.refreshToken }, f, now, p.refreshToken);

export const isExpired = (s: Session | null, now = Date.now(), skewMs = 60_000) =>
  !s || s.expiresAt - skewMs <= now;

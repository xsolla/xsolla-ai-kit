import { describe, expect, test } from 'vitest';
import { exchangeCode, isExpired, newState, parseCallback, refreshSession } from '../src/auth/oauth';

const json = (o: unknown, status = 200) => new Response(JSON.stringify(o), { status });

describe('parseCallback', () => {
  test('returns the code when state matches', () => {
    expect(parseCallback('?code=abc&state=s1', 's1')).toBe('abc');
  });
  test('rejects state mismatch, missing code, and provider errors', () => {
    expect(() => parseCallback('?code=abc&state=bad', 's1')).toThrow(/state/i);
    expect(() => parseCallback('?code=abc', null)).toThrow(/state/i);
    expect(() => parseCallback('?state=s1', 's1')).toThrow(/code/i);
    expect(() => parseCallback('?error=access_denied&state=s1', 's1')).toThrow(/access_denied/);
  });
  test('newState is random and non-trivial', () => {
    expect(newState()).not.toBe(newState());
    expect(newState().length).toBeGreaterThanOrEqual(16);
  });
});

describe('token requests', () => {
  test('exchangeCode posts form fields and maps expiry', async () => {
    let seen: { url: string; body: string } | undefined;
    const f = (async (url: string, init: RequestInit) => {
      seen = { url, body: String(init.body) };
      return json({ access_token: 'A', refresh_token: 'R', expires_in: 3600 });
    }) as unknown as typeof fetch;
    const s = await exchangeCode({ clientId: '7', code: 'c', redirectUri: 'http://x/cb' }, f, () => 1000);
    expect(seen!.url).toBe('https://login.xsolla.com/api/oauth2/token');
    const p = new URLSearchParams(seen!.body);
    expect(Object.fromEntries(p)).toEqual({ grant_type: 'authorization_code', client_id: '7', code: 'c', redirect_uri: 'http://x/cb' });
    expect(s).toEqual({ accessToken: 'A', refreshToken: 'R', expiresAt: 1000 + 3600 * 1000 });
  });

  test('refresh keeps the old refresh token when none is returned', async () => {
    const f = (async () => json({ access_token: 'B', expires_in: 60 })) as unknown as typeof fetch;
    const s = await refreshSession({ clientId: '7', refreshToken: 'R1' }, f, () => 0);
    expect(s.refreshToken).toBe('R1');
  });

  test('non-2xx throws', async () => {
    const f = (async () => json({}, 400)) as unknown as typeof fetch;
    await expect(exchangeCode({ clientId: '7', code: 'c', redirectUri: 'x' }, f)).rejects.toThrow(/400/);
  });
});

test('isExpired with skew; null session counts as expired', () => {
  expect(isExpired(null)).toBe(true);
  expect(isExpired({ accessToken: 'a', expiresAt: 100_000 }, 0, 60_000)).toBe(false);
  expect(isExpired({ accessToken: 'a', expiresAt: 50_000 }, 0, 60_000)).toBe(true);
});

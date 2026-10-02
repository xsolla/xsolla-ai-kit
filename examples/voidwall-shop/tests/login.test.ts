import { describe, expect, test } from 'vitest';
import { completeLogin } from '../src/auth/completeLogin';

const session = { accessToken: 'A', refreshToken: 'R', expiresAt: 1 };

describe('completeLogin', () => {
  test('merges the guest cart before publishing the session, so the cart refetch sees merged items', async () => {
    const order: string[] = [];
    await completeLogin(session, {
      merge: async () => { order.push('merge:start'); await Promise.resolve(); order.push('merge:end'); },
      setSession: () => { order.push('set'); },
    });
    expect(order).toEqual(['merge:start', 'merge:end', 'set']);
  });

  test('a failing merge still signs the user in and reports it', async () => {
    const published: unknown[] = [];
    const result = await completeLogin(session, {
      merge: async () => { throw new Error('boom'); },
      setSession: (s) => { published.push(s); },
    });
    expect(published).toEqual([session]);
    expect(result).toEqual({ mergeFailed: true });
  });

  test('a clean merge reports success', async () => {
    const result = await completeLogin(session, { merge: async () => {}, setSession: () => {} });
    expect(result).toEqual({ mergeFailed: false });
  });
});

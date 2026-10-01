import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { beforeEach, describe, expect, test } from 'vitest';
import { createHandler } from '../server/handler';
import { verifySignature } from '../server/signature';

const SECRET = 'test-secret';
const sign = (raw: Buffer) => `Signature ${createHash('sha1').update(Buffer.concat([raw, Buffer.from(SECRET)])).digest('hex')}`;
const fixture = (n: string) => readFileSync(`tests/fixtures/${n}.json`);

describe('verifySignature', () => {
  const raw = Buffer.from('{"a":1}');
  test('accepts a correct signature', () => expect(verifySignature(raw, sign(raw), SECRET)).toBe(true));
  test('rejects tampered body', () => expect(verifySignature(Buffer.from('{"a":2}'), sign(raw), SECRET)).toBe(false));
  test('rejects wrong length, missing header, wrong secret', () => {
    expect(verifySignature(raw, 'Signature abc', SECRET)).toBe(false);
    expect(verifySignature(raw, undefined, SECRET)).toBe(false);
    expect(verifySignature(raw, sign(raw), 'other')).toBe(false);
  });
  test('is plain sha1(body+secret), not HMAC', () => {
    const plain = createHash('sha1').update('{"a":1}test-secret').digest('hex');
    expect(sign(raw)).toBe(`Signature ${plain}`);
  });
});

describe('handler', () => {
  let grants: { userId: string; items: unknown; txn: string }[];
  let revokes: string[];
  let seen: Set<string>;
  let handle: ReturnType<typeof createHandler>;

  beforeEach(() => {
    grants = []; revokes = []; seen = new Set();
    handle = createHandler({
      secret: SECRET,
      grants: {
        async grant(userId, items, txn) { grants.push({ userId, items, txn }); },
        async revoke(_u, txn) { revokes.push(txn); },
      },
      claims: { async claim(id) { if (seen.has(id)) return false; seen.add(id); return true; } },
    });
  });

  test('bad signature: 400 INVALID_SIGNATURE and nothing granted', async () => {
    const raw = fixture('order_paid');
    const res = await handle(raw, 'Signature deadbeef');
    expect(res.status).toBe(400);
    expect(JSON.stringify(res.body)).toContain('INVALID_SIGNATURE');
    expect(grants).toEqual([]);
  });

  test('malformed JSON with a valid signature: 400, no crash', async () => {
    const raw = Buffer.from('{not json');
    expect((await handle(raw, sign(raw))).status).toBe(400);
  });

  test('user_validation: 204', async () => {
    const raw = fixture('user_validation');
    expect((await handle(raw, sign(raw))).status).toBe(204);
  });

  test('order_paid grants once; a duplicate delivery returns 2xx without granting again', async () => {
    const raw = fixture('order_paid');
    const a = await handle(raw, sign(raw));
    const b = await handle(raw, sign(raw));
    expect([a.status, b.status]).toEqual([204, 204]);
    expect(grants).toHaveLength(1);
    expect(grants[0]).toMatchObject({
      userId: 'a1b2c3d4-0000-4000-8000-019fb6caa51e',
      items: [{ sku: 'artifact_centaurs_axe', quantity: 1 }],
      txn: '2105129134',
    });
  });

  test('separate-mode payment is recorded only, never fulfilled', async () => {
    const raw = fixture('payment');
    expect((await handle(raw, sign(raw))).status).toBe(204);
    expect(grants).toEqual([]);
  });

  test('order_canceled revokes', async () => {
    const raw = Buffer.from(JSON.stringify({
      notification_type: 'order_canceled',
      user: { external_id: 'u1' },
      billing: { transaction: { id: 99 } },
      order: { id: 5 },
    }));
    expect((await handle(raw, sign(raw))).status).toBe(204);
    expect(revokes).toEqual(['99']);
  });

  test('unknown notification types are acknowledged, not errors', async () => {
    const raw = Buffer.from(JSON.stringify({ notification_type: 'something_new' }));
    expect((await handle(raw, sign(raw))).status).toBe(204);
  });

  test('order_paid without a user id is a permanent 400, not a retry-forever 5xx', async () => {
    const raw = Buffer.from(JSON.stringify({ notification_type: 'order_paid', items: [], order: { id: 1 } }));
    expect((await handle(raw, sign(raw))).status).toBe(400);
  });
});

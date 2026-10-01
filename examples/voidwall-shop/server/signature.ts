import { createHash, timingSafeEqual } from 'node:crypto';

/** lowercase(sha1(rawBody + secret)) vs the `Signature <hex>` header, compared in constant time. */
export function verifySignature(raw: Buffer, header: string | undefined, secret: string): boolean {
  if (!header) return false;
  const provided = Buffer.from(header.replace(/^Signature\s+/i, '').toLowerCase(), 'utf8');
  const expected = Buffer.from(
    createHash('sha1').update(Buffer.concat([raw, Buffer.from(secret, 'utf8')])).digest('hex'), 'utf8',
  );
  return provided.length === expected.length && timingSafeEqual(provided, expected);
}

# Signature verification

Every Xsolla webhook is authenticated with a SHA-1 signature over the **raw
body** plus the project's secret key. Verify it **before** parsing or acting on
anything. No verification = anyone can grant items.

## Algorithm

The `authorization` header is `Signature <40-hex-lowercase>`. Recompute:

```
signature = lowercase( sha1( rawRequestBody + projectSecretKey ) )
```

Then compare in constant time against the header value.

Rules that cause ~90% of `INVALID_SIGNATURE` failures:

- Hash the **raw bytes exactly as received**. Do **not** `JSON.parse` then
  re-stringify, pretty-print, reorder keys, or re-encode UTF-8 first.
- The secret key is **appended after** the body — not prepended, and **not** an
  HMAC key. This is plain `sha1(body + key)`.
- Compare in **constant time** (`crypto.timingSafeEqual`, `hash_equals`, …).

## Node.js (Express) — capture the raw body

```js
const express = require('express');
const crypto = require('crypto');

const SECRET = process.env.XSOLLA_WEBHOOK_SECRET;
const app = express();

// Keep the raw body so the signature can be verified byte-for-byte.
app.use('/xsolla/webhooks', express.json({
  verify: (req, _res, buf) => { req.rawBody = buf; },
}));

function verifyXsollaSignature(req) {
  const header = req.get('authorization') || '';
  const provided = header.replace(/^Signature\s+/i, '').toLowerCase();
  const expected = crypto
    .createHash('sha1')
    .update(Buffer.concat([req.rawBody, Buffer.from(SECRET, 'utf8')]))
    .digest('hex');
  const a = Buffer.from(provided, 'utf8');
  const b = Buffer.from(expected, 'utf8');
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
```

## PHP

```php
$rawBody  = file_get_contents('php://input');
$provided = strtolower(preg_replace('/^Signature\s+/i', '',
    $_SERVER['HTTP_AUTHORIZATION'] ?? ''));
$expected = sha1($rawBody . $secretKey);

if (!hash_equals($expected, $provided)) {
    http_response_code(400);
    echo json_encode(['error' => ['code' => 'INVALID_SIGNATURE', 'message' => 'Invalid signature']]);
    exit;
}
```

Xsolla publishes signature samples for C#, C++, Go, PHP, and Node.js, and ships
a **Pay Station PHP SDK** with a ready-made `WebhookAuthenticator`
(`xsolla/xsolla-sdk-php`). Prefer the SDK for PHP projects.

Reference: https://developers.xsolla.com/webhooks/section/webhook-listener/

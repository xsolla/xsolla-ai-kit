import express from 'express';
import { createHandler } from './handler';
import { fileClaims, fileGrants } from './stores';

const secret = process.env.XSOLLA_WEBHOOK_SECRET;
if (!secret) throw new Error('XSOLLA_WEBHOOK_SECRET is required'); // fail fast: every signature would fail otherwise

const handle = createHandler({ secret, grants: fileGrants, claims: fileClaims });
const app = express();

// express.raw keeps the exact bytes, which the signature is computed over.
app.post('/xsolla/webhooks', express.raw({ type: '*/*', limit: '1mb' }), async (req, res) => {
  try {
    const out = await handle(req.body as Buffer, req.get('authorization'));
    res.status(out.status);
    out.body ? res.json(out.body) : res.end();
  } catch (e) {
    console.error('webhook failed', (e as Error).message);
    res.status(500).json({ error: { code: 'INTERNAL', message: 'Temporary error' } }); // transient: Xsolla retries
  }
});

const port = Number(process.env.PORT ?? 8787);
app.listen(port, () => console.log(`webhook listening on :${port}/xsolla/webhooks`));

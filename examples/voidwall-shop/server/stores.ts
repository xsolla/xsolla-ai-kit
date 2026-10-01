import { appendFile, mkdir, readFile } from 'node:fs/promises';
import type { Claims, Grants } from './handler';

const DIR = new URL('./data/', import.meta.url);
const GRANTS = new URL('grants.jsonl', DIR);
const CLAIMS = new URL('claims.jsonl', DIR);

async function lines(url: URL): Promise<string[]> {
  try { return (await readFile(url, 'utf8')).split('\n').filter(Boolean); } catch { return []; }
}

/** Stand-in for the game's entitlement system. Replace with the real grant path. */
export const fileGrants: Grants = {
  async grant(userId, items, txnId) {
    await mkdir(DIR, { recursive: true });
    await appendFile(GRANTS, JSON.stringify({ op: 'grant', userId, items, txnId, at: new Date().toISOString() }) + '\n');
  },
  async revoke(userId, txnId) {
    await mkdir(DIR, { recursive: true });
    await appendFile(GRANTS, JSON.stringify({ op: 'revoke', userId, txnId, at: new Date().toISOString() }) + '\n');
  },
};

/** Check-then-write: safe for a single process only. Multi-instance needs a unique constraint in a real datastore. */
export const fileClaims: Claims = {
  async claim(txnId) {
    if ((await lines(CLAIMS)).includes(txnId)) return false;
    await mkdir(DIR, { recursive: true });
    await appendFile(CLAIMS, txnId + '\n');
    return true;
  },
};

import { buildPlan } from '../catalog/plan';
import { fetchCatalog } from '../src/api/store';
import { createAdmin, missingSkus, upsert, SeedError } from './lib/admin';
import { loadEnv } from './lib/env';

const args = process.argv.slice(2);
const apply = args.includes('--apply');
const verify = args.includes('--verify');

const env = loadEnv(
  new URL('../../../.env', import.meta.url), // repo root
  new URL('../.env', import.meta.url), // example dir, wins
);
const need = (k: string) => {
  const v = env[k] ?? process.env[k];
  if (!v) { console.error(`Missing ${k} in .env`); process.exit(2); }
  return v;
};
const projectId = need('XSOLLA_PROJECT_ID');
const plan = buildPlan();

async function main() {
  if (verify) {
    const found = (await fetchCatalog(projectId, 'en')).map((i) => i.sku);
    const expected = plan.filter((s) => s.expectInStore).map((s) => s.key);
    const missing = missingSkus(expected, found);
    console.log(`public catalog: ${expected.length - missing.length}/${expected.length} expected SKUs present`);
    if (missing.length) { console.log('missing:', missing.join(', ')); process.exit(1); }
    return;
  }

  const admin = createAdmin({ merchantId: need('XSOLLA_MERCHANT_ID'), projectId, apiKey: need('XSOLLA_PROJECT_API_KEY') });
  console.log(`${apply ? 'APPLY' : 'DRY RUN'} against project ${projectId}: ${plan.length} entities`);
  const tally = { create: 0, update: 0 };
  for (const s of plan) {
    try {
      const action = await upsert(admin, s, apply);
      tally[action]++;
      console.log(`${apply ? '' : 'would '}${action.padEnd(6)} ${s.kind.padEnd(8)} ${s.key}`);
    } catch (e) {
      if (e instanceof SeedError) { console.error(`STOP: ${e.message}`); process.exit(1); }
      throw e;
    }
  }
  console.log(`done: ${tally.create} create, ${tally.update} update${apply ? '' : ' (nothing written; rerun with --apply)'}`);
}

main();

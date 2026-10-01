import { describe, expect, test } from 'vitest';
import { parseEnv } from '../scripts/lib/env';
import { SeedError, missingSkus, upsert, type Admin } from '../scripts/lib/admin';
import type { PlanStep } from '../catalog/plan';

const step: PlanStep = { kind: 'item', key: 'tether_skin_anchor', payload: { sku: 'tether_skin_anchor' }, expectInStore: true };

function fakeAdmin(getStatus: number, writeStatus = 201) {
  const calls: { method: string; path: string }[] = [];
  const admin: Admin = {
    async call(method, path) {
      calls.push({ method, path });
      return { status: method === 'GET' ? getStatus : writeStatus, body: { err: 'x' } };
    },
  };
  return { admin, calls };
}

describe('upsert', () => {
  test('dry run never writes', async () => {
    const { admin, calls } = fakeAdmin(404);
    expect(await upsert(admin, step, false)).toBe('create');
    expect(calls.map((c) => c.method)).toEqual(['GET']);
  });

  test('404 then POST to the collection', async () => {
    const { admin, calls } = fakeAdmin(404);
    expect(await upsert(admin, step, true)).toBe('create');
    expect(calls).toEqual([
      { method: 'GET', path: '/items/virtual_items/sku/tether_skin_anchor' },
      { method: 'POST', path: '/items/virtual_items' },
    ]);
  });

  test('200 then PUT the full payload', async () => {
    const { admin, calls } = fakeAdmin(200, 204);
    expect(await upsert(admin, step, true)).toBe('update');
    expect(calls[1]).toEqual({ method: 'PUT', path: '/items/virtual_items/sku/tether_skin_anchor' });
  });

  test('unexpected GET status and failed writes throw SeedError', async () => {
    await expect(upsert(fakeAdmin(500).admin, step, true)).rejects.toBeInstanceOf(SeedError);
    await expect(upsert(fakeAdmin(404, 422).admin, step, true)).rejects.toBeInstanceOf(SeedError);
  });

  test('groups are addressed by external_id', async () => {
    const { admin, calls } = fakeAdmin(404);
    await upsert(admin, { kind: 'group', key: 'bundles', payload: {}, expectInStore: false }, true);
    expect(calls[0]!.path).toBe('/items/groups/bundles');
  });
});

test('SeedError message never contains request headers or keys', () => {
  const e = new SeedError(step, { status: 422, body: { errorMessage: 'bad' } });
  expect(e.message).toContain('422');
  expect(e.message).not.toMatch(/authorization|basic /i);
});

test('missingSkus', () => {
  expect(missingSkus(['a', 'b', 'c'], ['b'])).toEqual(['a', 'c']);
});

test('parseEnv reads KEY=VALUE, ignores comments and blanks, strips quotes', () => {
  expect(parseEnv('# c\nA=1\n\nB="two"\nC=\n')).toEqual({ A: '1', B: 'two', C: '' });
});

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { config } from '../config';
import { createCartApi, type Cart } from './cartApi';

export function useCart() {
  const auth = useAuth();
  const api = useMemo(() => createCartApi(config.projectId, auth.headers), [auth]);
  const [cart, setCart] = useState<Cart | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (fn: () => Promise<unknown>) => {
    setBusy(true); setError(null);
    try { await fn(); setCart(await api.get()); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }, [api]);

  const refresh = useCallback(() => run(async () => {}), [run]);
  useEffect(() => { void refresh(); }, [refresh, auth.session]);

  return {
    cart, busy, error, refresh,
    add: (sku: string) => run(async () => {
      const current = (await api.get()).items.find((i) => i.sku === sku)?.quantity ?? 0;
      await api.setQuantity(sku, current + 1);
    }),
    remove: (sku: string) => run(() => api.remove(sku)),
    clear: () => run(() => api.clear()),
  };
}

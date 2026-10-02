import { useEffect, useMemo, useState } from 'react';
import { CHARTER } from '../catalog/catalog';
import { fetchCatalog, type ShopItem } from './api/store';
import { byGroup, knownItems, visibleGroups } from './api/view';
import { useAuth } from './auth/AuthContext';
import { BundleStrip } from './components/BundleStrip';
import { CartDrawer } from './components/CartDrawer';
import { Footer } from './components/Footer';
import { Header } from './components/Header';
import { Hero } from './components/Hero';
import { Section } from './components/Section';
import { XsollaQuestModule } from './quests/XsollaQuestModule';
import { CheckoutModal } from './checkout/CheckoutModal';
import { InsufficientCoresError, buyWithCores, createCartPaymentToken, fetchCoresBalance } from './checkout/api';
import { config } from './config';
import { useCart } from './cart/useCart';
import { PAY_LANGUAGE, resolveLocale, type Locale } from './i18n/locales';
import { UI } from './i18n/ui';

export function useLocale(): [Locale, (l: Locale) => void] {
  const [locale, set] = useState<Locale>(() => resolveLocale(localStorage.getItem('voidwall.locale')));
  return [locale, (l) => { localStorage.setItem('voidwall.locale', l); set(l); }];
}

export function Shop({ locale, onLocale }: { locale: Locale; onLocale: (l: Locale) => void }) {
  const t = UI[locale];
  const auth = useAuth();
  const cart = useCart();
  const [items, setItems] = useState<ShopItem[] | null>(null);
  const [error, setError] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [balance, setBalance] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!auth.session) { setBalance(null); return; }
    fetchCoresBalance(config.projectId, auth.session).then(setBalance).catch(() => setBalance(null));
  }, [auth.session]);

  async function checkout() {
    if (!auth.session || !cart.cart) return;
    try {
      const r = await createCartPaymentToken({
        projectId: config.projectId, cartId: cart.cart.cartId, session: auth.session,
        language: PAY_LANGUAGE[locale], sandbox: config.sandbox,
      });
      setDrawer(false);
      setToken(r.token);
    } catch (e) { setNotice((e as Error).message); }
  }

  async function buyCores(item: ShopItem) {
    if (!auth.session) { auth.login(); return; }
    try {
      await buyWithCores({ projectId: config.projectId, sku: item.sku, session: auth.session });
      setNotice(t.purchased);
      setBalance(await fetchCoresBalance(config.projectId, auth.session));
    } catch (e) { setNotice(e instanceof InsufficientCoresError ? t.notEnoughCores : (e as Error).message); }
  }

  useEffect(() => {
    setError(false);
    fetchCatalog(config.projectId, locale).then((r) => setItems(knownItems(r))).catch(() => setError(true));
  }, [locale]);

  const inCart = useMemo(() => new Set(cart.cart?.items.map((i) => i.sku) ?? []), [cart.cart]);
  const count = cart.cart?.items.reduce((n, i) => n + i.quantity, 0) ?? 0;

  return (
    <>
      <Header locale={locale} onLocale={onLocale} cartCount={count} balance={balance} onCart={() => setDrawer(true)} />
      <main className="page">
        <Hero locale={locale} />
        <div id="shop" />
        {error && <p className="error">{t.loadError}</p>}
        {!items && !error && <p>{t.loading}</p>}
        {items && (
          <>
            <BundleStrip bundles={byGroup(items, 'bundles')} locale={locale} inCart={inCart} onAdd={cart.add} />
            {visibleGroups(items).filter((g) => g.id !== 'bundles').map((g) => (
              <Section key={g.id} id={g.id} items={byGroup(items, g.id)} locale={locale} inCart={inCart}
                onAdd={cart.add} onBuyWithCores={buyCores} />
            ))}
            <XsollaQuestModule locale={locale} />
            <section>
              <h2>{CHARTER.name}</h2>
              <p className="note">{t.comingSoon}</p>
            </section>
          </>
        )}
      </main>
      <Footer locale={locale} />
      {drawer && (
        <CartDrawer cart={cart.cart} locale={locale} loggedIn={Boolean(auth.session)} loginConfigured={auth.configured}
          busy={cart.busy} onClose={() => setDrawer(false)} onRemove={cart.remove} onLogin={auth.login} onCheckout={checkout} />
      )}
      {token && <CheckoutModal token={token} locale={locale} onClose={() => setToken(null)} />}
      {notice && <p className="note" role="status" style={{ position: 'fixed', bottom: 8, left: 8 }}>{notice}</p>}
    </>
  );
}

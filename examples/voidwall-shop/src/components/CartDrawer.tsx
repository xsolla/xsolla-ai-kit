import { formatMoney } from '../api/store';
import type { Cart } from '../cart/cartApi';
import type { Locale } from '../i18n/locales';
import { UI } from '../i18n/ui';

interface Props {
  cart: Cart | null; locale: Locale; loggedIn: boolean; loginConfigured: boolean; busy: boolean;
  onClose: () => void; onRemove: (sku: string) => void; onLogin: () => void; onCheckout: () => void;
}

export function CartDrawer({ cart, locale, loggedIn, loginConfigured, busy, onClose, onRemove, onLogin, onCheckout }: Props) {
  const t = UI[locale];
  const empty = !cart || cart.items.length === 0;
  return (
    <aside className="drawer" aria-label={t.cart}>
      <button onClick={onClose}>{t.close}</button>
      <h2>{t.cart}</h2>
      {empty && <p>{t.cartEmpty}</p>}
      {cart?.items.map((i) => (
        <div key={i.sku} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', margin: '0.5rem 0' }}>
          <span style={{ flex: 1 }}>{i.name} × {i.quantity}</span>
          <span>{formatMoney(i.price, locale)}</span>
          <button onClick={() => onRemove(i.sku)} disabled={busy}>{t.remove}</button>
        </div>
      ))}
      {!empty && (
        <>
          <p className="price">{t.total}: {formatMoney(cart!.total, locale)}</p>
          {loggedIn
            ? <button className="primary" disabled={busy} onClick={onCheckout}>{t.checkout}</button>
            : <button className="primary" disabled={!loginConfigured} onClick={onLogin}>{loginConfigured ? t.signInToCheckout : t.loginUnavailable}</button>}
        </>
      )}
    </aside>
  );
}

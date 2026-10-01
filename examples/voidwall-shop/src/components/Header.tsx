import { LOCALES, LOCALE_LABEL, type Locale } from '../i18n/locales';
import { UI } from '../i18n/ui';
import { useAuth } from '../auth/AuthContext';

export function Header({ locale, onLocale, cartCount, balance, onCart }: { locale: Locale; onLocale: (l: Locale) => void; cartCount: number; balance: number | null; onCart: () => void }) {
  const t = UI[locale];
  const auth = useAuth();
  return (
    <header className="header">
      <img src="/assets/brand/glyph.jpg" alt="" />
      <strong>VOIDWALL</strong>
      <span className="spacer" />
      {balance !== null && <span className="note">{t.balance}: {balance.toLocaleString(locale)}</span>}
      <select aria-label="Language" value={locale} onChange={(e) => onLocale(e.target.value as Locale)}>
        {LOCALES.map((l) => <option key={l} value={l}>{LOCALE_LABEL[l]}</option>)}
      </select>
      {auth.session
        ? <button onClick={auth.logout}>{t.logout}</button>
        : <button onClick={auth.login} disabled={!auth.configured} title={auth.configured ? undefined : t.loginUnavailable}>{t.login}</button>}
      <button onClick={onCart}>{t.cart} ({cartCount})</button>
    </header>
  );
}

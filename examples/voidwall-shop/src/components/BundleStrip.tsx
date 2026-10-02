import { BUNDLES, coresValue } from '../../catalog/catalog';
import type { ShopItem } from '../api/store';
import type { Locale } from '../i18n/locales';
import { UI } from '../i18n/ui';
import { ItemCard } from './ItemCard';

export function BundleStrip({ bundles, locale, inCart, onAdd }: { bundles: ShopItem[]; locale: Locale; inCart: Set<string>; onAdd: (sku: string) => void }) {
  if (bundles.length === 0) return null;
  const t = UI[locale];
  return (
    <section>
      <h2>{t.featured}</h2>
      <div className="grid">
        {bundles.map((b) => {
          const def = BUNDLES.find((d) => d.sku === b.sku);
          return (
            <div key={b.sku}>
              <ItemCard item={b} locale={locale} inCart={inCart.has(b.sku)} onAdd={onAdd} onBuyWithCores={() => {}} />
              {def && <p className="note">{t.valueOf}: {coresValue(def).toLocaleString(locale)} {t.balance}</p>}
            </div>
          );
        })}
      </div>
    </section>
  );
}

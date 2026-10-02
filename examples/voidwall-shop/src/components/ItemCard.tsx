import { IMAGES } from '../../catalog/catalog';
import { formatMoney, type ShopItem } from '../api/store';
import type { Locale } from '../i18n/locales';
import { UI } from '../i18n/ui';

interface Props {
  item: ShopItem; locale: Locale; inCart: boolean;
  onAdd: (sku: string) => void; onBuyWithCores: (item: ShopItem) => void;
}

export function ItemCard({ item, locale, inCart, onAdd, onBuyWithCores }: Props) {
  const t = UI[locale];
  const rarity = item.attributes.rarity ?? 'common';
  const img = IMAGES[item.sku] ? `/assets/${IMAGES[item.sku]}` : undefined;
  const hasMoney = Boolean(item.price);
  const discounted = item.price && item.price.amountWithoutDiscount > item.price.amount;
  return (
    <article className={`card rarity-${rarity}`}>
      {img && <img src={img} alt={item.name} loading="lazy" />}
      <h3>{item.name}</h3>
      <p className="note">{item.description}</p>
      <div className="price">
        {hasMoney && formatMoney(item.price, locale)}
        {discounted && <span className="was">{formatMoney({ ...item.price!, amount: item.price!.amountWithoutDiscount }, locale)}</span>}
        {!hasMoney && item.coresPrice !== undefined && `${item.coresPrice.toLocaleString(locale)} ${t.balance}`}
        {!hasMoney && item.coresPrice === undefined && <span className="note">{t.unavailable}</span>}
      </div>
      {hasMoney && <button className="primary" disabled={inCart} onClick={() => onAdd(item.sku)}>{inCart ? t.inCart : t.addToCart}</button>}
      {!hasMoney && item.coresPrice !== undefined && <button className="primary" onClick={() => onBuyWithCores(item)}>{t.buyWithCores}</button>}
      {!hasMoney && item.coresPrice === undefined && <button disabled>{t.unavailable}</button>}
    </article>
  );
}

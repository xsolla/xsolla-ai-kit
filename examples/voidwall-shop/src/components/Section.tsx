import { GROUPS } from '../../catalog/catalog';
import type { GroupId } from '../../catalog/types';
import type { ShopItem } from '../api/store';
import type { Locale } from '../i18n/locales';
import { ItemCard } from './ItemCard';

export function Section(props: {
  id: GroupId; items: ShopItem[]; locale: Locale; inCart: Set<string>;
  onAdd: (sku: string) => void; onBuyWithCores: (item: ShopItem) => void;
}) {
  const group = GROUPS.find((g) => g.id === props.id)!;
  return (
    <section id={props.id}>
      <h2>{group.names[props.locale]}</h2>
      <div className="grid">
        {props.items.map((i) => (
          <ItemCard key={i.sku} item={i} locale={props.locale}
            inCart={props.inCart.has(i.sku)} onAdd={props.onAdd} onBuyWithCores={props.onBuyWithCores} />
        ))}
      </div>
    </section>
  );
}

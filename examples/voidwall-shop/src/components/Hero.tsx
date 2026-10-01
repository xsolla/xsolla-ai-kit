import { UI } from '../i18n/ui';
import type { Locale } from '../i18n/locales';

export function Hero({ locale }: { locale: Locale }) {
  const t = UI[locale];
  return (
    <section className="hero">
      <div>
        <img src="/assets/brand/logo.jpg" alt="Voidwall" height={64} />
        <h1>{t.tagline}</h1>
        <p>{t.heroSub}</p>
        <a href="#shop"><button className="primary">{t.shopNow}</button></a>
      </div>
    </section>
  );
}

import { config } from '../config';
import { UI } from '../i18n/ui';
import type { Locale } from '../i18n/locales';

export function Footer({ locale }: { locale: Locale }) {
  const t = UI[locale];
  return (
    <footer className="footer">
      <p>{t.footer}</p>
      <p><a href={`mailto:${config.supportEmail}`}>{t.support}: {config.supportEmail}</a></p>
      {config.sandbox && <p className="note">{t.sandboxNote}</p>}
    </footer>
  );
}

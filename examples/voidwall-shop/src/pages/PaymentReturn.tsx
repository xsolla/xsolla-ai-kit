import { headlessCheckout } from '@xsolla/pay-station-sdk';
import { useEffect, useRef, useState } from 'react';
import { asLang } from '../checkout/sdk';
import { config } from '../config';
import { PAY_LANGUAGE, resolveLocale } from '../i18n/locales';

export function PaymentReturn() {
  const host = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const token = new URLSearchParams(location.search).get('token');
    if (!token) { setError('Missing token'); return; }
    const language = PAY_LANGUAGE[resolveLocale(localStorage.getItem('voidwall.locale'))];
    (async () => {
      await headlessCheckout.init({ sandbox: config.sandbox, isWebview: false, language: asLang(language) });
      await headlessCheckout.setToken(token);
      host.current?.appendChild(document.createElement('psdk-status')); // after setToken, never static
    })().catch((e) => setError((e as Error).message));
  }, []);
  return (
    <main className="page">
      <div ref={host} />
      {error && <p className="error">{error}</p>}
      <psdk-legal />
      <p><a href="/">Back to the store</a></p>
    </main>
  );
}

import { useEffect, useRef, useState } from 'react';
import { config } from '../config';
import { PAY_LANGUAGE, type Locale } from '../i18n/locales';
import { UI } from '../i18n/ui';
import { detachUi, initCheckout, openMethod } from './sdk';

export function CheckoutModal({ token, locale, onClose }: { token: string; locale: Locale; onClose: () => void }) {
  const t = UI[locale];
  const methodsRef = useRef<HTMLElement | null>(null);
  const fieldsRef = useRef<HTMLDivElement>(null);
  const statusRef = useRef<HTMLDivElement>(null);
  const errorRef = useRef<HTMLParagraphElement>(null);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    initCheckout(token, PAY_LANGUAGE[locale], config.sandbox)
      .then(() => alive && setReady(true))
      .catch((e) => alive && setFailed((e as Error).message));
    return () => { alive = false; detachUi(); };
  }, [token, locale]);

  useEffect(() => {
    const el = methodsRef.current;
    if (!ready || !el) return;
    const onSelect = (e: Event) => {
      const id = Number((e as CustomEvent).detail?.paymentMethodId);
      void openMethod(
        { fieldsEl: fieldsRef.current!, statusEl: statusRef.current!, errorEl: errorRef.current!, setLoading },
        id,
        `${location.origin}/payment/return?token=${encodeURIComponent(token)}`,
      ).catch((err) => setFailed((err as Error).message));
    };
    el.addEventListener('selectionChange', onSelect);
    return () => el.removeEventListener('selectionChange', onSelect);
  }, [ready, token]);

  return (
    <div className="modal" role="dialog" aria-modal="true">
      <div>
        <button onClick={onClose}>{t.close}</button>
        {failed && <p className="error">{failed}</p>}
        {ready && <psdk-payment-methods ref={methodsRef} />}
        {loading && <p>{t.loading}</p>}
        <div ref={fieldsRef} />
        <p ref={errorRef} className="error" />
        <div ref={statusRef} />
        {ready && <><psdk-payment-form-messages /><psdk-total /><psdk-legal /></>}
      </div>
    </div>
  );
}

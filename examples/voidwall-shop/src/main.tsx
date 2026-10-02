import { createRoot } from 'react-dom/client';
import { Shop, useLocale } from './App';
import { AuthProvider } from './auth/AuthContext';
import { createCartApi } from './cart/cartApi';
import { mergeGuestCart } from './cart/merge';
import { authHeaders, guestId } from './cart/headers';
import { PaymentReturn } from './pages/PaymentReturn';
import { config } from './config';
import './theme.css';

function Root() {
  const [locale, setLocale] = useLocale();
  return (
    <AuthProvider
      locale={locale}
      onLogin={async (session) => {
        const guest = createCartApi(config.projectId, () => authHeaders(null, guestId(localStorage)));
        const user = createCartApi(config.projectId, () => authHeaders(session, ''));
        await mergeGuestCart(guest, user);
      }}
    >
      <Shop locale={locale} onLocale={setLocale} />
    </AuthProvider>
  );
}

const isReturn = location.pathname === '/payment/return';
createRoot(document.getElementById('root')!).render(isReturn ? <PaymentReturn /> : <Root />); // no StrictMode: the checkout SDK is a page singleton and StrictMode's double effects double-init it

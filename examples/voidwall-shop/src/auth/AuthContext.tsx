import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Widget } from '@xsolla/login-sdk';
import { config, loginConfigured } from '../config';
import { LOGIN_LOCALE, type Locale } from '../i18n/locales';
import { authHeaders, guestId } from '../cart/headers';
import { exchangeCode, newState, parseCallback, refreshSession } from './oauth';
import { STATE_KEY, loadSession, saveSession } from './session';
import type { Session } from './types';

export interface AuthState {
  session: Session | null;
  configured: boolean;
  login(): void;
  logout(): void;
  headers(): Record<string, string>;
}

const Ctx = createContext<AuthState | null>(null);
export const useAuth = () => {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAuth outside AuthProvider');
  return v;
};

const WIDGET_HOST_ID = 'xsolla-login-widget';
const redirectUri = () => `${location.origin}/auth/callback`;

export function AuthProvider({ locale, onLogin, children }: { locale: Locale; onLogin?: (s: Session) => Promise<void>; children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(() => loadSession());
  const onLoginRef = useRef(onLogin);
  onLoginRef.current = onLogin;
  const widgetRef = useRef<Widget | null>(null);

  const set = useCallback((s: Session | null) => { saveSession(s); setSession(s); }, []);

  // Finish the OAuth redirect.
  useEffect(() => {
    if (location.pathname !== '/auth/callback') return;
    (async () => {
      try {
        const code = parseCallback(location.search, sessionStorage.getItem(STATE_KEY));
        sessionStorage.removeItem(STATE_KEY);
        const s = await exchangeCode({ clientId: config.loginClientId, code, redirectUri: redirectUri() });
        set(s);
        await onLoginRef.current?.(s);
      } catch (e) {
        console.error(e);
      } finally {
        history.replaceState(null, '', '/');
      }
    })();
  }, [set]);

  // Refresh a minute before expiry so Store calls never 401 mid-checkout.
  useEffect(() => {
    if (!session?.refreshToken) return;
    const wait = Math.max(session.expiresAt - Date.now() - 60_000, 0);
    const t = setTimeout(async () => {
      try { set(await refreshSession({ clientId: config.loginClientId, refreshToken: session.refreshToken! })); }
      catch { set(null); }
    }, wait);
    return () => clearTimeout(t);
  }, [session, set]);

  const value = useMemo<AuthState>(() => ({
    session,
    configured: loginConfigured,
    login() {
      if (!loginConfigured) return;
      const state = newState();
      sessionStorage.setItem(STATE_KEY, state);
      widgetRef.current?.unmount();
      const widget = new Widget({
        projectId: config.loginProjectId,
        preferredLocale: LOGIN_LOCALE[locale],
        clientId: Number(config.loginClientId), // the SDK types clientId as a number
        responseType: 'code',
        state,
        redirectUri: redirectUri(),
        scope: 'offline email',
      });
      widgetRef.current = widget;
      widget.mount(WIDGET_HOST_ID); // mount before open
      widget.open();
    },
    logout: () => set(null),
    headers: () => authHeaders(session, guestId(localStorage)),
  }), [session, locale, set]);

  return (
    <Ctx.Provider value={value}>
      {children}
      <div id={WIDGET_HOST_ID} />
    </Ctx.Provider>
  );
}

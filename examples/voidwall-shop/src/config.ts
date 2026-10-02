const env = import.meta.env;
export const config = {
  projectId: (env.VITE_XSOLLA_PROJECT_ID as string) ?? '',
  sandbox: (env.VITE_SANDBOX as string) !== 'false',
  loginProjectId: (env.VITE_LOGIN_PROJECT_ID as string) ?? '',
  loginClientId: (env.VITE_LOGIN_CLIENT_ID as string) ?? '',
  supportEmail: 'support@playvoidwall.com',
  qpMerchantId: (env.VITE_XSOLLA_QP_MERCHANT_ID as string) ?? '',
  qpProjectId: (env.VITE_XSOLLA_QP_PROJECT_ID as string) ?? '',
  qpBaseUrl: (env.VITE_XSOLLA_QP_PUBLIC_BASE_URL as string) ?? '',
};

export const loginConfigured = Boolean(config.loginProjectId && config.loginClientId);

const QP_PUBLIC_BASE = 'https://quests-platform.xsolla.com';

/** Quest Platform scope for the storefront, or null when either id is missing. The Store project id is never reused. */
export function questSource(c: Pick<typeof config, 'qpMerchantId' | 'qpProjectId' | 'qpBaseUrl'>) {
  if (!c.qpMerchantId || !c.qpProjectId) return null;
  let baseUrl = QP_PUBLIC_BASE;
  try {
    const u = new URL(c.qpBaseUrl);
    if (u.protocol === 'http:' || u.protocol === 'https:') baseUrl = u.origin;
  } catch { /* no override */ }
  return { baseUrl, merchantId: c.qpMerchantId, projectId: c.qpProjectId };
}

const env = import.meta.env;
export const config = {
  projectId: (env.VITE_XSOLLA_PROJECT_ID as string) ?? '',
  qpMerchantId: (env.VITE_XSOLLA_QP_MERCHANT_ID as string) ?? '',
  qpProjectId: (env.VITE_XSOLLA_QP_PROJECT_ID as string) ?? '',
  qpBaseUrl: (env.VITE_XSOLLA_QP_PUBLIC_BASE_URL as string) || 'https://quests-platform.xsolla.com',
  sandbox: (env.VITE_SANDBOX as string) !== 'false',
  loginProjectId: (env.VITE_LOGIN_PROJECT_ID as string) ?? '',
  loginClientId: (env.VITE_LOGIN_CLIENT_ID as string) ?? '',
  supportEmail: 'support@playvoidwall.com',
};

export const loginConfigured = Boolean(config.loginProjectId && config.loginClientId);

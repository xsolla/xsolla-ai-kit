const env = import.meta.env;
const merchantId = (env.VITE_XSOLLA_MERCHANT_ID as string) ?? '';
const projectId = (env.VITE_XSOLLA_PROJECT_ID as string) ?? '';
const derivedQuestListUrl = merchantId && projectId
  ? `https://quests-platform.xsolla.com/api/v2/public/merchants/${encodeURIComponent(merchantId)}/projects/${encodeURIComponent(projectId)}/quests?page=1&limit=100`
  : '';

export const config = {
  projectId,
  questListUrl: (env.VITE_XSOLLA_QP_QUESTS_URL as string) || derivedQuestListUrl,
  sandbox: (env.VITE_SANDBOX as string) !== 'false',
  loginProjectId: (env.VITE_LOGIN_PROJECT_ID as string) ?? '',
  loginClientId: (env.VITE_LOGIN_CLIENT_ID as string) ?? '',
  supportEmail: 'support@playvoidwall.com',
};

export const loginConfigured = Boolean(config.loginProjectId && config.loginClientId);

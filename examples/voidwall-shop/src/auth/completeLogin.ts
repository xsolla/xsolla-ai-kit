import type { Session } from './types';

/**
 * Finish a login: merge the guest cart first, then publish the session. Publishing first would make the
 * cart refetch race the merge and show an empty cart. A failed merge must not block sign-in; the guest
 * lines stay in the guest cart and the (now retry-safe) merge runs again on the next login.
 */
export async function completeLogin(
  session: Session,
  deps: { merge: (s: Session) => Promise<void>; setSession: (s: Session) => void },
): Promise<{ mergeFailed: boolean }> {
  let mergeFailed = false;
  try {
    await deps.merge(session);
  } catch (e) {
    console.error('Guest cart merge failed', e);
    mergeFailed = true;
  }
  deps.setSession(session);
  return { mergeFailed };
}

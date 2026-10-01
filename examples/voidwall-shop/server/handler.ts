import { verifySignature } from './signature';

export interface Grants {
  grant(userId: string, items: { sku: string; quantity: number }[], txnId: string): Promise<void>;
  revoke(userId: string, txnId: string): Promise<void>;
}
export interface Claims {
  /** True only the first time a transaction id is claimed. */
  claim(txnId: string): Promise<boolean>;
  /** Undo a claim whose grant failed, so the retry is not mistaken for a duplicate. */
  release(txnId: string): Promise<void>;
}
export interface Result { status: number; body?: unknown }

const err = (code: string, message: string): Result => ({ status: 400, body: { error: { code, message } } });
const ok: Result = { status: 204 };

export function createHandler(deps: { secret: string; grants: Grants; claims: Claims }) {
  return async function handle(raw: Buffer, authHeader: string | undefined): Promise<Result> {
    if (!verifySignature(raw, authHeader, deps.secret)) return err('INVALID_SIGNATURE', 'Invalid signature');

    let evt: any;
    try { evt = JSON.parse(raw.toString('utf8')); } catch { return err('INVALID_PARAMETER', 'Body is not JSON'); }

    const txnId = String(evt.billing?.transaction?.id ?? evt.transaction?.id ?? evt.order?.id ?? '');
    const userId: string | undefined = evt.user?.external_id ?? evt.user?.id;

    switch (evt.notification_type) {
      case 'user_validation':
        // No user database in this example: accept. Replace with a real lookup (400 INVALID_USER if unknown).
        return ok;

      case 'order_paid': {
        if (!userId || !txnId) return err('INVALID_PARAMETER', 'Missing user or transaction id');
        if (!(await deps.claims.claim(txnId))) return ok; // duplicate delivery
        const items = (evt.items ?? []).map((i: any) => ({ sku: String(i.sku), quantity: Number(i.quantity ?? 1) }));
        try {
          await deps.grants.grant(userId, items, txnId);
        } catch (e) {
          await deps.claims.release(txnId); // otherwise Xsolla's retry hits the claim and the purchase is never granted
          throw e;
        }
        return ok;
      }

      case 'order_canceled':
      case 'refund': {
        if (!userId || !txnId) return err('INVALID_PARAMETER', 'Missing user or transaction id');
        await deps.grants.revoke(userId, txnId);
        return ok;
      }

      // `payment` (separate delivery mode) is a financial record; fulfillment happens on order_paid only.
      default:
        return ok;
    }
  };
}

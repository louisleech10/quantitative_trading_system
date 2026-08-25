/**
 * GAP-3 UX Task 1.3 之驗收 ④(a)：雜湊入口之**執行期**計數（vitest `setupFiles`）。
 *
 * 🔴 這裡裝的是**計數包裝（passthrough）而非空殼 stub**：真實行為保持不變，
 *    只把每次呼叫記到 `globalThis.__hashEntryCalls`，其他既有測試因此不受影響。
 *
 * 覆蓋面（顯式枚舉，**不得自稱窮舉**——本清單已連三輪被補：R15 三項 → R16 補 `hash` → R17 補 `Hash`）：
 *   - `globalThis.crypto.subtle.digest`（Web Crypto；不在 node 模組列舉內，故另行處理）
 *   - `node:crypto` 之 `createHash`／`hash`／`Hash`／`webcrypto` ⇒ 由測試檔以 hoisted
 *     `vi.mock('node:crypto', …)` 包裝（ESM 命名空間物件唯讀，無法在此就地改寫）
 *
 * ⚠️ 具名殘留（**不得宣稱已解決**）：純 JS 手刻 sha256（不經上述入口）本閘看不見；
 *    三值理由 `needs-research`，owner 主委。
 */

export interface HashEntryCall {
  entry: string;
  input: string;
}

declare global {
  // eslint-disable-next-line no-var
  var __hashEntryCalls: HashEntryCall[] | undefined;
}

globalThis.__hashEntryCalls = globalThis.__hashEntryCalls ?? [];

/** 清空計數（測試於 act 前呼叫）。 */
export function resetHashEntryCalls(): void {
  globalThis.__hashEntryCalls = [];
}

/** 讀取計數。 */
export function hashEntryCalls(): HashEntryCall[] {
  return globalThis.__hashEntryCalls ?? [];
}

function decode(data: unknown): string {
  if (typeof data === 'string') return data;
  try {
    if (data instanceof ArrayBuffer) return new TextDecoder().decode(new Uint8Array(data));
    if (ArrayBuffer.isView(data)) return new TextDecoder().decode(data as Uint8Array);
  } catch {
    /* 無法解碼者以型別名記錄即可——計數才是斷言對象 */
  }
  return `<${Object.prototype.toString.call(data)}>`;
}

const subtle = globalThis.crypto?.subtle;
if (subtle) {
  const proto = Object.getPrototypeOf(subtle) as { digest?: (...a: unknown[]) => unknown };
  const original = proto?.digest;
  if (typeof original === 'function' && !(original as { __gap3Wrapped?: boolean }).__gap3Wrapped) {
    const wrapped = function (this: unknown, algorithm: unknown, data: unknown) {
      (globalThis.__hashEntryCalls ??= []).push({ entry: 'crypto.subtle.digest', input: decode(data) });
      return (original as (...a: unknown[]) => unknown).call(this, algorithm, data);
    };
    (wrapped as { __gap3Wrapped?: boolean }).__gap3Wrapped = true;
    proto.digest = wrapped as typeof original;
  }
}

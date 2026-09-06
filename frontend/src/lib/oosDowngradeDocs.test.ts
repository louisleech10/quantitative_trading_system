/**
 * `CODEX-R2-P1-06`：降級原因之文案，鍵集必須與**後端實際會產出的 reason** 對齊。
 *
 * 🔴 對證方式＝讀後端原始碼取出 `_downgrade_branch` 的回傳字面 ＋ fallback 的兩個 reason。
 * 這是本 repo 既有作法（同 `eventContractDocs.test.ts` 之契約逐字比對）：
 * 前端持文案，另以測試對後端來源機械比對——後端加了新 reason 而前端沒補說明，這裡會紅。
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  OOS_DOWNGRADE_DOCS,
  REASON_UNKNOWN_FALLBACK,
  oosDowngradeDoc,
} from './oosDowngradeDocs';

const ORCH = resolve(__dirname, '../../../momentum/Analysis/ic_filter_orchestrator.py');

/** 從後端原始碼撈出所有會進 `oos_downgrade.reason` 的字面值。 */
function backendReasons(): string[] {
  const src = readFileSync(ORCH, 'utf-8');
  const found = new Set<string>();

  // ① `_downgrade_branch` 的 `return "..."`（只取該函式區段，避免掃到全檔別的 return）
  const start = src.indexOf('def _downgrade_branch');
  expect(start, '找不到 _downgrade_branch——後端重構了就該同步本測試').toBeGreaterThan(0);
  const end = src.indexOf('\n    @staticmethod', start + 10);
  const body = src.slice(start, end > start ? end : start + 3000);
  for (const m of body.matchAll(/return "([a-z_]+)"/g)) found.add(m[1]);

  // ② full-sample fallback 的兩個 reason（以 keyword 形式傳入）
  for (const m of src.matchAll(/reason="([a-z_]+)"/g)) found.add(m[1]);

  return [...found].sort();
}

describe('oosDowngradeDocs — 鍵集對後端 reason 機械對證', () => {
  it('後端每一個 reason 都有前端說明（少一個就是畫面會說不出話）', () => {
    const missing = backendReasons().filter((r) => !(r in OOS_DOWNGRADE_DOCS));
    expect(missing, `後端有這些 reason 但前端沒有說明：${missing.join('、')}`).toEqual([]);
  });

  it('正向對照：真的撈到 reason（否則上一條是空迴圈假綠）', () => {
    const reasons = backendReasons();
    expect(reasons.length).toBeGreaterThanOrEqual(5);
    expect(reasons).toContain('event_filter_fallback');
    expect(reasons).toContain('no_holdout_evidence');
  });

  it('每條說明兩欄皆非空', () => {
    for (const [key, doc] of Object.entries(OOS_DOWNGRADE_DOCS)) {
      expect(doc.what.length, `${key}.what 空`).toBeGreaterThan(10);
      expect(doc.next.length, `${key}.next 空`).toBeGreaterThan(10);
    }
  });

  it('🔴 event_filter_fallback 不得宣稱「沒有獨立測試集」——那是 R1 說錯的那句話', () => {
    const doc = OOS_DOWNGRADE_DOCS.event_filter_fallback;
    // 該路徑可以同時有已套用的 holdout（`ic_train_test_split` 預設 true），
    // 所以文案只能講「事件條件沒生效」，不能講切分。
    expect(doc.what).not.toContain('沒有保留獨立');
    expect(doc.what).toContain('事件');
    expect(doc.next).toContain('事件');
  });

  it('認不得的 reason ⇒ fail-closed，不替它編解釋', () => {
    expect(oosDowngradeDoc('brand_new_reason_from_backend')).toBe(REASON_UNKNOWN_FALLBACK);
    expect(oosDowngradeDoc(undefined)).toBe(REASON_UNKNOWN_FALLBACK);
    expect(oosDowngradeDoc(null)).toBe(REASON_UNKNOWN_FALLBACK);
    expect(oosDowngradeDoc('')).toBe(REASON_UNKNOWN_FALLBACK);
  });

  it('已知 reason 走自己那條，不落 fallback', () => {
    expect(oosDowngradeDoc('event_filter_fallback')).toBe(
      OOS_DOWNGRADE_DOCS.event_filter_fallback,
    );
  });
});

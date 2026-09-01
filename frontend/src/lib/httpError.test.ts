/**
 * `httpErrorMessage()` 之驗收（`--run httpError`）。
 *
 * 🔴 本檔的核心是**第一條**：結構化 detail 不得變成 `[object Object]`。
 * 那正是使用者 UAT B11 看到的畫面，而它讓錯誤訊息完全失去作用。
 */
import { describe, expect, it } from 'vitest';
import { httpErrorMessage } from './httpError';

describe('httpErrorMessage', () => {
  it('🔴 結構化 detail（物件）⇒ 取得裡面的 message，**不得**是 [object Object]', () => {
    const body = {
      detail: {
        kind: 'new_schema_on_legacy_endpoint',
        message: '偵測到新 schema；請改投事件匯入端點',
        failures: [],
      },
    };
    const msg = httpErrorMessage(body, '匯入失敗');
    expect(msg).not.toContain('[object Object]');
    expect(msg).toContain('偵測到新 schema');
    expect(msg).toContain('new_schema_on_legacy_endpoint');   // kind 也要看得到，否則查不出是哪一類
  });

  it('逐列 failures 摘要出前三筆＋剩餘筆數（整包 JSON 塞給使用者等於沒說）', () => {
    const body = {
      detail: {
        kind: 'contract_violation',
        message: '99 筆契約違規',
        failures: Array.from({ length: 99 }, (_, i) => ({ row: i, field: 'label_definition', reason: 'missing_required_field' })),
      },
    };
    const msg = httpErrorMessage(body, 'x');
    expect(msg).toContain('列 0／label_definition／missing_required_field');
    expect(msg).toContain('另有 96 筆');
  });

  it('detail 是字串 ⇒ 原樣回（既有行為不得被這次改動弄壞）', () => {
    expect(httpErrorMessage({ detail: 'Unsupported file format' }, 'x')).toBe('Unsupported file format');
  });

  it('FastAPI 422 之 validation 陣列 ⇒ 逐項串起來', () => {
    const body = { detail: [{ msg: 'field required' }, { msg: 'value is not a valid integer' }] };
    expect(httpErrorMessage(body, 'x')).toBe('field required；value is not a valid integer');
  });

  it('Feature Factory 之 {code} 形狀：只有 code 也要顯示出來（否則查不出是哪一類）', () => {
    expect(httpErrorMessage({ detail: { code: 'run_not_found' } }, 'x')).toContain('run_not_found');
    const both = httpErrorMessage({ detail: { code: 'run_busy', message: '這個 run 正在跑' } }, 'x');
    expect(both).toContain('run_busy');
    expect(both).toContain('這個 run 正在跑');
  });

  it('取不出訊息 ⇒ 用 fallback（不得回空字串讓畫面空白）', () => {
    expect(httpErrorMessage({}, '匯入失敗')).toBe('匯入失敗');
    expect(httpErrorMessage(null, '匯入失敗')).toBe('匯入失敗');
    expect(httpErrorMessage({ detail: { failures: [] } }, '匯入失敗')).toBe('匯入失敗');
  });

  it('detail 不存在但頂層就是拒收物件 ⇒ 照樣取得到', () => {
    const msg = httpErrorMessage({ kind: 'parse_error', message: 'CSV 無資料列', failures: [] }, 'x');
    expect(msg).toContain('CSV 無資料列');
  });
});

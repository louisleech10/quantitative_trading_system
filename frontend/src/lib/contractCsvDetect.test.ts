/**
 * 「走錯區」偵測（`--run contractCsvDetect`）。
 *
 * 🔴 **與 `tests/api/test_gap3_contract_csv_guard.py` 用同一組輸入**：那邊驗後端側規則，
 * 這邊驗前端側。任一端的正規化或 marker 改了而另一端沒跟，兩邊會各自紅。
 */
import { describe, expect, it } from 'vitest';
import { CONTRACT_MARKER_COLUMNS, canonColumnName, looksContractCsv } from './contractCsvDetect';

describe('契約 CSV 偵測', () => {
  it('marker ＝ event_id／t0／label 三欄（與後端 looks_new_schema 同一組）', () => {
    expect([...CONTRACT_MARKER_COLUMNS].sort()).toEqual(['event_id', 'label', 't0']);
  });

  it.each([
    ['原樣', ['event_id', 't0', 'label']],
    ['大小寫', ['Event_ID', 'T0', 'Label']],
    ['空白與引號', ['  event_id  ', '"t0"', "'label'"]],
    ['BOM', ['﻿event_id', 't0', 'label']],
    ['帶 meta 欄', ['event_id', 't0', 'label', 'meta.price_change']],
  ])('判為契約 CSV：%s', (_name, cols) => {
    expect(looksContractCsv(cols as string[])).toBe(true);
  });

  it('🔴 over：自有欄名之 CSV 不得被誤判（否則對映區整個不能用）', () => {
    expect(looksContractCsv(['幣種', '週期', '進場時間_毫秒', '我的標記'])).toBe(false);
    expect(looksContractCsv(['symbol', 'timestamp', 'label'])).toBe(false);   // 只有一欄同名不算
    expect(looksContractCsv([])).toBe(false);
  });

  it('canonColumnName 四件事都真的做了', () => {
    expect(canonColumnName('﻿  "Event_ID" ')).toBe('event_id');
  });
});

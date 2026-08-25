/**
 * GAP-3 UX B4 R1 群集 D — 前端預覽解析與後端 pandas 的**逐格對位**（selector：`gap3_csv`）。
 *
 * R1 三家共提：前端若靜默截斷／補齊，使用者會依錯誤筆數勾下確認。
 * 本檔把「前端看到的每一格」釘死，並標明對應的後端行為（後端側之對證在
 * `tests/api/test_gap3_csv_ragged_rows.py`，兩邊各自可獨立跑）。
 *
 * 🔴 這裡驗的是**位元組層的解析**，不是契約檢核——契約權威一律在後端（V-3）。
 */
import { describe, expect, it } from 'vitest';
import { countDeclaredLabels, columnValues, parseCsvText } from '@/lib/csvPreview';

describe('CSV 預覽解析之對位', () => {
  it('引號內之 CR 原樣保留（後端 pandas 亦保留 → 兩端同值）', () => {
    const parsed = parseCsvText('eid,sym\n"E1\r",ETHUSDT\n');
    expect(parsed.rows[0][0]).toBe('E1\r');
    expect(parsed.raggedRows).toEqual([]);
  });

  it('CRLF 行尾不會把 \\r 併進最後一格', () => {
    const parsed = parseCsvText('eid,lab\r\nE1,0\r\nE2,1\r\n');
    expect(parsed.rows).toEqual([['E1', '0'], ['E2', '1']]);
    expect(parsed.raggedRows).toEqual([]);
  });

  it('欄數比標頭多之列：**不截斷**，列進 raggedRows（後端會整批拒收）', () => {
    const parsed = parseCsvText('a,b,c\n1,2,3\n4,5,6,7\n');
    expect(parsed.raggedRows).toEqual([{ row: 1, width: 4 }]);
  });

  it('欄數比標頭少之列：補空字串但仍列進 raggedRows（不得靜默當成有值）', () => {
    const parsed = parseCsvText('a,b,c\n1,2,3\n4,5\n');
    expect(parsed.raggedRows).toEqual([{ row: 1, width: 2 }]);
    expect(parsed.rows[1]).toEqual(['4', '5', '']);
  });

  it('BOM 與跳脫雙引號', () => {
    const parsed = parseCsvText('﻿a,b\n"say ""hi""",2\n');
    expect(parsed.columns.map((c) => c.name)).toEqual(['a', 'b']);
    expect(parsed.rows[0][0]).toBe('say "hi"');
  });

  it('引號內之逗號與換行不被當成分隔', () => {
    const parsed = parseCsvText('a,b\n"x,y\nz",2\n');
    expect(parsed.rows).toEqual([['x,y\nz', '2']]);
    expect(parsed.raggedRows).toEqual([]);
  });

  it('筆數只認 0/1；空白儲存格與其他值分開計，不猜（與後端對映層同一條規則）', () => {
    const parsed = parseCsvText('lab,x\n1,a\n0,b\n,c\ntrue,d\n1,e\n');
    const counts = countDeclaredLabels(columnValues(parsed, 0));
    expect(counts).toEqual({ positive: 2, negative: 1, blank: 1, unreadable: 1 });
  });

  it('整行空白之列被略過（與 pandas 之 skip_blank_lines 預設一致，不算成一列空值）', () => {
    const parsed = parseCsvText('lab\n1\n\n0\n');
    expect(parsed.rows).toEqual([['1'], ['0']]);
    expect(parsed.raggedRows).toEqual([]);
  });

  it('舊式 Mac 換行（只有 CR）⇒ 回空模型並標記不支援，不得產出看似合理的欄名', () => {
    const parsed = parseCsvText('a,b\r1,2\r3,4\r');
    expect(parsed.unsupportedLineEnding).toBe(true);
    expect(parsed.columns).toEqual([]);      // 舊版會得到 ['a','b1','23','4'] 這種拼接欄名
    expect(parsed.rows).toEqual([]);
  });

  it('CRLF 與引號內之 CR 不得被誤判為舊式 Mac 換行', () => {
    expect(parseCsvText('a,b\r\n1,2\r\n').unsupportedLineEnding).toBe(false);
    expect(parseCsvText('a,b\n"x\r",2\n').unsupportedLineEnding).toBe(false);
    expect(parseCsvText('a,b\n"x\r",2\n').rows[0][0]).toBe('x\r');   // 引號內是資料，原樣保留
  });

  it('重複欄名之下拉字樣逐項可辨（第 N 欄）', () => {
    const parsed = parseCsvText('lab,lab,x\n1,0,9\n');
    expect(parsed.columns.map((c) => c.label)).toEqual(['lab（第 1 欄）', 'lab（第 2 欄）', 'x']);
    expect(parsed.duplicateNames).toEqual(['lab']);
  });
});

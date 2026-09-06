/**
 * `GAP3_EVENT_DISCLOSURE` Task 1.4 驗收：參數說明文案之單一來源。
 *
 * 🔴 本檔守的是**分界**，不是內容：契約已有 `doc` 的欄位不得在此再寫一份。
 *    兩份文案的失敗形態是「只改一處」，而那不會有任何東西紅。
 */
import { describe, expect, it } from 'vitest';
import { EVENT_PARAM_DOCS, EVENT_PARAM_DOC_KEYS } from '@/lib/eventParamDocs';
import { EVENT_CONTRACT_DOCS } from '@/lib/eventContractDocs';

const EXPECTED_KEYS = [
  'horizon_bars',
  'decision_offset_bars_analysis',
  'advanced_pair',
  'seed',
  'neighborhood_bars',
  'embargo_bars',
  'h_scan_inapplicable',
];

describe('EVENT_PARAM_DOCS', () => {
  it('鍵集**恰為**七個（多一個沒 render、少一個顯示不出來，皆須紅）', () => {
    expect(new Set(EVENT_PARAM_DOC_KEYS)).toEqual(new Set(EXPECTED_KEYS));
    expect(EVENT_PARAM_DOC_KEYS.length).toBe(7);
  });

  it('每鍵之 what／effect 皆非空，且不是同一句話', () => {
    for (const key of EXPECTED_KEYS) {
      const doc = EVENT_PARAM_DOCS[key];
      expect(doc, `缺鍵 ${key}`).toBeTruthy();
      expect(doc.what.trim().length, `${key}.what 為空`).toBeGreaterThan(10);
      expect(doc.effect.trim().length, `${key}.effect 為空`).toBeGreaterThan(10);
      // 🔴 兩欄語意不同：`what`＝這是什麼、`effect`＝為什麼你該在意。
      //    複製貼上兩份一樣的字等於只寫了一半。
      expect(doc.what, `${key} 的 what 與 effect 相同`).not.toBe(doc.effect);
    }
  });

  it('🔴 與契約 doc **鍵集不相交**（不得有第二份真相源）', () => {
    const contractKeys = new Set(Object.keys(EVENT_CONTRACT_DOCS));
    const overlap = EVENT_PARAM_DOC_KEYS.filter((k) => contractKeys.has(k));
    expect(overlap, `這些鍵在契約 doc 已有一份：${overlap.join('、')}`).toEqual([]);
    // 正向對照：契約 doc 真的非空（否則上一條對空集合恆成立）
    expect(contractKeys.size).toBeGreaterThan(0);
  });

  it('不得寫死任何數值門檻（門檻來自後端揭露，寫在前端會過期）', () => {
    for (const key of EXPECTED_KEYS) {
      const text = `${EVENT_PARAM_DOCS[key].what}${EVENT_PARAM_DOCS[key].effect}`;
      // 允許 h=1／h=24／k=0／k=2 這類**舉例**；擋的是「至少 131 列」這種門檻數字。
      expect(text, `${key} 疑似寫死門檻`).not.toMatch(/至少\s*\d+|不得少於\s*\d+|上限\s*\d+/);
    }
  });
});

/**
 * Task 4.1b 之**防漂移**：前端揭露文案之契約鏡像須與契約檔逐字相同。
 *
 * 契約沒有對前端開放的端點，故沿用本 repo 既有作法（`eventId.ts` ＋ `canonicalSourceCoverage.test.ts`）：
 * 前端持鏡像常數，本檔**讀契約 JSON 逐字比對**——契約改字而前端沒跟，這裡會轉紅。
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { EVENT_CONTRACT_DOCS, EVENT_CONTRACT_DOC_PATHS } from './eventContractDocs';

const CONTRACT = resolve(
  __dirname, '../../../momentum/Analysis/contracts/event_import_contract.json',
);

function at(obj: unknown, path: readonly string[]): unknown {
  return path.reduce<unknown>((acc, key) => (acc as Record<string, unknown>)?.[key], obj);
}

describe('Task 4.1b — 揭露文案之契約鏡像', () => {
  const contract = JSON.parse(readFileSync(CONTRACT, 'utf8')) as unknown;

  it.each(Object.keys(EVENT_CONTRACT_DOCS) as (keyof typeof EVENT_CONTRACT_DOCS)[])(
    '`%s` 之白話逐字等於契約 doc',
    (key) => {
      const fromContract = at(contract, EVENT_CONTRACT_DOC_PATHS[key]);
      // 正向對照：契約真的有這個路徑（打錯路徑時 `undefined === undefined` 不會被當成通過）
      expect(typeof fromContract).toBe('string');
      expect(EVENT_CONTRACT_DOCS[key]).toBe(fromContract);
    },
  );

  it('🔴 附帶欄之契約 doc 逐欄含「不進 ic_feed」（`D-004 A-020` 之裁定字面）', () => {
    const optional = at(contract, ['optional_fields']) as Record<string, { doc?: string }>;
    const futures = Object.keys(optional).filter((k) => /^future_\d+bar_return$/.test(k));
    expect(futures.length).toBe(12);          // 逐欄列舉 12 鍵（契約無 pattern 機制）
    for (const name of futures) {
      expect(optional[name].doc, `${name} 之 doc`).toContain('不進 ic_feed');
      expect(optional[name].doc, `${name} 之 doc`).toContain('Excel');
    }
  });
});

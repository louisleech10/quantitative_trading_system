/**
 * GAP-3 UX Task 2.2 驗收（`npm --prefix frontend test -- --run exportFilterPersist`）。
 *
 * 判準字面之唯一來源＝SPEC L1865–1879「驗證」欄：
 * ①匯出檔 `label_definition.filters` 與送出條件**深度相等**（逐鍵遞迴比對）；
 * ②`filters` 鍵**存在於**契約 `label_definition.fields`（防漂移）。
 * 🔴 **不可做**：不得把篩選條件納入 `event_id` 之輸入（違反 D-2）。
 *
 * 🔴 落點說明：SPEC／TODO 之「修改檔案」行寫的是後端序列化函式，但 `label_definition`
 * 實際是在**前端** `eventExport.ts` 組的（後端只驗證與落檔）。該 doc drift 已走延伸檔
 * `docs/GAP3_EVENT_UX_TODO.D-003.md` A-018 更正。
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { buildEventContractRecords } from '@/lib/eventExport';
import { buildExportFilterSpec, type ExportFilterCondition } from '@/lib/exportFilter';
import type { CaseData } from '@/lib/types';

const CONTRACT_PATH = path.resolve(__dirname, '../../../momentum/Analysis/contracts/event_import_contract.json');
const CONTRACT = JSON.parse(readFileSync(CONTRACT_PATH, 'utf8'));

const SOURCE_TEXT = '[{"close":1.0,"symbol":"ETHUSDT"}]';
const SOURCE_DIGEST = createHash('sha256').update(SOURCE_TEXT, 'utf8').digest('hex');

const CASES = [
  { symbol: 'ETHUSDT', timeframe: '12h', timestamp: '2024-01-01 00:00:00', positive_case: true, future_2bar_return: 1.5 },
  { symbol: 'ETHUSDT', timeframe: '12h', timestamp: '2024-01-01 12:00:00', positive_case: false, future_2bar_return: -0.5 },
] as unknown as CaseData[];

const CONDITIONS: ExportFilterCondition[] = [
  { column: 'future_2bar_return', op: '>=', value: 1.0 },
  { column: 'volume_multiplier', op: 'between', range: [1, 2] },
];

async function build(filters: ReturnType<typeof buildExportFilterSpec>) {
  return buildEventContractRecords(CASES, {
    timeframe: '12h',
    conditions: [],
    priceChangeMethod: 'close_to_close',
    horizonBars: 2,
    sourceFileText: SOURCE_TEXT,
    sourceFileDigest: SOURCE_DIGEST,
    filters,
  });
}

describe('Task 2.2 篩選條件寫入 label_definition.filters', () => {
  it('① 匯出檔之 filters 與送出條件深度相等（逐鍵遞迴）', async () => {
    const spec = buildExportFilterSpec(CONDITIONS);
    const payload = await build(spec);
    for (const rec of payload.records) {
      const written = (rec.label_definition as { filters?: unknown }).filters;
      expect(written).toEqual(spec);                    // toEqual＝逐鍵遞迴比對
      expect(JSON.stringify(written)).toBe(JSON.stringify(spec));   // 連鍵序都一致
    }
  });

  it('② filters 鍵存在於契約之 label_definition.fields（防漂移）', () => {
    expect(Object.keys(CONTRACT.required_fields.label_definition.fields)).toContain('filters');
    // 形狀之唯一定義來源也在契約裡，且與前端產出的鍵一致
    const shape = CONTRACT.required_fields.label_definition.fields.filters.wire_shape;
    expect(shape.version).toBe(1);
    expect(shape.combinator).toBe('AND');
    const spec = buildExportFilterSpec(CONDITIONS)!;
    expect(Object.keys(spec).sort()).toEqual(Object.keys(shape).sort());
  });

  it('③ 🔴 篩選條件不得改變 event_id（D-2：同事件跨批 id 必須相同）', async () => {
    const withoutFilters = await build(null);
    const withFilters = await build(buildExportFilterSpec(CONDITIONS));
    const other = await build(buildExportFilterSpec([{ column: 'price_change', op: '<=', value: -1 }]));

    const ids = (p: Awaited<ReturnType<typeof build>>) => p.records.map((r) => r.event_id);
    expect(ids(withFilters)).toEqual(ids(withoutFilters));
    expect(ids(other)).toEqual(ids(withoutFilters));
    expect(ids(withoutFilters).length).toBe(2);         // 防「兩邊都是空集合」之恆等假綠
  });

  it('④ 無條件 ⇒ 不寫 filters 鍵（存在與否本身有語意）', async () => {
    const payload = await build(null);
    for (const rec of payload.records) {
      expect('filters' in (rec.label_definition as object)).toBe(false);
    }
  });

  it('⑤ label_definition 之其他鍵不因加了 filters 而改變', async () => {
    const withoutFilters = await build(null);
    const withFilters = await build(buildExportFilterSpec(CONDITIONS));
    for (let i = 0; i < withFilters.records.length; i += 1) {
      const a = { ...(withFilters.records[i].label_definition as Record<string, unknown>) };
      delete a.filters;
      expect(a).toEqual(withoutFilters.records[i].label_definition);
    }
  });
});

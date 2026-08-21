/**
 * GAP-3 B5.2：把 /search 結果組成事件契約（event_import_contract.json）新 schema 記錄。
 * 純組裝、不算統計；欄位語意：t0＝觸發根 open（ms UTC）、label＝正反例標記、direction 由條件方向推、
 * scenario 預設 C（確認型）、entry_price_semantic 預設 trigger_open、label_definition 由搜尋條件摘要＋digest 組。
 * 使用者匯入前仍可手改；後端 validator 為唯一真相源（本檔不重做檢查）。
 */
import type { CaseData } from './types';

export interface EventExportOptions {
  timeframe: string;
  conditions: unknown[];
  priceChangeMethod: string;
  horizonBars?: number;
  direction?: 'long' | 'short';
  scenario?: 'A' | 'B' | 'C' | 'two_stage';
  entryPriceSemantic?: 'trigger_open' | 'trigger_close' | 'next_open' | 'decision_bar_open' | 'decision_bar_close';
}

async function sha256Hex(text: string): Promise<string> {
  const subtle = globalThis.crypto?.subtle;
  if (subtle) {
    const buf = await subtle.digest('SHA-256', new TextEncoder().encode(text));
    return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, '0')).join('');
  }
  // jsdom／舊環境退路：FNV-1a 64 位展開為 64 hex（僅供測試環境；瀏覽器一律走 subtle）
  let h1 = 0x811c9dc5;
  let h2 = 0x01000193;
  for (let i = 0; i < text.length; i++) {
    const c = text.charCodeAt(i);
    h1 = Math.imul(h1 ^ c, 0x01000193) >>> 0;
    h2 = Math.imul(h2 ^ c, 0x811c9dc5) >>> 0;
  }
  const part = (h1.toString(16).padStart(8, '0') + h2.toString(16).padStart(8, '0')).repeat(4);
  return part.slice(0, 64);
}

/** timestamp 字串／數字 → epoch ms（秒級自動 ×1000；ISO 字串 Date.parse）。 */
export function toEpochMs(ts: string | number | null | undefined): number | null {
  if (ts === null || ts === undefined || ts === '') return null;
  if (typeof ts === 'number') return ts < 1e12 ? Math.round(ts * 1000) : Math.round(ts);
  const n = Number(ts);
  if (Number.isFinite(n)) return n < 1e12 ? Math.round(n * 1000) : Math.round(n);
  const parsed = Date.parse(ts.endsWith('Z') || /[+-]\d\d:?\d\d$/.test(ts) ? ts : `${ts.replace(' ', 'T')}Z`);
  return Number.isFinite(parsed) ? parsed : null;
}

export function inferDirection(conditions: unknown[]): 'long' | 'short' {
  for (const c of conditions as { parameter?: string; operator?: string; value?: unknown }[]) {
    if (c?.parameter === 'price_change') {
      const v = Array.isArray(c.value) ? Number(c.value[0]) : Number(c.value);
      if (c.operator === '<=' || (Number.isFinite(v) && v < 0)) return 'short';
    }
  }
  return 'long';
}

export async function buildEventContractRecords(cases: CaseData[], opts: EventExportOptions) {
  const horizon = opts.horizonBars ?? 2;
  const direction = opts.direction ?? inferDirection(opts.conditions);
  const ruleSummary = JSON.stringify({ conditions: opts.conditions, price_change_method: opts.priceChangeMethod, timeframe: opts.timeframe });
  const ruleDigest = await sha256Hex(ruleSummary);
  const sourceDigest = await sha256Hex(JSON.stringify(cases.map((c) => [c.symbol, c.timestamp, (c as CaseData & { positive_case?: unknown }).positive_case])));
  const snapshot = `search:${opts.timeframe}:${new Date().toISOString().slice(0, 10)}`;
  const skipped: { index: number; reason: string }[] = [];
  const records = cases.flatMap((c, i) => {
    const t0 = toEpochMs(c.timestamp);
    if (t0 === null) {
      skipped.push({ index: i, reason: 'unparseable_timestamp' });
      return [];
    }
    const pc = (c as CaseData & { positive_case?: boolean | number }).positive_case;
    const label = pc === true || pc === 1 ? 1 : pc === false || pc === 0 ? 0 : null;
    if (label === null) {
      skipped.push({ index: i, reason: 'missing_positive_case_flag' });
      return [];
    }
    return [{
      event_id: `${c.symbol}:${c.timeframe || opts.timeframe}:${t0}`,
      symbol: c.symbol,
      timeframe: c.timeframe || opts.timeframe,
      t0,
      decision_offset_bars: 0,
      entry_price_semantic: opts.entryPriceSemantic ?? 'trigger_open',
      direction,
      scenario: opts.scenario ?? 'C',
      label,
      label_definition: {
        rule_id: `search:price_change:${opts.priceChangeMethod || 'default'}`,
        canonical_digest: ruleDigest,
        window: { horizon_bars: horizon },
        label_return_mode: 'close_to_close',
      },
      control_kind: 'user_labeled_same_trigger',
      source_file_digest: sourceDigest,
      data_snapshot_digest: snapshot,
      search_rule_summary: ruleSummary,
      kind_source: 'user',
    }];
  });
  return { records, skipped, n_cases: cases.length, n_records: records.length, note: '匯入前請確認 label_definition.window.horizon_bars 與你的答案窗一致；欄位以 event_import_contract.json 為準' };
}

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

/** 真 SHA-256（WebCrypto）；環境無 subtle ⇒ 拋錯，不做假 hash 退路（CODEX-R1-P1-02）。 */
export async function sha256Hex(text: string): Promise<string> {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) throw new Error('WebCrypto subtle 不可用：無法計算 source_file_digest（不提供非 SHA-256 退路）');
  const buf = await subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, '0')).join('');
}

/** 來源 canonical bytes：搜尋結果（cases）之 canonical JSON——`source_file_digest` 綁的是這份「來源」，非匯出檔自身。 */
export function canonicalSourceText(cases: CaseData[]): string {
  return JSON.stringify(
    cases.map((c) => ({
      symbol: c.symbol,
      timeframe: c.timeframe ?? null,
      timestamp: c.timestamp,
      positive_case: (c as CaseData & { positive_case?: unknown }).positive_case ?? null,
      price_change: typeof c.price_change === 'number' ? c.price_change : null,
    })),
  );
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
  const sourceText = canonicalSourceText(cases);
  const sourceDigest = await sha256Hex(sourceText);
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
    // label_value：**答案窗**未來報酬（`future_{horizon}bar_return`），與 label_definition.window.horizon_bars 對齊；
    // CODEX-R2-P1-02：不得用 `price_change`（觸發根自身報酬，語意不同）。缺該欄 ⇒ 不寫 label_value（條件 IC 會 loud unavailable）。
    const futureKey = `future_${horizon}bar_return` as keyof CaseData;
    const fwdRaw = typeof c[futureKey] === 'number' && Number.isFinite(c[futureKey] as number) ? (c[futureKey] as number) : null;
    const labelValue = fwdRaw === null ? null : direction === 'short' ? -fwdRaw : fwdRaw;
    if (fwdRaw === null) skipped.push({ index: i, reason: `missing_${String(futureKey)}_label_value_omitted` });
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
      ...(labelValue === null ? {} : { label_value: labelValue }),
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
  return {
    records,
    skipped,
    n_cases: cases.length,
    n_records: records.length,
    source_file_digest: sourceDigest,
    source_digest_of: 'canonical JSON of search result cases (symbol,timeframe,timestamp,positive_case,price_change)',
    /** 契約所指「來源檔」之內容：其 sha256 === source_file_digest；匯入時以 source_file 一併上傳即可通過 verify（CODEX-R2-P1-03） */
    source_file_text: sourceText,
    verify_note: '要驗 digest：匯入時把同時下載的 *.source.json 放在 source_file 欄並開 verify_source_digest；事件檔自身含 digest 欄，自我對證必然不符',
    n_missing_label_value: skipped.filter((s) => s.reason.includes('label_value_omitted')).length,
    label_value_source: `future_${horizon}bar_return（signed；short 取負）`,
    note: `匯入前請確認 label_definition.window.horizon_bars（現為 ${horizon}）與你的答案窗一致；label_value 取同 horizon 之未來報酬欄，缺者不寫（條件 IC 會顯示 unavailable）；欄位以 event_import_contract.json 為準`,
  };
}

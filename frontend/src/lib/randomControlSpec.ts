/**
 * `G3-D2` D5.3 — 由**觸發批 detail** ＋ 使用者參數組出 `random_control_spec`（純函式）。
 *
 * 🔴 存在理由：抽樣契約有十幾個鍵，其中大半是**從批次事實導出**的（symbol／timeframe／
 * direction／期間／答案窗長度）。若在元件內就地拼裝，那些導出規則會散落在 JSX 裡，
 * 而「導出錯了」的症狀是——抽樣照跑、值合法、對照組卻不是同一個母體。
 * ⇒ 集中成一支純函式，可單元測試、可證偽。
 *
 * 🔴 **只產出輸入鍵**（universe／strata／allocation／exclusion／label_rule／seed／
 * n_requested／replacement）。收據鍵（n_drawn／per_stratum／sample_ids_digest／
 * candidate_count／data_snapshot_digest／generator_version）由後端產生器填回；
 * 前端送這些鍵是把產出當輸入。
 */
import type { EventImportDetail } from './types';

/** 抽樣契約之 `allocation` 封閉單值（後端契約定死；此處為鏡像，由測試對證）。 */
export const RANDOM_CONTROL_ALLOCATION = 'proportional_to_candidates';

export interface RandomControlParams {
  /** 想抽幾筆（實際抽出可能較少，後端以 `n_drawn` 揭露）。 */
  nRequested: number;
  seed: number;
  /** 觸發事件**之前**幾根一併排除。 */
  neighborhoodBars: number;
  /** 觸發事件答案窗**之後**幾根一併排除。 */
  embargoBars: number;
  /**
   * 標籤門檻。🔴 觸發批有落檔 `receipt_batch.label_rule` 時**以它為準**，
   * 使用者輸入僅在缺席時使用——那種情況下比較會回 `identity_unverifiable`，
   * 由 UI 誠實揭露，不假裝兩批用的是同一把尺。
   */
  threshold: number;
}

export type RandomControlSpecResult =
  | { ok: true; spec: Record<string, unknown>; usedBatchLabelRule: boolean }
  | { ok: false; reason: string };

/** 逐列讀 `label_definition.window.horizon_bars`；混值／缺值 ⇒ `null`（不取第一列）。 */
export function batchHorizonBars(detail: EventImportDetail): number | null {
  const seen = new Set<number>();
  for (const rec of detail.records ?? []) {
    const ld = (rec as { label_definition?: { window?: { horizon_bars?: unknown } } }).label_definition;
    const h = ld?.window?.horizon_bars;
    if (typeof h !== 'number' || !Number.isInteger(h)) return null;
    seen.add(h);
  }
  return seen.size === 1 ? [...seen][0] : null;
}

/** 逐列讀 `symbol`／`timeframe`；混值／缺值 ⇒ `null`（單一 symbol×timeframe 才可抽樣）。 */
function singleString(detail: EventImportDetail, field: string): string | null {
  const seen = new Set<string>();
  for (const rec of detail.records ?? []) {
    const v = (rec as Record<string, unknown>)[field];
    if (typeof v !== 'string' || v === '') return null;
    seen.add(v);
  }
  return seen.size === 1 ? [...seen][0] : null;
}

export function buildRandomControlSpec(
  detail: EventImportDetail, params: RandomControlParams,
): RandomControlSpecResult {
  const t0s = (detail.batch_facts.t0 ?? []).map((r) => r.t0_ms).filter((n) => Number.isFinite(n));
  if (t0s.length === 0) return { ok: false, reason: '這批沒有事件，沒有可對照的對象' };
  const symbol = singleString(detail, 'symbol');
  const timeframe = singleString(detail, 'timeframe');
  if (symbol === null || timeframe === null) {
    return { ok: false, reason: '這批跨 symbol／timeframe（或欄位缺值）；對照組之母體須為單一 symbol×timeframe，請先拆批' };
  }
  const direction = detail.batch_facts.direction;
  if (!direction) return { ok: false, reason: '這批之 direction 非單值；對照組要用同一個方向標籤' };
  const horizon = batchHorizonBars(detail);
  if (horizon === null || horizon < 1) {
    return { ok: false, reason: '這批之答案窗長度非單值（或 < 1）；對照組要用同一條規則' };
  }
  const batchRule = detail.receipt_batch?.label_rule ?? null;
  const threshold = batchRule ? batchRule.threshold : params.threshold;
  const horizonBars = batchRule ? batchRule.horizon_bars : horizon;
  const period = { start_ms: Math.min(...t0s), end_ms: Math.max(...t0s) };
  return {
    ok: true,
    usedBatchLabelRule: batchRule !== null,
    spec: {
      universe: { symbol, timeframe, start_ms: period.start_ms, end_ms: period.end_ms },
      strata: { symbol, timeframe, period, direction },
      allocation: RANDOM_CONTROL_ALLOCATION,
      exclusion: {
        trigger_ids_digest: '',
        neighborhood_bars: params.neighborhoodBars,
        embargo_bars: params.embargoBars,
      },
      label_rule: { threshold, horizon_bars: horizonBars },
      seed: params.seed,
      n_requested: params.nRequested,
      replacement: false,
    },
  };
}

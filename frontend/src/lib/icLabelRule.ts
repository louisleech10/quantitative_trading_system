/**
 * EVTLABEL Task 1.2／1.3：本次分析**實際用到**的 label 規則揭露與 h／k 單位文案。
 *
 * 後端只在事件路徑寫 `metadata.event_label_rule`（`momentum/Analysis/event_label_mode.py`），
 * 全域 run 沒這個鍵 ⇒ 不渲染。前端**不重算任何單位**，只把後端算好的值排成句子。
 *
 * 使用者 2026-09-10 裁定：h／k 一律是「事件週期的根數」，UI 必須寫清楚；
 * 且要講明「t₀ 前幾小時的細節」是特徵週期的 Lag 欄在管，不是靠調 k。
 */

/** 後端 `metadata.event_label_rule`；鍵集之單一真相源＝`momentum/Analysis/contracts/event_label_mode.json`。 */
export interface ICEventLabelRule {
  label_source?: string | null;
  statistic_kind?: string | null;
  horizon_bars?: number | null;
  decision_offset_bars?: number | null;
  entry_price_semantic?: string | null;
  label_return_mode?: string | null;
  h_unit?: string | null;
  event_timeframe?: string | null;
  feature_timeframe?: string | null;
  feature_bars_per_event_bar?: number | null;
  ratio_integral?: boolean | null;
  label_window_feature_bars?: number | null;
  return_formula?: string | null;
  imported_binary_label?: {
    present?: boolean;
    n_pos?: number;
    n_neg?: number;
    used?: boolean;
  } | null;
  n_events_consumed?: number | null;
  uniqueness?: {
    mean?: number | null;
    min?: number | null;
    n_eff?: number | null;
    n_overlapping_pairs?: number | null;
  } | null;
}

export function readLabelRule(
  metadata: Record<string, unknown> | undefined | null,
): ICEventLabelRule | null {
  const raw = metadata?.event_label_rule;
  return raw && typeof raw === 'object' ? (raw as ICEventLabelRule) : null;
}

/**
 * Task 1.3：timeframe 字串 → 秒。
 * 🔴 **刻意用解析而非再抄一份表**：`12h`／`1h` 這種標籤本身就是定義，抄表會多出一份會漂的真相源。
 * 認得 `m`／`h`／`d`／`w`；認不得 ⇒ null（呼叫端退化成不帶換算的句子，不猜）。
 */
export function timeframeSeconds(tf: string | null | undefined): number | null {
  if (!tf) return null;
  const m = /^(\d+)([mhdw])$/.exec(tf.trim());
  if (!m) return null;
  const n = Number(m[1]);
  const unit = { m: 60, h: 3600, d: 86400, w: 604800 }[m[2] as 'm' | 'h' | 'd' | 'w'];
  return n > 0 && unit ? n * unit : null;
}

/** Task 1.3：事件週期 1 根＝特徵週期幾根；非整數倍或認不得 ⇒ null。 */
export function barsPerEventBar(
  eventTf: string | null | undefined,
  featureTf: string | null | undefined,
): number | null {
  const e = timeframeSeconds(eventTf);
  const f = timeframeSeconds(featureTf);
  if (!e || !f || e % f !== 0) return null;
  return e / f;
}

/**
 * Task 1.3：h／k 輸入框旁的單位說明。`ratio` 由呼叫端給（整數才傳）。
 * 缺 tf 或非整數倍 ⇒ 退化成不帶換算的句子（不猜數字）。
 */
export function unitCaption(
  eventTf: string | null | undefined,
  featureTf: string | null | undefined,
  ratio: number | null | undefined,
): string {
  if (eventTf && featureTf && typeof ratio === 'number' && Number.isInteger(ratio) && ratio > 0) {
    return `單位：事件週期（${eventTf}）的根數；1 根＝${featureTf} 特徵的 ${ratio} 根`;
  }
  return '單位：事件週期的根數';
}

/** Task 1.3：k 旁的第二句（使用者 2026-09-10：粗細粒度的誤解要在畫面上講掉）。 */
export function kHintCaption(featureTf: string | null | undefined): string {
  const tf = featureTf || '特徵週期';
  return `k=0 即在 t₀ 決策、特徵取到 t₀ 前最後一根 ${tf}；t₀ 前幾小時的細節在 ${tf} 特徵的 Lag／Momentum 欄，不需調 k`;
}

/** Task 1.3：h 旁的第二句。 */
export function hHintCaption(eventTf: string | null | undefined): string {
  return `答案窗＝h 根 ${eventTf || '事件週期'}（open 起算模式為 h+1 根）`;
}

/**
 * Task 1.2：隔離區下方「本次 label 怎麼算」四行。
 * 缺 `metadata.event_label_rule` ⇒ null（不渲染）。任一欄缺 ⇒ 該行退化，**不得空白**。
 */
export function labelRuleLines(rule: ICEventLabelRule | null | undefined): string[] | null {
  if (!rule) return null;
  const h = rule.horizon_bars ?? '—';
  const k = rule.decision_offset_bars ?? '—';
  const eventTf = rule.event_timeframe || '事件週期';
  const featureTf = rule.feature_timeframe || '特徵週期';
  const windowBars = rule.label_window_feature_bars;
  const ratioKnown =
    typeof rule.feature_bars_per_event_bar === 'number' && rule.ratio_integral === true;

  const unitTail =
    ratioKnown && typeof windowBars === 'number'
      ? `（單位＝事件週期 ${eventTf} 的根數＝${featureTf} 特徵的第 ${windowBars} 根）`
      : '（單位＝事件週期的根數）';
  const kTail = ratioKnown
    ? `（同單位；1 根＝${featureTf} 特徵的 ${rule.feature_bars_per_event_bar} 根）`
    : '（同單位）';

  const entry = rule.entry_price_semantic || '未揭露';
  const formula = rule.return_formula || '報酬算法未揭露（後端缺欄）';

  const bin = rule.imported_binary_label;
  const hasBinary = Boolean(bin?.present);
  const binaryHave = hasBinary
    ? `有（正 ${bin?.n_pos ?? '—'}／反 ${bin?.n_neg ?? '—'}）`
    : '無';
  const binaryUsed = bin?.used
    ? '本次已用（IC 對的是你的 0/1 標籤）'
    : '本次未用（IC 對的是規則重算的報酬）';

  const lines = [
    `h=${h} 根${unitTail}`,
    `k=${k} 根${kTail}`,
    `進場價＝${entry}；報酬＝${formula}`,
    `你匯入的 0/1 標籤：${binaryHave}；${binaryUsed}`,
  ];

  // R-1 不重工預留之揭露：事件答案窗重疊程度（只看，不參與計算）
  const uq = rule.uniqueness;
  if (uq && typeof uq.n_eff === 'number' && typeof rule.n_events_consumed === 'number') {
    lines.push(
      `事件重疊度：${rule.n_events_consumed} 個事件之有效樣本 ${uq.n_eff.toFixed(1)}（重疊配對 ${uq.n_overlapping_pairs ?? 0} 對）`,
    );
  }
  return lines;
}

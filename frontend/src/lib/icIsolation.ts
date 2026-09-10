/**
 * EVTALIGN Task 5.1：`report.metadata.isolation`——隔離區兩塊來源分開講。
 * 使用者混淆點：purge 用全域 default_horizon 算、與事件 label 的 h 無關；embargo 才是事件 look-ahead 抬高的。
 * 後端只在事件分析且切分已套用時才寫；沒鍵 ⇒ null，不渲染（不顯示 0 根）。
 */
export interface ICIsolation {
  purge?: { bars?: number; source?: string; effective_horizon?: number | null; note?: string } | null;
  embargo?: { bars?: number; source?: string; event_purge_rows?: number; config_embargo?: number } | null;
  total_bars?: number | null;
  note?: string;
}

const SOURCE_TEXT: Record<string, string> = {
  // EVTLABEL Task 2.3 之新來源（舊鍵保留：舊報告仍讀得到）
  event_label_window: '由你設的 label 答案窗（h×事件週期）換算成特徵根數',
  mainline_horizon: '由主線 horizon 決定（你的 label 答案窗沒有比它長）',
  event_lookahead_depth: '由這批宣告的 look-ahead 深度（挑樣本時看了多遠）換算成特徵根數',
  // 舊鍵（EVTALIGN 時代）：僅供舊報告顯示，新報告不再產生
  global_default_horizon: '由全域 default_horizon 決定（與你在事件 label 設的 h 無關）',
  event_lookahead: '由事件的 look-ahead（答案窗長度）換算成列數',
  config_embargo: '沿用設定檔的 embargo（事件換算值沒有比它大）',
};

export function readIsolation(metadata: Record<string, unknown> | undefined | null): ICIsolation | null {
  const raw = metadata?.isolation;
  return raw && typeof raw === 'object' ? (raw as ICIsolation) : null;
}

export function isolationLines(iso: ICIsolation | null | undefined): string[] | null {
  if (!iso || typeof iso.purge?.bars !== 'number' || typeof iso.embargo?.bars !== 'number') return null;
  const purgeSrc = SOURCE_TEXT[iso.purge.source ?? ''] ?? (iso.purge.source ?? '來源未標');
  const embargoSrc = SOURCE_TEXT[iso.embargo.source ?? ''] ?? (iso.embargo.source ?? '來源未標');
  const total = typeof iso.total_bars === 'number' ? iso.total_bars : iso.purge.bars + iso.embargo.bars;
  return [
    `purge ${iso.purge.bars} 根：${purgeSrc}`,
    `embargo ${iso.embargo.bars} 根：${embargoSrc}`,
    `總隔離 ${total} 根＝purge＋embargo（相加，只會偏保守，不是洩漏）`,
  ];
}

/** EVTWARMUP Task 2.1：`metadata.ic_window_disclosure`（事件路徑；TFWINDOW 後全域亦有）。沒鍵 ⇒ null。 */
export interface ICWindowDisclosure {
  window_unit?: string;
  timeframe_adjustment?: string;
  ic_mean_source?: { rolling_mean?: number; pooled_point_ic?: number; unavailable?: number };
  icir_role?: 'diagnostic' | 'threshold' | string;
  adjusted_windows?: number[];
}

export function windowDisclosureLine(metadata: Record<string, unknown> | undefined | null): string | null {
  const raw = metadata?.ic_window_disclosure;
  if (!raw || typeof raw !== 'object') return null;
  const d = raw as ICWindowDisclosure;
  const adj = d.timeframe_adjustment === 'applied'
    ? `rolling 視窗已依本 run 週期換算${Array.isArray(d.adjusted_windows) ? `（${d.adjusted_windows.join('／')} 根）` : ''}`
    : `rolling 視窗**未**依本 run 週期換算（沿用設定檔 12h 基準的根數；${d.timeframe_adjustment ?? 'not_applied'}）`;
  const role = d.icir_role === 'diagnostic'
    ? 'ICIR 在本次分析只作診斷、不當篩選門檻'
    : 'ICIR 為篩選門檻';
  const src = (d as { ic_mean_source?: { pooled_point_ic?: number; rolling_mean?: number } }).ic_mean_source;
  const meanNote = src && (src.pooled_point_ic ?? 0) > 0
    ? `；IC Mean 欄＝事件樣本 pooled IC（rolling 序列為空，${src.pooled_point_ic} 個特徵回退；t／p 檢定的即此統計量）`
    : '';
  return `${adj}；${role}${meanNote}。`;
}

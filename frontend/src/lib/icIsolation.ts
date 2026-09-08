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

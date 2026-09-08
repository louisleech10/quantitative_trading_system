/**
 * EVTALIGN Task 3.1：`report.metadata.period_alignment` 之顯示文字。
 * 🔴 後端**只在真的裁了／丟了**才寫這個鍵；沒有鍵 ⇒ 回 null，UI 不渲染（不顯示「裁 0 根」這種假揭露）。
 * 兩層來源：orchestrator（feature ∩ K 線之 used／trimmed_bars）與 service（dropped_events：被丟事件之 ID）。
 */
export interface ICPeriodAlignment {
  used?: { start?: string; end?: string; bars?: number } | null;
  trimmed_bars?: { head?: number; tail?: number } | null;
  feature_period?: { start?: string; end?: string; bars?: number } | null;
  kline_period?: { start?: string; end?: string; bars?: number } | null;
  event_period?: { start?: string; end?: string } | null;
  feature_run?: { start_ms?: number | null; end_ms?: number | null } | null;
  dropped_events?: { count?: number; ids?: string[]; reason?: string } | null;
  covered_event_count?: number | null;
}

export interface PeriodAlignmentSummary {
  /** 裁掉的根數（頭／尾）；兩者皆 0 或缺 ⇒ null */
  trimmed: { head: number; tail: number } | null;
  /** 實際採用區間 */
  used: { start: string; end: string; bars: number | null } | null;
  /** 被丟掉的事件 ID（**必列**，不只數量） */
  droppedIds: string[];
  droppedReason: string | null;
  lines: string[];
}

const REASON_TEXT: Record<string, string> = {
  outside_feature_run: '落在特徵 run 的期間之外（無法取到對應的特徵列）',
};

export function readPeriodAlignment(metadata: Record<string, unknown> | undefined | null): ICPeriodAlignment | null {
  const raw = metadata?.period_alignment;
  return raw && typeof raw === 'object' ? (raw as ICPeriodAlignment) : null;
}

export function summarizePeriodAlignment(pa: ICPeriodAlignment | null | undefined): PeriodAlignmentSummary | null {
  if (!pa) return null;
  const head = Number(pa.trimmed_bars?.head ?? 0) || 0;
  const tail = Number(pa.trimmed_bars?.tail ?? 0) || 0;
  const trimmed = head > 0 || tail > 0 ? { head, tail } : null;
  const used = pa.used?.start && pa.used?.end
    ? { start: pa.used.start, end: pa.used.end, bars: typeof pa.used.bars === 'number' ? pa.used.bars : null }
    : null;
  const droppedIds = Array.isArray(pa.dropped_events?.ids) ? pa.dropped_events!.ids!.map(String) : [];
  const droppedReason = pa.dropped_events?.reason ?? null;
  const lines: string[] = [];
  if (trimmed) {
    lines.push(
      `特徵超出 K 線期間的部分已自動裁掉：開頭 ${trimmed.head} 根、結尾 ${trimmed.tail} 根`
      + (pa.kline_period?.start && pa.kline_period?.end ? `（K 線期間 ${pa.kline_period.start} ～ ${pa.kline_period.end}）` : ''),
    );
  }
  if (used) {
    lines.push(`實際分析區間：${used.start} ～ ${used.end}${used.bars !== null ? `（${used.bars} 根）` : ''}`);
  }
  if (droppedIds.length > 0) {
    const reason = droppedReason ? (REASON_TEXT[droppedReason] ?? droppedReason) : '原因未標';
    lines.push(`有 ${droppedIds.length} 個事件沒有進分析：${reason}。事件 ID：${droppedIds.join('、')}`);
  }
  if (lines.length === 0) return null;
  return { trimmed, used, droppedIds, droppedReason, lines };
}

'use client';

import { useICAnalysisStore } from '@/store/icAnalysisStore';
import { readPeriodAlignment, summarizePeriodAlignment } from '@/lib/icPeriodAlignment';

/**
 * EVTALIGN Task 3.1：期間自動對齊之揭露（`report.metadata.period_alignment`）。
 * 後端只在**真的裁了特徵頭尾／丟了事件**時才寫這個鍵 ⇒ 沒鍵就不渲染（不顯示假揭露）。
 * 🔴 被丟掉的事件**列 ID**，不只列數量（只報數不算揭露）。這不是錯誤 banner——分析已成功，只是告訴你系統替你做了什麼。
 */
export default function PeriodAlignmentBanner() {
  const report = useICAnalysisStore((s) => s.report);
  const summary = summarizePeriodAlignment(readPeriodAlignment(report?.metadata));
  if (!summary) return null;
  return (
    <div
      data-testid="period-alignment-banner"
      className="glass-panel rounded-2xl border border-sky-400/40 bg-sky-500/10 p-4 text-sky-100 space-y-1"
      role="status"
    >
      <div className="font-medium">期間對齊：系統已自動處理特徵／K 線／事件的期間差異</div>
      {summary.lines.map((line, idx) => (
        <p key={idx} className="text-sm text-sky-200/90" data-testid={`period-alignment-line-${idx}`}>
          {line}
        </p>
      ))}
      <p className="text-xs text-sky-300/70">
        不需要重生特徵或手動裁 K 線；只有三者完全沒有交集時才會擋下並說明各自的期間。
      </p>
    </div>
  );
}

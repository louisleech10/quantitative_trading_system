'use client';

import { useICAnalysisStore } from '@/store/icAnalysisStore';
import { isolationLines, readIsolation } from '@/lib/icIsolation';

/**
 * EVTALIGN Task 5.1：隔離區（purge／embargo）兩塊來源分開揭露。
 * 後端只在事件分析且切分已套用時寫 `metadata.isolation` ⇒ 沒鍵不渲染。
 * 🔴 不把兩塊合併成一個數字；purge 明講「與事件 label 的 h 無關」。
 */
export default function IsolationNote() {
  const report = useICAnalysisStore((s) => s.report);
  const lines = isolationLines(readIsolation(report?.metadata));
  if (!lines) return null;
  return (
    <div
      data-testid="isolation-note"
      className="glass-panel rounded-2xl border border-slate-400/30 bg-slate-500/10 p-4 text-slate-100 space-y-1"
      role="note"
    >
      <div className="font-medium">隔離區怎麼來的（purge／embargo 分開看）</div>
      {lines.map((line, idx) => (
        <p key={idx} className="text-sm text-slate-200/90" data-testid={`isolation-line-${idx}`}>
          {line}
        </p>
      ))}
    </div>
  );
}

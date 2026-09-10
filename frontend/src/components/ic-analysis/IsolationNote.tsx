'use client';

import { useICAnalysisStore } from '@/store/icAnalysisStore';
import { isolationLines, readIsolation, windowDisclosureLine } from '@/lib/icIsolation';
import { labelRuleLines, readLabelRule } from '@/lib/icLabelRule';

/**
 * EVTALIGN Task 5.1：隔離區（purge／embargo）兩塊來源分開揭露。
 * 後端只在事件分析且切分已套用時寫 `metadata.isolation` ⇒ 沒鍵不渲染。
 * 🔴 不把兩塊合併成一個數字；purge 明講「與事件 label 的 h 無關」。
 */
export default function IsolationNote() {
  const report = useICAnalysisStore((s) => s.report);
  const isoLines = isolationLines(readIsolation(report?.metadata));
  const windowLine = windowDisclosureLine(report?.metadata);
  // EVTLABEL Task 1.2：本次**實際用到**的 label 規則（h／k／進場價／報酬算法／0-1 有無與用沒用）。
  // 與隔離區獨立：切分未套用時 isolation 不寫，label 規則仍會寫 ⇒ 各自判斷是否渲染。
  const ruleLines = labelRuleLines(readLabelRule(report?.metadata));
  if (!isoLines && !windowLine && !ruleLines) return null;
  const lines = [...(isoLines ?? []), ...(windowLine ? [windowLine] : [])];
  return (
    <div
      data-testid="isolation-note"
      className="glass-panel rounded-2xl border border-slate-400/30 bg-slate-500/10 p-4 text-slate-100 space-y-1"
      role="note"
    >
      {lines.length > 0 && (
        <>
          <div className="font-medium">隔離區怎麼來的（purge／embargo 分開看）</div>
          {lines.map((line, idx) => (
            <p key={idx} className="text-sm text-slate-200/90" data-testid={`isolation-line-${idx}`}>
              {line}
            </p>
          ))}
        </>
      )}
      {ruleLines && (
        <section data-testid="label-rule-note" className="pt-2 space-y-1">
          <div className="font-medium">本次 label 怎麼算（實際用到的規則）</div>
          {ruleLines.map((line, idx) => (
            <p key={idx} className="text-sm text-slate-200/90" data-testid={`label-rule-line-${idx}`}>
              {line}
            </p>
          ))}
        </section>
      )}
    </div>
  );
}

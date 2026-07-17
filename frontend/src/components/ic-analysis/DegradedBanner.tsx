'use client';

import { useICAnalysisStore } from '@/store/icAnalysisStore';

/**
 * LA-1 B3：degraded full-sample 紅標 banner。
 * store 讀 analysis_status !== "ok_oos" 時顯示；缺欄位 / ok_oos → null。
 */
export default function DegradedBanner() {
  const report = useICAnalysisStore((s) => s.report);
  const status = report?.analysis_status;
  const oos = report?.oos_guarantees;

  // 舊 artifact 無欄位 → 不炸、不顯示
  if (status === undefined || status === null) {
    return null;
  }
  if (status === 'ok_oos') {
    return null;
  }

  return (
    <div
      data-testid="degraded-banner"
      className="glass-panel rounded-2xl border border-rose-400/50 bg-rose-500/10 p-4 text-rose-100 space-y-1"
      role="alert"
    >
      <div className="font-medium">⚠ Full-sample research-only（非 OOS 保證）</div>
      <p className="text-sm text-rose-200/90">
        analysis_status=<code className="bg-slate-900/50 px-1 rounded">{status}</code>
        {oos === false ? ' · oos_guarantees=false' : ''}
        。此結果來自 full-sample fallback 或無 holdout 保證，不可當 out-of-sample 通過特徵使用。
      </p>
    </div>
  );
}

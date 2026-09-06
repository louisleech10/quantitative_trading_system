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

  // ICHC Task 4.1：事件 fallback 副文案（metadata.event_filter 單一路徑）
  const eventFilter = report?.metadata?.event_filter as
    | { fallback?: boolean; reason?: string }
    | undefined;
  const eventFallback = eventFilter?.fallback === true;

  // 🔴 `GAP3_EVENT_DISCLOSURE` Task 1.3：降級之**具體原因與門檻**。
  //    出生事故（2026-09-06 UAT）：使用者對 60／115／219 筆三種事件批都看到這個 banner，
  //    但看不出是為什麼、也看不出還差多少 ⇒ 無從判斷該加樣本還是改設定。
  //    這四個數字後端本來就算出來了（只進了 logger.warning），本欄把它們帶到畫面。
  const downgrade = report?.metadata?.oos_downgrade as
    | { reason?: string; train_rows?: number; test_rows?: number; min_test_rows?: number }
    | undefined;

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
      {downgrade?.reason && (
        <p data-testid="ic-oos-downgrade" className="text-sm text-rose-200/90">
          原因：<code className="bg-slate-900/50 px-1 rounded">{downgrade.reason}</code>
          ——訓練 {downgrade.train_rows} 列、測試 {downgrade.test_rows} 列，
          但滾動 IC 需要測試集至少 {downgrade.min_test_rows} 列。
          <br />
          <span className="text-rose-200/70">
            要拿到 OOS 保證，得讓**測試集的列數**過門檻。列數不等於事件數——
            事件經對齊與 purge 之後才變成列，兩者沒有固定倍數。
          </span>
        </p>
      )}
      {eventFallback && (
        <p data-testid="degraded-banner-event" className="text-sm text-rose-200/90">
          事件樣本不足，已退回全樣本分析——你看到的<strong>不是</strong>事件條件下的結果
          {eventFilter?.reason ? (
            <code className="bg-slate-900/50 px-1 rounded ml-1">{eventFilter.reason}</code>
          ) : null}
          。
        </p>
      )}
    </div>
  );
}

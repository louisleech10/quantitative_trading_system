'use client';

import { useICAnalysisStore } from '@/store/icAnalysisStore';
import { oosDowngradeDoc } from '@/lib/oosDowngradeDocs';
import type { ICOosDowngrade } from '@/lib/types';

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
  const downgrade = report?.metadata?.oos_downgrade as ICOosDowngrade | undefined;
  // 三個列數**同時**存在才顯示——只有 full-sample fallback 那條路會產生它們。
  const hasRowCounts = typeof downgrade?.train_rows === 'number'
    && typeof downgrade?.test_rows === 'number'
    && typeof downgrade?.min_test_rows === 'number';
  const doc = oosDowngradeDoc(downgrade?.reason);

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
          {/* 🔴 `R1` 閉合：只有 full-sample fallback 那條路有列數；其餘四條分支
              （事件樣本不足／config 直設 full_sample／split 未套用／無 holdout 證據）
              **沒有**列數可報 ⇒ 那時不得印 `null 列`，改講這個 reason 的意思。 */}
          {hasRowCounts ? (
            <>
              ——訓練 {downgrade.train_rows} 列、測試 {downgrade.test_rows} 列，
              但滾動 IC 需要測試集至少 {downgrade.min_test_rows} 列。
            </>
          ) : null}
          <br />
          {/* 🔴 `CODEX-R2-P1-06`：文案**依 reason 分流**（SSOT＝`oosDowngradeDocs.ts`）。
              R1 的版本寫死一句「沒有保留獨立的測試集」，對 `event_filter_fallback`
              是假的——那條路可以同時有已套用的 holdout，缺的是事件樣本。 */}
          <span className="text-rose-200/70" data-testid="ic-oos-downgrade-explain">
            {doc.what}
            <br />
            <strong>怎麼辦：</strong>{doc.next}
          </span>
          {!hasRowCounts ? (
            <span className="block text-rose-200/60" data-testid="ic-oos-downgrade-no-rows">
              （這條路徑沒有訓練／測試列數可報——列數只有在切分真的跑過才會產生。）
            </span>
          ) : null}
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

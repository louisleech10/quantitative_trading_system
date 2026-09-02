import { useEffect, useRef } from 'react';
import type { ICAnalysisConfig } from '@/lib/types';

interface AutoRefilterArgs {
  taskId: string | null;
  status: string;
  /** 是否已有報告（只當「可不可以 refilter」的門，**不**當觸發條件）。 */
  hasReport: boolean;
  thresholds: ICAnalysisConfig['thresholds'];
  refilter: (taskId: string, thresholds: ICAnalysisConfig['thresholds']) => Promise<unknown>;
  setError: (message: string | null) => void;
  setIsRefiltering: (value: boolean) => void;
  /** 去抖毫秒（測試可縮短）。 */
  debounceMs?: number;
}

/**
 * 門檻變更 ⇒ 去抖後自動 refilter（`/ic-analysis` 頁）。
 *
 * 🔴 UAT B15（2026-09-02，票 `G3-D16`）：原本的 effect 把 `report` 放進依賴，而 `refilter()` 成功後會
 * `setReport(result)` ⇒ `report` 物件身分改變 ⇒ effect 重跑 ⇒ 再 refilter……每 600ms 一次無限迴圈，
 * 後端每次都重新落檔（log 每秒兩筆「IC report saved」，單日 104 次 refilter 對應使用者改門檻不到十次）。
 * 修法：**觸發條件只有 `thresholdsKey`／`taskId`／`status`**；`hasReport` 以 ref 讀取當下值、不進依賴；
 * 同一組 (taskId, thresholdsKey) 只 refilter 一次。
 */
export function useAutoRefilter({
  taskId, status, hasReport, thresholds, refilter, setError, setIsRefiltering, debounceMs = 600,
}: AutoRefilterArgs): void {
  const thresholdsKey = JSON.stringify(thresholds);
  const hasReportRef = useRef(hasReport);
  hasReportRef.current = hasReport;
  const thresholdsRef = useRef(thresholds);
  thresholdsRef.current = thresholds;
  const lastRunKeyRef = useRef<string | null>(null);

  useEffect(() => {
    if (!taskId || status !== 'completed' || !hasReportRef.current) {
      return;
    }
    const runKey = `${taskId}|${thresholdsKey}`;
    if (lastRunKeyRef.current === runKey) {
      return;                                   // 同一組門檻不重跑（report 身分改變不算變更）
    }
    const timer = setTimeout(() => {
      lastRunKeyRef.current = runKey;
      setIsRefiltering(true);
      refilter(taskId, thresholdsRef.current)
        .catch((err) => {
          const message = err instanceof Error ? err.message : '重新篩選失敗';
          setError(message);
        })
        .finally(() => setIsRefiltering(false));
    }, debounceMs);
    return () => clearTimeout(timer);
  }, [taskId, status, thresholdsKey, refilter, setError, setIsRefiltering, debounceMs]);
}

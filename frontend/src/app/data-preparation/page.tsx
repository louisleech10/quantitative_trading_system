"use client";

import { useState, useEffect, useRef } from "react";
import CaseImportForm from "@/components/case/CaseImportForm";
import BatchDownloadPanel from "@/components/case/BatchDownloadPanel";
import EventImportForm from "@/components/case/EventImportForm";
import EventCsvMappingForm from "@/components/case/EventCsvMappingForm";
import EventBatchDeleteDialog from "@/components/case/EventBatchDeleteDialog";
import { deleteEventImport, listEventImports } from "@/lib/api";
import { forgetImportReference, isImportReferenced, referencedImportIds } from "@/lib/eventBatchReferences";
import type { EventImportSummary } from "@/lib/types";

export default function DataPreparationPage() {
  const [totalCases, setTotalCases] = useState(0);
  const [refreshKey, setRefreshKey] = useState(0);
  const [isClearing, setIsClearing] = useState(false);
  const [eventImports, setEventImports] = useState<EventImportSummary[]>([]);
  const [eventImportsError, setEventImportsError] = useState<string | null>(null);
  // GAP-3 UX Task 3.2／3.3：待確認刪除之批（null ⇒ 確認框未開）
  const [pendingDelete, setPendingDelete] = useState<EventImportSummary | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [referenced, setReferenced] = useState<Set<string>>(() => new Set<string>());
  // 刪除是否在途（見 handleDeleteConfirmed 之註解——state 守不住同一 tick 的重入）
  const deleteInFlightRef = useRef(false);

  // GAP-3 B5.2：已匯入事件批（新契約）
  useEffect(() => {
    listEventImports()
      .then((r) => setEventImports(r.imports))
      .catch((err) => setEventImportsError(err instanceof Error ? err.message : '載入事件批失敗'));
  }, [refreshKey]);

  // GAP-3 UX Task 3.3：引用紀錄之讀取（判準與來源見 `@/lib/eventBatchReferences`；PENDING-RULING）
  useEffect(() => {
    setReferenced(referencedImportIds());
  }, [refreshKey]);

  const handleDeleteConfirmed = async () => {
    if (!pendingDelete) return;
    // 🔴 R1 群集 B（`CODEX-R1-P1-02`）：確認鍵**刻意保持可按**（B4 教訓，設 disabled 會讓
    //    fireEvent.click 什麼都不觸發、測試恆綠），因此重入必須由 handler 自己擋。
    //    用 `useRef` 而**不是** `deleteBusy` state：同一 tick 內連點兩次時 state 尚未更新，
    //    守不住；第二個請求會收 404，其錯誤還會寫進已經關閉的確認框。
    if (deleteInFlightRef.current) return;
    deleteInFlightRef.current = true;
    const importId = pendingDelete.import_id;
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await deleteEventImport(importId);
      // 該批已不存在 ⇒ 一併移除其引用紀錄，不留指向不存在批之紀錄
      forgetImportReference(importId);
      setPendingDelete(null);
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : '刪除事件批失敗');
    } finally {
      deleteInFlightRef.current = false;
      setDeleteBusy(false);
    }
  };

  // 頁面加載時獲取當前案例數
  useEffect(() => {
    const fetchCaseCount = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/case/list');
        if (response.ok) {
          const result = await response.json();
          setTotalCases(result.total || 0);
        }
      } catch (error) {
        console.error('Failed to fetch case count:', error);
      }
    };

    fetchCaseCount();
  }, [refreshKey]);

  const handleImportSuccess = (result: { imported_cases: number }) => {
    // 更新案例總數
    setTotalCases(result.imported_cases);
  };

  const handleDownloadComplete = () => {
    // 下載完成後可以觸發其他操作
    console.log("Download completed");
  };

  const handleClearAll = async () => {
    if (!confirm('確定要清空所有案例嗎？此操作無法撤銷。')) {
      return;
    }

    try {
      setIsClearing(true);
      const response = await fetch('http://localhost:8000/api/v1/case/clear-all', {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`清空失敗: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        alert(`成功清空 ${result.cleared_count || 0} 個案例`);
        setTotalCases(0);
        setRefreshKey(prev => prev + 1); // 觸發子組件刷新
        window.location.reload(); // 刷新整個頁面以確保狀態一致
      } else {
        throw new Error(result.error?.message || '清空失敗');
      }
    } catch (error) {
      console.error('Clear all cases error:', error);
      alert(error instanceof Error ? error.message : '清空案例時發生錯誤');
    } finally {
      setIsClearing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950/40">
      {/* Header */}
      <div className="bg-slate-950/80 border-b border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-slate-100">
                數據準備
              </h1>
              <p className="mt-2 text-sm font-medium text-slate-400">
                上傳案例CSV文件並批量下載K線數據
              </p>
            </div>
            <button
              onClick={handleClearAll}
              disabled={isClearing}
              className="px-4 py-2 bg-rose-500/20 text-rose-100 rounded-lg border border-rose-400/40 hover:bg-rose-500/30 disabled:bg-slate-700/60 disabled:text-slate-400 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {isClearing ? '清空中...' : '清空所有案例'}
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Workflow Steps */}
        <div className="mb-8">
          <div className="flex items-center justify-center space-x-4">
            <div className="flex items-center">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-100 font-bold border border-emerald-400/40">
                1
              </div>
              <span className="ml-2 text-sm font-bold text-slate-100">導入案例</span>
            </div>

            <div className="flex-1 border-t border-slate-700"></div>

            <div className="flex items-center">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-sky-500/20 text-sky-100 font-bold border border-sky-400/40">
                2
              </div>
              <span className="ml-2 text-sm font-bold text-slate-100">批量下載</span>
            </div>

            <div className="flex-1 border-t border-slate-700"></div>

            <div className="flex items-center">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-slate-700 text-slate-200 font-bold border border-slate-600">
                3
              </div>
              <span className="ml-2 text-sm font-bold text-slate-400">
                圖表分析
                <span className="ml-1 text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">Phase 2</span>
              </span>
            </div>
          </div>
        </div>

        {/* Two-Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column: CSV Import */}
          <div>
            <CaseImportForm key={refreshKey} onImportSuccess={handleImportSuccess} />

            {/* Cases Summary */}
            {totalCases > 0 && (
              <div className="mt-4 glass-panel rounded-xl p-4 border border-slate-800/80">
                <h4 className="font-bold text-slate-100 mb-2">已導入案例總覽</h4>
                <div className="grid grid-cols-2 gap-2 text-sm font-medium text-slate-200">
                  <div>總案例數:</div>
                  <div className="font-bold text-emerald-300">{totalCases}</div>
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Batch Download */}
          <div>
            <BatchDownloadPanel
              key={refreshKey}
              totalCases={totalCases}
              onDownloadComplete={handleDownloadComplete}
            />
          </div>
        </div>

        {/* GAP-3 B5.2：新契約事件匯入＋已匯入批列表（與舊三欄流程並列、不互轉） */}
        <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-8">
          <EventImportForm onImported={() => setRefreshKey((k) => k + 1)} />
          <div className="glass-panel rounded-xl p-6 border border-slate-800/80" data-testid="event-imports-list">
            <h4 className="font-bold text-slate-100 mb-2">已匯入事件批（GAP-3）</h4>
            {eventImportsError && <p className="text-sm text-rose-300">{eventImportsError}</p>}
            {!eventImportsError && eventImports.length === 0 && (
              <p className="text-sm text-slate-400">尚無事件批。匯入後可在「IC 分析 → Event-Driven 模式」選用。</p>
            )}
            {eventImports.length > 0 && (
              <ul className="space-y-1 text-sm text-slate-200">
                {eventImports.map((it) => (
                  <li key={it.import_id} className="flex items-center justify-between gap-2 font-mono text-xs">
                    <span>
                      {it.import_id} · {it.symbols.join('/')} {it.timeframes.join('/')} · {it.n_events} 筆 · {it.imported_at}
                    </span>
                    {/* GAP-3 UX Task 3.2：刪除入口**只在批列表**提供（邊界②） */}
                    <button
                      type="button"
                      data-testid={`event-batch-delete-open-${it.import_id}`}
                      onClick={() => { setDeleteError(null); setPendingDelete(it); }}
                      className="shrink-0 rounded border border-rose-400/40 px-2 py-0.5 text-rose-200 hover:bg-rose-500/10"
                    >
                      刪除
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {/* Task 3.2／3.3：二次確認框（不得以 window.confirm 帶過）。警語由 3.3 之判準決定是否顯示。 */}
            {pendingDelete && (
              <EventBatchDeleteDialog
                batch={pendingDelete}
                isReferenced={isImportReferenced(pendingDelete.import_id, referenced)}
                busy={deleteBusy}
                errorMessage={deleteError}
                onCancel={() => { setPendingDelete(null); setDeleteError(null); }}
                onConfirm={handleDeleteConfirmed}
              />
            )}
          </div>
        </div>

        {/* GAP-3 UX Task 1.5／1.6／1.7：自有欄名 CSV ＋ 逐項對映（與上方新契約直傳並列） */}
        <div className="mt-8">
          <EventCsvMappingForm onImported={() => setRefreshKey((k) => k + 1)} />
        </div>

        {/* Help Section */}
        <div className="mt-8 glass-panel rounded-xl p-6 border border-slate-800/80">
          <h3 className="text-lg font-bold text-slate-100 mb-4">📖 使用說明（Phase 1）</h3>

          <div className="space-y-4 text-sm">
            <div>
              <h4 className="font-bold text-slate-100 mb-1">步驟 1: 導入案例CSV</h4>
              <p className="text-slate-300 leading-relaxed">
                上傳包含案例的CSV文件。必要欄位：<code className="bg-slate-900/70 text-slate-200 px-1.5 py-0.5 rounded font-mono border border-slate-800">symbol</code>,{" "}
                <code className="bg-slate-900/70 text-slate-200 px-1.5 py-0.5 rounded font-mono border border-slate-800">timestamp</code>,{" "}
                <code className="bg-slate-900/70 text-slate-200 px-1.5 py-0.5 rounded font-mono border border-slate-800">Positive_case</code>。
                可選欄位：<code className="bg-slate-900/70 text-slate-200 px-1.5 py-0.5 rounded font-mono border border-slate-800">timeframe</code>
              </p>
            </div>

            <div>
              <h4 className="font-bold text-slate-100 mb-1">步驟 2: 配置下載參數</h4>
              <p className="text-slate-300 leading-relaxed">
                設定往前（lookback）和往後（forward）K線根數。例如：100前+48後 表示案例時間點前100根K線和後48根K線。
              </p>
            </div>

            <div>
              <h4 className="font-bold text-slate-100 mb-1">步驟 3: 批量下載</h4>
              <p className="text-slate-300 leading-relaxed">
                點擊&quot;開始批量下載&quot;按鈕，系統將自動下載所有案例的K線數據並存儲到HDF5。下載過程中可查看實時進度。
              </p>
            </div>

            <div>
              <h4 className="font-bold text-slate-100 mb-1">💡 支援的時間格式</h4>
              <p className="text-slate-300 leading-relaxed">
                系統自動識別多種時間格式：Unix timestamp、ISO格式 (YYYY-MM-DD HH:MM:SS)、Excel日期等。
              </p>
            </div>

            <div className="mt-4 pt-4 border-t border-slate-800/80">
              <div className="flex items-start space-x-2 bg-emerald-500/10 p-3 rounded border border-emerald-400/30">
                <span className="text-emerald-300 font-bold">ℹ️</span>
                <div>
                  <p className="text-sm font-bold text-emerald-200 mb-1">Phase 1 已完成 ✅</p>
                  <p className="text-xs text-emerald-200/80">
                    目前已實作：案例CSV導入 + 批量K線下載。<br/>
                    <span className="font-bold">Phase 2（規劃中）</span>：圖表視覺化分析、技術指標計算、策略回測等進階功能。
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import CaseImportForm from "@/components/case/CaseImportForm";
import BatchDownloadPanel from "@/components/case/BatchDownloadPanel";

export default function DataPreparationPage() {
  const [totalCases, setTotalCases] = useState(0);
  const [refreshKey, setRefreshKey] = useState(0);
  const [isClearing, setIsClearing] = useState(false);

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

  const handleImportSuccess = (result: any) => {
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
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-white shadow-md border-b-2 border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                數據準備
              </h1>
              <p className="mt-2 text-sm font-medium text-gray-700">
                上傳案例CSV文件並批量下載K線數據
              </p>
            </div>
            <button
              onClick={handleClearAll}
              disabled={isClearing}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium shadow-md"
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
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-blue-600 text-white font-bold shadow-md">
                1
              </div>
              <span className="ml-2 text-sm font-bold text-gray-900">導入案例</span>
            </div>

            <div className="flex-1 border-t-2 border-gray-400"></div>

            <div className="flex items-center">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-green-600 text-white font-bold shadow-md">
                2
              </div>
              <span className="ml-2 text-sm font-bold text-gray-900">批量下載</span>
            </div>

            <div className="flex-1 border-t-2 border-gray-400"></div>

            <div className="flex items-center">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-400 text-white font-bold shadow-md">
                3
              </div>
              <span className="ml-2 text-sm font-bold text-gray-600">
                圖表分析
                <span className="ml-1 text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">Phase 2</span>
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
              <div className="mt-4 bg-white rounded-lg shadow-md p-4 border border-gray-200">
                <h4 className="font-bold text-gray-900 mb-2">已導入案例總覽</h4>
                <div className="grid grid-cols-2 gap-2 text-sm font-medium text-gray-900">
                  <div>總案例數:</div>
                  <div className="font-bold text-blue-700">{totalCases}</div>
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

        {/* Help Section */}
        <div className="mt-8 bg-white rounded-lg shadow-md p-6 border border-gray-200">
          <h3 className="text-lg font-bold text-gray-900 mb-4">📖 使用說明（Phase 1）</h3>

          <div className="space-y-4 text-sm">
            <div>
              <h4 className="font-bold text-gray-900 mb-1">步驟 1: 導入案例CSV</h4>
              <p className="text-gray-700 leading-relaxed">
                上傳包含案例的CSV文件。必要欄位：<code className="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded font-mono">symbol</code>,{" "}
                <code className="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded font-mono">timestamp</code>,{" "}
                <code className="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded font-mono">Positive_case</code>。
                可選欄位：<code className="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded font-mono">timeframe</code>
              </p>
            </div>

            <div>
              <h4 className="font-bold text-gray-900 mb-1">步驟 2: 配置下載參數</h4>
              <p className="text-gray-700 leading-relaxed">
                設定往前（lookback）和往後（forward）K線根數。例如：100前+48後 表示案例時間點前100根K線和後48根K線。
              </p>
            </div>

            <div>
              <h4 className="font-bold text-gray-900 mb-1">步驟 3: 批量下載</h4>
              <p className="text-gray-700 leading-relaxed">
                點擊"開始批量下載"按鈕，系統將自動下載所有案例的K線數據並存儲到HDF5。下載過程中可查看實時進度。
              </p>
            </div>

            <div>
              <h4 className="font-bold text-gray-900 mb-1">💡 支援的時間格式</h4>
              <p className="text-gray-700 leading-relaxed">
                系統自動識別多種時間格式：Unix timestamp、ISO格式 (YYYY-MM-DD HH:MM:SS)、Excel日期等。
              </p>
            </div>

            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="flex items-start space-x-2 bg-blue-50 p-3 rounded border border-blue-200">
                <span className="text-blue-600 font-bold">ℹ️</span>
                <div>
                  <p className="text-sm font-bold text-blue-900 mb-1">Phase 1 已完成 ✅</p>
                  <p className="text-xs text-blue-800">
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

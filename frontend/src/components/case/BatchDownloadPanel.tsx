"use client";

import { useState, useEffect } from "react";

interface BatchDownloadPanelProps {
  totalCases: number;
  onDownloadComplete?: () => void;
}

interface DownloadProgress {
  task_id: string;
  status: "pending" | "running" | "completed" | "failed";
  total_cases: number;
  completed_cases: number;
  failed_cases: number;
  progress_percent: number;
  current_symbol?: string;
  estimated_time_remaining?: number;
  failed_case_ids: string[];
  error_messages: string[];
}

export default function BatchDownloadPanel({
  totalCases,
  onDownloadComplete,
}: BatchDownloadPanelProps) {
  const [warmupBars, setWarmupBars] = useState(150); // 新增：Warmup期K線數
  const [lookbackBars, setLookbackBars] = useState(100);
  const [forwardBars, setForwardBars] = useState(48);
  const [downloadTimeframe, setDownloadTimeframe] = useState("1h"); // 新增：K線下載時間框架（預設1h）
  const [downloading, setDownloading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState<DownloadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 輪詢進度（優化版：動態間隔）
  useEffect(() => {
    if (!taskId) return;

    let pollCount = 0;
    let timeoutId: NodeJS.Timeout;

    const pollProgress = async () => {
      try {
        const response = await fetch(
          `/api/v1/kline/download-status/${taskId}`
        );

        if (!response.ok) {
          throw new Error("Failed to fetch progress");
        }

        const data: DownloadProgress = await response.json();
        setProgress(data);

        // 如果任務完成或失敗，停止輪詢
        if (data.status === "completed" || data.status === "failed") {
          setDownloading(false);

          if (data.status === "completed" && onDownloadComplete) {
            onDownloadComplete();
          }
          return;
        }

        // 動態調整輪詢間隔：從1秒開始，逐漸增加到3秒
        pollCount++;
        const interval = Math.min(1000 + pollCount * 200, 3000);

        // 繼續輪詢
        timeoutId = setTimeout(pollProgress, interval);
      } catch (err) {
        console.error("Failed to fetch progress:", err);

        // 錯誤時使用較長間隔重試（5秒）
        timeoutId = setTimeout(pollProgress, 5000);
      }
    };

    // 開始輪詢
    pollProgress();

    // 清理函數
    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [taskId, onDownloadComplete]);

  const handleStartDownload = async () => {
    setDownloading(true);
    setError(null);
    setProgress(null);

    // 計算總lookback（warmup + 有效K線）
    const totalLookbackBars = warmupBars + lookbackBars;

    // 保存lookback/forward設定到localStorage，供圖表頁面使用
    localStorage.setItem('kline_warmup_bars', warmupBars.toString());
    localStorage.setItem('kline_lookback_bars', lookbackBars.toString());
    localStorage.setItem('kline_forward_bars', forwardBars.toString());

    try {
      const response = await fetch("/api/v1/kline/batch-download", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          case_ids: null, // 下載全部案例
          lookback_bars: lookbackBars, // 傳送真正的 lookback（不含 warmup）
          warmup_bars: warmupBars, // 明確傳送 warmup_bars
          forward_bars: forwardBars,
          force_redownload: false,
          timeframe: downloadTimeframe, // 新增：K線下載時間框架
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Download failed");
      }

      const data = await response.json();
      setTaskId(data.task_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
      setDownloading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
      <h3 className="text-lg font-bold text-gray-900 mb-4">批量K線下載</h3>

      {totalCases === 0 && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-300 rounded">
          <p className="text-sm font-medium text-yellow-800">
            請先導入案例CSV文件
          </p>
        </div>
      )}

      {/* Configuration */}
      <div className="mb-4 grid grid-cols-2 gap-4">
        {/* K線時間框架選擇器 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            K線時間框架
          </label>
          <select
            value={downloadTimeframe}
            onChange={(e) => setDownloadTimeframe(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 bg-white text-gray-900 font-medium focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            disabled={downloading}
          >
            <option value="1m">1 分鐘</option>
            <option value="5m">5 分鐘</option>
            <option value="15m">15 分鐘</option>
            <option value="30m">30 分鐘</option>
            <option value="1h">1 小時 (預設)</option>
            <option value="4h">4 小時</option>
            <option value="12h">12 小時</option>
            <option value="1d">1 天</option>
          </select>
          <p className="text-xs text-gray-600 mt-1 font-medium">
            用於ML訓練（與案例搜尋時間框架獨立）
          </p>
        </div>

        {/* 新增：Warmup期輸入框 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Warmup期K線數
          </label>
          <input
            type="number"
            value={warmupBars}
            onChange={(e) => setWarmupBars(Number(e.target.value))}
            min={0}
            max={500}
            className="w-full border border-gray-300 rounded px-3 py-2 bg-white text-gray-900 font-medium focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            disabled={downloading}
            placeholder="150"
          />
          <p className="text-xs text-gray-500 mt-1 font-medium">
            建議：最長EMA週期×4.5 (例如：EMA50 → 225)
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            TO前有效K線數（不含Warmup）
          </label>
          <input
            type="number"
            value={lookbackBars}
            onChange={(e) => setLookbackBars(Number(e.target.value))}
            min={1}
            max={1000}
            className="w-full border border-gray-300 rounded px-3 py-2 bg-white text-gray-900 font-medium focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            disabled={downloading}
            placeholder="100"
          />
          <p className="text-xs text-blue-600 mt-1 font-medium">
            密度計算基數（實際有效K線數）
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            往後K線根數 (Forward)
          </label>
          <input
            type="number"
            value={forwardBars}
            onChange={(e) => setForwardBars(Number(e.target.value))}
            min={1}
            max={500}
            className="w-full border border-gray-300 rounded px-3 py-2 bg-white text-gray-900 font-medium focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            disabled={downloading}
            placeholder="48"
          />
          <p className="text-xs text-gray-600 mt-1 font-medium">
            範圍: 1-500（預設: 48）
          </p>
        </div>
      </div>

      {/* Download Info */}
      <div className="mb-4 p-3 bg-blue-50 border border-blue-300 rounded">
        <p className="text-sm font-bold text-blue-900 mb-2">
          下載配置
        </p>
        <p className="text-sm font-medium text-gray-700 mb-1">
          案例數量：<span className="font-bold text-blue-700">{totalCases}</span> 個
        </p>
        <p className="text-sm font-medium text-gray-700 mb-1">
          時間框架：<span className="font-bold text-blue-700">{downloadTimeframe}</span>
        </p>
        <p className="text-sm font-bold text-gray-900 mt-2 mb-1">
          每個案例下載：
        </p>
        <p className="text-sm font-medium text-gray-700">
          <span className="font-bold text-blue-700">{warmupBars + lookbackBars + forwardBars}</span> 根K線
          <span className="text-gray-500 text-xs ml-2">
            = {warmupBars} (Warmup) + {lookbackBars} (有效) + {forwardBars} (往後)
          </span>
        </p>
        <p className="text-xs text-green-600 mt-2 font-medium">
          ✓ 密度計算基數：{lookbackBars} 根有效K線
        </p>
      </div>

      {/* Download Button */}
      <button
        onClick={handleStartDownload}
        disabled={totalCases === 0 || downloading}
        className={`w-full py-3 px-4 rounded-lg font-bold text-white transition-colors ${
          totalCases === 0 || downloading
            ? "bg-gray-400 cursor-not-allowed"
            : "bg-green-600 hover:bg-green-700 shadow-md"
        }`}
      >
        {downloading ? "下載中..." : "開始批量下載"}
      </button>

      {/* Error Message */}
      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-300 rounded">
          <p className="text-sm font-medium text-red-800">{error}</p>
        </div>
      )}

      {/* Progress Bar */}
      {progress && (
        <div className="mt-4">
          <div className="mb-2 flex justify-between text-sm font-medium text-gray-900">
            <span>進度: {progress.completed_cases} / {progress.total_cases}</span>
            <span className="font-bold">{progress.progress_percent.toFixed(1)}%</span>
          </div>

          <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                progress.status === "completed"
                  ? "bg-green-600"
                  : progress.status === "failed"
                  ? "bg-red-600"
                  : "bg-blue-600"
              }`}
              style={{ width: `${progress.progress_percent}%` }}
            ></div>
          </div>

          {/* Status Info */}
          <div className="mt-3 text-sm font-medium text-gray-900">
            <div className="grid grid-cols-2 gap-2">
              <div>狀態: <span className="font-bold">{progress.status}</span></div>
              <div>當前: <span className="font-bold">{progress.current_symbol || "N/A"}</span></div>
              <div>成功: <span className="text-green-700 font-bold">{progress.completed_cases}</span></div>
              <div>失敗: <span className="text-red-700 font-bold">{progress.failed_cases}</span></div>
            </div>

            {progress.estimated_time_remaining && (
              <div className="mt-2 text-gray-800 font-medium">
                預估剩餘時間: {Math.round(progress.estimated_time_remaining / 60)} 分鐘
              </div>
            )}
          </div>

          {/* Failed Cases */}
          {progress.failed_case_ids.length > 0 && (
            <div className="mt-4 p-3 bg-red-50 border border-red-300 rounded">
              <p className="text-sm font-bold text-red-900 mb-2">
                失敗案例 ({progress.failed_case_ids.length}):
              </p>
              <ul className="list-disc list-inside text-sm font-medium text-red-800">
                {progress.failed_case_ids.slice(0, 5).map((caseId, idx) => (
                  <li key={idx}>{caseId}</li>
                ))}
                {progress.failed_case_ids.length > 5 && (
                  <li className="text-gray-500">
                    ...還有 {progress.failed_case_ids.length - 5} 個
                  </li>
                )}
              </ul>

              {progress.error_messages.length > 0 && (
                <div className="mt-2">
                  <p className="text-sm font-semibold mb-1">錯誤訊息:</p>
                  <ul className="list-disc list-inside text-sm text-red-700">
                    {progress.error_messages.slice(0, 3).map((msg, idx) => (
                      <li key={idx}>{msg}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Completion Message */}
          {progress.status === "completed" && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded">
              <p className="text-sm text-green-700 font-semibold">
                ✅ 批量下載完成！
                成功: {progress.completed_cases}, 失敗: {progress.failed_cases}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

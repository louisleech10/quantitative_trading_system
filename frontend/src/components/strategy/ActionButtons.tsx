/**
 * ActionButtons.tsx - 操作按鈕組件
 *
 * Phase 3.3+3.4 - Task B3: 主頁面整合
 *
 * 功能:
 * - 執行測試按鈕 (觸發策略測試)
 * - 保存範本按鈕 (打開保存對話框)
 * - 載入範本按鈕 (選擇已保存的範本)
 * - 清除配置按鈕 (重置所有設定)
 * - 顯示執行狀態 (loading/success/error)
 *
 * Ultra Think 記錄:
 * - 步驟 1: 初版代碼 (當前)
 * - 步驟 2: 審查優化 (待執行)
 * - 步驟 3: 最終優化 (待執行)
 */

"use client";

import { useState } from "react";

export interface ActionButtonsProps {
  onRunTest: () => Promise<void>;
  onSaveTemplate: () => void;
  onLoadTemplate: () => void;
  onClearConfig: () => void;
  isValid: boolean;
  isRunning: boolean;
  className?: string;
}

export default function ActionButtons({
  onRunTest,
  onSaveTemplate,
  onLoadTemplate,
  onClearConfig,
  isValid,
  isRunning,
  className = "",
}: ActionButtonsProps) {
  const [showSuccessMessage, setShowSuccessMessage] = useState(false);

  const handleRunTest = async () => {
    try {
      await onRunTest();
      // 顯示成功訊息
      setShowSuccessMessage(true);
      setTimeout(() => setShowSuccessMessage(false), 3000);
    } catch (error) {
      // 錯誤處理由父組件處理
      console.error("Test execution failed:", error);
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 主要操作按鈕 */}
      <div className="grid grid-cols-2 gap-3">
        {/* 執行測試 */}
        <button
          type="button"
          onClick={handleRunTest}
          disabled={!isValid || isRunning}
          className={`
            relative px-6 py-3 rounded-lg font-medium text-sm transition-all
            ${
              isValid && !isRunning
                ? "bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800"
                : "bg-gray-300 text-gray-500 cursor-not-allowed"
            }
            ${isRunning ? "animate-pulse" : ""}
          `}
        >
          {/* Loading 動畫 */}
          {isRunning && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {/* 按鈕文字 */}
          <span className={isRunning ? "invisible" : ""}>
            {isRunning ? "執行中..." : "▶ 執行測試"}
          </span>
        </button>

        {/* 保存範本 */}
        <button
          type="button"
          onClick={onSaveTemplate}
          disabled={!isValid || isRunning}
          className={`
            px-6 py-3 rounded-lg font-medium text-sm transition-all
            ${
              isValid && !isRunning
                ? "bg-green-600 text-white hover:bg-green-700 active:bg-green-800"
                : "bg-gray-300 text-gray-500 cursor-not-allowed"
            }
          `}
        >
          💾 保存範本
        </button>
      </div>

      {/* 次要操作按鈕 */}
      <div className="grid grid-cols-2 gap-3">
        {/* 載入範本 */}
        <button
          type="button"
          onClick={onLoadTemplate}
          disabled={isRunning}
          className={`
            px-4 py-2 rounded-lg font-medium text-sm transition-all
            border-2
            ${
              !isRunning
                ? "border-purple-600 text-purple-600 hover:bg-purple-50 active:bg-purple-100"
                : "border-gray-300 text-gray-400 cursor-not-allowed"
            }
          `}
        >
          📂 載入範本
        </button>

        {/* 清除配置 */}
        <button
          type="button"
          onClick={onClearConfig}
          disabled={isRunning}
          className={`
            px-4 py-2 rounded-lg font-medium text-sm transition-all
            border-2
            ${
              !isRunning
                ? "border-gray-400 text-gray-600 hover:bg-gray-50 active:bg-gray-100"
                : "border-gray-300 text-gray-400 cursor-not-allowed"
            }
          `}
        >
          🗑️ 清除配置
        </button>
      </div>

      {/* 成功訊息 */}
      {showSuccessMessage && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 animate-fadeIn">
          <div className="flex items-center gap-2 text-green-700">
            <span className="text-lg">✅</span>
            <span className="text-sm font-medium">測試執行成功!</span>
          </div>
        </div>
      )}

      {/* 驗證狀態提示 */}
      {!isValid && !isRunning && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <span className="text-yellow-600 text-sm">⚠️</span>
            <div className="text-xs text-yellow-700">
              <div className="font-medium mb-1">配置驗證失敗</div>
              <div className="text-yellow-600">
                請檢查並修正所有必填欄位和參數約束條件
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 執行中提示 */}
      {isRunning && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <div className="w-4 h-4 mt-0.5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
            <div className="text-xs text-blue-700">
              <div className="font-medium mb-1">正在執行測試...</div>
              <div className="text-blue-600">
                請稍候,這可能需要幾秒到幾分鐘時間
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 快捷鍵提示 */}
      <div className="text-xs text-gray-500 bg-gray-50 p-2 rounded">
        <span className="font-medium">快捷鍵:</span>
        <span className="ml-2">
          Ctrl+Enter 執行測試 | Ctrl+S 保存範本
        </span>
      </div>
    </div>
  );
}

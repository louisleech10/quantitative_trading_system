/**
 * SaveTemplateDialog.tsx - 策略範本保存/載入對話框
 *
 * Phase 3.3+3.4 - Task B3: 主頁面整合
 *
 * 功能:
 * - 保存當前策略配置為範本 (JSON 序列化)
 * - 載入已保存的範本 (JSON 反序列化)
 * - 範本管理 (列表顯示、刪除、重命名)
 * - 本地存儲 (localStorage) + 可選 API 同步
 * - 範本驗證和錯誤處理
 *
 * Ultra Think 記錄:
 * - 步驟 1: 初版代碼 (當前)
 * - 步驟 2: 審查優化 (待執行)
 * - 步驟 3: 最終優化 (待執行)
 */

"use client";

import { useState, useEffect } from "react";

export interface StrategyTemplate {
  id: string;
  name: string;
  description: string;
  created_at: number;
  updated_at: number;
  config: {
    data_source: string;
    indicator_type: string;
    strategy_logic: string;
    test_mode: {
      mode: "single" | "optuna";
      optuna_trials?: number;
    };
    ema_parameters: unknown; // ParameterRange | number 依 test_mode 而定
    training_window: {
      reference_point: "TO" | "TC";
      lookback_bars: number;
      lookforward_bars: number;
      mode: "relative" | "full_range";
    };
  };
}

export interface SaveTemplateDialogProps {
  isOpen: boolean;
  mode: "save" | "load";
  currentConfig?: StrategyTemplate["config"];
  onClose: () => void;
  onSave?: (template: StrategyTemplate) => void;
  onLoad?: (template: StrategyTemplate) => void;
  className?: string;
}

const STORAGE_KEY = "strategy_templates";

export default function SaveTemplateDialog({
  isOpen,
  mode,
  currentConfig,
  onClose,
  onSave,
  onLoad,
  className = "",
}: SaveTemplateDialogProps) {
  const [templates, setTemplates] = useState<StrategyTemplate[]>([]);
  const [templateName, setTemplateName] = useState("");
  const [templateDescription, setTemplateDescription] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);

  // 從 localStorage 載入範本列表
  useEffect(() => {
    if (isOpen) {
      loadTemplatesFromStorage();
    }
  }, [isOpen]);

  const loadTemplatesFromStorage = () => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        setTemplates(parsed);
      }
    } catch (err) {
      console.error("Failed to load templates:", err);
      setError("載入範本列表失敗");
    }
  };

  const saveTemplateToStorage = (newTemplate: StrategyTemplate) => {
    try {
      const updatedTemplates = [...templates, newTemplate];
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedTemplates));
      setTemplates(updatedTemplates);
    } catch (err) {
      console.error("Failed to save template:", err);
      setError("保存範本失敗");
    }
  };

  const deleteTemplateFromStorage = (templateId: string) => {
    try {
      const updatedTemplates = templates.filter((t) => t.id !== templateId);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedTemplates));
      setTemplates(updatedTemplates);
    } catch (err) {
      console.error("Failed to delete template:", err);
      setError("刪除範本失敗");
    }
  };

  const handleSave = () => {
    if (!templateName.trim()) {
      setError("請輸入範本名稱");
      return;
    }

    if (!currentConfig) {
      setError("當前配置無效");
      return;
    }

    const newTemplate: StrategyTemplate = {
      id: `template_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      name: templateName.trim(),
      description: templateDescription.trim(),
      created_at: Date.now(),
      updated_at: Date.now(),
      config: currentConfig,
    };

    saveTemplateToStorage(newTemplate);
    onSave?.(newTemplate);

    // 重置表單
    setTemplateName("");
    setTemplateDescription("");
    setError(null);
    onClose();
  };

  const handleLoad = () => {
    const selectedTemplate = templates.find((t) => t.id === selectedTemplateId);
    if (!selectedTemplate) {
      setError("請選擇一個範本");
      return;
    }

    onLoad?.(selectedTemplate);
    setError(null);
    onClose();
  };

  const handleDelete = (templateId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    if (confirm("確定要刪除此範本嗎?")) {
      deleteTemplateFromStorage(templateId);
      if (selectedTemplateId === templateId) {
        setSelectedTemplateId(null);
      }
    }
  };

  const handleClose = () => {
    setTemplateName("");
    setTemplateDescription("");
    setSelectedTemplateId(null);
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  // 保存模式
  if (mode === "save") {
    return (
      <div className={`fixed inset-0 z-50 flex items-center justify-center ${className}`}>
        {/* 背景遮罩 */}
        <div
          className="absolute inset-0 bg-black/70"
          onClick={handleClose}
        />

        {/* 對話框 */}
        <div className="relative bg-[#0b1220] border border-white/10 rounded-lg shadow-xl p-6 w-full max-w-md max-h-[80vh] overflow-y-auto">
          {/* 標題 */}
          <div className="mb-4">
            <h2 className="text-lg font-bold text-slate-100">💾 保存策略範本</h2>
            <p className="text-xs text-slate-400 mt-1">
              將當前策略配置保存為範本,方便日後快速載入
            </p>
          </div>

          {/* 表單 */}
          <div className="space-y-4">
            {/* 範本名稱 */}
            <div>
              <label className="block text-sm font-medium text-slate-200 mb-1">
                範本名稱 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                placeholder="例: 三線排列 EMA(7,18,35) TO前24根"
                className="w-full px-3 py-2 border border-white/10 rounded-lg text-sm bg-white/5 text-slate-100 placeholder:text-slate-500 focus:ring-2 focus:ring-violet-400/40 focus:border-transparent"
                autoFocus
              />
            </div>

            {/* 範本描述 */}
            <div>
              <label className="block text-sm font-medium text-slate-200 mb-1">
                範本描述 (可選)
              </label>
              <textarea
                value={templateDescription}
                onChange={(e) => setTemplateDescription(e.target.value)}
                placeholder="例: 適用於強趨勢市場,捕捉明確上升趨勢,高勝率策略"
                className="w-full px-3 py-2 border border-white/10 rounded-lg text-sm bg-white/5 text-slate-100 placeholder:text-slate-500 focus:ring-2 focus:ring-violet-400/40 focus:border-transparent"
                rows={3}
              />
            </div>

            {/* 配置預覽 */}
            {currentConfig && (
              <div className="bg-white/5 border border-white/10 rounded-lg p-3">
                <div className="text-xs font-medium text-slate-200 mb-2">
                  配置預覽:
                </div>
                <div className="text-xs text-slate-300 space-y-1">
                  <div>
                    • 數據源: <span className="font-mono">{currentConfig.data_source}</span>
                  </div>
                  <div>
                    • 指標: <span className="font-mono">{currentConfig.indicator_type}</span>
                  </div>
                  <div>
                    • 策略: <span className="font-mono">{currentConfig.strategy_logic}</span>
                  </div>
                  <div>
                    • 測試模式: <span className="font-mono">{currentConfig.test_mode.mode}</span>
                  </div>
                </div>
              </div>
            )}

            {/* 錯誤訊息 */}
            {error && (
              <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-2">
                <div className="text-xs text-rose-200">⚠️ {error}</div>
              </div>
            )}
          </div>

          {/* 按鈕 */}
          <div className="flex gap-3 mt-6">
            <button
              type="button"
              onClick={handleClose}
              className="flex-1 px-4 py-2 border border-white/10 rounded-lg text-sm font-medium text-slate-200 hover:bg-white/5 transition-colors"
            >
              取消
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="flex-1 px-4 py-2 bg-violet-500 text-white rounded-lg text-sm font-medium hover:bg-violet-400 transition-colors"
            >
              💾 保存範本
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 載入模式
  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center ${className}`}>
      {/* 背景遮罩 */}
      <div
          className="absolute inset-0 bg-black/70"
        onClick={handleClose}
      />

      {/* 對話框 */}
        <div className="relative bg-[#0b1220] border border-white/10 rounded-lg shadow-xl p-6 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
        {/* 標題 */}
        <div className="mb-4">
            <h2 className="text-lg font-bold text-slate-100">📂 載入策略範本</h2>
            <p className="text-xs text-slate-400 mt-1">
            從已保存的範本中選擇一個載入到當前配置
          </p>
        </div>

        {/* 範本列表 */}
        {templates.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-4xl mb-3">📭</div>
            <div className="text-sm text-slate-400">尚未保存任何範本</div>
            <div className="text-xs text-slate-500 mt-1">
              保存第一個策略配置以快速重複使用
            </div>
          </div>
        ) : (
          <div className="space-y-2 mb-4">
            {templates.map((template) => {
              const isSelected = selectedTemplateId === template.id;
              return (
                <button
                  key={template.id}
                  type="button"
                  onClick={() => setSelectedTemplateId(template.id)}
                  className={`
                    w-full p-3 rounded-lg border-2 text-left transition-all
                    ${
                      isSelected
                        ? "border-violet-400/60 bg-violet-500/10"
                        : "border-white/10 bg-white/5 hover:border-white/20"
                    }
                  `}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      {/* 範本名稱 */}
                      <div
                        className={`text-sm font-semibold ${
                          isSelected ? "text-violet-100" : "text-slate-100"
                        }`}
                      >
                        {template.name}
                      </div>

                      {/* 範本描述 */}
                      {template.description && (
                        <div
                          className={`text-xs mt-1 ${
                            isSelected ? "text-violet-300" : "text-slate-400"
                          }`}
                        >
                          {template.description}
                        </div>
                      )}

                      {/* 配置摘要 */}
                      <div className="flex gap-2 mt-2 text-xs">
                        <span className="px-2 py-0.5 bg-sky-500/20 text-sky-200 rounded">
                          {template.config.strategy_logic}
                        </span>
                        <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-200 rounded">
                          {template.config.test_mode.mode}
                        </span>
                        <span className="px-2 py-0.5 bg-amber-500/20 text-amber-200 rounded">
                          {template.config.training_window.reference_point}
                        </span>
                      </div>

                      {/* 時間戳記 */}
                      <div className="text-xs text-slate-500 mt-1">
                        建立於:{" "}
                        {new Date(template.created_at).toLocaleString("zh-TW")}
                      </div>
                    </div>

                    {/* 刪除按鈕 */}
                    <button
                      type="button"
                      onClick={(e) => handleDelete(template.id, e)}
                      className="ml-2 p-1 text-rose-300 hover:bg-rose-500/10 rounded transition-colors"
                      title="刪除範本"
                    >
                      🗑️
                    </button>
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {/* 錯誤訊息 */}
        {error && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-2 mb-4">
            <div className="text-xs text-rose-200">⚠️ {error}</div>
          </div>
        )}

        {/* 按鈕 */}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleClose}
            className="flex-1 px-4 py-2 border border-white/10 rounded-lg text-sm font-medium text-slate-200 hover:bg-white/5 transition-colors"
          >
            取消
          </button>
          <button
            type="button"
            onClick={handleLoad}
            disabled={!selectedTemplateId}
            className={`
              flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors
              ${
                selectedTemplateId
                  ? "bg-violet-500 text-white hover:bg-violet-400"
                  : "bg-white/10 text-slate-500 cursor-not-allowed"
              }
            `}
          >
            📂 載入範本
          </button>
        </div>
      </div>
    </div>
  );
}

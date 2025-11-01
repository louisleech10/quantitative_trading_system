/**
 * page.tsx - 策略測試主頁面
 *
 * Phase 3.3+3.4 - Task B3: 主頁面整合
 *
 * 功能:
 * - 整合所有策略配置組件 (B1+B2)
 * - 整合操作按鈕組件 (B3)
 * - 統一狀態管理 (useState)
 * - 配置驗證邏輯
 * - API 調用 (POST /api/chart-signals/signals)
 * - 錯誤處理和使用者反饋
 *
 * Ultra Think 記錄:
 * - 步驟 1: 初版代碼 (當前)
 * - 步驟 2: 審查優化 (待執行)
 * - 步驟 3: 最終優化 (待執行)
 */

"use client";

import { useState } from "react";
import DataSourceSelector from "@/components/strategy/DataSourceSelector";
import IndicatorSelector from "@/components/strategy/IndicatorSelector";
import StrategyLogicSelector from "@/components/strategy/StrategyLogicSelector";
import ParameterRangeInput, {
  type EMAParameters,
} from "@/components/strategy/ParameterRangeInput";
import WindowConfigPanel, {
  type TrainingWindowConfig,
} from "@/components/strategy/WindowConfigPanel";
import TestModeSelector, {
  type TestModeConfig,
} from "@/components/strategy/TestModeSelector";
import ActionButtons from "@/components/strategy/ActionButtons";
import SaveTemplateDialog, {
  type StrategyTemplate,
} from "@/components/strategy/SaveTemplateDialog";

/**
 * 策略配置完整狀態
 */
interface StrategyTestState {
  // B1: 基礎選擇
  data_source: string;
  indicator_type: string;
  strategy_logic: string;

  // B2: 配置組件
  test_mode: TestModeConfig;
  ema_parameters: EMAParameters;
  training_window: TrainingWindowConfig;

  // 測試範圍 (時間和標的)
  symbol: string;
  timeframe: string;
  start_time: number;
  end_time: number;
}

/**
 * API 回應類型
 */
interface SignalPoint {
  timestamp: number;
  indicator_values: Record<string, number>;
  signal_density?: number;
}

interface ChartSignalResponse {
  success: boolean;
  symbol: string;
  timeframe: string;
  signal_points: SignalPoint[];
  total_signals: number;
  sampled: boolean;
  metadata: {
    total_klines: number;
    calculation_time_ms: number;
    strategy_config: any;
  };
}

export default function StrategyTestPage() {
  // ========== 狀態管理 ==========
  const [state, setState] = useState<StrategyTestState>({
    // 預設值
    data_source: "close",
    indicator_type: "ema",
    strategy_logic: "three_line",

    test_mode: {
      mode: "single",
    },

    ema_parameters: {
      ema_short: 7,
      ema_mid: 18,
      ema_long: 35,
    },

    training_window: {
      reference_point: "TO",
      lookback_bars: 24,
      lookforward_bars: 0,
      mode: "relative",
    },

    // 測試範圍 (預設: BTCUSDT 1小時 最近7天)
    symbol: "BTCUSDT",
    timeframe: "1h",
    start_time: Date.now() - 7 * 24 * 60 * 60 * 1000,
    end_time: Date.now(),
  });

  const [isRunning, setIsRunning] = useState(false);
  const [testResult, setTestResult] = useState<ChartSignalResponse | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);

  // 範本對話框狀態
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<"save" | "load">("save");

  // ========== 配置更新函數 ==========
  const updateState = <K extends keyof StrategyTestState>(
    field: K,
    value: StrategyTestState[K]
  ) => {
    setState((prev) => ({ ...prev, [field]: value }));
  };

  // ========== 配置驗證 ==========
  const validateConfig = (): { isValid: boolean; errors: string[] } => {
    const errors: string[] = [];

    // 驗證 EMA 參數
    if (state.test_mode.mode === "single") {
      const short = state.ema_parameters.ema_short as number;
      const mid = state.ema_parameters.ema_mid as number;
      const long = state.ema_parameters.ema_long as number;

      if (short >= mid) {
        errors.push("短期 EMA 必須小於中期 EMA");
      }
      if (mid >= long) {
        errors.push("中期 EMA 必須小於長期 EMA");
      }
    } else {
      // Optuna 模式: 驗證範圍
      const short = state.ema_parameters.ema_short as {
        min: number;
        max: number;
      };
      const mid = state.ema_parameters.ema_mid as { min: number; max: number };
      const long = state.ema_parameters.ema_long as {
        min: number;
        max: number;
      };

      if (short.min >= short.max) {
        errors.push("短期 EMA 最小值必須小於最大值");
      }
      if (mid.min >= mid.max) {
        errors.push("中期 EMA 最小值必須小於最大值");
      }
      if (long.min >= long.max) {
        errors.push("長期 EMA 最小值必須小於最大值");
      }
      if (short.max >= mid.min) {
        errors.push("短期 EMA 最大值必須小於中期 EMA 最小值");
      }
      if (mid.max >= long.min) {
        errors.push("中期 EMA 最大值必須小於長期 EMA 最小值");
      }
    }

    // 驗證時間範圍
    if (state.start_time >= state.end_time) {
      errors.push("開始時間必須早於結束時間");
    }

    // 驗證標的和時間框架
    if (!state.symbol) {
      errors.push("請選擇交易標的");
    }
    if (!state.timeframe) {
      errors.push("請選擇時間框架");
    }

    return {
      isValid: errors.length === 0,
      errors,
    };
  };

  const { isValid } = validateConfig();

  // ========== API 調用 ==========
  const handleRunTest = async () => {
    setIsRunning(true);
    setError(null);
    setTestResult(null);

    try {
      // 構建 API 請求
      const requestBody = {
        symbol: state.symbol,
        timeframe: state.timeframe,
        start_time: state.start_time,
        end_time: state.end_time,
        strategy_config: {
          data_source: state.data_source,
          indicator_type: state.indicator_type,
          strategy_logic: state.strategy_logic,
          ema_parameters: state.ema_parameters,
          training_window: state.training_window,
          test_mode: state.test_mode.mode,
          optuna_trials: state.test_mode.optuna_trials,
        },
      };

      const response = await fetch("/api/chart-signals/signals", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "API 請求失敗");
      }

      const data: ChartSignalResponse = await response.json();
      setTestResult(data);
    } catch (err) {
      console.error("Test execution failed:", err);
      setError(
        err instanceof Error ? err.message : "執行測試時發生未知錯誤"
      );
    } finally {
      setIsRunning(false);
    }
  };

  // ========== 範本管理 ==========
  const handleSaveTemplate = () => {
    setDialogMode("save");
    setDialogOpen(true);
  };

  const handleLoadTemplate = () => {
    setDialogMode("load");
    setDialogOpen(true);
  };

  const handleClearConfig = () => {
    if (confirm("確定要清除所有配置嗎?")) {
      setState({
        data_source: "close",
        indicator_type: "ema",
        strategy_logic: "three_line",
        test_mode: { mode: "single" },
        ema_parameters: {
          ema_short: 7,
          ema_mid: 18,
          ema_long: 35,
        },
        training_window: {
          reference_point: "TO",
          lookback_bars: 24,
          lookforward_bars: 0,
          mode: "relative",
        },
        symbol: "BTCUSDT",
        timeframe: "1h",
        start_time: Date.now() - 7 * 24 * 60 * 60 * 1000,
        end_time: Date.now(),
      });
      setTestResult(null);
      setError(null);
    }
  };

  const handleTemplateSave = (template: StrategyTemplate) => {
    console.log("Template saved:", template);
    // 可選: 顯示成功訊息
  };

  const handleTemplateLoad = (template: StrategyTemplate) => {
    setState((prev) => ({
      ...prev,
      data_source: template.config.data_source,
      indicator_type: template.config.indicator_type,
      strategy_logic: template.config.strategy_logic,
      test_mode: template.config.test_mode,
      ema_parameters: template.config.ema_parameters,
      training_window: template.config.training_window,
    }));
    console.log("Template loaded:", template);
  };

  // ========== 渲染 ==========
  return (
    <div className="min-h-screen bg-gray-50">
      {/* 頁面標題 */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-2xl font-bold text-gray-900">
            📊 策略測試配置
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Phase 3.3+3.4: 策略選擇 UI + 圖表信號箭頭系統
          </p>
        </div>
      </div>

      {/* 主要內容區域 */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左側: 配置面板 */}
          <div className="lg:col-span-2 space-y-6">
            {/* 測試範圍配置 */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">
                🎯 測試範圍
              </h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    交易標的
                  </label>
                  <input
                    type="text"
                    value={state.symbol}
                    onChange={(e) => updateState("symbol", e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    placeholder="例: BTCUSDT"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    時間框架
                  </label>
                  <select
                    value={state.timeframe}
                    onChange={(e) => updateState("timeframe", e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  >
                    <option value="1m">1分鐘</option>
                    <option value="5m">5分鐘</option>
                    <option value="15m">15分鐘</option>
                    <option value="1h">1小時</option>
                    <option value="4h">4小時</option>
                    <option value="1d">1天</option>
                  </select>
                </div>
              </div>
            </div>

            {/* B1: 基礎選擇組件 */}
            <div className="bg-white rounded-lg shadow p-6 space-y-6">
              <h2 className="text-lg font-bold text-gray-900">
                ⚙️ 基礎配置
              </h2>

              <DataSourceSelector
                value={state.data_source}
                onChange={(v) => updateState("data_source", v)}
                disabled={isRunning}
              />

              <IndicatorSelector
                value={state.indicator_type}
                onChange={(v) => updateState("indicator_type", v)}
                disabled={isRunning}
              />

              <StrategyLogicSelector
                value={state.strategy_logic}
                onChange={(v) => updateState("strategy_logic", v)}
                disabled={isRunning}
              />
            </div>

            {/* B2: 參數配置組件 */}
            <div className="bg-white rounded-lg shadow p-6 space-y-6">
              <h2 className="text-lg font-bold text-gray-900">
                🔧 參數配置
              </h2>

              <TestModeSelector
                value={state.test_mode}
                onChange={(v) => updateState("test_mode", v)}
                disabled={isRunning}
              />

              <ParameterRangeInput
                value={state.ema_parameters}
                onChange={(v) => updateState("ema_parameters", v)}
                mode={state.test_mode.mode}
                disabled={isRunning}
              />

              <WindowConfigPanel
                value={state.training_window}
                onChange={(v) => updateState("training_window", v)}
                disabled={isRunning}
              />
            </div>
          </div>

          {/* 右側: 操作面板和結果 */}
          <div className="lg:col-span-1 space-y-6">
            {/* B3: 操作按鈕 */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">
                🚀 操作
              </h2>
              <ActionButtons
                onRunTest={handleRunTest}
                onSaveTemplate={handleSaveTemplate}
                onLoadTemplate={handleLoadTemplate}
                onClearConfig={handleClearConfig}
                isValid={isValid}
                isRunning={isRunning}
              />
            </div>

            {/* 測試結果 */}
            {testResult && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-bold text-gray-900 mb-4">
                  📈 測試結果
                </h2>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">信號數量:</span>
                    <span className="font-semibold text-gray-900">
                      {testResult.total_signals}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">K線總數:</span>
                    <span className="font-semibold text-gray-900">
                      {testResult.metadata.total_klines}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">計算時間:</span>
                    <span className="font-semibold text-gray-900">
                      {testResult.metadata.calculation_time_ms.toFixed(2)} ms
                    </span>
                  </div>
                  {testResult.sampled && (
                    <div className="bg-yellow-50 border border-yellow-200 rounded p-2 text-xs text-yellow-700">
                      ⚠️ 信號數量超過 500,已進行均勻採樣
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 錯誤訊息 */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-start gap-2">
                  <span className="text-red-600">❌</span>
                  <div>
                    <div className="text-sm font-medium text-red-700">
                      執行失敗
                    </div>
                    <div className="text-xs text-red-600 mt-1">{error}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 範本對話框 */}
      <SaveTemplateDialog
        isOpen={dialogOpen}
        mode={dialogMode}
        currentConfig={{
          data_source: state.data_source,
          indicator_type: state.indicator_type,
          strategy_logic: state.strategy_logic,
          test_mode: state.test_mode,
          ema_parameters: state.ema_parameters,
          training_window: state.training_window,
        }}
        onClose={() => setDialogOpen(false)}
        onSave={handleTemplateSave}
        onLoad={handleTemplateLoad}
      />
    </div>
  );
}

/**
 * page.tsx - 策略信號完整演示頁面
 *
 * Phase 3.3+3.4 - Task D1: 整合示例頁面
 *
 * 功能:
 * - 左側: 策略配置面板 (緊湊版)
 * - 右側: 圖表信號可視化 (TradingChartWithSignals)
 * - 實時連接: 配置變更 → API 調用 → 信號標記渲染
 * - 完整流程演示: 配置 → 測試 → 可視化
 *
 * Ultra Think 記錄:
 * - 步驟 1: 初版代碼 (當前)
 * - 步驟 2: 審查優化 (待執行)
 * - 步驟 3: 最終優化 (待執行)
 */

"use client";

import { useState, useCallback } from "react";
import { TradingChartWithSignals } from "@/components/charts/TradingChartWithSignals";
import { SignalPoint, KlineData } from "@/components/charts/StrategySignalChart";
import DataSourceSelector from "@/components/strategy/DataSourceSelector";
import IndicatorSelector from "@/components/strategy/IndicatorSelector";
import StrategyLogicSelector from "@/components/strategy/StrategyLogicSelector";
import TestModeSelector, {
  type TestModeConfig,
} from "@/components/strategy/TestModeSelector";
import ParameterRangeInput, {
  type EMAParameters,
} from "@/components/strategy/ParameterRangeInput";

/**
 * 策略配置狀態
 */
interface StrategyConfig {
  data_source: string;
  indicator_type: string;
  strategy_logic: string;
  test_mode: TestModeConfig;
  ema_parameters: EMAParameters;
}

/**
 * API 回應類型
 */
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

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function StrategyDemoPage() {
  // ========== 配置狀態 ==========
  const [config, setConfig] = useState<StrategyConfig>({
    data_source: "close",
    indicator_type: "ema",
    strategy_logic: "three_line",
    test_mode: { mode: "single" },
    ema_parameters: {
      ema_short: 7,
      ema_mid: 18,
      ema_long: 35,
    },
  });

  // ========== 測試範圍 ==========
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [startTime, setStartTime] = useState(
    Date.now() - 30 * 24 * 60 * 60 * 1000
  ); // 最近 30 天
  const [endTime, setEndTime] = useState(Date.now());

  // ========== 圖表數據 ==========
  const [klines, setKlines] = useState<KlineData[]>([]);
  const [signalPoints, setSignalPoints] = useState<SignalPoint[]>([]);
  const [toTimestamp, setToTimestamp] = useState<number | undefined>(undefined);

  // ========== 狀態管理 ==========
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<ChartSignalResponse | null>(
    null
  );

  /**
   * 更新配置
   */
  const updateConfig = <K extends keyof StrategyConfig>(
    field: K,
    value: StrategyConfig[K]
  ) => {
    setConfig((prev) => ({ ...prev, [field]: value }));
  };

  /**
   * 執行策略測試
   */
  const handleRunTest = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // 1. 構建 API 請求
      const requestBody = {
        symbol,
        timeframe,
        start_time: Math.floor(startTime / 1000), // 轉為 Unix 秒
        end_time: Math.floor(endTime / 1000),
        strategy_config: {
          data_source: config.data_source,
          indicator_type: config.indicator_type,
          strategy_logic: config.strategy_logic,
          ema_parameters: config.ema_parameters,
          training_window: {
            reference_point: "TO",
            lookback_bars: 24,
            lookforward_bars: 0,
            mode: "relative",
          },
          test_mode: config.test_mode.mode,
          optuna_trials: config.test_mode.optuna_trials,
        },
      };

      console.log("[StrategyDemo] API Request:", requestBody);

      // 2. 調用 API
      const response = await fetch(`${API_BASE_URL}/api/v1/chart/signals`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        let message = "API 請求失敗";
        const errorText = await response.text().catch(() => "");
        try {
          const errorData = JSON.parse(errorText || "{}");
          message =
            errorData.detail ||
            errorData.message ||
            errorData.error?.message ||
            message;
        } catch {
          if (response.status) {
            message = `HTTP ${response.status}: ${errorText || message}`;
          }
        }
        throw new Error(message);
      }

      const data: ChartSignalResponse = await response.json();
      console.log("[StrategyDemo] API Response:", data);

      // 3. 更新狀態
      setTestResult(data);
      setSignalPoints(data.signal_points);

      // TODO: 從 API 獲取 K 線數據
      // 目前先使用模擬數據
      const mockKlines = generateMockKlines(
        Math.floor(startTime / 1000),
        Math.floor(endTime / 1000),
        parseInt(timeframe)
      );
      setKlines(mockKlines);

      // 設置 TO 時間戳（假設為數據中點）
      if (mockKlines.length > 0) {
        setToTimestamp(mockKlines[Math.floor(mockKlines.length / 2)].timestamp);
      }
    } catch (err) {
      console.error("[StrategyDemo] Test execution failed:", err);
      setError(
        err instanceof Error ? err.message : "執行測試時發生未知錯誤"
      );
    } finally {
      setIsLoading(false);
    }
  }, [config, symbol, timeframe, startTime, endTime]);

  /**
   * 配置驗證
   */
  const isConfigValid = (): boolean => {
    if (config.test_mode.mode === "single") {
      const short = config.ema_parameters.ema_short as number;
      const mid = config.ema_parameters.ema_mid as number;
      const long = config.ema_parameters.ema_long as number;
      return short < mid && mid < long;
    }
    return true;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 頁面標題 */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-[1920px] mx-auto px-4 py-6">
          <h1 className="text-2xl font-bold text-gray-900">
            🚀 策略信號完整演示
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Phase 3.3+3.4: 策略配置 UI + 圖表信號可視化整合
          </p>
        </div>
      </div>

      {/* 主要內容區域 */}
      <div className="max-w-[1920px] mx-auto px-4 py-6">
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
          {/* 左側: 配置面板 (緊湊版) */}
          <div className="xl:col-span-3 space-y-4">
            {/* 測試範圍 */}
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-sm font-bold text-gray-900 mb-3">
                🎯 測試範圍
              </h2>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    交易標的
                  </label>
                  <input
                    type="text"
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value)}
                    className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
                    placeholder="BTCUSDT"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    時間框架
                  </label>
                  <select
                    value={timeframe}
                    onChange={(e) => setTimeframe(e.target.value)}
                    className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
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

            {/* 策略配置 */}
            <div className="bg-white rounded-lg shadow p-4 space-y-4">
              <h2 className="text-sm font-bold text-gray-900">⚙️ 策略配置</h2>

              <DataSourceSelector
                value={config.data_source}
                onChange={(v) => updateConfig("data_source", v)}
                disabled={isLoading}
              />

              <IndicatorSelector
                value={config.indicator_type}
                onChange={(v) => updateConfig("indicator_type", v)}
                disabled={isLoading}
              />

              <StrategyLogicSelector
                value={config.strategy_logic}
                onChange={(v) => updateConfig("strategy_logic", v)}
                disabled={isLoading}
              />

              <TestModeSelector
                value={config.test_mode}
                onChange={(v) => updateConfig("test_mode", v)}
                disabled={isLoading}
              />

              <ParameterRangeInput
                value={config.ema_parameters}
                onChange={(v) => updateConfig("ema_parameters", v)}
                mode={config.test_mode.mode}
                disabled={isLoading}
              />
            </div>

            {/* 執行按鈕 */}
            <button
              type="button"
              onClick={handleRunTest}
              disabled={isLoading || !isConfigValid()}
              className={`
                w-full px-4 py-3 rounded-lg text-sm font-medium transition-all
                ${
                  isLoading || !isConfigValid()
                    ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                    : "bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:from-green-600 hover:to-emerald-700 shadow-lg"
                }
              `}
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin">⏳</span>
                  執行中...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  ▶️ 執行策略測試
                </span>
              )}
            </button>

            {/* 測試結果統計 */}
            {testResult && (
              <div className="bg-white rounded-lg shadow p-4">
                <h2 className="text-sm font-bold text-gray-900 mb-3">
                  📊 測試結果
                </h2>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-600">信號數量:</span>
                    <span className="font-semibold text-green-600">
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
                    <div className="bg-yellow-50 border border-yellow-200 rounded p-2 text-yellow-700">
                      ⚠️ 已採樣至 500 個標記
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
                    <div className="text-xs font-medium text-red-700">
                      執行失敗
                    </div>
                    <div className="text-xs text-red-600 mt-1">{error}</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 右側: 圖表可視化 */}
          <div className="xl:col-span-9">
            <div className="bg-white rounded-lg shadow">
              {klines.length > 0 ? (
                <TradingChartWithSignals
                  symbol={symbol}
                  timeframe={timeframe}
                  klines={klines}
                  signalPoints={signalPoints}
                  toTimestamp={toTimestamp}
                  totalHeight={800}
                  showCaseMarker={true}
                  showSignalMarkers={true}
                  onSignalClick={(signal) => {
                    console.log("[StrategyDemo] Signal clicked:", signal);
                  }}
                />
              ) : (
                <div className="flex items-center justify-center h-[800px]">
                  <div className="text-center">
                    <div className="text-4xl mb-4">📊</div>
                    <div className="text-sm text-gray-500">
                      點擊「執行策略測試」查看信號可視化
                    </div>
                    <div className="text-xs text-gray-400 mt-2">
                      配置完成後,系統將自動計算並顯示策略信號
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * 生成模擬 K 線數據 (用於演示)
 * TODO: 替換為真實 API 調用
 */
function generateMockKlines(
  startTime: number,
  endTime: number,
  intervalMinutes: number
): KlineData[] {
  const klines: KlineData[] = [];
  const intervalSeconds = intervalMinutes * 60;
  let currentTime = startTime;
  let price = 60000 + Math.random() * 10000;

  while (currentTime <= endTime) {
    const open = price;
    const changePercent = (Math.random() - 0.5) * 0.02; // ±1% 變化
    const close = open * (1 + changePercent);
    const high = Math.max(open, close) * (1 + Math.random() * 0.01);
    const low = Math.min(open, close) * (1 - Math.random() * 0.01);
    const volume = 100 + Math.random() * 900;

    klines.push({
      timestamp: currentTime,
      open,
      high,
      low,
      close,
      volume,
      taker_buy_volume: volume * (0.4 + Math.random() * 0.2),
      taker_ratio: 0.4 + Math.random() * 0.2,
    });

    price = close;
    currentTime += intervalSeconds;
  }

  return klines;
}

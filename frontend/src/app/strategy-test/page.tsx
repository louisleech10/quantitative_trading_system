"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "react-hot-toast";
import { useStrategyTestStore } from "@/store/strategyTestStore";
import {
  BarChart2,
  ChevronRight,
  Database,
  Layers,
  LineChart,
  Loader2,
  RefreshCw,
  Save,
  Share2,
  Sparkles,
  Trash2,
} from "lucide-react";
import { Accordion } from "@/components/ui/Accordion";
import { AccordionItem } from "@/components/ui/AccordionItem";
import { Select, type SelectOption } from "@/components/ui/select";
import { NumberInput } from "@/components/ui/NumberInput";
import { DateRangePicker } from "@/components/ui/DateRangePicker";
import StatMetricCard from "@/components/ui/StatMetricCard";
import CombinedDensityBoxplot from "@/components/charts/CombinedDensityBoxplot";
import WindowConfigPanel, {
  type TrainingWindowConfig,
} from "@/components/strategy/WindowConfigPanel";
import {
  useStrategyConfig,
  type StrategyTemplatePayload,
} from "@/hooks/useStrategyConfig";
import {
  OptunaConfigPanel,
  type OptunaConfig,
  loadOptunaConfig,
  saveOptunaConfig,
} from "@/components/strategy-test/OptunaConfigPanel";

interface SignalPoint {
  timestamp: number;
  indicator_values: Record<string, number>;
  signal_density?: number;
}

interface DensityMetrics {
  // 近期密度 (Near window density)
  positive_avg_density?: number;
  negative_avg_density?: number;

  // 遠期密度 (Far window density)
  positive_far_avg_density?: number;
  negative_far_avg_density?: number;

  // 近遠比 (Near/Far ratio)
  positive_near_far_ratio?: number;
  negative_near_far_ratio?: number;
  near_far_ratio?: number; // Legacy field, maps to positive_near_far_ratio

  // 標準差 (Standard deviations)
  positive_std?: number;
  negative_std?: number;
  positive_far_std?: number;
  negative_far_std?: number;
  positive_ratio_std?: number;
  negative_ratio_std?: number;

  // 分離度指標 (Separation metrics)
  separation?: number;
  ratio_separation?: number;

  // 統計檢驗 (Statistical tests)
  p_value?: number;
  cohens_d?: number;
  stability_cv?: number;

  // 雙密度穩定性指標 (Dual density stability)
  positive_ratio_cv?: number;
  separation_cv?: number;

  // 樣本數 (Sample sizes)
  positive_sample_size?: number;
  negative_sample_size?: number;

  // 零值統計 (v1.1 新增) - 透明化顯示策略信號未觸發或 Far=0 被排除的案例比例
  positive_near_zero_count?: number;
  positive_near_zero_ratio?: number;
  positive_far_zero_count?: number;
  positive_far_zero_ratio?: number;
  negative_near_zero_count?: number;
  negative_near_zero_ratio?: number;
  negative_far_zero_count?: number;
  negative_far_zero_ratio?: number;
}

interface DataQualitySummary {
  total_cases?: number;
  positive_cases?: number;
  negative_cases?: number;
  success_rate?: number;
  error_messages?: string[];
}

interface ChartSignalResponse {
  signal_points: SignalPoint[];
  total_bars: number;
  signal_count: number;
  signal_density: number;
  is_sampled: boolean;
  strategy_name: string;
  metadata?: {
    total_klines?: number;
    calculation_time_ms?: number;
    strategy_config?: Record<string, unknown>;
    density_metrics?: DensityMetrics;
    quality?: DataQualitySummary;
  };
}

const DATA_SOURCE_OPTIONS = [
  { value: "close", label: "收盤價 Close", icon: "📊" },
  { value: "open", label: "開盤價 Open", icon: "🔓" },
  { value: "high", label: "最高價 High", icon: "⬆️" },
  { value: "low", label: "最低價 Low", icon: "⬇️" },
  { value: "volume", label: "成交量 Volume", icon: "📦" },
  { value: "taker_buy_volume", label: "主動買量", icon: "🟢" },
  { value: "taker_ratio", label: "Taker Ratio", icon: "%" },
];

const INDICATOR_OPTIONS: SelectOption[] = [
  { value: "ema", label: "EMA 指數移動平均", icon: "📈" },
  { value: "sma", label: "SMA 簡單移動平均", icon: "📉", disabled: true },
  { value: "rsi", label: "RSI 相對強弱", icon: "⚡", disabled: true },
  { value: "macd", label: "MACD", icon: "🌊", disabled: true },
];

const STRATEGY_OPTIONS: SelectOption[] = [
  { value: "three_line", label: "三線順勢 (EMA 短 > 中 > 長)", icon: "📐" },
  { value: "crossover", label: "均線交叉", icon: "✂️", disabled: true },
  { value: "threshold", label: "閾值突破", icon: "🎯", disabled: true },
];

interface StrategyGuide {
  title: string;
  description: string;
  bullets?: string[];
  status: "active" | "locked";
  note?: string;
}

const STRATEGY_GUIDES: Record<string, StrategyGuide> = {
  three_line: {
    title: "三線順勢 (EMA 短 > 中 > 長)",
    description:
      "EMA 短線必須大於中線、中線大於長線，搭配多數據源 (Close + Volume/Taker) 觀察趨勢延續性，適合尋找連續性突破案例。",
    bullets: [
      "建議與 Near 24 / Far 100 雙窗口搭配，強調近期密度聚集。",
      "可同時觀察 Volume / Taker Buy Volume 以過濾放量假突破。",
      "若出現 EMA 排序被破壞，可將其視為策略失效並重置窗口。",
    ],
    status: "active",
  },
  crossover: {
    title: "均線交叉 (等待驗證)",
    description:
      "觀察 EMA/SMA 快慢線交叉觸發信號，需結合波動過濾才能有效區分雜訊，目前仍在驗證資料品質。",
    bullets: [
      "預計支援多指標組合，並加入震盪/趨勢濾網。",
      "完成 Phase 3.4 驗證後才會開放。",
    ],
    status: "locked",
    note: "預計 3.4 版開放",
  },
  threshold: {
    title: "閾值突破 (規劃中)",
    description:
      "以 RSI / ATR / Volume Spike 等閾值觸發進出場，需與 Optuna 參數掃描結合，目前僅保留 UI 區塊。",
    bullets: [
      "將支援自定義指標加總與布林帶偏離率。",
      "待雙密度驗證完成後再導入。",
    ],
    status: "locked",
    note: "Roadmap Q1",
  },
};

const SYMBOL_OPTIONS: SelectOption[] = [
  { value: "BTCUSDT", label: "BTCUSDT", icon: "₿" },
  { value: "ETHUSDT", label: "ETHUSDT", icon: "◇" },
  { value: "SOLUSDT", label: "SOLUSDT", icon: "🌀" },
  { value: "CUSTOM", label: "自訂交易對", icon: "✏️" },
];

const TIMEFRAME_OPTIONS: SelectOption[] = [
  { value: "1h", label: "1 小時" },
  { value: "4h", label: "4 小時" },
  { value: "12h", label: "12 小時" },
  { value: "1d", label: "1 天" },
];

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const formatPercent = (value?: number) => {
  if (value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(2)}%`;
};

const formatNumber = (value?: number, digits = 2) => {
  if (value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
};

const formatCount = (value?: number) => {
  if (value === undefined || value === null) return "—";
  return value.toLocaleString();
};

const parseDateToTimestamp = (date: string, fallback: number) => {
  if (!date) return fallback;
  const timestamp = Date.parse(`${date}T00:00:00Z`);
  return Number.isNaN(timestamp) ? fallback : timestamp;
};

function StrategyTestPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const {
    state,
    setField,
    reset,
    saveTemplate,
    loadTemplate,
    listTemplates,
    deleteTemplate,
    syncToUrl,
    cacheStateSnapshot,
    hydrateFromUrl,
  } = useStrategyConfig();

  const [isRunning, setIsRunning] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [templates, setTemplates] = useState<StrategyTemplatePayload[]>([]);
  const [isTemplatePanelOpen, setTemplatePanelOpen] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const hasHydratedFromUrl = useRef(false);

  // Use Zustand store for persistent state across route changes
  const {
    testResult,
    caseLevelDensities,
    positiveCaseIds,
    negativeCaseIds,
    apiError,
    setTestResult,
    setCaseLevelDensities,
    setPositiveCaseIds,
    setNegativeCaseIds,
    setApiError,
    clearResults,
  } = useStrategyTestStore();
  // Optuna 配置狀態
  const [optunaConfig, setOptunaConfig] = useState<OptunaConfig>(() => loadOptunaConfig());

  useEffect(() => {
    setIsClient(true);
  }, []);

  // Optuna 配置變更處理
  const handleOptunaConfigChange = (newConfig: OptunaConfig) => {
    setOptunaConfig(newConfig);
    saveOptunaConfig(newConfig);
  };

  useEffect(() => {
    if (!isClient || hasHydratedFromUrl.current) return;
    const stateParam = searchParams?.get("state");
    if (!stateParam) return;
    const hydrated = hydrateFromUrl(searchParams);
    if (hydrated) {
      hasHydratedFromUrl.current = true;
      toast.success("已從 URL 還原策略設定");
    }
  }, [hydrateFromUrl, isClient, searchParams]);

  useEffect(() => {
    if (!isClient) return;
    const timeout = window.setTimeout(() => {
      cacheStateSnapshot();
      if (!state.syncToUrl) return;
      const query = syncToUrl();
      if (!query) return;
      if (typeof window === "undefined") return;
      if (window.location.search === query) return;
      const path = window.location.pathname.replace(/\/$/, "");
      if (path !== "/strategy-test") return;
      router.replace(`/strategy-test${query}`, { scroll: false });
    }, 400);
    return () => window.clearTimeout(timeout);
  }, [state, syncToUrl, cacheStateSnapshot, router, isClient]);

  useEffect(() => {
    if (isTemplatePanelOpen) {
      setTemplates(listTemplates());
    }
  }, [isTemplatePanelOpen, listTemplates]);

  const validationErrors = useMemo(() => {
    const errors: string[] = [];
    const { indicatorParams, dateRange, dataSources } = state;
    const short = indicatorParams.short_period;
    const mid = indicatorParams.mid_period;
    const long = indicatorParams.long_period;

    if (!(short < mid && mid < long)) {
      errors.push("請維持 EMA 週期為 短 < 中 < 長");
    }

    if (!dateRange.start || !dateRange.end) {
      errors.push("請完整設定時間範圍");
    } else if (dateRange.start > dateRange.end) {
      errors.push("開始日期不可晚於結束日期");
    }

    if (!dataSources) {
      errors.push("請選擇數據源");
    }

    if (!state.symbol) {
      errors.push("請輸入或選擇交易對");
    }

    if (!state.timeframe) {
      errors.push("請選擇時間框架");
    }

    return errors;
  }, [state]);

  const densityMetrics = useMemo(
    () => testResult?.metadata?.density_metrics ?? null,
    [testResult]
  );
  const qualitySummary = useMemo(
    () => testResult?.metadata?.quality ?? null,
    [testResult]
  );

  const handleIndicatorParamChange = (field: string, value: number) => {
    setField("indicatorParams", {
      ...state.indicatorParams,
      [field]: value,
    });
  };

  const handleWindowConfigChange = (config: TrainingWindowConfig) => {
    setField("windowConfig", config);
  };

  const handleApplyDualWindowPreset = () => {
    setField("windowConfig", {
      ...state.windowConfig,
      reference_point: "TO",
      lookback_bars: 24,
      lookforward_bars: 0,
      far_lookback_bars: 100,
      mode: "relative",
    });
  };

  // 獲取指定 symbol 的案例
  const fetchCasesBySymbol = async (symbol: string): Promise<{ positive: string[]; negative: string[] }> => {
    try {
      const casesResponse = await fetch(`${API_BASE_URL}/api/v1/case/list`);
      if (!casesResponse.ok) return { positive: [], negative: [] };

      const casesData = await casesResponse.json();
      const positive: string[] = [];
      const negative: string[] = [];

      if (casesData.cases && Array.isArray(casesData.cases)) {
        casesData.cases.forEach((c: { symbol: string; positive_case: number; case_id: string }) => {
          if (c.symbol === symbol) {
            if (c.positive_case === 1) {
              positive.push(c.case_id);
            } else if (c.positive_case === 0) {
              negative.push(c.case_id);
            }
          }
        });
      }

      return { positive, negative };
    } catch (error) {
      console.error("Failed to fetch cases:", error);
      return { positive: [], negative: [] };
    }
  };

  // 開始 Optuna 優化
  const handleStartOptimization = async () => {
    // 驗證基本配置
    if (validationErrors.length > 0) {
      toast.error("請先修正配置錯誤");
      return;
    }

    if (!optunaConfig.enabled) {
      toast.error("請先啟用 Optuna 優化");
      return;
    }

    setIsOptimizing(true);
    setApiError(null);

    try {
      // Step 1: 獲取案例
      const { positive, negative } = await fetchCasesBySymbol(state.symbol);

      if (positive.length === 0 || negative.length === 0) {
        throw new Error(`符合 ${state.symbol} 的案例數量不足：正例 ${positive.length} 個，反例 ${negative.length} 個`);
      }

      toast.success(`已載入 ${positive.length} 個正例和 ${negative.length} 個反例`);

      // Step 2: 創建優化任務
      const createResponse = await fetch(`${API_BASE_URL}/api/v1/optimization/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          study_name: `${state.symbol}_${state.strategyLogic}_${Date.now()}`,
          positive_cases: positive,
          negative_cases: negative,
          training_window: state.windowConfig,
          sampler_type: "TPE",
          n_trials: optunaConfig.n_trials,
          n_jobs: 1,
          use_multi_objective: false,
          parameter_ranges: {
            ema_short_range: optunaConfig.ema_short_range,
            ema_mid_range: optunaConfig.ema_mid_range,
            ema_long_range: optunaConfig.ema_long_range,
            data_sources: [state.dataSources ?? "close"],
            strategy_logics: [state.strategyLogic],
            indicator_types: [state.indicatorType],  // 傳遞用戶選擇的指標類型
          },
        }),
      });

      if (!createResponse.ok) {
        const errorData = await createResponse.json().catch(() => ({}));
        throw new Error(errorData.detail || errorData.message || "創建優化任務失敗");
      }

      const createData = await createResponse.json();
      const taskId = createData.task_id;

      toast.success(`優化任務已創建：${taskId}`);

      // Step 3: 啟動優化任務
      const startResponse = await fetch(`${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/start`, {
        method: "POST",
      });

      if (!startResponse.ok) {
        const errorData = await startResponse.json().catch(() => ({}));
        throw new Error(errorData.detail || errorData.message || "啟動優化任務失敗");
      }

      toast.success("優化任務已啟動！");

      // Step 4: 等待一小段時間再跳轉（讓用戶看到成功消息）
      await new Promise(resolve => setTimeout(resolve, 1000));

      // 提示用戶任務正在後台執行
      toast.loading(`優化進行中 (${optunaConfig.n_trials} trials)，正在跳轉到結果頁面...`, {
        duration: 2000
      });

      // 導航到結果頁面
      router.push(`/optimization-result/${taskId}`);

    } catch (error) {
      const message = error instanceof Error ? error.message : "執行優化時發生未知錯誤";
      setApiError(message);
      toast.error(message);
    } finally {
      setIsOptimizing(false);
    }
  };

  const handleRunTest = async () => {
    if (validationErrors.length > 0) {
      toast.error("請先修正配置錯誤");
      return;
    }

    setIsRunning(true);
    setApiError(null);

    try {
      const startTime = parseDateToTimestamp(state.dateRange.start, Date.now() - 7 * 24 * 60 * 60 * 1000);
      const endTime = parseDateToTimestamp(state.dateRange.end, Date.now());

      // Step 1: 呼叫 chart/signals 取得圖表數據
      const chartRequestBody = {
        symbol: state.symbol,
        timeframe: state.timeframe,
        start_time: startTime,
        end_time: endTime,
        strategy_config: {
          data_source: state.dataSources ?? "close",
          data_sources: [state.dataSources],
          indicator_type: state.indicatorType,
          strategy_logic: state.strategyLogic,
          params: state.indicatorParams,
          training_window: state.windowConfig,
          clustering_weight: state.clusteringWeight,
        },
      };

      const chartResponse = await fetch(`${API_BASE_URL}/api/v1/chart/signals`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(chartRequestBody),
      });

      if (!chartResponse.ok) {
        let message = "API 請求失敗";
        const errorText = await chartResponse.text().catch(() => "");
        try {
          const errorData = JSON.parse(errorText || "{}");
          // 優先顯示驗證錯誤的詳細信息
          if (errorData.error?.details?.validation_errors?.length > 0) {
            const errors = errorData.error.details.validation_errors;
            const errorDetails = errors.map((e: { field: string; message: string }) => 
              `${e.field}: ${e.message}`
            ).join('; ');
            message = `驗證失敗: ${errorDetails}`;
          } else {
            message =
              errorData.detail ||
              errorData.message ||
              errorData.error?.message ||
              message;
          }
        } catch {
          if (chartResponse.status) {
            message = `HTTP ${chartResponse.status}: ${errorText || message}`;
          }
        }
        throw new Error(message);
      }

      const chartData: ChartSignalResponse = await chartResponse.json();

      // Step 2: 載入真實案例並過濾出符合當前 symbol/timeframe 的案例
      const casesResponse = await fetch(`${API_BASE_URL}/api/v1/case/list`);
      if (casesResponse.ok) {
        const casesData = await casesResponse.json();

        // 過濾出符合當前測試配置的案例（相同 symbol 和 timeframe）
        const positiveCases: string[] = [];
        const negativeCases: string[] = [];

        if (casesData.cases && Array.isArray(casesData.cases)) {
          casesData.cases.forEach((c: any) => {
            // 只使用符合當前 symbol 的案例（忽略 timeframe 差異，因為後端會處理）
            if (c.symbol === state.symbol) {
              if (c.positive_case === 1) {
                positiveCases.push(c.case_id);
              } else if (c.positive_case === 0) {
                negativeCases.push(c.case_id);
              }
            }
          });
        }

        // Step 3: 如果有足夠的案例，呼叫 signal-analysis/density 取得密度統計
        if (positiveCases.length > 0 && negativeCases.length > 0) {
          const densityRequestBody = {
            strategy_config: {
              data_source: state.dataSources ?? "close",
              indicator_type: state.indicatorType,
              strategy_logic: state.strategyLogic,
              params: state.indicatorParams,
            },
            training_window: state.windowConfig,
            positive_cases: positiveCases,
            negative_cases: negativeCases,
          };

          const densityResponse = await fetch(`${API_BASE_URL}/api/v1/signal-analysis/density`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(densityRequestBody),
          });

          if (densityResponse.ok) {
            const densityData = await densityResponse.json();

            // Debug: Log stability CV values
            console.log("Density API Response - Stability CVs:", {
              positive_ratio_cv: densityData.positive_ratio_cv,
              separation_cv: densityData.separation_cv,
            });

            // Store data for Boxplot chart
            setCaseLevelDensities(densityData.case_level_densities || {});
            setPositiveCaseIds(positiveCases);
            setNegativeCaseIds(negativeCases);

            // 合併密度數據到圖表結果中
            chartData.metadata = {
              ...chartData.metadata,
              density_metrics: {
                // 近期密度
                positive_avg_density: densityData.positive_avg_density,
                negative_avg_density: densityData.negative_avg_density,

                // 遠期密度
                positive_far_avg_density: densityData.positive_far_avg_density,
                negative_far_avg_density: densityData.negative_far_avg_density,

                // 近遠比
                positive_near_far_ratio: densityData.positive_near_far_ratio,
                negative_near_far_ratio: densityData.negative_near_far_ratio,
                near_far_ratio: densityData.positive_near_far_ratio, // Legacy compatibility

                // 標準差
                positive_std: densityData.positive_std,
                negative_std: densityData.negative_std,
                positive_far_std: densityData.positive_far_std,
                negative_far_std: densityData.negative_far_std,
                positive_ratio_std: densityData.positive_ratio_std,
                negative_ratio_std: densityData.negative_ratio_std,

                // 分離度指標
                separation: densityData.separation,
                ratio_separation: densityData.ratio_separation,

                // 統計檢驗
                p_value: densityData.p_value,
                cohens_d: densityData.cohens_d,
                stability_cv: densityData.stability_cv,

                // 雙密度穩定性指標
                positive_ratio_cv: densityData.positive_ratio_cv,
                separation_cv: densityData.separation_cv,

                // 樣本數
                positive_sample_size: densityData.positive_sample_size,
                negative_sample_size: densityData.negative_sample_size,

                // 零值統計 (v1.1 新增)
                positive_near_zero_count: densityData.positive_near_zero_count,
                positive_near_zero_ratio: densityData.positive_near_zero_ratio,
                positive_far_zero_count: densityData.positive_far_zero_count,
                positive_far_zero_ratio: densityData.positive_far_zero_ratio,
                negative_near_zero_count: densityData.negative_near_zero_count,
                negative_near_zero_ratio: densityData.negative_near_zero_ratio,
                negative_far_zero_count: densityData.negative_far_zero_count,
                negative_far_zero_ratio: densityData.negative_far_zero_ratio,
              },
              quality: {
                total_cases: densityData.positive_sample_size + densityData.negative_sample_size,
                positive_cases: densityData.positive_sample_size,
                negative_cases: densityData.negative_sample_size,
                success_rate: densityData.positive_sample_size / (densityData.positive_sample_size + densityData.negative_sample_size),
              },
            };
          } else {
            // ❌ 密度分析失敗時應立即中斷執行，並顯示錯誤給使用者
            let message = "密度分析失敗";
            const errorText = await densityResponse.text().catch(() => "");

            try {
              const errorData = JSON.parse(errorText || "{}");
              // 優先顯示驗證錯誤的詳細信息
              if (errorData.error?.details?.validation_errors?.length > 0) {
                const errors = errorData.error.details.validation_errors;
                const errorDetails = errors.map((e: { field: string; message: string }) => 
                  `${e.field}: ${e.message}`
                ).join('; ');
                message = `驗證失敗: ${errorDetails}`;
              } else {
                message =
                  errorData.error?.message ||
                  errorData.detail ||
                  errorData.message ||
                  message;
              }
            } catch {
              message = errorText || message;
            }

            throw new Error(message);  // 中斷執行並傳播錯誤
          }
        } else {
          console.warn(`符合 ${state.symbol} 的案例數量不足：正例${positiveCases.length}個，反例${negativeCases.length}個`);
        }
      }
      // ✅ 內層 try-catch 已移除，讓所有錯誤向上傳播到主 catch 處理（第 522 行）

      setTestResult(chartData);
      toast.success("測試完成");
    } catch (error) {
      const message = error instanceof Error ? error.message : "執行測試時發生未知錯誤";
      setApiError(message);
      toast.error(message);
    } finally {
      setIsRunning(false);
    }
  };

  const handleSaveTemplate = () => {
    const name = window.prompt("輸入範本名稱", state.strategyName || "自訂策略");
    if (!name) return;
    const description = window.prompt("輸入範本描述 (可留空)", state.strategyDescription ?? "") || undefined;
    const result = saveTemplate({ name, description });
    if (result) {
      toast.success(`已保存範本「${result.name}」`);
      setTemplates(listTemplates());
    }
  };

  const handleReset = () => {
    if (confirm("確定要清除所有配置嗎？")) {
      reset();
      clearResults();  // Clear all persisted results from store
      toast.success("已回復預設值");
    }
  };

  const handleViewCharts = () => {
    const query = syncToUrl();
    router.push(`/charts${query ?? ""}`);
  };

  const handleLoadTemplate = (template: StrategyTemplatePayload) => {
    loadTemplate(template);
    toast.success(`已載入範本「${template.name}」`);
    setTemplatePanelOpen(false);
  };

  const handleDeleteTemplate = (templateId: string) => {
    deleteTemplate(templateId);
    setTemplates(listTemplates());
  };

  const selectedSymbolOption = SYMBOL_OPTIONS.find((option) => option.value === state.symbol) ?? null;
  const symbolSelectValue = selectedSymbolOption ? selectedSymbolOption.value : null;
  const currentStrategyGuide =
    STRATEGY_GUIDES[state.strategyLogic] ?? STRATEGY_GUIDES.three_line;

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-3 text-sm text-slate-500">
              <span className="flex items-center gap-1 text-indigo-600">
                <Layers className="h-4 w-4" /> Phase 3.2
              </span>
              <ChevronRight className="h-4 w-4 text-slate-400" />
              <span>雙窗口密度 / 策略測試</span>
            </div>
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:gap-6">
              <input
                type="text"
                value={state.strategyName}
                onChange={(event) => setField("strategyName", event.target.value)}
                className="w-full rounded-lg border border-slate-200 px-4 py-2 text-lg font-semibold text-slate-900 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200"
                placeholder="輸入策略名稱"
              />
              <button
                type="button"
                onClick={() => setTemplatePanelOpen(true)}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
              >
                <Database className="h-4 w-4" /> 管理範本
              </button>
            </div>
            <textarea
              value={state.strategyDescription ?? ""}
              onChange={(event) => setField("strategyDescription", event.target.value)}
              rows={2}
              className="w-full rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-700 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200"
              placeholder="補充策略說明、假設或使用情境..."
            />
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleSaveTemplate}
              className="inline-flex items-center gap-2 rounded-lg border border-indigo-100 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700 transition hover:bg-indigo-100"
            >
              <Save className="h-4 w-4" /> 保存範本
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              <Trash2 className="h-4 w-4" /> 清除
            </button>
            <button
              type="button"
              onClick={handleViewCharts}
              className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
            >
              <LineChart className="h-4 w-4" /> 查看圖表
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[360px,1fr]">
        <div className="space-y-4">
          <Accordion defaultExpanded={["basic", "indicator"]}>
            <AccordionItem id="basic" title="基本配置" badge={state.dataSources || "未選擇"}>
              <div className="space-y-4">
                <Select
                  label="數據來源"
                  options={DATA_SOURCE_OPTIONS}
                  value={state.dataSources}
                  onChange={(value) => setField("dataSources", value ?? "close")}
                  placeholder="選擇欲追蹤的 K 線欄位"
                />
                <Select
                  label="指標類型"
                  options={INDICATOR_OPTIONS}
                  value={state.indicatorType}
                  onChange={(value) => setField("indicatorType", value ?? "ema")}
                />
                <Select
                  label="策略邏輯"
                  options={STRATEGY_OPTIONS}
                  value={state.strategyLogic}
                  onChange={(value) => setField("strategyLogic", value ?? "three_line")}
                />
                <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-3 text-xs text-slate-600">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-slate-800">
                      {currentStrategyGuide.title}
                    </p>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        currentStrategyGuide.status === "active"
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-slate-200 text-slate-600"
                      }`}
                    >
                      {currentStrategyGuide.status === "active" ? "已啟用" : "開發中"}
                    </span>
                    {currentStrategyGuide.note && (
                      <span className="text-[10px] text-slate-500">{currentStrategyGuide.note}</span>
                    )}
                  </div>
                  <p className="mt-2 leading-relaxed text-slate-600">
                    {currentStrategyGuide.description}
                  </p>
                  {currentStrategyGuide.bullets && (
                    <ul className="mt-2 list-inside list-disc space-y-1 text-[11px] text-slate-500">
                      {currentStrategyGuide.bullets.map((tip, index) => (
                        <li key={`${currentStrategyGuide.title}-${index}`}>{tip}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </AccordionItem>

            <AccordionItem id="indicator" title="指標參數" badge="EMA">
              <div className="grid grid-cols-1 gap-4">
                <NumberInput
                  label="EMA Short"
                  value={state.indicatorParams.short_period}
                  min={2}
                  max={500}
                  onChange={(value) => handleIndicatorParamChange("short_period", value)}
                />
                <NumberInput
                  label="EMA Mid"
                  value={state.indicatorParams.mid_period}
                  min={state.indicatorParams.short_period + 1}
                  max={500}
                  onChange={(value) => handleIndicatorParamChange("mid_period", value)}
                />
                <NumberInput
                  label="EMA Long"
                  value={state.indicatorParams.long_period}
                  min={state.indicatorParams.mid_period + 1}
                  max={500}
                  onChange={(value) => handleIndicatorParamChange("long_period", value)}
                />
              </div>
            </AccordionItem>

            <AccordionItem
              id="window"
              title="窗口配置"
              badge={state.windowConfig.far_lookback_bars ? "雙密度" : "單密度"}
            >
              <div className="space-y-4">
                <WindowConfigPanel
                  value={state.windowConfig}
                  onChange={handleWindowConfigChange}
                />
                <button
                  type="button"
                  onClick={handleApplyDualWindowPreset}
                  className="inline-flex items-center gap-2 rounded-lg border border-purple-200 bg-purple-50 px-3 py-2 text-xs font-medium text-purple-700 transition hover:bg-purple-100"
                >
                  套用 Near 24 / Far 100 預設
                </button>
              </div>
            </AccordionItem>

            <AccordionItem id="range" title="測試範圍" badge={state.timeframe}>
              <div className="space-y-4">
                <Select
                  label="交易對"
                  options={SYMBOL_OPTIONS}
                  value={symbolSelectValue}
                  onChange={(value) => {
                    if (!value || value === "CUSTOM") return;
                    setField("symbol", value);
                  }}
                  allowClear
                />
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-600">自訂交易對</label>
                  <input
                    type="text"
                    value={state.symbol}
                    onChange={(event) => setField("symbol", event.target.value.toUpperCase())}
                    placeholder="例：BTCUSDT"
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200"
                  />
                </div>
                <Select
                  label="時間框架"
                  options={TIMEFRAME_OPTIONS}
                  value={state.timeframe}
                  onChange={(value) => setField("timeframe", value ?? state.timeframe)}
                />
                <DateRangePicker
                  label="時間範圍"
                  startDate={state.dateRange.start}
                  endDate={state.dateRange.end}
                  onChange={(start, end) =>
                    setField("dateRange", {
                      start,
                      end,
                    })
                  }
                />
                <label className="flex items-center gap-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={state.syncToUrl}
                    onChange={(event) => setField("syncToUrl", event.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  轉跳 /charts 時同步參數至 URL
                </label>
              </div>
            </AccordionItem>

            <AccordionItem id="optimizer" title="優化參數" badge={`${(state.clusteringWeight * 100).toFixed(0)}% 聚集權重`}>
              <div className="space-y-3">
                <label className="text-sm font-medium text-slate-700">clustering_weight (0=只看區分度, 1=只看聚集度)</label>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={state.clusteringWeight}
                  onChange={(event) => setField("clusteringWeight", Number(event.target.value))}
                  className="w-full"
                />
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>偏重 Near/Far Ratio</span>
                  <span className="font-semibold text-slate-700">{state.clusteringWeight.toFixed(2)}</span>
                  <span>偏重 正反例區分</span>
                </div>
              </div>
            </AccordionItem>

            <AccordionItem
              id="optuna"
              title="Optuna 參數優化"
              badge={optunaConfig.enabled ? `已啟用 (${optunaConfig.n_trials} trials)` : "未啟用"}
            >
              <OptunaConfigPanel
                config={optunaConfig}
                onChange={handleOptunaConfigChange}
                disabled={isRunning}
              />
            </AccordionItem>
          </Accordion>

          <button
            type="button"
            disabled={isRunning || isOptimizing}
            onClick={handleRunTest}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-300"
          >
            {isRunning ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> 執行中...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4" /> 執行測試
              </>
            )}
          </button>

          {/* Optuna 優化按鈕 - 僅在啟用時顯示 */}
          {optunaConfig.enabled && (
            <button
              type="button"
              disabled={isOptimizing || isRunning}
              onClick={handleStartOptimization}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-purple-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-purple-500 disabled:cursor-not-allowed disabled:bg-purple-300"
            >
              {isOptimizing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> 優化中...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" /> 開始優化 ({optunaConfig.n_trials} trials)
                </>
              )}
            </button>
          )}

          {validationErrors.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
              <div className="mb-1 font-semibold">需先修正：</div>
              <ul className="list-inside list-disc space-y-1">
                {validationErrors.map((error) => (
                  <li key={error}>{error}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm uppercase tracking-wide text-slate-500">密度統計</p>
                <h2 className="text-2xl font-semibold text-slate-900">模型指標</h2>
              </div>
              <BarChart2 className="h-6 w-6 text-indigo-500" />
            </div>
            {/* 正例密度指標 */}
            <div className="mt-5">
              <div className="text-sm font-semibold text-slate-700 mb-3">正例密度指標</div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {densityMetrics?.positive_avg_density !== undefined && (
                  <StatMetricCard
                    label="正例近期密度"
                    value={densityMetrics.positive_avg_density}
                    std={densityMetrics.positive_std}
                    helper={`TO前${state.windowConfig.lookback_bars}根K線的策略信號密度`}
                    format="decimal"
                    colorCode={true}
                  />
                )}
                {densityMetrics?.positive_far_avg_density !== undefined && (
                  <StatMetricCard
                    label="正例遠期密度"
                    value={densityMetrics.positive_far_avg_density}
                    std={densityMetrics.positive_far_std}
                    helper={`TO-${state.windowConfig.far_lookback_bars}至TO-${state.windowConfig.lookback_bars + 1}根K線的背景密度`}
                    format="decimal"
                    colorCode={true}
                  />
                )}
                {densityMetrics?.positive_near_far_ratio !== undefined && (
                  <StatMetricCard
                    label="正例 Near/Far Ratio"
                    value={densityMetrics.positive_near_far_ratio}
                    std={densityMetrics.positive_ratio_std}
                    helper="近期密度 / 遠期密度"
                    format="ratio"
                    colorCode={true}
                  />
                )}
                {densityMetrics?.positive_sample_size !== undefined && (
                  <StatMetricCard
                    label="正例樣本數"
                    value={densityMetrics.positive_sample_size}
                    helper="有效的正例案例數量"
                    format="number"
                  />
                )}
              </div>
            </div>

            {/* 反例密度指標 */}
            <div className="mt-5">
              <div className="text-sm font-semibold text-slate-700 mb-3">反例密度指標</div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {densityMetrics?.negative_avg_density !== undefined && (
                  <StatMetricCard
                    label="反例近期密度"
                    value={densityMetrics.negative_avg_density}
                    std={densityMetrics.negative_std}
                    helper={`TO前${state.windowConfig.lookback_bars}根K線的策略信號密度`}
                    format="decimal"
                    colorCode={true}
                  />
                )}
                {densityMetrics?.negative_far_avg_density !== undefined && (
                  <StatMetricCard
                    label="反例遠期密度"
                    value={densityMetrics.negative_far_avg_density}
                    std={densityMetrics.negative_far_std}
                    helper={`TO-${state.windowConfig.far_lookback_bars}至TO-${state.windowConfig.lookback_bars + 1}根K線的背景密度`}
                    format="decimal"
                    colorCode={true}
                  />
                )}
                {densityMetrics?.negative_near_far_ratio !== undefined && (
                  <StatMetricCard
                    label="反例 Near/Far Ratio"
                    value={densityMetrics.negative_near_far_ratio}
                    std={densityMetrics.negative_ratio_std}
                    helper="近期密度 / 遠期密度"
                    format="ratio"
                    colorCode={true}
                  />
                )}
                {densityMetrics?.negative_sample_size !== undefined && (
                  <StatMetricCard
                    label="反例樣本數"
                    value={densityMetrics.negative_sample_size}
                    helper="有效的反例案例數量"
                    format="number"
                  />
                )}
              </div>
            </div>

            {/* 統計檢驗指標 */}
            <div className="mt-5">
              <div className="text-sm font-semibold text-slate-700 mb-3">統計檢驗指標</div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {densityMetrics?.separation !== undefined && (
                  <StatMetricCard
                    label="Density Separation"
                    value={densityMetrics.separation}
                    helper="正反例密度差異 (優化目標)"
                    format="decimal"
                    source="= 正例 Near 密度均值 − 反例 Near 密度均值"
                  />
                )}
                {densityMetrics?.ratio_separation !== undefined && (
                  <StatMetricCard
                    label="Ratio Separation"
                    value={densityMetrics.ratio_separation}
                    helper="正反例比率差異 (雙密度優化目標)"
                    format="decimal"
                    source="= 正例 Near/Far Ratio − 反例 Near/Far Ratio"
                  />
                )}
                {densityMetrics?.p_value !== undefined && (
                  <StatMetricCard
                    label="p-value"
                    value={densityMetrics.p_value}
                    helper="統計顯著性 (<0.05為顯著)"
                    format="decimal"
                    source="獨立 t-test: 正例 Near 密度 vs 反例 Near 密度"
                  />
                )}
                {densityMetrics?.cohens_d !== undefined && (
                  <StatMetricCard
                    label="Cohen's d"
                    value={densityMetrics.cohens_d}
                    helper="效果量 (>0.5為中等, >0.8為大效果)"
                    format="decimal"
                    source="= (正例均值 − 反例均值) / 合併標準差 (Near 密度)"
                  />
                )}
                {densityMetrics?.stability_cv !== undefined && (
                  <StatMetricCard
                    label="Stability CV"
                    value={densityMetrics.stability_cv}
                    helper="穩定性係數 (<0.3穩定, <0.5可接受)"
                    format="decimal"
                    source="= 正例每月 Near 密度均值的標準差 / 整體均值"
                  />
                )}
                {densityMetrics?.positive_ratio_cv !== undefined && (
                  <StatMetricCard
                    label="正例 Ratio 穩定性"
                    value={densityMetrics.positive_ratio_cv}
                    helper="正例 Near/Far Ratio 跨月穩定性 (<0.3穩定, <0.5可接受)"
                    format="decimal"
                    source="= 每月正例 Ratio 均值的標準差 / 整體 Ratio 均值"
                  />
                )}
                {densityMetrics?.separation_cv !== undefined && (
                  <StatMetricCard
                    label="Separation 穩定性"
                    value={densityMetrics.separation_cv}
                    helper="每月分離度穩定性 (<0.3穩定, <0.5可接受)"
                    format="decimal"
                    source="= 每月 Separation 的標準差 / |Separation 均值|"
                  />
                )}
              </div>
            </div>

            {/* 零值統計 (v1.1 新增) */}
            {(densityMetrics?.positive_far_zero_count !== undefined ||
              densityMetrics?.negative_far_zero_count !== undefined) && (
              <div className="mt-5">
                <div className="text-sm font-semibold text-slate-700 mb-3">零值統計 (透明化)</div>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                    <div className="text-sm font-medium text-gray-600 mb-1">正例 Near=0</div>
                    <div className="text-2xl font-bold text-gray-900">
                      {densityMetrics.positive_near_zero_count ?? 0}
                      <span className="text-base font-normal text-gray-500 ml-2">
                        ({((densityMetrics.positive_near_zero_ratio ?? 0) * 100).toFixed(1)}%)
                      </span>
                    </div>
                    <div className="text-xs text-gray-400 mt-2">策略信號完全未觸發的案例</div>
                  </div>
                  <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                    <div className="text-sm font-medium text-gray-600 mb-1">正例 Far=0</div>
                    <div className="text-2xl font-bold text-amber-600">
                      {densityMetrics.positive_far_zero_count ?? 0}
                      <span className="text-base font-normal text-gray-500 ml-2">
                        ({((densityMetrics.positive_far_zero_ratio ?? 0) * 100).toFixed(1)}%)
                      </span>
                    </div>
                    <div className="text-xs text-gray-400 mt-2">被排除於 ratio 統計的案例</div>
                  </div>
                  <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                    <div className="text-sm font-medium text-gray-600 mb-1">反例 Near=0</div>
                    <div className="text-2xl font-bold text-gray-900">
                      {densityMetrics.negative_near_zero_count ?? 0}
                      <span className="text-base font-normal text-gray-500 ml-2">
                        ({((densityMetrics.negative_near_zero_ratio ?? 0) * 100).toFixed(1)}%)
                      </span>
                    </div>
                    <div className="text-xs text-gray-400 mt-2">策略信號完全未觸發的案例</div>
                  </div>
                  <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                    <div className="text-sm font-medium text-gray-600 mb-1">反例 Far=0</div>
                    <div className="text-2xl font-bold text-amber-600">
                      {densityMetrics.negative_far_zero_count ?? 0}
                      <span className="text-base font-normal text-gray-500 ml-2">
                        ({((densityMetrics.negative_far_zero_ratio ?? 0) * 100).toFixed(1)}%)
                      </span>
                    </div>
                    <div className="text-xs text-gray-400 mt-2">被排除於 ratio 統計的案例</div>
                  </div>
                </div>
              </div>
            )}
            {!densityMetrics && (
              <p className="mt-4 rounded-lg bg-slate-100 px-3 py-2 text-xs text-slate-500">
                後端尚未回傳密度統計，或尚未執行測試。
              </p>
            )}
          </div>

          {/* Combined Boxplot 密度分佈視覺化 - 三種指標橫向對比 */}
          {densityMetrics &&
            positiveCaseIds.length > 0 &&
            negativeCaseIds.length > 0 &&
            Object.keys(caseLevelDensities).length > 0 && (
              <CombinedDensityBoxplot
                caseLevelDensities={caseLevelDensities}
                positiveCases={positiveCaseIds}
                negativeCases={negativeCaseIds}
                title="密度分佈對比 (Near / Far / Ratio)"
              />
            )}

          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm uppercase tracking-wide text-slate-500">執行概況</p>
                <h2 className="text-2xl font-semibold text-slate-900">測試結果</h2>
              </div>
              <Share2 className="h-6 w-6 text-indigo-500" />
            </div>
            {testResult ? (
              <div className="mt-6 grid gap-4 md:grid-cols-2">
                <SummaryItem label="回傳信號數" value={formatCount(testResult.signal_count)} />
                <SummaryItem label="K 線採樣" value={formatCount(testResult.total_bars)} />
                <SummaryItem
                  label="計算耗時"
                  value={
                    testResult.metadata?.calculation_time_ms !== undefined
                      ? `${testResult.metadata.calculation_time_ms.toFixed(1)} ms`
                      : "—"
                  }
                />
                <SummaryItem label="採樣狀態" value={testResult.is_sampled ? "已抽樣 (500)" : "完整樣本"} />
              </div>
            ) : (
              <div className="mt-6 rounded-lg border border-dashed border-slate-200 p-6 text-center text-sm text-slate-500">
                尚未執行測試，執行後會顯示密度統計與資料品質。
              </div>
            )}
            {qualitySummary && (
              <div className="mt-6 rounded-lg border border-slate-100 bg-slate-50 p-4 text-sm text-slate-600">
                <div className="font-semibold text-slate-800">資料品質</div>
                <div className="mt-2 grid gap-4 md:grid-cols-2">
                  <SummaryItem label="案例總數" value={qualitySummary.total_cases?.toString() ?? "—"} subtle />
                  <SummaryItem label="成功率" value={formatPercent(qualitySummary.success_rate)} subtle />
                </div>
                {qualitySummary.error_messages && qualitySummary.error_messages.length > 0 && (
                  <ul className="mt-3 list-inside list-disc text-xs text-amber-700">
                    {qualitySummary.error_messages.map((message) => (
                      <li key={message}>{message}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            {apiError && (
              <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                {apiError}
              </div>
            )}
          </div>
        </div>
      </div>

      {isTemplatePanelOpen && (
        <TemplatePanel
          templates={templates}
          onClose={() => setTemplatePanelOpen(false)}
          onLoad={handleLoadTemplate}
          onDelete={handleDeleteTemplate}
        />
      )}
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: string;
  helper?: string;
}

function MetricCard({ label, value, helper }: MetricCardProps) {
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-slate-900">{value}</p>
      {helper && <p className="text-xs text-slate-500">{helper}</p>}
    </div>
  );
}

interface SummaryItemProps {
  label: string;
  value: string;
  subtle?: boolean;
}

function SummaryItem({ label, value, subtle = false }: SummaryItemProps) {
  return (
    <div className={`rounded-lg p-3 ${subtle ? "bg-white" : "bg-slate-50"}`}>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-lg font-semibold text-slate-900">{value}</p>
    </div>
  );
}

interface TemplatePanelProps {
  templates: StrategyTemplatePayload[];
  onClose: () => void;
  onLoad: (template: StrategyTemplatePayload) => void;
  onDelete: (templateId: string) => void;
}

function TemplatePanel({ templates, onClose, onLoad, onDelete }: TemplatePanelProps) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-end bg-black/40">
      <div className="h-full w-full max-w-md overflow-y-auto border-l border-slate-200 bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Templates</p>
            <h3 className="text-lg font-semibold text-slate-900">策略範本管理</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-slate-200 p-2 text-slate-500 transition hover:bg-slate-50"
          >
            ✕
          </button>
        </div>
        <div className="space-y-3 px-5 py-4">
          {templates.length === 0 ? (
            <p className="rounded-lg border border-dashed border-slate-200 p-4 text-center text-sm text-slate-500">
              尚未建立任何範本，保存後即可在此快速載入。
            </p>
          ) : (
            templates.map((template) => (
              <div key={template.id} className="rounded-lg border border-slate-200 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-base font-semibold text-slate-900">{template.name}</p>
                    {template.description && (
                      <p className="text-xs text-slate-500">{template.description}</p>
                    )}
                    <p className="mt-1 text-[11px] text-slate-400">更新於 {new Date(template.updatedAt).toLocaleString()}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => onDelete(template.id)}
                    className="text-xs text-rose-500 hover:underline"
                  >
                    移除
                  </button>
                </div>
                <div className="mt-3 flex gap-2">
                  <button
                    type="button"
                    onClick={() => onLoad(template)}
                    className="flex-1 rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white"
                  >
                    載入此範本
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default function StrategyTestPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><div className="text-gray-500">Loading...</div></div>}>
      <StrategyTestPageContent />
    </Suspense>
  );
}

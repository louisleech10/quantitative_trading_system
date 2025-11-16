"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "react-hot-toast";
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
  Trash2,
} from "lucide-react";
import { Accordion } from "@/components/ui/Accordion";
import { AccordionItem } from "@/components/ui/AccordionItem";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Select, type SelectOption } from "@/components/ui/Select";
import { NumberInput } from "@/components/ui/NumberInput";
import { DateRangePicker } from "@/components/ui/DateRangePicker";
import WindowConfigPanel, {
  type TrainingWindowConfig,
} from "@/components/strategy/WindowConfigPanel";
import {
  useStrategyConfig,
  type StrategyTemplatePayload,
} from "@/hooks/useStrategyConfig";

interface SignalPoint {
  timestamp: number;
  indicator_values: Record<string, number>;
  signal_density?: number;
}

interface DensityMetrics {
  positive_avg_density?: number;
  negative_avg_density?: number;
  near_far_ratio?: number;
  separation?: number;
  ratio_separation?: number;
  p_value?: number;
  cohens_d?: number;
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

export default function StrategyTestPage() {
  const router = useRouter();
  const {
    state,
    setField,
    reset,
    saveTemplate,
    loadTemplate,
    listTemplates,
    deleteTemplate,
    syncToUrl,
  } = useStrategyConfig();

  const [isRunning, setIsRunning] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<ChartSignalResponse | null>(null);
  const [templates, setTemplates] = useState<StrategyTemplatePayload[]>([]);
  const [isTemplatePanelOpen, setTemplatePanelOpen] = useState(false);

  useEffect(() => {
    if (isTemplatePanelOpen) {
      setTemplates(listTemplates());
    }
  }, [isTemplatePanelOpen, listTemplates]);

  const validationErrors = useMemo(() => {
    const errors: string[] = [];
    const { indicatorParams, dateRange, dataSources } = state;
    const short = indicatorParams.ema_short;
    const mid = indicatorParams.ema_mid;
    const long = indicatorParams.ema_long;

    if (!(short < mid && mid < long)) {
      errors.push("請維持 EMA 週期為 短 < 中 < 長");
    }

    if (!dateRange.start || !dateRange.end) {
      errors.push("請完整設定時間範圍");
    } else if (dateRange.start > dateRange.end) {
      errors.push("開始日期不可晚於結束日期");
    }

    if (dataSources.length === 0) {
      errors.push("至少選擇一個數據源");
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

      const requestBody = {
        symbol: state.symbol,
        timeframe: state.timeframe,
        start_time: startTime,
        end_time: endTime,
        strategy_config: {
          data_source: state.dataSources[0] ?? "close",
          data_sources: state.dataSources,
          indicator_type: state.indicatorType,
          strategy_logic: state.strategyLogic,
          params: state.indicatorParams,
          training_window: state.windowConfig,
          clustering_weight: state.clusteringWeight,
        },
      };

      const response = await fetch(`${API_BASE_URL}/api/v1/chart/signals`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
      setTestResult(data);
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
      setTestResult(null);
      setApiError(null);
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
            <AccordionItem id="basic" title="基本配置" badge={`${state.dataSources.length} 個來源`}>
              <div className="space-y-4">
                <MultiSelect
                  label="數據來源"
                  options={DATA_SOURCE_OPTIONS}
                  value={state.dataSources}
                  onChange={(options) => setField("dataSources", options)}
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
              </div>
            </AccordionItem>

            <AccordionItem id="indicator" title="指標參數" badge="EMA">
              <div className="grid grid-cols-1 gap-4">
                <NumberInput
                  label="EMA Short"
                  value={state.indicatorParams.ema_short}
                  min={3}
                  max={50}
                  onChange={(value) => handleIndicatorParamChange("ema_short", value)}
                />
                <NumberInput
                  label="EMA Mid"
                  value={state.indicatorParams.ema_mid}
                  min={state.indicatorParams.ema_short + 1}
                  max={150}
                  onChange={(value) => handleIndicatorParamChange("ema_mid", value)}
                />
                <NumberInput
                  label="EMA Long"
                  value={state.indicatorParams.ema_long}
                  min={state.indicatorParams.ema_mid + 1}
                  max={400}
                  onChange={(value) => handleIndicatorParamChange("ema_long", value)}
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
          </Accordion>

          <button
            type="button"
            disabled={isRunning}
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
            <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <MetricCard label="正例密度" value={formatPercent(densityMetrics?.positive_avg_density)} helper="正例平均 signal density" />
              <MetricCard label="反例密度" value={formatPercent(densityMetrics?.negative_avg_density)} helper="反例平均 signal density" />
              <MetricCard label="Near/Far Ratio" value={formatNumber(densityMetrics?.near_far_ratio)} helper="正例窗口密度比" />
              <MetricCard label="Separation" value={formatNumber(densityMetrics?.separation)} helper="正反差值" />
              <MetricCard label="Ratio Separation" value={formatNumber(densityMetrics?.ratio_separation)} helper="ratio 差值" />
              <MetricCard label="p-value" value={densityMetrics?.p_value ? densityMetrics.p_value.toExponential(2) : "—"} helper="統計顯著性" />
              <MetricCard label="Cohen's d" value={formatNumber(densityMetrics?.cohens_d)} helper="效果量" />
            </div>
            {!densityMetrics && (
              <p className="mt-4 rounded-lg bg-slate-100 px-3 py-2 text-xs text-slate-500">
                後端尚未回傳密度統計，或尚未執行測試。
              </p>
            )}
          </div>

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

"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  LineChart,
  Loader2,
  RefreshCcw,
} from "lucide-react";
import {
  useStrategyConfig,
  type HydrationSource,
} from "@/hooks/useStrategyConfig";
import {
  TradingChartWithSignals,
  type IndicatorLineSeries,
  type WindowOverlayRange,
} from "@/components/charts/TradingChartWithSignals";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SignalPoint {
  timestamp: number;
  indicator_values: Record<string, number>;
  signal_density?: number;
}

interface ChartSignalResponse {
  signal_points: SignalPoint[];
  total_bars: number;
  signal_count: number;
  signal_density: number;
  is_sampled: boolean;
  strategy_name: string;
}

interface ChartKline {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  taker_buy_volume?: number;
  taker_ratio?: number;
  quote_volume?: number;
  number_of_trades?: number;
}

interface ChartDataPayload {
  case_timestamp: number;
  klines: ChartKline[];
  center_index?: number;
  to_index?: number;
  tc_index?: number;
  case_bars?: number;
  aligned_case_timestamp?: number;
  aligned_tc_timestamp?: number;
  metadata: {
    symbol: string;
    timeframe: string;
    total_bars: number;
    case_timeframe?: string;
    time_range: {
      start: number;
      end: number;
    };
  };
}

interface ChartDataResponse {
  success: boolean;
  data?: ChartDataPayload;
  error?: {
    code: string;
    message: string;
  };
}

interface ChartDataRequestState {
  queryString: string | null;
  warning: string | null;
  error: string | null;
  info?: {
    requestedBars: number;
    lookbackBars: number;
    forwardBars: number;
    startSec: number;
    endSec: number;
  };
}

const INDICATOR_COLORS: Record<string, string> = {
  ema_short: "#10b981",
  ema_mid: "#3b82f6",
  ema_long: "#a855f7",
};

const timeframeToSeconds = (timeframe: string): number | null => {
  const match = timeframe.match(/^(\d+)([mhd])$/i);
  if (!match) return null;
  const value = Number(match[1]);
  const unit = match[2].toLowerCase();
  if (Number.isNaN(value) || value <= 0) return null;
  switch (unit) {
    case "m":
      return value * 60;
    case "h":
      return value * 60 * 60;
    case "d":
      return value * 24 * 60 * 60;
    default:
      return null;
  }
};

const hydrationSourceLabel: Record<HydrationSource, string> = {
  url: "URL 參數",
  storage: "LocalStorage",
  default: "預設值",
};

const formatPercent = (value?: number) => {
  if (value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(2)}%`;
};

const formatNumber = (value?: number, digits = 2) => {
  if (value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
};

const formatDate = (date?: string) => {
  if (!date) return "—";
  return new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10);
};

const formatTimestampDate = (timestamp?: number) => {
  if (typeof timestamp !== "number") return "—";
  return new Date(timestamp * 1000).toISOString().slice(0, 10);
};

const parseDateToTimestamp = (date?: string): number | null => {
  if (!date) return null;
  const timestamp = Date.parse(`${date}T00:00:00Z`);
  return Number.isNaN(timestamp) ? null : timestamp;
};

const calculateEMA = (klines: ChartKline[], period: number): Array<{ time: number; value: number }> => {
  if (!period || klines.length === 0) return [];
  const multiplier = 2 / (period + 1);
  let ema = klines[0].close;
  return klines.map((kline, index) => {
    if (index === 0) {
      ema = kline.close;
    } else {
      ema = (kline.close - ema) * multiplier + ema;
    }
    return { time: kline.timestamp, value: ema };
  });
};

export default function ChartsPage() {
  const searchParams = useSearchParams();
  const queryString = searchParams.toString();
  const router = useRouter();

  const {
    state,
    hydrateFromUrl,
    hydrateFromCache,
    lastHydrationSource,
    isHydrated,
    lastSyncedQuery,
    syncToUrl,
  } = useStrategyConfig();

  const [hydrationSource, setHydrationSource] = useState<HydrationSource>(
    lastHydrationSource ?? "default"
  );
  const [hydrationError, setHydrationError] = useState<string | null>(null);

  const [loadingSignals, setLoadingSignals] = useState(false);
  const [signalError, setSignalError] = useState<string | null>(null);
  const [signalResponse, setSignalResponse] = useState<ChartSignalResponse | null>(
    null
  );
  const [loadingChartData, setLoadingChartData] = useState(false);
  const [chartDataError, setChartDataError] = useState<string | null>(null);
  const [chartData, setChartData] = useState<ChartDataPayload | null>(null);
  const [indicatorVisibility, setIndicatorVisibility] = useState<Record<string, boolean>>({
    ema_short: true,
    ema_mid: true,
    ema_long: true,
  });
  const [showWindowOverlay, setShowWindowOverlay] = useState(true);
  const [showSignalMarkers, setShowSignalMarkers] = useState(true);
  const [refreshToken, setRefreshToken] = useState(0);

  const handleToggleSeries = (seriesId: string) => {
    setIndicatorVisibility((prev) => ({
      ...prev,
      [seriesId]: !prev[seriesId],
    }));
  };

  useEffect(() => {
    if (queryString) {
      const success = hydrateFromUrl(queryString);
      if (success) {
        setHydrationSource("url");
        setHydrationError(null);
        return;
      }
      if (isHydrated) {
        setHydrationSource(lastHydrationSource ?? "storage");
        setHydrationError("URL state 無效，改用最近一次配置");
        return;
      }
      const restoredFromCache = hydrateFromCache();
      if (restoredFromCache) {
        setHydrationSource("storage");
        setHydrationError("URL state 無效，已載入最近一次配置");
        return;
      }
      setHydrationSource("default");
      setHydrationError("無法從 URL 或歷史設定恢復，請返回策略測試頁重新設定");
      return;
    }

    if (isHydrated) {
      setHydrationSource(lastHydrationSource ?? "storage");
      setHydrationError(null);
      return;
    }

    const restored = hydrateFromCache();
    if (restored) {
      setHydrationSource("storage");
      setHydrationError(null);
      return;
    }

    setHydrationSource("default");
    setHydrationError("尚未設定策略，請先返回策略測試頁");
  }, [
    queryString,
    hydrateFromUrl,
    hydrateFromCache,
    isHydrated,
    lastHydrationSource,
  ]);

  const startTimestamp = useMemo(
    () => parseDateToTimestamp(state.dateRange.start),
    [state.dateRange.start]
  );
  const endTimestamp = useMemo(
    () => parseDateToTimestamp(state.dateRange.end),
    [state.dateRange.end]
  );

  const chartRequestPayload = useMemo(() => {
    if (
      startTimestamp === null ||
      endTimestamp === null ||
      startTimestamp >= endTimestamp
    ) {
      return null;
    }

    return {
      symbol: state.symbol,
      timeframe: state.timeframe,
      start_time: startTimestamp,
      end_time: endTimestamp,
      strategy_config: {
        data_source: state.dataSources[0] ?? "close",
        data_sources: state.dataSources,
        indicator_type: state.indicatorType,
        strategy_logic: state.strategyLogic,
        params: state.indicatorParams,
      },
    };
  }, [state, startTimestamp, endTimestamp]);

  const chartDataRequest = useMemo<ChartDataRequestState>(() => {
    if (startTimestamp === null || endTimestamp === null) {
      return {
        queryString: null,
        warning: null,
        error: "請先完成時間範圍設定",
      };
    }

    if (startTimestamp >= endTimestamp) {
      return {
        queryString: null,
        warning: null,
        error: "時間範圍無效，請重新選擇",
      };
    }

    const timeframeSeconds = timeframeToSeconds(state.timeframe);
    if (!timeframeSeconds) {
      return {
        queryString: null,
        warning: null,
        error: `目前不支援 ${state.timeframe} 時間框架`,
      };
    }

    const startSec = Math.floor(startTimestamp / 1000);
    const endSec = Math.floor(endTimestamp / 1000);
    const totalSeconds = endSec - startSec;
    const requestedBars = Math.max(1, Math.ceil(totalSeconds / timeframeSeconds));
    const requiredLookback = Math.max(
      requestedBars,
      state.windowConfig.far_lookback_bars ?? 0,
      state.windowConfig.lookback_bars ?? 0
    );
    const lookbackBars = Math.min(requiredLookback, 1000);
    const forwardBarsRaw = state.windowConfig.lookforward_bars ?? 0;
    const forwardBars = Math.min(Math.max(forwardBarsRaw, 0), 1000);

    const params = new URLSearchParams({
      symbol: state.symbol,
      timeframe: state.timeframe,
      case_timestamp: String(endSec),
      case_timeframe: state.timeframe,
      lookback_bars: String(lookbackBars),
      forward_bars: String(forwardBars),
    });

    return {
      queryString: params.toString(),
      warning:
        requestedBars > 1000
          ? `時間範圍過長，僅顯示最近 ${lookbackBars} 根 K 線`
          : null,
      error: null,
      info: {
        requestedBars,
        lookbackBars,
        forwardBars,
        startSec,
        endSec,
      },
    };
  }, [
    startTimestamp,
    endTimestamp,
    state.symbol,
    state.timeframe,
    state.windowConfig.far_lookback_bars,
    state.windowConfig.lookback_bars,
    state.windowConfig.lookforward_bars,
  ]);

  const setupBlockingMessage = useMemo(() => {
    if (chartDataRequest.error) {
      return chartDataRequest.error;
    }
    if (!chartRequestPayload) {
      return "尚未完成策略或時間範圍設定，請返回策略測試頁。";
    }
    if (
      hydrationError &&
      (hydrationError.includes("重新設定") ||
        hydrationError.includes("請先返回"))
    ) {
      return hydrationError;
    }
    return null;
  }, [chartDataRequest.error, chartRequestPayload, hydrationError]);

  const handleRetryFetch = () => {
    if (setupBlockingMessage) return;
    setRefreshToken((token) => token + 1);
  };

  useEffect(() => {
    if (!chartRequestPayload) {
      setSignalResponse(null);
      setSignalError(null);
      return;
    }

    let cancelled = false;

    const fetchSignals = async () => {
      try {
        setLoadingSignals(true);
        setSignalError(null);

        const response = await fetch(`${API_BASE_URL}/api/v1/chart/signals`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(chartRequestPayload),
        });

        if (!response.ok) {
          const message = await response.text();
          throw new Error(message || "API 請求失敗");
        }

        const data: ChartSignalResponse = await response.json();
        if (!cancelled) {
          setSignalResponse(data);
        }
      } catch (error) {
        if (!cancelled) {
          const message =
            error instanceof Error ? error.message : "載入圖表信號失敗";
          setSignalError(message);
        }
      } finally {
        if (!cancelled) {
          setLoadingSignals(false);
        }
      }
    };

    fetchSignals();

    return () => {
      cancelled = true;
    };
  }, [chartRequestPayload, refreshToken]);

  useEffect(() => {
    if (!chartDataRequest.queryString) {
      setChartData(null);
      setChartDataError(
        chartDataRequest.error ?? "請先完成時間範圍與策略參數設定"
      );
      return;
    }

    let cancelled = false;

    const fetchChartData = async () => {
      try {
        setLoadingChartData(true);
        setChartDataError(null);

        const response = await fetch(
          `${API_BASE_URL}/api/v1/chart/data?${chartDataRequest.queryString}`
        );

        if (!response.ok) {
          const message = await response.text();
          throw new Error(message || "API 請求失敗");
        }

        const data: ChartDataResponse = await response.json();
        if (!data.success || !data.data) {
          throw new Error(data.error?.message || "載入K線數據失敗");
        }

        if (!cancelled) {
          setChartData(data.data);
        }
      } catch (error) {
        if (!cancelled) {
          setChartData(null);
          const message =
            error instanceof Error ? error.message : "載入K線數據失敗";
          setChartDataError(message);
        }
      } finally {
        if (!cancelled) {
          setLoadingChartData(false);
        }
      }
    };

    fetchChartData();

    return () => {
      cancelled = true;
    };
  }, [chartDataRequest, refreshToken]);

  const normalizedSignalPoints = useMemo(() => {
    if (!signalResponse) return [] as SignalPoint[];
    return signalResponse.signal_points
      .map((point) => ({
        ...point,
        timestamp: Math.floor(point.timestamp / 1000),
      }))
      .filter((point) => {
        if (!chartData) return true;
        const { start, end } = chartData.metadata.time_range;
        return point.timestamp >= start && point.timestamp <= end;
      });
  }, [signalResponse, chartData]);

  const indicatorSeries = useMemo<IndicatorLineSeries[]>(() => {
    if (!chartData || chartData.klines.length === 0) return [];
    const { ema_short, ema_mid, ema_long } = state.indicatorParams;
    const periods = [
      { key: "ema_short", period: ema_short, label: `EMA Short (${ema_short})` },
      { key: "ema_mid", period: ema_mid, label: `EMA Mid (${ema_mid})` },
      { key: "ema_long", period: ema_long, label: `EMA Long (${ema_long})` },
    ];
    return periods
      .filter((item) => Number.isFinite(item.period) && item.period > 0)
      .map((item) => ({
        id: item.key,
        label: item.label,
        color: INDICATOR_COLORS[item.key] ?? "#64748b",
        data: calculateEMA(chartData.klines, item.period),
      }));
  }, [chartData, state.indicatorParams]);

  const windowOverlays = useMemo<WindowOverlayRange[]>(() => {
    if (!chartData || chartData.klines.length === 0) return [];
    const toIndex = typeof chartData.to_index === "number" ? chartData.to_index : null;
    if (toIndex === null) return [];
    const nearBars = state.windowConfig.lookback_bars ?? 0;
    const farLookback = state.windowConfig.far_lookback_bars ?? 0;
    if (nearBars <= 0 && farLookback <= nearBars) return [];

    const clampIndex = (index: number) =>
      Math.min(Math.max(index, 0), chartData.klines.length - 1);
    const overlays: WindowOverlayRange[] = [];

    if (nearBars > 0) {
      const startIdx = clampIndex(toIndex - nearBars);
      const endIdx = clampIndex(Math.max(toIndex - 1, startIdx));
      if (startIdx <= endIdx) {
        overlays.push({
          type: "near",
          startTimestamp: chartData.klines[startIdx].timestamp,
          endTimestamp: chartData.klines[endIdx].timestamp,
        });
      }
    }

    if (farLookback > nearBars) {
      const farStartIdx = clampIndex(toIndex - farLookback);
      const farEndIdx = clampIndex(Math.max(toIndex - nearBars - 1, farStartIdx));
      if (farStartIdx <= farEndIdx) {
        overlays.push({
          type: "far",
          startTimestamp: chartData.klines[farStartIdx].timestamp,
          endTimestamp: chartData.klines[farEndIdx].timestamp,
        });
      }
    }

    return overlays;
  }, [chartData, state.windowConfig]);

  const activeIndicatorSeries = useMemo<IndicatorLineSeries[]>(
    () =>
      indicatorSeries.filter(
        (series) => indicatorVisibility[series.id] !== false
      ),
    [indicatorSeries, indicatorVisibility]
  );

  const handleBack = () => {
    const query = state.syncToUrl
      ? lastSyncedQuery
        ? `?${lastSyncedQuery}`
        : syncToUrl() ?? ""
      : "";
    router.push(`/strategy-test${query ?? ""}`);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-6 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex items-center gap-3 text-sm text-slate-500">
              <button
                onClick={handleBack}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-100"
              >
                <ArrowLeft className="h-3.5 w-3.5" /> 返回策略測試
              </button>
              <span className="flex items-center gap-1 text-indigo-600">
                <LineChart className="h-4 w-4" /> /charts
              </span>
            </div>
            <h1 className="mt-3 text-2xl font-semibold text-slate-900">
              雙窗口密度圖表
            </h1>
            <p className="text-sm text-slate-500">
              已載入 {hydrationSourceLabel[hydrationSource]} 的策略設定
            </p>
            {hydrationError && (
              <p className="mt-1 text-xs text-amber-600">{hydrationError}</p>
            )}
          </div>
          <div className="flex flex-wrap gap-3">
            <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600">
              Hydration: {hydrationSourceLabel[hydrationSource]}
            </span>
            <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600">
              時間範圍: {formatDate(state.dateRange.start)} → {" "}
              {formatDate(state.dateRange.end)}
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6">
        {setupBlockingMessage && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              <span>{setupBlockingMessage}</span>
            </div>
            <button
              type="button"
              onClick={handleBack}
              className="inline-flex items-center gap-2 rounded-md border border-amber-300 bg-white px-3 py-1 text-xs font-semibold text-amber-700 transition hover:bg-amber-100"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> 返回策略測試
            </button>
          </div>
        )}
        <section className="grid gap-4 lg:grid-cols-[360px,1fr]">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              策略概要
            </h2>
            <dl className="mt-4 space-y-3 text-sm text-slate-600">
              <div className="flex items-center justify-between">
                <dt>策略名稱</dt>
                <dd className="font-medium text-slate-900">
                  {state.strategyName || "未命名策略"}
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt>交易對 / 週期</dt>
                <dd className="font-medium text-slate-900">
                  {state.symbol} ・ {state.timeframe}
                </dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-400">
                  Data Sources
                </dt>
                <dd className="mt-1 flex flex-wrap gap-1">
                  {state.dataSources.map((source) => (
                    <span
                      key={source}
                      className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700"
                    >
                      {source}
                    </span>
                  ))}
                </dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-400">
                  EMA 參數
                </dt>
                <dd className="mt-1 grid grid-cols-3 gap-2 text-center text-sm">
                  <div className="rounded-lg bg-slate-50 px-2 py-1">
                    <p className="text-[11px] uppercase text-slate-500">短</p>
                    <p className="font-semibold text-slate-900">
                      {state.indicatorParams.ema_short}
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-50 px-2 py-1">
                    <p className="text-[11px] uppercase text-slate-500">中</p>
                    <p className="font-semibold text-slate-900">
                      {state.indicatorParams.ema_mid}
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-50 px-2 py-1">
                    <p className="text-[11px] uppercase text-slate-500">長</p>
                    <p className="font-semibold text-slate-900">
                      {state.indicatorParams.ema_long}
                    </p>
                  </div>
                </dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-400">
                  窗口設定
                </dt>
                <dd className="mt-1 grid grid-cols-2 gap-2 text-center text-sm">
                  <div className="rounded-lg bg-slate-50 px-2 py-1">
                    <p className="text-[11px] uppercase text-slate-500">
                      Near Lookback
                    </p>
                    <p className="font-semibold text-slate-900">
                      {state.windowConfig.lookback_bars}
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-50 px-2 py-1">
                    <p className="text-[11px] uppercase text-slate-500">
                      Far Lookback
                    </p>
                    <p className="font-semibold text-slate-900">
                      {state.windowConfig.far_lookback_bars ?? "—"}
                    </p>
                  </div>
                </dd>
              </div>
            </dl>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm uppercase tracking-wide text-slate-500">
                  圖表信號狀態
                </p>
                <h2 className="text-2xl font-semibold text-slate-900">
                  {loadingSignals ? "載入中" : signalResponse ? "資料就緒" : "等待配置"}
                </h2>
              </div>
              <RefreshCcw
                className={`h-5 w-5 ${loadingSignals ? "animate-spin text-indigo-500" : "text-slate-400"}`}
              />
            </div>

            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              <MetricCard
                label="信號數"
                value={formatNumber(signalResponse?.signal_count, 0)}
                helper="符合策略的 K 線"
              />
              <MetricCard
                label="密度"
                value={formatPercent(signalResponse?.signal_density)}
                helper="signal_count / total"
              />
              <MetricCard
                label="採樣"
                value={signalResponse?.is_sampled ? "已抽樣" : "完整樣本"}
                helper={signalResponse ? `${signalResponse.total_bars} 根 K 線` : "—"}
              />
            </div>

            {signalError && (
              <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4" />
                    <span>{signalError}</span>
                  </div>
                  <button
                    type="button"
                    onClick={handleRetryFetch}
                    disabled={Boolean(setupBlockingMessage)}
                    className="inline-flex items-center gap-2 rounded-md border border-rose-300 bg-white px-3 py-1 text-xs font-semibold text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <RefreshCcw className="h-3.5 w-3.5" /> 重新載入
                  </button>
                </div>
              </div>
            )}

            {loadingSignals && (
              <div className="mt-4 flex items-center gap-3 text-sm text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                取得圖表信號資料中...
              </div>
            )}

            {!loadingSignals && signalResponse && (
              <div className="mt-4 rounded-lg border border-slate-100 bg-slate-50 p-4 text-sm text-slate-600">
                <div className="flex items-center gap-2 text-slate-700">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  已取得 {signalResponse.signal_points.length} 個信號點
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  信號資料已就緒，若圖表未顯示請確認 K 線資料是否載入成功。
                </p>
              </div>
            )}

            {chartData && !loadingChartData && (
              <div className="mt-4 rounded-lg border border-slate-100 bg-slate-50 p-4 text-sm text-slate-600">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-700">K 線資料</span>
                  <span className="font-medium text-slate-900">
                    {chartData.metadata.total_bars.toLocaleString()} 根
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {formatTimestampDate(chartData.metadata.time_range.start)} → {" "}
                  {formatTimestampDate(chartData.metadata.time_range.end)}
                </p>
              </div>
            )}

            {chartDataRequest.warning && (
              <p className="mt-3 text-xs text-amber-600">
                {chartDataRequest.warning}
              </p>
            )}

            {chartDataError && (
              <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4" />
                    <span>{chartDataError}</span>
                  </div>
                  <button
                    type="button"
                    onClick={handleRetryFetch}
                    disabled={Boolean(setupBlockingMessage)}
                    className="inline-flex items-center gap-2 rounded-md border border-rose-300 bg-white px-3 py-1 text-xs font-semibold text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <RefreshCcw className="h-3.5 w-3.5" /> 重新載入
                  </button>
                </div>
              </div>
            )}

            {loadingChartData && (
              <div className="mt-4 flex items-center gap-3 text-sm text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                載入 K 線資料中...
              </div>
            )}
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
            {indicatorSeries.length > 0 && (
              <span className="font-semibold text-slate-800">指標顯示：</span>
            )}
            {indicatorSeries.map((series) => {
              const isActive = indicatorVisibility[series.id] !== false;
              return (
                <button
                  key={series.id}
                  type="button"
                  onClick={() => handleToggleSeries(series.id)}
                  className={`rounded-full border px-3 py-1 font-medium transition ${
                    isActive
                      ? "border-indigo-200 bg-indigo-50 text-indigo-700"
                      : "border-slate-200 text-slate-500"
                  }`}
                >
                  <span className="inline-flex items-center gap-1">
                    <span
                      className="inline-block h-2 w-2 rounded-full"
                      style={{ backgroundColor: series.color }}
                    />
                    {series.label}
                  </span>
                </button>
              );
            })}
            <button
              type="button"
              onClick={() => setShowWindowOverlay((prev) => !prev)}
              className={`rounded-full border px-3 py-1 font-medium transition ${
                showWindowOverlay
                  ? "border-purple-200 bg-purple-50 text-purple-700"
                  : "border-slate-200 text-slate-500"
              }`}
            >
              近/遠窗口遮罩
            </button>
            <button
              type="button"
              onClick={() => setShowSignalMarkers((prev) => !prev)}
              className={`rounded-full border px-3 py-1 font-medium transition ${
                showSignalMarkers
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-slate-200 text-slate-500"
              }`}
            >
              策略信號
            </button>
          </div>
          {chartData && chartData.klines.length > 0 ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900">
                    Price / Volume / Taker Ratio 多 Pane 圖表
                  </p>
                  <p className="text-xs text-slate-500">
                    {formatTimestampDate(chartData.metadata.time_range.start)} → {" "}
                    {formatTimestampDate(chartData.metadata.time_range.end)} ・ {chartData.metadata.total_bars} 根 K 線
                  </p>
                </div>
                <div className="text-xs text-slate-500">
                  {normalizedSignalPoints.length.toLocaleString()} 策略信號
                </div>
              </div>

              {chartDataRequest.warning && (
                <p className="text-xs text-amber-600">
                  {chartDataRequest.warning}
                </p>
              )}

              <div className="relative">
                {(loadingChartData || loadingSignals) && (
                  <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/70">
                    <Loader2 className="h-5 w-5 animate-spin text-slate-500" />
                  </div>
                )}

                <TradingChartWithSignals
                  symbol={state.symbol}
                  timeframe={state.timeframe}
                  klines={chartData.klines}
                  signalPoints={normalizedSignalPoints}
                  toTimestamp={
                    chartData.aligned_case_timestamp ?? chartData.case_timestamp
                  }
                  tcTimestamp={chartData.aligned_tc_timestamp}
                  totalHeight={780}
                  showSignalMarkers={
                    showSignalMarkers && normalizedSignalPoints.length > 0
                  }
                  indicatorSeries={activeIndicatorSeries}
                  windowOverlays={showWindowOverlay ? windowOverlays : []}
                />
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-sm text-slate-500">
              {chartDataError ? (
                <>
                  <AlertCircle className="h-6 w-6 text-rose-500" />
                  <p className="text-rose-600">{chartDataError}</p>
                </>
              ) : (
                <>
                  <LineChart className="h-6 w-6 text-slate-300" />
                  <p>請先設定合法的時間範圍並等待圖表資料載入</p>
                </>
              )}
            </div>
          )}
        </section>
      </main>
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
    <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-4 text-left">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-slate-900">{value}</p>
      {helper && <p className="text-xs text-slate-500">{helper}</p>}
    </div>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
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
} from "@/components/charts/TradingChartWithSignals";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ============ 接口定義 ============

interface CaseRecord {
  case_id: string;
  symbol: string;
  timeframe: string;
  timestamp: number;
  positive_case: boolean;
}

interface CaseListResponse {
  total: number;
  cases: CaseRecord[];
  positive_count: number;
  negative_count: number;
  symbols: string[];
  timeframes: string[];
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
}

interface ChartDataPayload {
  case_timestamp: number;
  klines: ChartKline[];
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
    time_range: { start: number; end: number };
  };
}

interface ChartDataResponse {
  success: boolean;
  data?: ChartDataPayload;
  error?: { code: string; message: string };
}

type CaseTypeFilter = "all" | "positive" | "negative";

// ============ 輔助函數 ============

const INDICATOR_COLORS: Record<string, string> = {
  ema_short: "#10b981",
  ema_mid: "#3b82f6",
  ema_long: "#a855f7",
};

const hydrationSourceLabel: Record<HydrationSource, string> = {
  url: "URL 參數",
  storage: "LocalStorage",
  default: "預設值",
};

const formatTimestamp = (timestamp: number): string => {
  const date = new Date(timestamp * 1000);
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  const hours = String(date.getUTCHours()).padStart(2, "0");
  const minutes = String(date.getUTCMinutes()).padStart(2, "0");
  return `${year}-${month}-${day} ${hours}:${minutes}`;
};

const formatTimestampDate = (timestamp?: number) => {
  if (typeof timestamp !== "number") return "—";
  return new Date(timestamp * 1000).toISOString().slice(0, 10);
};

const calculateEMA = (
  klines: ChartKline[],
  period: number
): Array<{ time: number; value: number }> => {
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

const AVAILABLE_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"];

// ============ 主組件 ============

export default function ChartsPage() {
  const router = useRouter();

  // 策略配置 Hook (用於 EMA 參數和窗口設定)
  const { state, hydrateFromCache, lastHydrationSource, isHydrated, lastSyncedQuery, syncToUrl } = useStrategyConfig();

  const [hydrationSource, setHydrationSource] = useState<HydrationSource>(lastHydrationSource ?? "default");

  // ============ 案例選擇狀態 ============
  const [loadingCases, setLoadingCases] = useState(true);
  const [caseListError, setCaseListError] = useState<string | null>(null);
  const [caseList, setCaseList] = useState<CaseRecord[]>([]);
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);

  const [selectedSymbol, setSelectedSymbol] = useState<string>("");
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>("1h");
  const [caseTypeFilter, setCaseTypeFilter] = useState<CaseTypeFilter>("all");
  const [selectedTimestamp, setSelectedTimestamp] = useState<number | null>(null);
  const [currentCase, setCurrentCase] = useState<CaseRecord | null>(null);

  // ============ 圖表數據狀態 ============
  const [loadingChartData, setLoadingChartData] = useState(false);
  const [chartDataError, setChartDataError] = useState<string | null>(null);
  const [chartData, setChartData] = useState<ChartDataPayload | null>(null);
  const [alignedCaseTimestamp, setAlignedCaseTimestamp] = useState<number | null>(null);
  const [alignedTcTimestamp, setAlignedTcTimestamp] = useState<number | null>(null);

  // ============ UI 控制狀態 ============
  const [indicatorVisibility, setIndicatorVisibility] = useState<Record<string, boolean>>({
    ema_short: true,
    ema_mid: true,
    ema_long: true,
  });
  const [refreshToken, setRefreshToken] = useState(0);

  // ============ 窗口參數 ============
  const lookbackBars = useMemo(() => {
    if (typeof window === "undefined") return 100;
    const stored = localStorage.getItem("kline_lookback_bars");
    return stored ? parseInt(stored, 10) : 100;
  }, []);

  const forwardBars = useMemo(() => {
    if (typeof window === "undefined") return 48;
    const stored = localStorage.getItem("kline_forward_bars");
    return stored ? parseInt(stored, 10) : 48;
  }, []);

  // ============ Hydration ============
  useEffect(() => {
    if (isHydrated) {
      setHydrationSource(lastHydrationSource ?? "storage");
    } else {
      const restored = hydrateFromCache();
      setHydrationSource(restored ? "storage" : "default");
    }
  }, [hydrateFromCache, isHydrated, lastHydrationSource]);

  // ============ 載入案例列表 ============
  useEffect(() => {
    const fetchCaseList = async () => {
      try {
        setLoadingCases(true);
        setCaseListError(null);
        const response = await fetch(`${API_BASE_URL}/api/v1/case/list`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const result: CaseListResponse = await response.json();
        setCaseList(result.cases);
        setAvailableSymbols(result.symbols);
        if (result.symbols.length > 0) setSelectedSymbol(result.symbols[0]);
      } catch (err) {
        console.error("Failed to fetch case list:", err);
        setCaseListError(err instanceof Error ? err.message : "載入案例列表失敗");
      } finally {
        setLoadingCases(false);
      }
    };
    fetchCaseList();
  }, []);

  // ============ 過濾案例 ============
  const filteredCases = useMemo(() => {
    return caseList.filter((c) => {
      if (selectedSymbol && c.symbol !== selectedSymbol) return false;
      if (caseTypeFilter === "positive" && !c.positive_case) return false;
      if (caseTypeFilter === "negative" && c.positive_case) return false;
      return true;
    });
  }, [caseList, selectedSymbol, caseTypeFilter]);

  // ============ 自動選擇第一個案例 ============
  useEffect(() => {
    if (filteredCases.length > 0) {
      setSelectedTimestamp(filteredCases[0].timestamp);
      setCurrentCase(filteredCases[0]);
    } else {
      setSelectedTimestamp(null);
      setCurrentCase(null);
    }
  }, [selectedSymbol, caseTypeFilter, filteredCases.length]);

  // ============ 更新當前案例 ============
  useEffect(() => {
    if (selectedTimestamp !== null) {
      const foundCase = filteredCases.find((c) => c.timestamp === selectedTimestamp);
      setCurrentCase(foundCase || null);
    }
  }, [selectedTimestamp, filteredCases]);

  // ============ 獲取 K 線數據 ============
  useEffect(() => {
    if (!selectedSymbol || selectedTimestamp === null || !selectedTimeframe || !currentCase) return;

    let cancelled = false;
    const fetchChartData = async () => {
      try {
        setLoadingChartData(true);
        setChartDataError(null);
        setAlignedCaseTimestamp(null);
        setAlignedTcTimestamp(null);

        const caseTimeframe = currentCase.timeframe;
        const url = `${API_BASE_URL}/api/v1/chart/data?symbol=${selectedSymbol}&case_timestamp=${selectedTimestamp}&timeframe=${selectedTimeframe}&case_timeframe=${caseTimeframe}&lookback_bars=${lookbackBars}&forward_bars=${forwardBars}`;

        console.log(`[ChartsPage] Fetching: case_tf=${caseTimeframe}, view_tf=${selectedTimeframe}, lookback=${lookbackBars}, forward=${forwardBars}`);

        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const result: ChartDataResponse = await response.json();
        if (!result.success || !result.data) throw new Error(result.error?.message || "獲取K線數據失敗");

        if (!cancelled) {
          setChartData(result.data);
          setAlignedCaseTimestamp(result.data.aligned_case_timestamp ?? selectedTimestamp);
          setAlignedTcTimestamp(result.data.aligned_tc_timestamp ?? null);
          console.log(`[ChartsPage] Loaded ${result.data.klines.length} klines, TO at ${result.data.to_index}, TC at ${result.data.tc_index}`);
        }
      } catch (err) {
        if (!cancelled) {
          console.error("Failed to fetch chart data:", err);
          setChartDataError(err instanceof Error ? err.message : "載入K線數據失敗");
          setChartData(null);
        }
      } finally {
        if (!cancelled) setLoadingChartData(false);
      }
    };

    fetchChartData();
    return () => { cancelled = true; };
  }, [selectedSymbol, selectedTimestamp, selectedTimeframe, currentCase, lookbackBars, forwardBars, refreshToken]);

  // ============ 計算 EMA（支持不同數據源）============
  const calculateEMAForSource = (
    klines: ChartKline[],
    period: number,
    dataSource: string
  ): Array<{ time: number; value: number }> => {
    if (!period || klines.length === 0) return [];
    
    // 根據數據源選擇對應的欄位
    const getSourceValue = (kline: ChartKline): number => {
      switch (dataSource) {
        case "close": return kline.close;
        case "open": return kline.open;
        case "high": return kline.high;
        case "low": return kline.low;
        case "volume": return kline.volume;
        case "taker_buy_volume": return kline.taker_buy_volume ?? 0;
        case "taker_ratio": return kline.taker_ratio ?? 0;
        default: return kline.close;
      }
    };
    
    const multiplier = 2 / (period + 1);
    let ema = getSourceValue(klines[0]);
    
    return klines.map((kline, index) => {
      const value = getSourceValue(kline);
      if (index === 0) {
        ema = value;
      } else {
        ema = (value - ema) * multiplier + ema;
      }
      return { time: kline.timestamp, value: ema };
    });
  };

  // ============ 計算指標線並根據數據源分配到正確的圖表 ============
  const dataSource = state.dataSources ?? "close";
  
  // 判斷數據源屬於哪種類型的圖表
  const isVolumeSource = dataSource === "volume" || dataSource === "taker_buy_volume";
  const isTakerSource = dataSource === "taker_ratio";
  const isPriceSource = !isVolumeSource && !isTakerSource; // close, open, high, low
  
  const indicatorSeries = useMemo<IndicatorLineSeries[]>(() => {
    if (!chartData || chartData.klines.length === 0) return [];
    const { ema_short, ema_mid, ema_long } = state.indicatorParams;
    return [
      { key: "ema_short", period: ema_short, label: `EMA Short (${ema_short})` },
      { key: "ema_mid", period: ema_mid, label: `EMA Mid (${ema_mid})` },
      { key: "ema_long", period: ema_long, label: `EMA Long (${ema_long})` },
    ]
      .filter((item) => Number.isFinite(item.period) && item.period > 0)
      .map((item) => ({
        id: item.key,
        label: item.label,
        color: INDICATOR_COLORS[item.key] ?? "#64748b",
        data: calculateEMAForSource(chartData.klines, item.period, dataSource),
      }));
  }, [chartData, state.indicatorParams, dataSource]);

  const activeIndicatorSeries = useMemo<IndicatorLineSeries[]>(
    () => indicatorSeries.filter((series) => indicatorVisibility[series.id] !== false),
    [indicatorSeries, indicatorVisibility]
  );
  
  // 根據數據源將指標分配到對應的圖表
  const priceIndicatorSeries = isPriceSource ? activeIndicatorSeries : [];
  const volumeIndicatorSeries = isVolumeSource ? activeIndicatorSeries : [];
  const takerIndicatorSeries = isTakerSource ? activeIndicatorSeries : [];

  const handleToggleSeries = (seriesId: string) => {
    setIndicatorVisibility((prev) => ({ ...prev, [seriesId]: !prev[seriesId] }));
  };

  const handleRetryFetch = () => setRefreshToken((t) => t + 1);

  const handleBack = () => {
    const query = state.syncToUrl ? (lastSyncedQuery ? `?${lastSyncedQuery}` : syncToUrl() ?? "") : "";
    router.push(`/strategy-test${query ?? ""}`);
  };

  // ============ 渲染 ============

  if (loadingCases) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-500 mx-auto mb-3" />
          <p className="text-slate-600">載入案例數據中...</p>
        </div>
      </div>
    );
  }

  if (caseListError) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <h2 className="text-red-800 text-lg font-semibold mb-2">載入失敗</h2>
          <p className="text-red-600">{caseListError}</p>
          <button onClick={() => window.location.reload()} className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">
            重新載入
          </button>
        </div>
      </div>
    );
  }

  if (caseList.length === 0) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 max-w-md text-center">
          <h2 className="text-yellow-800 text-lg font-semibold mb-2">暫無數據</h2>
          <p className="text-yellow-700 mb-4">尚未導入任何案例數據。請先到「數據準備」頁面導入案例 CSV 並下載 K 線數據。</p>
          <button onClick={() => router.push("/data-preparation")} className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700">
            前往數據準備
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 text-sm text-slate-500">
                <button onClick={handleBack} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100">
                  <ArrowLeft className="h-3.5 w-3.5" /> 返回策略測試
                </button>
                <span className="flex items-center gap-1 text-indigo-600">
                  <LineChart className="h-4 w-4" /> /charts
                </span>
              </div>
              <h1 className="mt-2 text-2xl font-semibold text-slate-900">案例圖表查看</h1>
              <p className="text-sm text-slate-500">選擇案例查看 K 線圖表，包含 EMA 指標和窗口遮罩</p>
            </div>
            <div className="text-right text-xs text-slate-500">
              <p>策略設定來源: {hydrationSourceLabel[hydrationSource]}</p>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 space-y-6">
        {/* 案例選擇 */}
        <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">案例選擇</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">交易對</label>
              <select value={selectedSymbol} onChange={(e) => setSelectedSymbol(e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-md text-slate-900 text-sm">
                {availableSymbols.map((symbol) => (<option key={symbol} value={symbol}>{symbol}</option>))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">案例類型</label>
              <select value={caseTypeFilter} onChange={(e) => setCaseTypeFilter(e.target.value as CaseTypeFilter)} className="w-full px-3 py-2 border border-slate-300 rounded-md text-slate-900 text-sm">
                <option value="all">全部</option>
                <option value="positive">正例</option>
                <option value="negative">反例</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">時間框架（查看用）</label>
              <select value={selectedTimeframe} onChange={(e) => setSelectedTimeframe(e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-md text-slate-900 text-sm">
                {AVAILABLE_TIMEFRAMES.map((tf) => (<option key={tf} value={tf}>{tf}</option>))}
              </select>
              <p className="text-[10px] text-slate-400 mt-1">與案例時間框架獨立</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">案例時間點 ({filteredCases.length} 個)</label>
              <select value={selectedTimestamp || ""} onChange={(e) => setSelectedTimestamp(Number(e.target.value))} disabled={filteredCases.length === 0} className="w-full px-3 py-2 border border-slate-300 rounded-md text-slate-900 text-sm">
                {filteredCases.map((c) => (<option key={c.case_id} value={c.timestamp}>{formatTimestamp(c.timestamp)} {c.positive_case ? "✓" : "✗"}</option>))}
              </select>
            </div>
          </div>
          {currentCase && (
            <div className="mt-4 pt-4 border-t border-slate-100 grid grid-cols-2 md:grid-cols-5 gap-4 text-xs">
              <div><span className="text-slate-500">案例ID：</span><span className="font-mono text-slate-800">{currentCase.case_id}</span></div>
              <div><span className="text-slate-500">類型：</span><span className={`font-semibold ${currentCase.positive_case ? "text-green-600" : "text-red-600"}`}>{currentCase.positive_case ? "正例 ✓" : "反例 ✗"}</span></div>
              <div><span className="text-slate-500">案例時間框架：</span><span className="font-mono text-slate-800">{currentCase.timeframe}</span></div>
              <div><span className="text-slate-500">Lookback：</span><span className="font-mono text-slate-800">{lookbackBars} 根</span></div>
              <div><span className="text-slate-500">Forward：</span><span className="font-mono text-slate-800">{forwardBars} 根</span></div>
            </div>
          )}
        </section>

        {/* 指標控制 */}
        <section className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
            <span className="font-semibold text-slate-800">指標顯示：</span>
            <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-500">
              數據源: {dataSource} → {isPriceSource ? "Price圖" : isVolumeSource ? "Volume圖" : "Taker圖"}
            </span>
            {indicatorSeries.map((series) => (
              <button key={series.id} onClick={() => handleToggleSeries(series.id)} className={`rounded-full border px-3 py-1 font-medium ${indicatorVisibility[series.id] !== false ? "border-indigo-200 bg-indigo-50 text-indigo-700" : "border-slate-200 text-slate-500"}`}>
                <span className="inline-flex items-center gap-1">
                  <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: series.color }} />
                  {series.label}
                </span>
              </button>
            ))}
          </div>
        </section>

        {/* 圖表區域 */}
        <section className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          {selectedTimestamp !== null ? (
            loadingChartData ? (
              <div className="flex items-center justify-center bg-slate-50 rounded-lg" style={{ height: "640px" }}>
                <div className="text-center">
                  <Loader2 className="h-8 w-8 animate-spin text-indigo-500 mx-auto mb-2" />
                  <p className="text-slate-600 text-sm">載入 K 線數據中...</p>
                </div>
              </div>
            ) : chartDataError ? (
              <div className="flex items-center justify-center bg-red-50 rounded-lg" style={{ height: "640px" }}>
                <div className="text-center">
                  <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
                  <p className="text-red-600 text-sm mb-3">{chartDataError}</p>
                  <button onClick={handleRetryFetch} className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm">
                    <RefreshCcw className="h-4 w-4" /> 重新載入
                  </button>
                </div>
              </div>
            ) : chartData && chartData.klines.length > 0 ? (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{selectedSymbol} / {selectedTimeframe} — Price / Volume / Taker Ratio</p>
                    <p className="text-xs text-slate-500">{formatTimestampDate(chartData.metadata.time_range.start)} → {formatTimestampDate(chartData.metadata.time_range.end)} ・ {chartData.metadata.total_bars} 根 K 線</p>
                  </div>
                  <button onClick={handleRetryFetch} className="inline-flex items-center gap-2 px-3 py-1 border border-slate-200 rounded-md text-xs text-slate-600 hover:bg-slate-50">
                    <RefreshCcw className="h-3.5 w-3.5" /> 刷新
                  </button>
                </div>
                <TradingChartWithSignals
                  symbol={selectedSymbol}
                  timeframe={selectedTimeframe}
                  klines={chartData.klines}
                  signalPoints={[]}
                  toTimestamp={alignedCaseTimestamp ?? selectedTimestamp ?? 0}
                  tcTimestamp={alignedTcTimestamp ?? undefined}
                  totalHeight={700}
                  showSignalMarkers={false}
                  priceIndicatorSeries={priceIndicatorSeries}
                  volumeIndicatorSeries={volumeIndicatorSeries}
                  takerIndicatorSeries={takerIndicatorSeries}
                  showVolumeToTcMarkers={false}
                />
              </div>
            ) : (
              <div className="flex items-center justify-center bg-slate-50 rounded-lg" style={{ height: "640px" }}>
                <div className="text-center"><LineChart className="h-8 w-8 text-slate-300 mx-auto mb-2" /><p className="text-slate-500">無 K 線數據</p></div>
              </div>
            )
          ) : (
            <div className="flex items-center justify-center bg-slate-50 rounded-lg" style={{ height: "640px" }}>
              <div className="text-center"><LineChart className="h-8 w-8 text-slate-300 mx-auto mb-2" /><p className="text-slate-500">請選擇案例以查看圖表</p></div>
            </div>
          )}
        </section>

        {/* 調試信息 */}
        {chartData && (
          <section className="bg-slate-100 rounded-lg p-4 text-xs text-slate-600">
            <p className="font-semibold mb-2">調試信息</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              <div>to_index: {chartData.to_index ?? "null"}</div>
              <div>tc_index: {chartData.tc_index ?? "null"}</div>
              <div>case_bars: {chartData.case_bars ?? "null"}</div>
              <div>total_bars: {chartData.metadata.total_bars}</div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

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
  type WindowOverlayRange,
} from "@/components/charts/TradingChartWithSignals";
import type { SignalPoint } from "@/components/charts/StrategySignalChart";

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
  // 新增：後端計算的指標數據
  indicators?: {
    ema_short?: Array<{ time: number; value: number | null }>;
    ema_mid?: Array<{ time: number; value: number | null }>;
    ema_long?: Array<{ time: number; value: number | null }>;
    [key: string]: Array<{ time: number; value: number | null }> | undefined;
  };
  indicator_error?: string;
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

// ============ 指標顏色配置 ============

const AVAILABLE_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"];

// 空數組常量，避免重新渲染
const EMPTY_ARRAY: never[] = [];

// ============ 主組件 ============

export default function ChartsPage() {
  const router = useRouter();

  // 策略配置 Hook (用於 EMA 參數和窗口設定)
  const { state, hydrateFromCache, hydrateFromUrl, lastHydrationSource, isHydrated, lastSyncedQuery, syncToUrl } = useStrategyConfig();

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
    // 優先從 URL 讀取參數（從 Strategy Test 頁面跳轉時）
    if (typeof window !== "undefined") {
      const urlParams = window.location.search;
      if (urlParams && urlParams.length > 1) {
        const hydratedFromUrl = hydrateFromUrl(urlParams);
        if (hydratedFromUrl) {
          setHydrationSource("url");
          return;
        }
      }
    }
    
    // Fallback 到 cache/storage
    if (isHydrated) {
      setHydrationSource(lastHydrationSource ?? "storage");
    } else {
      const restored = hydrateFromCache();
      setHydrationSource(restored ? "storage" : "default");
    }
  }, [hydrateFromCache, hydrateFromUrl, isHydrated, lastHydrationSource]);

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

  // ============ 獲取 K 線數據（含指標計算）============
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
        
        // 防護性檢查：確保 case_timeframe 有效
        if (!caseTimeframe) {
          console.error(`[ChartsPage] ERROR: currentCase.timeframe is undefined for case ${currentCase.case_id}`);
          throw new Error("案例缺少時間框架資訊，請重新導入案例");
        }
        
        // 構建 URL 參數
        const params = new URLSearchParams({
          symbol: selectedSymbol,
          case_timestamp: selectedTimestamp.toString(),
          timeframe: selectedTimeframe,
          case_timeframe: caseTimeframe,
          lookback_bars: lookbackBars.toString(),
          forward_bars: forwardBars.toString(),
        });
        
        // 新增：指標計算參數
        const dataSource = state.dataSources ?? "close";
        const indicatorType = state.indicatorType ?? "ema";
        const strategyLogic = state.strategyLogic ?? "three_line";
        const indicatorParams = state.indicatorParams;
        
        if (indicatorParams) {
          params.append("indicator_type", indicatorType);
          params.append("data_source", dataSource);
          params.append("strategy_logic", strategyLogic);
          
          if (indicatorParams.short_period) {
            params.append("short_period", indicatorParams.short_period.toString());
          }
          if (indicatorParams.mid_period) {
            params.append("mid_period", indicatorParams.mid_period.toString());
          }
          if (indicatorParams.long_period) {
            params.append("long_period", indicatorParams.long_period.toString());
          }
        }
        
        const url = `${API_BASE_URL}/api/v1/chart/data?${params.toString()}`;

        console.log(`[ChartsPage] Fetching: case_tf=${caseTimeframe}, view_tf=${selectedTimeframe}, lookback=${lookbackBars}, forward=${forwardBars}, indicator=${indicatorType}, source=${dataSource}`);

        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const result: ChartDataResponse = await response.json();
        if (!result.success || !result.data) throw new Error(result.error?.message || "獲取K線數據失敗");

        if (!cancelled) {
          setChartData(result.data);
          setAlignedCaseTimestamp(result.data.aligned_case_timestamp ?? selectedTimestamp);
          setAlignedTcTimestamp(result.data.aligned_tc_timestamp ?? null);
          
          // 日誌：是否包含指標數據
          const hasIndicators = !!result.data.indicators;
          console.log(`[ChartsPage] Loaded ${result.data.klines.length} klines, TO at ${result.data.to_index}, TC at ${result.data.tc_index}, has_indicators=${hasIndicators}`);
          
          if (result.data.indicator_error) {
            console.warn(`[ChartsPage] Indicator calculation warning: ${result.data.indicator_error}`);
          }
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
  }, [selectedSymbol, selectedTimestamp, selectedTimeframe, currentCase, lookbackBars, forwardBars, refreshToken, state.dataSources, state.indicatorType, state.strategyLogic, state.indicatorParams]);

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
    
    // 使用統一命名規範：short_period, mid_period, long_period
    const ema_short = state.indicatorParams.short_period;
    const ema_mid = state.indicatorParams.mid_period;
    const ema_long = state.indicatorParams.long_period;
    
    const indicatorConfigs = [
      { key: "ema_short", period: ema_short, label: `EMA Short (${ema_short})` },
      { key: "ema_mid", period: ema_mid, label: `EMA Mid (${ema_mid})` },
      { key: "ema_long", period: ema_long, label: `EMA Long (${ema_long})` },
    ].filter((item) => Number.isFinite(item.period) && item.period > 0);
    
    // 優先使用後端計算的指標數據
    const backendIndicators = chartData.indicators;
    
    return indicatorConfigs.map((item) => {
      let data: Array<{ time: number; value: number }>;
      
      if (backendIndicators && backendIndicators[item.key]) {
        // 使用後端數據（過濾掉 null 值）
        data = backendIndicators[item.key]!
          .filter((point): point is { time: number; value: number } => point.value !== null)
          .map((point) => ({ time: point.time, value: point.value }));
        console.log(`[ChartsPage] Using backend EMA for ${item.key}: ${data.length} points`);
      } else {
        // 回退到前端計算（兜底方案，不應該常發生）
        console.warn(`[ChartsPage] Fallback to frontend EMA calculation for ${item.key} - backend data not available`);
        data = calculateEMAForSource(chartData.klines, item.period, dataSource);
      }
      
      return {
        id: item.key,
        label: item.label,
        color: INDICATOR_COLORS[item.key] ?? "#64748b",
        data,
      };
    });
  }, [chartData, state.indicatorParams, dataSource]);

  const activeIndicatorSeries = useMemo<IndicatorLineSeries[]>(
    () => indicatorSeries.filter((series) => indicatorVisibility[series.id] !== false),
    [indicatorSeries, indicatorVisibility]
  );
  
  // 根據數據源將指標分配到對應的圖表（使用 useMemo 穩定引用）
  const priceIndicatorSeries = useMemo(() => isPriceSource ? activeIndicatorSeries : EMPTY_ARRAY as IndicatorLineSeries[], [isPriceSource, activeIndicatorSeries]);
  const volumeIndicatorSeries = useMemo(() => isVolumeSource ? activeIndicatorSeries : EMPTY_ARRAY as IndicatorLineSeries[], [isVolumeSource, activeIndicatorSeries]);
  const takerIndicatorSeries = useMemo(() => isTakerSource ? activeIndicatorSeries : EMPTY_ARRAY as IndicatorLineSeries[], [isTakerSource, activeIndicatorSeries]);

  // ============ 計算近窗口遮罩 (near window overlay) ============
  const windowOverlays = useMemo<WindowOverlayRange[]>(() => {
    // 需要 alignedCaseTimestamp (TO 時間戳) 和 timeframe 來計算
    const toTs = alignedCaseTimestamp ?? selectedTimestamp;
    if (!toTs || !selectedTimeframe) return [];
    
    // 從 state 獲取 lookback_bars (近窗口範圍)
    const nearWindowBars = state.windowConfig?.lookback_bars ?? 24;
    
    // 將 timeframe 轉換為秒數
    const getTimeframeSeconds = (tf: string): number => {
      const match = tf.match(/^(\d+)([mhdwM])$/);
      if (!match) return 43200; // 默認 12h
      const [, numStr, unit] = match;
      const num = parseInt(numStr, 10);
      switch (unit) {
        case "m": return num * 60;
        case "h": return num * 3600;
        case "d": return num * 86400;
        case "w": return num * 604800;
        case "M": return num * 2592000; // ~30 days
        default: return 43200;
      }
    };
    
    const barSeconds = getTimeframeSeconds(selectedTimeframe);
    
    // near window: TO - nearWindowBars 到 TO - 1
    // 使用 bar 的結束時間作為時間戳 (因為 K 線 timestamp 是開盤時間)
    const nearStartTs = toTs - nearWindowBars * barSeconds;
    const nearEndTs = toTs - barSeconds; // TO - 1 bar
    
    return [
      {
        type: "near" as const,
        startTimestamp: nearStartTs,
        endTimestamp: nearEndTs,
      },
    ];
  }, [alignedCaseTimestamp, selectedTimestamp, selectedTimeframe, state.windowConfig?.lookback_bars]);

  // ============ 計算策略信號點 ============
  const signalPoints = useMemo<SignalPoint[]>(() => {
    // 需要指標數據和策略邏輯
    if (!chartData || chartData.klines.length === 0) return [];
    if (indicatorSeries.length < 3) return []; // 需要至少 3 條 EMA 線
    
    const strategyLogic = state.strategyLogic;
    if (!strategyLogic) return [];
    
    // 獲取 EMA 數據
    const emaShort = indicatorSeries.find(s => s.id === 'ema_short')?.data ?? [];
    const emaMid = indicatorSeries.find(s => s.id === 'ema_mid')?.data ?? [];
    const emaLong = indicatorSeries.find(s => s.id === 'ema_long')?.data ?? [];
    
    if (emaShort.length === 0 || emaMid.length === 0 || emaLong.length === 0) return [];
    
    // 獲取窗口配置
    const toTs = alignedCaseTimestamp ?? selectedTimestamp;
    const nearBars = state.windowConfig?.lookback_bars ?? 24;
    const farBars = state.windowConfig?.far_lookback_bars; // 可能為 undefined
    
    // 計算 timeframe 秒數
    const getTimeframeSeconds = (tf: string): number => {
      const match = tf.match(/^(\d+)([mhdwM])$/);
      if (!match) return 43200;
      const [, numStr, unit] = match;
      const num = parseInt(numStr, 10);
      switch (unit) {
        case "m": return num * 60;
        case "h": return num * 3600;
        case "d": return num * 86400;
        case "w": return num * 604800;
        case "M": return num * 2592000;
        default: return 43200;
      }
    };
    
    const barSeconds = selectedTimeframe ? getTimeframeSeconds(selectedTimeframe) : 43200;
    
    // 計算窗口邊界時間戳
    const nearStartTs = toTs ? toTs - nearBars * barSeconds : 0;
    const nearEndTs = toTs ? toTs - barSeconds : 0; // TO - 1
    const farStartTs = toTs && farBars ? toTs - farBars * barSeconds : 0;
    const farEndTs = toTs ? toTs - (nearBars + 1) * barSeconds : 0; // TO - nearBars - 1
    
    const signals: SignalPoint[] = [];
    
    // 遍歷每個時間點檢查策略條件
    chartData.klines.forEach((kline, index) => {
      const ts = kline.timestamp;
      
      // 查找對應的 EMA 值
      const shortVal = emaShort.find(d => d.time === ts)?.value;
      const midVal = emaMid.find(d => d.time === ts)?.value;
      const longVal = emaLong.find(d => d.time === ts)?.value;
      
      if (shortVal === undefined || midVal === undefined || longVal === undefined) return;
      
      // 檢查策略條件
      let conditionMet = false;
      if (strategyLogic === 'three_line') {
        conditionMet = shortVal > midVal && midVal > longVal;
      } else if (strategyLogic === 'short_long_cross') {
        conditionMet = shortVal > longVal;
      } else if (strategyLogic === 'mid_long_cross') {
        conditionMet = midVal > longVal;
      }
      
      if (!conditionMet) return;
      
      // 判斷屬於哪個窗口
      let windowType: 'near' | 'far' | undefined;
      
      if (toTs) {
        if (ts >= nearStartTs && ts <= nearEndTs) {
          windowType = 'near';
        } else if (farBars) {
          // 有設定 far_lookback_bars
          if (ts >= farStartTs && ts <= farEndTs) {
            windowType = 'far';
          }
        } else {
          // 沒設定 far_lookback_bars，近期以外都是遠期
          if (ts < nearStartTs) {
            windowType = 'far';
          }
        }
      }
      
      // 只有在窗口內的信號才加入
      if (windowType) {
        signals.push({
          timestamp: ts,
          indicator_values: {
            ema_short: shortVal,
            ema_mid: midVal,
            ema_long: longVal,
          },
          windowType,
        });
      }
    });
    
    return signals;
  }, [chartData, indicatorSeries, state.strategyLogic, state.windowConfig, alignedCaseTimestamp, selectedTimestamp, selectedTimeframe]);

  // 根據數據源分配信號點到對應圖表（使用 useMemo 穩定引用）
  const priceSignalPoints = useMemo(() => isPriceSource ? signalPoints : EMPTY_ARRAY as SignalPoint[], [isPriceSource, signalPoints]);
  const volumeSignalPoints = useMemo(() => isVolumeSource ? signalPoints : EMPTY_ARRAY as SignalPoint[], [isVolumeSource, signalPoints]);
  const takerSignalPoints = useMemo(() => isTakerSource ? signalPoints : EMPTY_ARRAY as SignalPoint[], [isTakerSource, signalPoints]);

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
        <div className="px-6 py-4">
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

      <main className="px-6 py-6 space-y-6">
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
            <span className="px-2 py-0.5 rounded bg-indigo-100 text-indigo-700 font-medium">
              EMA: {state.indicatorParams.short_period} / {state.indicatorParams.mid_period} / {state.indicatorParams.long_period}
            </span>
            <span className="px-2 py-0.5 rounded bg-purple-100 text-purple-700">
              策略: {state.strategyLogic === 'three_line' ? '三線順勢' : state.strategyLogic}
            </span>
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
                  signalPoints={priceSignalPoints}
                  toTimestamp={alignedCaseTimestamp ?? selectedTimestamp ?? 0}
                  tcTimestamp={alignedTcTimestamp ?? undefined}
                  totalHeight={700}
                  showSignalMarkers={priceSignalPoints.length > 0}
                  priceIndicatorSeries={priceIndicatorSeries}
                  volumeIndicatorSeries={volumeIndicatorSeries}
                  takerIndicatorSeries={takerIndicatorSeries}
                  volumeSignalPoints={volumeSignalPoints}
                  takerSignalPoints={takerSignalPoints}
                  showVolumeToTcMarkers={false}
                  windowOverlays={EMPTY_ARRAY}
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

        {/* 信號統計 */}
        {chartData && (
          <section className="bg-slate-100 rounded-lg p-4 text-xs text-slate-600">
            <p className="font-semibold mb-2">信號統計</p>
            {(() => {
              const nearCount = signalPoints.filter(s => s.windowType === 'near').length;
              const farCount = signalPoints.filter(s => s.windowType === 'far').length;
              const totalBars = chartData.metadata.total_bars;
              const nearBars = state.windowConfig?.lookback_bars ?? 24;
              const farBars = state.windowConfig?.far_lookback_bars ?? (totalBars - nearBars);
              const nearRatio = nearBars > 0 ? (nearCount / nearBars * 100) : 0;
              const farRatio = farBars > 0 ? (farCount / farBars * 100) : 0;
              // Near/Far 比率 = Near密度 / Far密度
              const densityRatio = farRatio > 0 ? (nearRatio / farRatio).toFixed(2) : (nearRatio > 0 ? '∞' : '0.00');
              
              return (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div className="flex items-center gap-2">
                    <span className="inline-block w-3 h-3 rounded" style={{ backgroundColor: '#3B82F6' }}></span>
                    <span>Near 信號: <strong>{nearCount}</strong></span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="inline-block w-3 h-3 rounded" style={{ backgroundColor: '#CA8A04' }}></span>
                    <span>Far 信號: <strong>{farCount}</strong></span>
                  </div>
                  <div>
                    Near 密度: <strong>{nearRatio.toFixed(1)}%</strong>
                    <span className="text-gray-400 ml-1">({nearCount}/{nearBars} bars)</span>
                  </div>
                  <div>
                    Far 密度: <strong>{farRatio.toFixed(1)}%</strong>
                    <span className="text-gray-400 ml-1">({farCount}/{farBars} bars)</span>
                  </div>
                  <div>
                    Near/Far 密度比: <strong className={parseFloat(String(densityRatio)) > 1 ? 'text-green-600' : parseFloat(String(densityRatio)) < 1 ? 'text-red-600' : ''}>{densityRatio}</strong>
                  </div>
                </div>
              );
            })()}
          </section>
        )}
      </main>
    </div>
  );
}

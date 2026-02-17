/**
 * StrategySignalChart.tsx - 帶策略信號標記的價格圖表
 *
 * Phase 3.3+3.4 - Task C1: 圖表信號標記整合
 *
 * 功能:
 * - 繼承 PriceChart 的所有功能
 * - 添加策略信號箭頭標記 (綠色向上箭頭)
 * - 支持最多 500 個信號標記
 * - 懸停顯示信號詳情 (指標數值、信號密度)
 * - 與 TO/TC 標記區分顯示
 *
 * Ultra Think 記錄:
 * - 步驟 1: 初版代碼 (當前)
 * - 步驟 2: 審查優化 (待執行)
 * - 步驟 3: 最終優化 (待執行)
 */

"use client";

import { useEffect, useState, useRef } from "react";
import { useChartSync } from "@/hooks/useChartSync";
import { darkChartOptions } from "@/utils/chartConfig";
import {
  candlestickSeriesOptions,
  formatTime,
  formatPrice,
  formatVolume,
  chartColors,
} from "@/utils/chartConfig";
import {
  ISeriesApi,
  SeriesMarker,
  Time,
  MouseEventParams,
  UTCTimestamp,
} from "lightweight-charts";
import type { IndicatorLineSeries } from "./TradingChartWithSignals";

const toUtcTime = (timestamp: number): UTCTimestamp =>
  timestamp as UTCTimestamp;

const extractNumericTime = (time: Time | undefined): number | null =>
  typeof time === "number" ? time : null;
 // moved above

/**
 * K線數據接口
 */
export interface KlineData {
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

/**
 * 策略信號點接口
 */
export interface SignalPoint {
  timestamp: number;
  indicator_values: Record<string, number>; // 例: { ema_short: 7, ema_mid: 18, ema_long: 35 }
  signal_density?: number; // 信號密度 (0-1)
  windowType?: 'near' | 'far'; // 窗口類型: 近期窗口或遠期窗口
}

/**
 * 懸停信號資訊
 */
export interface HoveredSignalInfo {
  timestamp: number;
  indicator_values: Record<string, number>;
  signal_density?: number;
  price: number;
}

/**
 * StrategySignalChart 組件 Props
 */
export interface StrategySignalChartProps {
  /**
   * 交易對 symbol
   */
  symbol: string;

  /**
   * 時間框架
   */
  timeframe: string;

  /**
   * K線數據數組
   */
  klines: KlineData[];

  /**
   * 策略信號點數組 (最多 500 個)
   */
  signalPoints?: SignalPoint[];

  /**
   * 案例時間點 T (Unix 秒)
   */
  caseTimestamp?: number;

  /**
   * TO 時間戳 (對齊後的案例開始時間)
   */
  toTimestamp?: number;

  /**
   * TC 時間戳 (對齊後的案例結束時間)
   */
  tcTimestamp?: number;

  /**
   * 圖表高度 (像素)
   */
  height?: number;

  /**
   * 是否顯示案例標記 (TO/TC)
   */
  showCaseMarker?: boolean;

  /**
   * 是否顯示策略信號標記
   */
  showSignalMarkers?: boolean;

  /**
   * 圖表唯一ID (用於同步)
   */
  chartId?: string;

  /**
   * 是否啟用同步
   */
  enableSync?: boolean;

  /**
   * 信號點擊回調
   */
  onSignalClick?: (signal: SignalPoint) => void;

  /**
   * 信號懸停回調
   */
  onSignalHover?: (signal: HoveredSignalInfo | null) => void;

  /**
   * 指標線資料
   */
  indicatorSeries?: IndicatorLineSeries[];
}

/**
 * StrategySignalChart 組件 - 帶策略信號標記的價格圖表
 */
export function StrategySignalChart({
  symbol,
  timeframe,
  klines,
  signalPoints = [],
  caseTimestamp,
  toTimestamp,
  tcTimestamp,
  height = 400,
  showCaseMarker = true,
  showSignalMarkers = true,
  chartId = "strategy-signal-chart",
  enableSync = false,
  onSignalClick,
  onSignalHover,
  indicatorSeries = [],
}: StrategySignalChartProps) {

  const { chartContainerRef, chartInstance, isReady } = useChartSync({
    chartId,
    toTimestamp: toTimestamp || caseTimestamp || 0,
    enableSync,
    debug: true,
    chartOptions: darkChartOptions,
  });

  // 狀態管理
  const [error, setError] = useState<string | null>(null);
  const [hoveredData, setHoveredData] = useState<KlineData | null>(null);
  const [hoveredSignal, setHoveredSignal] = useState<SignalPoint | null>(null);
  const [hoveredIndicators, setHoveredIndicators] = useState<Record<string, number>>({});

  // 保存 series 引用，用於 cleanup
  const candlestickSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const indicatorLineRefs = useRef<ISeriesApi<"Line">[]>([]);
  
  // 追蹤用戶是否手動縮放了 Y 軸
  const userScaledYAxisRef = useRef(false);

  // 使用 ref 存儲回調函數，避免依賴變化導致 useEffect 重新執行
  const onSignalHoverRef = useRef(onSignalHover);
  const onSignalClickRef = useRef(onSignalClick);
  
  // 使用 ref 緩存 indicatorSeries，避免不必要的重渲染
  const indicatorSeriesRef = useRef(indicatorSeries);
  
  // 更新 ref 當 props 變化時
  useEffect(() => {
    onSignalHoverRef.current = onSignalHover;
    onSignalClickRef.current = onSignalClick;
    indicatorSeriesRef.current = indicatorSeries;
  }, [onSignalHover, onSignalClick, indicatorSeries]);
  
  // 更新 indicatorSeries ref（淺比較）
  useEffect(() => {
    indicatorSeriesRef.current = indicatorSeries;
  }, [indicatorSeries]);

  /**
   * 獨立的 Y 軸縮放控制 useEffect
   * 這個 useEffect 只依賴 chartInstance 和 isReady，不會因為其他狀態變化而重新執行
   */
  useEffect(() => {
    if (!chartInstance || !isReady) return;
    
    const container = chartContainerRef.current;
    if (!container) return;

    const priceScale = chartInstance.priceScale('right');

    const handleMouseDown = (e: MouseEvent) => {
      // 檢查是否點擊在右側 Y 軸區域（大約右邊 60px）
      const rect = container.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const isYAxisArea = clickX > rect.width - 60;
      
      if (isYAxisArea) {
        // 用戶開始拖曳 Y 軸
        const handleMouseUp = () => {
          // 拖曳結束後，禁用 autoScale 以維持縮放
          userScaledYAxisRef.current = true;
          priceScale.applyOptions({ autoScale: false });
          document.removeEventListener('mouseup', handleMouseUp);
        };
        document.addEventListener('mouseup', handleMouseUp);
      }
    };

    // 雙擊重置 Y 軸
    const handleDoubleClick = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const isYAxisArea = clickX > rect.width - 60;
      
      if (isYAxisArea) {
        userScaledYAxisRef.current = false;
        priceScale.applyOptions({ autoScale: true });
      }
    };

    container.addEventListener('mousedown', handleMouseDown);
    container.addEventListener('dblclick', handleDoubleClick);

    return () => {
      container.removeEventListener('mousedown', handleMouseDown);
      container.removeEventListener('dblclick', handleDoubleClick);
    };
  }, [chartContainerRef, chartInstance, isReady]);

  /**
   * 渲染 K線數據和信號標記到圖表
   */
  useEffect(() => {
    if (!chartInstance || !isReady || !klines || klines.length === 0) {
      return;
    }

    try {
      // 添加 K線系列
      const candlestickSeries =
        chartInstance.addCandlestickSeries(candlestickSeriesOptions);
      candlestickSeriesRef.current = candlestickSeries;

      // 配置 right price scale - 根據用戶是否已縮放來決定 autoScale
      const priceScale = chartInstance.priceScale('right');
      priceScale.applyOptions({
        autoScale: !userScaledYAxisRef.current,
        scaleMargins: {
          top: 0.1,
          bottom: 0.1,
        },
      });

      // 轉換數據格式 (Lightweight Charts 格式)
      const formattedKlines = klines.map((kline) => ({
        time: toUtcTime(kline.timestamp),
        open: kline.open,
        high: kline.high,
        low: kline.low,
        close: kline.close,
      }));

      // 設置 K線數據
      candlestickSeries.setData(formattedKlines);

      // 構建標記數組
      const markers: SeriesMarker<UTCTimestamp>[] = [];

      // 1. 添加 TO/TC 標記 (案例標記)
      if (showCaseMarker) {
        if (toTimestamp && tcTimestamp) {
          // 標記 TO 和 TC 兩個點
          markers.push({
            time: toUtcTime(toTimestamp),
            position: "aboveBar" as const,
            color: "#60a5fa", // 藍色 - TO
            shape: "arrowDown" as const,
            text: "TO",
          });
          markers.push({
            time: toUtcTime(tcTimestamp),
            position: "aboveBar" as const,
            color: "#fb923c", // 橙色 - TC
            shape: "arrowDown" as const,
            text: "TC",
          });
        } else if (caseTimestamp) {
          // 只標記一個 T 點 (向後兼容)
          markers.push({
            time: toUtcTime(caseTimestamp),
            position: "aboveBar" as const,
            color: chartColors.caseMarkerColor,
            shape: "arrowDown" as const,
            text: "T",
          });
        }
      }

      // 2. 添加策略信號標記 (根據窗口類型使用不同顏色)
      if (showSignalMarkers && signalPoints.length > 0) {
        signalPoints.forEach((signal) => {
          // 根據 windowType 決定顏色: 近期窗口藍色，遠期窗口土黃色
          const color = signal.windowType === 'near' ? '#60a5fa' : '#fbbf24';
          const text = signal.windowType === 'near' ? 'N' : 'F';
          
          markers.push({
            time: toUtcTime(signal.timestamp),
            position: "belowBar" as const,
            color: color,
            shape: "arrowUp" as const,
            text: text,
            id: `signal-${signal.timestamp}`,
          });
        });
      }

      // 按時間排序標記（Lightweight Charts 要求）
      markers.sort((a, b) => (a.time as number) - (b.time as number));

      // 設置所有標記
      candlestickSeries.setMarkers(markers);

      // 不再手動設置可見範圍，讓同步機制控制
      // 首次載入時使用 fitContent，但只在非同步模式下
      if (!enableSync && formattedKlines.length > 0) {
        chartInstance.timeScale().fitContent();
      }

      // 訂閱懸停事件 (用於顯示 OHLCV 和信號資訊)
      const handleCrosshairMove = (param: MouseEventParams<Time>) => {
        const hoveredTime = extractNumericTime(param.time);
        
        if (hoveredTime !== null) {
          // 查找懸停的 K線
          const hoveredKline = klines.find((k) => k.timestamp === hoveredTime);
          if (hoveredKline) {
            setHoveredData(hoveredKline);
          }

          // 查找懸停的指標值
          const indicatorValues: Record<string, number> = {};
          indicatorSeriesRef.current.forEach((series) => {
            const point = series.data.find((d) => d.time === hoveredTime);
            if (point) {
              indicatorValues[series.id] = point.value;
            }
          });
          setHoveredIndicators(indicatorValues);

          // 查找懸停的信號點
          const hoveredSignalPoint = signalPoints.find(
            (s) => s.timestamp === hoveredTime
          );
          if (hoveredSignalPoint) {
            setHoveredSignal(hoveredSignalPoint);

            // 觸發回調（使用 ref 避免依賴問題）
            if (onSignalHoverRef.current) {
              const price =
                hoveredKline?.close || klines[klines.length - 1].close;
              onSignalHoverRef.current({
                timestamp: hoveredSignalPoint.timestamp,
                indicator_values: hoveredSignalPoint.indicator_values,
                signal_density: hoveredSignalPoint.signal_density,
                price,
              });
            }
          } else {
            setHoveredSignal(null);
            if (onSignalHoverRef.current) {
              onSignalHoverRef.current(null);
            }
          }
        } else {
          setHoveredData(null);
          setHoveredSignal(null);
          setHoveredIndicators({});
          if (onSignalHoverRef.current) {
            onSignalHoverRef.current(null);
          }
        }
      };

      chartInstance.subscribeCrosshairMove(handleCrosshairMove);

      // 訂閱點擊事件 (用於信號點擊)
      const handleClick = (param: MouseEventParams<Time>) => {
        const clickedTime = extractNumericTime(param.time);
        if (clickedTime !== null && onSignalClickRef.current) {
          const clickedSignal = signalPoints.find(
            (s) => s.timestamp === clickedTime
          );
          if (clickedSignal) {
            onSignalClickRef.current(clickedSignal);
          }
        }
      };

      chartInstance.subscribeClick(handleClick);

      // cleanup 函數: 移除 series 和事件訂閱
      return () => {
        try {
          chartInstance.unsubscribeCrosshairMove(handleCrosshairMove);
          chartInstance.unsubscribeClick(handleClick);
          indicatorLineRefs.current.forEach((line) => {
            try {
              chartInstance.removeSeries(line);
            } catch (err) {
              console.error("[StrategySignalChart] Indicator cleanup error", err);
            }
          });
          indicatorLineRefs.current = [];
          if (candlestickSeries) {
            chartInstance.removeSeries(candlestickSeries);
          }
        } catch (err) {
          console.error("[StrategySignalChart] Cleanup error:", err);
        }
      };
    } catch (err) {
      console.error("[StrategySignalChart] Failed to render chart:", err);
      setError(
        err instanceof Error ? err.message : "Failed to render chart"
      );
    }
  }, [
    chartInstance,
    isReady,
    klines,
    signalPoints,
    caseTimestamp,
    toTimestamp,
    tcTimestamp,
    showCaseMarker,
    showSignalMarkers,
    symbol,
    enableSync,
  ]);

  /**
   * 指標線渲染 useEffect
   * 使用 JSON 字符串比較來避免不必要的重渲染
   */
  const prevIndicatorSeriesJsonRef = useRef<string>("");
  
  useEffect(() => {
    if (!chartInstance || !isReady) return;
    
    // 序列化當前 indicatorSeries 用於比較
    const currentJson = JSON.stringify(
      indicatorSeries.map(s => ({ id: s.id, color: s.color, dataLength: s.data.length }))
    );
    
    // 如果內容相同，跳過更新
    if (currentJson === prevIndicatorSeriesJsonRef.current && indicatorLineRefs.current.length > 0) {
      return;
    }
    
    // 更新緩存
    prevIndicatorSeriesJsonRef.current = currentJson;
    
    // 清除舊的指標線
    indicatorLineRefs.current.forEach((line) => {
      try {
        chartInstance.removeSeries(line);
      } catch (err) {
        console.error("[StrategySignalChart] Indicator cleanup error", err);
      }
    });
    indicatorLineRefs.current = [];

    // 添加新的指標線
    indicatorSeries.forEach((series) => {
      if (!series.data.length) return;
      const line = chartInstance.addLineSeries({
        color: series.color,
        lineWidth: 2,
        priceScaleId: "right",
        lastValueVisible: false,
        priceLineVisible: false,
      });
      line.setData(
        series.data.map((point) => ({
          time: toUtcTime(point.time),
          value: point.value,
        }))
      );
      indicatorLineRefs.current.push(line);
    });

    return () => {
      indicatorLineRefs.current.forEach((line) => {
        try {
          chartInstance.removeSeries(line);
        } catch (err) {
          console.error("[StrategySignalChart] Indicator cleanup error", err);
        }
      });
      indicatorLineRefs.current = [];
    };
  }, [chartInstance, indicatorSeries, isReady]);

  return (
    <div
      className="w-full flex flex-col bg-[#0A0F1C]"
      style={{ height: `${height}px` }}
    >
      {/* 頂部資訊欄 */}
      <div className="px-4 py-2 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h3 className="text-sm font-semibold text-slate-100">
            {symbol} / {timeframe}
          </h3>
          <span className="text-xs text-slate-400">策略信號圖表</span>

          {/* 信號統計 - 顯示 Near(藍) 和 Far(土黃) 計數 */}
          {showSignalMarkers && signalPoints.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs px-2 py-0.5 bg-blue-400/15 text-blue-300 rounded flex items-center gap-1">
                <span style={{ color: '#60a5fa' }}>▼</span>
                N: {signalPoints.filter(s => s.windowType === 'near').length}
              </span>
              <span className="text-xs px-2 py-0.5 bg-amber-400/15 text-amber-300 rounded flex items-center gap-1">
                <span style={{ color: '#fbbf24' }}>▼</span>
                F: {signalPoints.filter(s => s.windowType === 'far').length}
              </span>
            </div>
          )}
        </div>

        {/* OHLCV 懸停資訊 */}
        {hoveredData && (
          <div className="flex items-center gap-3 text-xs flex-wrap">
            <span className="text-slate-300">
              O: <span className="font-mono">{formatPrice(hoveredData.open)}</span>
            </span>
            <span className="text-slate-300">
              H: <span className="font-mono">{formatPrice(hoveredData.high)}</span>
            </span>
            <span className="text-slate-300">
              L: <span className="font-mono">{formatPrice(hoveredData.low)}</span>
            </span>
            <span className="text-slate-300">
              C:{" "}
              <span
                className={`font-mono ${
                  hoveredData.close >= hoveredData.open
                    ? "text-emerald-400"
                    : "text-rose-400"
                }`}
              >
                {formatPrice(hoveredData.close)}
              </span>
            </span>
            <span className="text-slate-300">
              V: <span className="font-mono">{formatVolume(hoveredData.volume)}</span>
            </span>
            {/* 指標值顯示 */}
            {indicatorSeries.map((series) => {
              const value = hoveredIndicators[series.id];
              if (value === undefined) return null;
              return (
                <span key={series.id} className="text-slate-300">
                  <span style={{ color: series.color }}>●</span>{" "}
                  {series.label || series.id}:{" "}
                  <span className="font-mono" style={{ color: series.color }}>
                    {formatPrice(value)}
                  </span>
                </span>
              );
            })}
            <span className="text-slate-500">
              {formatTime(hoveredData.timestamp)}
            </span>
          </div>
        )}
      </div>

      {/* 圖表容器 */}
      <div className="flex-1 relative">
        <div
          ref={chartContainerRef}
          className="w-full h-full"
        />

        {/* 錯誤提示 */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#0A0F1C]">
            <div className="text-sm text-rose-400">
              <span className="mr-2">⚠️</span>
              {error}
            </div>
          </div>
        )}

        {/* 載入中提示 */}
        {!isReady && !error && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#0A0F1C]">
            <div className="text-sm text-slate-400">載入圖表中...</div>
          </div>
        )}
      </div>

      {/* 底部信號詳情 (懸停時顯示) */}
      {hoveredSignal && (
        <div className="px-4 py-2 border-t border-emerald-400/30 bg-emerald-400/10">
          <div className="flex items-center gap-4 text-xs">
            <span className="font-semibold text-emerald-300">📍 信號詳情:</span>
            {Object.entries(hoveredSignal.indicator_values).map(
              ([key, value]) => (
                <span key={key} className="text-slate-300">
                  {key}: <span className="font-mono">{value.toFixed(2)}</span>
                </span>
              )
            )}
            {hoveredSignal.signal_density !== undefined && (
              <span className="text-slate-300">
                密度:{" "}
                <span className="font-mono">
                  {(hoveredSignal.signal_density * 100).toFixed(1)}%
                </span>
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

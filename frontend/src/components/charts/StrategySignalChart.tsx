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
  console.log("[StrategySignalChart] Initializing with:", {
    chartId,
    enableSync,
    signalCount: signalPoints.length,
    toTimestamp: toTimestamp || caseTimestamp,
  });

  const { chartContainerRef, chartInstance, isReady } = useChartSync({
    chartId,
    toTimestamp: toTimestamp || caseTimestamp || 0,
    enableSync,
    debug: true,
  });

  // 狀態管理
  const [error, setError] = useState<string | null>(null);
  const [hoveredData, setHoveredData] = useState<KlineData | null>(null);
  const [hoveredSignal, setHoveredSignal] = useState<SignalPoint | null>(null);

  // 保存 series 引用，用於 cleanup
  const candlestickSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const indicatorLineRefs = useRef<ISeriesApi<"Line">[]>([]);

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
            color: "#2196F3", // 藍色 - TO
            shape: "arrowDown" as const,
            text: "TO",
          });
          markers.push({
            time: toUtcTime(tcTimestamp),
            position: "aboveBar" as const,
            color: "#FF9800", // 橙色 - TC
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

      // 2. 添加策略信號標記 (綠色向上箭頭)
      if (showSignalMarkers && signalPoints.length > 0) {
        signalPoints.forEach((signal) => {
          markers.push({
            time: toUtcTime(signal.timestamp),
            position: "belowBar" as const,
            color: "#4CAF50", // 綠色 - 信號
            shape: "arrowUp" as const,
            text: "S", // Signal
            id: `signal-${signal.timestamp}`, // 用於點擊識別
          });
        });

        console.log(
          `[StrategySignalChart] Added ${signalPoints.length} signal markers`
        );
      }

      // 設置所有標記
      candlestickSeries.setMarkers(markers);

      // 設置可見範圍為所有 K線
      if (formattedKlines.length > 0) {
        const firstTime = formattedKlines[0].time;
        const lastTime = formattedKlines[formattedKlines.length - 1].time;
        chartInstance.timeScale().setVisibleRange({
          from: firstTime,
          to: lastTime,
        });
      }

      console.log(`[StrategySignalChart] Rendered ${formattedKlines.length} klines and ${markers.length} markers for ${symbol}`);

      // 訂閱懸停事件 (用於顯示 OHLCV 和信號資訊)
      const handleCrosshairMove = (param: MouseEventParams<Time>) => {
        const hoveredTime = extractNumericTime(param.time);
        if (hoveredTime !== null) {
          // 查找懸停的 K線
          const hoveredKline = klines.find((k) => k.timestamp === hoveredTime);
          if (hoveredKline) {
            setHoveredData(hoveredKline);
          }

          // 查找懸停的信號點
          const hoveredSignalPoint = signalPoints.find(
            (s) => s.timestamp === hoveredTime
          );
          if (hoveredSignalPoint) {
            setHoveredSignal(hoveredSignalPoint);

            // 觸發回調
            if (onSignalHover) {
              const price =
                hoveredKline?.close || klines[klines.length - 1].close;
              onSignalHover({
                timestamp: hoveredSignalPoint.timestamp,
                indicator_values: hoveredSignalPoint.indicator_values,
                signal_density: hoveredSignalPoint.signal_density,
                price,
              });
            }
          } else {
            setHoveredSignal(null);
            if (onSignalHover) {
              onSignalHover(null);
            }
          }
        } else {
          setHoveredData(null);
          setHoveredSignal(null);
          if (onSignalHover) {
            onSignalHover(null);
          }
        }
      };

      chartInstance.subscribeCrosshairMove(handleCrosshairMove);

      // 訂閱點擊事件 (用於信號點擊)
      const handleClick = (param: MouseEventParams<Time>) => {
        const clickedTime = extractNumericTime(param.time);
        if (clickedTime !== null && onSignalClick) {
          const clickedSignal = signalPoints.find(
            (s) => s.timestamp === clickedTime
          );
          if (clickedSignal) {
            onSignalClick(clickedSignal);
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
    onSignalClick,
    onSignalHover,
  ]);

  useEffect(() => {
    if (!chartInstance || !isReady) return;
    indicatorLineRefs.current.forEach((line) => {
      try {
        chartInstance.removeSeries(line);
      } catch (err) {
        console.error("[StrategySignalChart] Indicator cleanup error", err);
      }
    });
    indicatorLineRefs.current = [];

    indicatorSeries.forEach((series) => {
      if (!series.data.length) return;
      const line = chartInstance.addLineSeries({
        color: series.color,
        lineWidth: 2,
        priceScaleId: "right",
        lastValueVisible: false,
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
      className="w-full flex flex-col bg-white"
      style={{ height: `${height}px` }}
    >
      {/* 頂部資訊欄 */}
      <div className="px-4 py-2 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h3 className="text-sm font-semibold text-gray-900">
            {symbol} / {timeframe}
          </h3>
          <span className="text-xs text-gray-500">策略信號圖表</span>

          {/* 信號統計 */}
          {showSignalMarkers && signalPoints.length > 0 && (
            <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded">
              {signalPoints.length} 個信號
            </span>
          )}
        </div>

        {/* OHLCV 懸停資訊 */}
        {hoveredData && (
          <div className="flex items-center gap-3 text-xs">
            <span className="text-gray-600">
              O: <span className="font-mono">{formatPrice(hoveredData.open)}</span>
            </span>
            <span className="text-gray-600">
              H: <span className="font-mono">{formatPrice(hoveredData.high)}</span>
            </span>
            <span className="text-gray-600">
              L: <span className="font-mono">{formatPrice(hoveredData.low)}</span>
            </span>
            <span className="text-gray-600">
              C:{" "}
              <span
                className={`font-mono ${
                  hoveredData.close >= hoveredData.open
                    ? "text-green-600"
                    : "text-red-600"
                }`}
              >
                {formatPrice(hoveredData.close)}
              </span>
            </span>
            <span className="text-gray-600">
              V: <span className="font-mono">{formatVolume(hoveredData.volume)}</span>
            </span>
            <span className="text-gray-400">
              {formatTime(hoveredData.timestamp)}
            </span>
          </div>
        )}
      </div>

      {/* 圖表容器 */}
      <div className="flex-1 relative">
        <div
          ref={chartContainerRef}
          className="absolute inset-0"
          style={{ width: "100%", height: "100%" }}
        />

        {/* 錯誤提示 */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-red-50">
            <div className="text-sm text-red-600">
              <span className="mr-2">⚠️</span>
              {error}
            </div>
          </div>
        )}

        {/* 載入中提示 */}
        {!isReady && !error && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
            <div className="text-sm text-gray-400">載入圖表中...</div>
          </div>
        )}
      </div>

      {/* 底部信號詳情 (懸停時顯示) */}
      {hoveredSignal && (
        <div className="px-4 py-2 border-t border-green-200 bg-green-50">
          <div className="flex items-center gap-4 text-xs">
            <span className="font-semibold text-green-700">📍 信號詳情:</span>
            {Object.entries(hoveredSignal.indicator_values).map(
              ([key, value]) => (
                <span key={key} className="text-gray-700">
                  {key}: <span className="font-mono">{value.toFixed(2)}</span>
                </span>
              )
            )}
            {hoveredSignal.signal_density !== undefined && (
              <span className="text-gray-700">
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

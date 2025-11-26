/**
 * TradingChartWithSignals.tsx - 帶策略信號的圖表容器
 *
 * Phase 3.3+3.4 - Task C: 圖表信號整合
 *
 * 功能:
 * - 整合 TradingChartContainer 的所有功能
 * - 添加策略信號可視化 (使用 StrategySignalChart)
 * - 信號工具提示 (SignalTooltip)
 * - 支持信號點擊和懸停交互
 * - 垂直堆疊: 策略信號圖 + 成交量圖 + Taker Ratio 圖
 *
 * Ultra Think 記錄:
 * - 步驟 1: 初版代碼 (當前)
 * - 步驟 2: 審查優化 (待執行)
 * - 步驟 3: 最終優化 (待執行)
 */

"use client";

import React, { useRef, useEffect, useState, useMemo, useCallback } from "react";
import { StrategySignalChart, KlineData, SignalPoint } from "./StrategySignalChart";
import { VolumeChart } from "./VolumeChart";
import { TakerRatioChart } from "./TakerRatioChart";
import SignalTooltip, { SignalTooltipData } from "./SignalTooltip";
import { TimeAxisProvider, useTimeAxis } from "@/contexts/TimeAxisContext";

export interface IndicatorLineSeries {
  id: string;
  label: string;
  color: string;
  data: Array<{ time: number; value: number }>;
}

export interface WindowOverlayRange {
  type: "near" | "far";
  startTimestamp: number;
  endTimestamp: number;
}

/**
 * TradingChartWithSignals Props
 */
export interface TradingChartWithSignalsProps {
  /**
   * 交易對 symbol
   */
  symbol: string;

  /**
   * 時間框架
   */
  timeframe: string;

  /**
   * K 線數據數組
   */
  klines: KlineData[];

  /**
   * 策略信號點數組
   */
  signalPoints?: SignalPoint[];

  /**
   * TO 時間戳（對齊後的案例開始時間，Unix 秒）
   */
  toTimestamp?: number;

  /**
   * TC 時間戳（對齊後的案例結束時間，Unix 秒，可選）
   */
  tcTimestamp?: number;

  /**
   * 容器總高度（像素），默認 800px
   */
  totalHeight?: number;

  /**
   * 是否顯示 TO/TC 點標記
   */
  showCaseMarker?: boolean;

  /**
   * 是否顯示策略信號標記
   */
  showSignalMarkers?: boolean;

  /**
   * 是否在成交量和 Taker Ratio 圖表顯示 TO/TC 標線（默認 true）
   */
  showVolumeToTcMarkers?: boolean;

  /**
   * 信號點擊回調
   */
  onSignalClick?: (signal: SignalPoint) => void;

  /**
   * 指標線資料 (如 EMA) - 顯示在 Price 圖表上
   * @deprecated 使用 priceIndicatorSeries 替代
   */
  indicatorSeries?: IndicatorLineSeries[];

  /**
   * Price 圖表的指標線資料（基於 OHLC 計算的指標）
   */
  priceIndicatorSeries?: IndicatorLineSeries[];

  /**
   * Volume 圖表的指標線資料（基於 volume 計算的指標）
   */
  volumeIndicatorSeries?: IndicatorLineSeries[];

  /**
   * Taker Ratio 圖表的指標線資料（基於 taker_ratio/taker_buy_volume 計算的指標）
   */
  takerIndicatorSeries?: IndicatorLineSeries[];

  /**
   * 近/遠窗口覆蓋範圍
   */
  windowOverlays?: WindowOverlayRange[];

  /**
   * Volume 圖表的策略信號點
   */
  volumeSignalPoints?: SignalPoint[];

  /**
   * Taker Ratio 圖表的策略信號點
   */
  takerSignalPoints?: SignalPoint[];
}

/**
 * TradingChartWithSignals 組件
 *
 * 垂直堆疊三個圖表，並添加策略信號可視化
 */
export function TradingChartWithSignals(props: TradingChartWithSignalsProps) {
  return (
    <TimeAxisProvider debug={false}>
      <TradingChartWithSignalsInner {...props} />
    </TimeAxisProvider>
  );
}

/**
 * 內部組件（可以使用 TimeAxisContext）
 */
function TradingChartWithSignalsInner({
  symbol,
  timeframe,
  klines,
  signalPoints = [],
  toTimestamp,
  tcTimestamp,
  totalHeight = 800,
  showCaseMarker = true,
  showSignalMarkers = true,
  showVolumeToTcMarkers = true,
  onSignalClick,
  indicatorSeries = [],
  priceIndicatorSeries,
  volumeIndicatorSeries = [],
  takerIndicatorSeries = [],
  windowOverlays = [],
  volumeSignalPoints = [],
  takerSignalPoints = [],
}: TradingChartWithSignalsProps) {
  // 合併 indicatorSeries 和 priceIndicatorSeries（向後兼容）
  const effectivePriceIndicatorSeries = priceIndicatorSeries ?? indicatorSeries;
  
  // ===== Refs =====
  const containerRef = useRef<HTMLDivElement>(null);

  // ===== Context =====
  const { resetToCenter } = useTimeAxis();
  
  // 使用 ref 穩定 resetToCenter，避免 useEffect 重複執行
  const resetToCenterRef = useRef(resetToCenter);
  resetToCenterRef.current = resetToCenter;

  // ===== State =====
  const [isInitialized, setIsInitialized] = useState(false);
  const [hoveredSignal, setHoveredSignal] = useState<SignalTooltipData | null>(
    null
  );
  const [mousePosition, setMousePosition] = useState<{ x: number; y: number }>({
    x: 0,
    y: 0,
  });
  const [crosshairX, setCrosshairX] = useState<number | null>(null);

  // ===== 高度分配（調整為 K線:成交量:Taker = 10:7:7 比例）=====
  const priceHeight = Math.floor(totalHeight * 0.42); // 42% - 策略信號圖
  const volumeHeight = Math.floor(totalHeight * 0.29); // 29% - 成交量圖（約為 K 線的 70%）
  const takerRatioHeight = Math.floor(totalHeight * 0.29); // 29% - Taker Ratio 圖（約為 K 線的 70%）

  const timelineRange = useMemo(() => {
    if (!klines.length) return null;
    const first = klines[0].timestamp;
    const last = klines[klines.length - 1].timestamp;
    return {
      start: first,
      end: last,
      total: Math.max(last - first, 1),
    };
  }, [klines]);

  const overlayRects = useMemo(() => {
    if (!timelineRange || windowOverlays.length === 0) return [];
    return windowOverlays
      .map((overlay) => {
        const clampedStart = Math.max(
          timelineRange.start,
          Math.min(overlay.startTimestamp, timelineRange.end)
        );
        const clampedEnd = Math.max(
          timelineRange.start,
          Math.min(overlay.endTimestamp, timelineRange.end)
        );
        if (clampedEnd <= clampedStart) {
          return null;
        }
        const left = ((clampedStart - timelineRange.start) / timelineRange.total) * 100;
        const width = ((clampedEnd - clampedStart) / timelineRange.total) * 100;
        return {
          ...overlay,
          left,
          width,
        };
      })
      .filter((rect): rect is WindowOverlayRange & { left: number; width: number } =>
        rect !== null && rect.width > 0
      );
  }, [timelineRange, windowOverlays]);

  const verticalLines = useMemo(() => {
    if (!timelineRange) return [];
    const toPercent = (timestamp?: number) => {
      if (!timestamp) return null;
      const clamped = Math.max(
        timelineRange.start,
        Math.min(timestamp, timelineRange.end)
      );
      return ((clamped - timelineRange.start) / timelineRange.total) * 100;
    };

    const lines: Array<{ label: string; color: string; left: number }> = [];
    const toLeft = toPercent(toTimestamp);
    if (toLeft !== null) {
      lines.push({ label: "TO", color: "#4338ca", left: toLeft });
    }
    const tcLeft = toPercent(tcTimestamp);
    if (tcLeft !== null) {
      lines.push({ label: "TC", color: "#ea580c", left: tcLeft });
    }
    return lines.filter((line) => line.left >= 0 && line.left <= 100);
  }, [timelineRange, toTimestamp, tcTimestamp]);

  /**
   * 初始化延遲（避免刷新歪掉）+ 初始同步
   */
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsInitialized(true);
      // 初始化完成後，觸發一次 fitContent 同步所有圖表
      setTimeout(() => {
        resetToCenterRef.current(toTimestamp || 0);
      }, 100);
    }, 50);
    return () => clearTimeout(timer);
  }, [toTimestamp]); // 移除 resetToCenter 依賴，使用 ref

  /**
   * 監聽滑鼠移動，用於 tooltip 位置
   */
  useEffect(() => {
    if (!containerRef.current) return;

    const handleMouseMove = (e: MouseEvent) => {
      // 更新滑鼠位置（用於 tooltip）
      setMousePosition({ x: e.clientX, y: e.clientY });
    };

    const handleMouseLeave = () => {
      setHoveredSignal(null);
    };

    const container = containerRef.current;
    container.addEventListener("mousemove", handleMouseMove);
    container.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      container.removeEventListener("mousemove", handleMouseMove);
      container.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, []);

  /**
   * 處理信號懸停
   */
  const handleSignalHover = useCallback((signal: SignalTooltipData | null) => {
    setHoveredSignal(signal);
  }, []);

  /**
   * 處理信號點擊
   */
  const handleSignalClick = useCallback((signal: SignalPoint) => {
    console.log("[TradingChartWithSignals] Signal clicked:", signal);
    onSignalClick?.(signal);
  }, [onSignalClick]);

  return (
    <div
      ref={containerRef}
      className="relative w-full bg-white rounded-lg shadow-md overflow-hidden"
      style={{ height: `${totalHeight}px` }}
    >
      {overlayRects.map((overlay) => (
        <div
          key={`${overlay.type}-${overlay.left.toFixed(2)}`}
          className="absolute inset-y-0 pointer-events-none"
          style={{
            left: `${overlay.left}%`,
            width: `${overlay.width}%`,
            backgroundColor:
              overlay.type === "near"
                ? "rgba(79, 70, 229, 0.08)"
                : "rgba(168, 85, 247, 0.08)",
          }}
        />
      ))}

      {verticalLines.map((line) => (
        <div
          key={`line-${line.label}`}
          className="absolute top-0 bottom-0 pointer-events-none"
          style={{
            left: `${line.left}%`,
            width: "1px",
            backgroundColor: line.color,
          }}
        >
          <span className="absolute -top-2 -translate-x-1/2 rounded bg-slate-900 px-1 text-[10px] font-semibold text-white">
            {line.label}
          </span>
        </div>
      ))}

      {/* 十字線疊層（貫穿三個圖表的灰色虛線） */}
      {crosshairX !== null && (
        <div
          className="absolute top-0 bottom-0 pointer-events-none z-30"
          style={{
            left: `${crosshairX}px`,
            width: "1px",
            borderLeft: "1px dashed rgba(128, 128, 128, 0.6)",
          }}
        />
      )}

      {/* 三個圖表垂直堆疊 */}
      <div className="relative z-10 w-full h-full flex flex-col">
        {!isInitialized ? (
          <div className="flex items-center justify-center w-full h-full">
            <div className="text-gray-400 text-sm">初始化中...</div>
          </div>
        ) : (
          <>
            {/* 1. Strategy Signal Chart (策略信號圖) - 50% 高度 */}
            <div
              className="w-full border-b border-gray-200"
              style={{ height: `${priceHeight}px` }}
            >
              <StrategySignalChart
                symbol={symbol}
                timeframe={timeframe}
                klines={klines}
                signalPoints={signalPoints}
                toTimestamp={toTimestamp}
                tcTimestamp={tcTimestamp}
                height={priceHeight}
                showCaseMarker={showCaseMarker}
                showSignalMarkers={showSignalMarkers}
                chartId="strategy-signal-chart"
                enableSync={true}
                onSignalHover={handleSignalHover}
                onSignalClick={handleSignalClick}
                indicatorSeries={effectivePriceIndicatorSeries}
              />
            </div>

            {/* 2. Volume Chart (成交量圖) - 25% 高度 */}
            <div
              className="w-full border-b border-gray-200"
              style={{ height: `${volumeHeight}px` }}
            >
              <VolumeChart
                symbol={symbol}
                timeframe={timeframe}
                klines={klines}
                height={volumeHeight}
                chartId="volume-chart"
                enableSync={true}
                toTimestamp={showVolumeToTcMarkers ? toTimestamp : undefined}
                tcTimestamp={showVolumeToTcMarkers ? tcTimestamp : undefined}
                windowOverlays={windowOverlays}
                indicatorSeries={volumeIndicatorSeries}
                signalPoints={volumeSignalPoints}
              />
            </div>

            {/* 3. Taker Ratio Chart (Taker 比率圖) - 25% 高度 */}
            <div className="w-full" style={{ height: `${takerRatioHeight}px` }}>
              <TakerRatioChart
                symbol={symbol}
                timeframe={timeframe}
                klines={klines}
                height={takerRatioHeight}
                chartId="taker-ratio-chart"
                enableSync={true}
                toTimestamp={showVolumeToTcMarkers ? toTimestamp : undefined}
                tcTimestamp={showVolumeToTcMarkers ? tcTimestamp : undefined}
                windowOverlays={windowOverlays}
                indicatorSeries={takerIndicatorSeries}
                signalPoints={takerSignalPoints}
              />
            </div>
          </>
        )}
      </div>

      {/* 信號工具提示 */}
      <SignalTooltip
        data={hoveredSignal}
        mousePosition={mousePosition}
        showArrow={true}
      />
    </div>
  );
}

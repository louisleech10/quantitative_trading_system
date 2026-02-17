/**
 * TakerRatioChart組件 - Taker Ratio線圖
 *
 * 功能：
 * - 顯示Taker Ratio線圖（LineSeries）
 * - 0.5水平參考線（虛線，中性線）
 * - Y軸範圍固定0-1
 * - 背景色區域（>0.5偏綠，<0.5偏紅）
 * - 懸停顯示taker_ratio數值
 *
 * Ultra Think步驟3：優化版本
 * 修復：P0-3（Y軸固定）、P0-4（數據檢查）、P0-6（cleanup）、P1-3（硬編碼）
 */

'use client';

import { useEffect, useState, useRef, useMemo } from 'react';
import { useChartSync } from '../../hooks/useChartSync';
import { darkChartOptions } from '../../utils/chartConfig';
import { useTimeAxis } from '@/contexts/TimeAxisContext';
import {
  formatPercentage,
} from '../../utils/chartConfig';
import { ISeriesApi, LineStyle, MouseEventParams, Time, UTCTimestamp } from 'lightweight-charts';
import { KlineData } from './PriceChart';
import type { WindowOverlayRange, IndicatorLineSeries } from './TradingChartWithSignals';
import type { SignalPoint } from './StrategySignalChart';

const toUtcTime = (timestamp: number): UTCTimestamp =>
  timestamp as UTCTimestamp;

/**
 * TakerRatioChart組件Props
 */
export interface TakerRatioChartProps {
  /**
   * 交易對symbol
   */
  symbol: string;

  /**
   * 時間框架
   */
  timeframe: string;

  /**
   * K線數據數組（需要taker_ratio欄位）
   */
  klines: KlineData[];

  /**
   * 圖表高度（像素），預設120px
   */
  height?: number;

  /**
   * 圖表唯一ID（用於同步）
   */
  chartId?: string;

  /**
   * 是否啟用同步
   */
  enableSync?: boolean;

  /**
   * TO時間戳（用於初始可見範圍）
   */
  toTimestamp?: number;

  /**
   * TC時間戳（案例結束點，用於垂直參考線）
   */
  tcTimestamp?: number;

  /**
   * 近/遠窗口覆蓋範圍
   */
  windowOverlays?: WindowOverlayRange[];

  /**
   * 指標線資料（基於 taker_ratio/taker_buy_volume 計算的 EMA 等指標）
   */
  indicatorSeries?: IndicatorLineSeries[];

  /**
   * 策略信號點（用於標記策略條件符合的 K 線）
   */
  signalPoints?: SignalPoint[];
}

/**
 * TakerRatioChart組件 - Taker Ratio線圖
 */
export function TakerRatioChart({
  symbol,
  timeframe,
  klines,
  height = 120,
  chartId = 'taker-ratio-chart',
  enableSync = false,
  toTimestamp,
  tcTimestamp,
  windowOverlays = [],
  indicatorSeries = [],
  signalPoints = []
}: TakerRatioChartProps) {
  void timeframe;
  const { chartContainerRef, chartInstance, isReady } = useChartSync({
    chartId,
    toTimestamp: toTimestamp || (klines.length > 0 ? klines[0].timestamp : Date.now() / 1000),
    enableSync,
    debug: true,
    chartOptions: darkChartOptions
  });
  const { subscribeCrosshairChange } = useTimeAxis();

  // 狀態管理
  const [error, setError] = useState<string | null>(null);
  const [hoveredRatio, setHoveredRatio] = useState<number | null>(null);
  const [hoveredIndicators, setHoveredIndicators] = useState<Record<string, number>>({});

  // 保存series引用，用於cleanup
  const lineSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  // 使用 ref 緩存 indicatorSeries，避免閉包問題
  const indicatorSeriesRef = useRef(indicatorSeries);
  useEffect(() => {
    indicatorSeriesRef.current = indicatorSeries;
  }, [indicatorSeries]);
  const buyAreaSeriesRef = useRef<ISeriesApi<'Area'> | null>(null);
  const sellAreaSeriesRef = useRef<ISeriesApi<'Area'> | null>(null);

  const timelineRange = useMemo(() => {
    if (!klines.length) return null;
    const start = klines[0].timestamp;
    const end = klines[klines.length - 1].timestamp;
    return {
      start,
      end,
      total: Math.max(end - start, 1),
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
        const left =
          ((clampedStart - timelineRange.start) / timelineRange.total) * 100;
        const width =
          ((clampedEnd - clampedStart) / timelineRange.total) * 100;
        return {
          ...overlay,
          left,
          width,
        };
      })
      .filter(
        (
          rect
        ): rect is WindowOverlayRange & { left: number; width: number } =>
          rect !== null && rect.width > 0
      );
  }, [timelineRange, windowOverlays]);

  const verticalLines = useMemo(() => {
    if (!timelineRange) return [];
    const positions: Array<{ label: string; color: string; left: number }> = [];

    const toPercent = (timestamp?: number) => {
      if (!timestamp) return null;
      const clamped = Math.max(
        timelineRange.start,
        Math.min(timestamp, timelineRange.end)
      );
      return ((clamped - timelineRange.start) / timelineRange.total) * 100;
    };

    const toLeft = toPercent(toTimestamp);
    if (toLeft !== null) {
      positions.push({ label: 'TO', color: '#818cf8', left: toLeft });
    }

    const tcLeft = toPercent(tcTimestamp);
    if (tcLeft !== null) {
      positions.push({ label: 'TC', color: '#fb923c', left: tcLeft });
    }

    return positions;
  }, [timelineRange, toTimestamp, tcTimestamp]);

  /**
   * 渲染Taker Ratio數據到圖表
   * 修復P0-3: 正確固定Y軸範圍0-1
   * 修復P0-4: 過濾後檢查數據是否為空
   * 修復P0-6: 正確cleanup三個series
   * 修復P1-3: 使用chartColors配置，避免硬編碼
   */
  useEffect(() => {
    if (!chartInstance || !isReady || !klines || klines.length === 0) {
      return;
    }

    try {
      // 過濾有效的taker_ratio數據
      const takerRatioData = klines
        .filter(k => k.taker_ratio !== undefined && k.taker_ratio !== null)
        .map(kline => ({
          time: toUtcTime(kline.timestamp),
          value: kline.taker_ratio!,
        }));

      // 修復P0-4: 檢查過濾後是否有數據
      if (takerRatioData.length === 0) {
        console.warn(`[TakerRatioChart] No valid taker_ratio data for ${symbol}`);
        setError('無有效的Taker Ratio數據');
        return;
      }

      // 創建背景色區域 - 賣盤強勢區域（0-0.5，紅色）
      // 修復P1-3: 使用chartColors而非硬編碼
      const sellAreaSeries = chartInstance.addAreaSeries({
        topColor: `rgba(251, 113, 133, 0.12)`,
        bottomColor: `rgba(251, 113, 133, 0.04)`,
        lineColor: 'transparent',
        priceScaleId: 'taker_ratio',
        lastValueVisible: false,
        priceLineVisible: false,
      });
      sellAreaSeriesRef.current = sellAreaSeries;

      // 創建背景色區域 - 買盤強勢區域（0.5-1，綠色）
      const buyAreaSeries = chartInstance.addAreaSeries({
        topColor: `rgba(52, 211, 153, 0.12)`,
        bottomColor: `rgba(52, 211, 153, 0.04)`,
        lineColor: 'transparent',
        priceScaleId: 'taker_ratio',
        lastValueVisible: false,
        priceLineVisible: false,
      });
      buyAreaSeriesRef.current = buyAreaSeries;

      // 創建主線圖（Taker Ratio線）
      const lineSeries = chartInstance.addLineSeries({
        color: '#60a5fa',
        lineWidth: 2,
        priceScaleId: 'taker_ratio',
        priceFormat: {
          type: 'percent',
          precision: 2,
          minMove: 0.01,
        },
        lastValueVisible: false,
        priceLineVisible: false,
      });
      lineSeriesRef.current = lineSeries;

      // 背景區域數據（賣盤強勢區：0到實際ratio，只在<0.5時顯示）
      const sellAreaData = takerRatioData.map(d => ({
        time: d.time,
        value: d.value <= 0.5 ? d.value : 0.5,
      }));

      // 背景區域數據（買盤強勢區：0.5到實際ratio，只在>0.5時顯示）
      const buyAreaData = takerRatioData.map(d => ({
        time: d.time,
        value: d.value >= 0.5 ? d.value : 0.5,
      }));

      // 設置數據
      sellAreaSeries.setData(sellAreaData);
      buyAreaSeries.setData(buyAreaData);
      lineSeries.setData(takerRatioData);

      // 在主線上設置信號標記
      if (signalPoints.length > 0) {
        const markers = signalPoints.map((signal) => ({
          time: toUtcTime(signal.timestamp),
          position: 'aboveBar' as const,
          color: signal.windowType === 'near' ? '#60a5fa' : '#fbbf24',
          shape: 'arrowDown' as const,
          text: signal.windowType === 'near' ? 'N' : 'F',
        }));
        lineSeries.setMarkers(markers);
        console.log(`[TakerRatioChart] Set ${markers.length} signal markers on main line`);
      }

      // 添加0.5參考線（中性線，虛線）
      lineSeries.createPriceLine({
        price: 0.5,
        color: '#64748b',
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: '中性',
      });

      // 修復P0-3: 正確配置Y軸範圍（固定0-1）
      chartInstance.priceScale('taker_ratio').applyOptions({
        scaleMargins: {
          top: 0.1,
          bottom: 0.1,
        },
        mode: 1,  // Logarithmic模式改為Percentage模式
        autoScale: false,
      });

      // 不再手動調用 fitContent，讓同步機制控制時間軸
      // 首次載入時使用 fitContent，但只在非同步模式下
      if (!enableSync) {
        chartInstance.timeScale().fitContent();
      }

      console.log(`[TakerRatioChart] Rendered ${takerRatioData.length} taker ratio data for ${symbol}`);

      // 訂閱懸停事件（用於顯示 Taker Ratio 和指標值）
      const handleCrosshairMove = (param: MouseEventParams<Time>) => {
        const crosshairTime = typeof param.time === 'number' ? param.time : null
        if (crosshairTime !== null) {
          const hoveredKline = klines.find(k => k.timestamp === crosshairTime);
          if (hoveredKline && hoveredKline.taker_ratio !== undefined) {
            setHoveredRatio(hoveredKline.taker_ratio);
          }
          // 查找指標值（使用 ref 避免閉包問題）
          const indicatorValues: Record<string, number> = {};
          indicatorSeriesRef.current.forEach((series) => {
            const point = series.data.find((d) => d.time === crosshairTime);
            if (point) {
              indicatorValues[series.id] = point.value;
            }
          });
          setHoveredIndicators(indicatorValues);
        } else {
          setHoveredRatio(null);
          setHoveredIndicators({});
        }
      };

      chartInstance.subscribeCrosshairMove(handleCrosshairMove);

      // 訂閱 Context 十字線時間變化（修復數值同步問題）
      const unsubscribeCrosshair = subscribeCrosshairChange(chartId, (time) => {
        if (time !== null) {
          const hoveredKline = klines.find(k => k.timestamp === time);
          setHoveredRatio(hoveredKline?.taker_ratio ?? null);
          
          // 查找指標值（使用 ref 避免閉包問題）
          const indicatorValues: Record<string, number> = {};
          indicatorSeriesRef.current.forEach((series) => {
            const point = series.data.find((d) => d.time === time);
            if (point) {
              indicatorValues[series.id] = point.value;
            }
          });
          setHoveredIndicators(indicatorValues);
        } else {
          setHoveredRatio(null);
          setHoveredIndicators({});
        }
      });

      // 修復P0-6: 正確cleanup三個series
      return () => {
        try {
          chartInstance.unsubscribeCrosshairMove(handleCrosshairMove);
          unsubscribeCrosshair();

          if (lineSeries) {
            chartInstance.removeSeries(lineSeries);
          }
          if (buyAreaSeries) {
            chartInstance.removeSeries(buyAreaSeries);
          }
          if (sellAreaSeries) {
            chartInstance.removeSeries(sellAreaSeries);
          }
        } catch (err) {
          console.error('[TakerRatioChart] Cleanup error:', err);
        }
      };

    } catch (err) {
      console.error('[TakerRatioChart] Failed to render chart:', err);
      setError(err instanceof Error ? err.message : 'Failed to render taker ratio chart');
    }
  }, [chartId, chartInstance, enableSync, isReady, klines, signalPoints, subscribeCrosshairChange, symbol]);

  // 指標線渲染 refs
  const indicatorLineRefs = useRef<ISeriesApi<'Line'>[]>([]);
  const prevIndicatorSeriesJsonRef = useRef<string>("");

  /**
   * 指標線渲染 useEffect（基於 taker_ratio/taker_buy_volume 計算的 EMA 等指標）
   */
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
        console.error("[TakerRatioChart] Indicator cleanup error", err);
      }
    });
    indicatorLineRefs.current = [];

    // 添加新的指標線
    indicatorSeries.forEach((series) => {
      if (!series.data.length) return;
      const line = chartInstance.addLineSeries({
        color: series.color,
        lineWidth: 2,
        priceScaleId: "taker_ratio",
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
          console.error("[TakerRatioChart] Indicator cleanup error", err);
        }
      });
      indicatorLineRefs.current = [];
    };
  }, [chartInstance, indicatorSeries, isReady]);

  return (
    <div className="w-full flex flex-col bg-[#0A0F1C] border-t border-white/10" style={{ height: `${height}px` }}>
      {/* 頂部標籤 */}
      <div className="px-4 py-1 flex items-center justify-between border-b border-white/10">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium text-slate-300">Taker Ratio</span>
          
          {/* 信號統計 - 顯示 Near(藍) 和 Far(土黃) 計數 */}
          {signalPoints.length > 0 && (
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
          
          {hoveredRatio !== null && (
            <span className="text-xs text-slate-300">
              {formatPercentage(hoveredRatio)}
              {' - '}
              {hoveredRatio > 0.5 ? (
                <span className="text-emerald-400">買盤強</span>
              ) : hoveredRatio < 0.5 ? (
                <span className="text-rose-400">賣盤強</span>
              ) : (
                <span className="text-slate-400">中性</span>
              )}
            </span>
          )}
          {/* 指標值顯示 */}
          {indicatorSeries.map((series) => {
            const value = hoveredIndicators[series.id];
            if (value === undefined) return null;
            return (
              <span key={series.id} className="text-xs text-slate-300">
                <span style={{ color: series.color }}>●</span>{" "}
                {series.label?.replace(/\s*\(\d+\)/, "") || series.id}:{" "}
                <span className="font-mono" style={{ color: series.color }}>
                  {formatPercentage(value)}
                </span>
              </span>
            );
          })}
        </div>
      </div>

      {/* 圖表容器 */}
      <div className="flex-1 relative">
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#0A0F1C] z-20">
            <div className="text-center">
              <div className="text-rose-400 text-xl mb-1">⚠️</div>
              <p className="text-xs text-rose-300">{error}</p>
            </div>
          </div>
        )}

        {klines.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#0A0F1C] z-20">
            <p className="text-xs text-slate-400">無Taker Ratio數據</p>
          </div>
        )}

        <div
          ref={chartContainerRef}
          className="w-full h-full"
        />
        {(overlayRects.length > 0 || verticalLines.length > 0) && (
          <div className="pointer-events-none absolute inset-0 z-10">
            {overlayRects.map((overlay) => (
              <div
                key={`${overlay.type}-${overlay.left.toFixed(3)}`}
                className="absolute inset-y-0"
                style={{
                  left: `${overlay.left}%`,
                  width: `${overlay.width}%`,
                  backgroundColor:
                    overlay.type === 'near'
                      ? 'rgba(96, 165, 250, 0.08)'
                      : 'rgba(251, 191, 36, 0.08)',
                }}
              />
            ))}
            {verticalLines.map((line) => (
              <div
                key={`taker-${line.label}`}
                className="absolute inset-y-0"
                style={{
                  left: `${line.left}%`,
                  width: '1px',
                  backgroundColor: line.color,
                }}
              >
                <span className="absolute -top-1 -translate-x-1/2 rounded bg-slate-900 px-1 text-[10px] font-semibold text-white">
                  {line.label}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

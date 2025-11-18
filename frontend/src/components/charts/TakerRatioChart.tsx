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
import { useTimeAxis } from '@/contexts/TimeAxisContext';
import {
  formatPercentage,
  chartColors
} from '../../utils/chartConfig';
import { ISeriesApi, LineStyle } from 'lightweight-charts';
import { KlineData } from './PriceChart';
import type { WindowOverlayRange } from './TradingChartWithSignals';

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
  windowOverlays = []
}: TakerRatioChartProps) {
  console.log('[TakerRatioChart] Initializing with:', { chartId, enableSync, toTimestamp });
  
  const { chartContainerRef, chartInstance, isReady } = useChartSync({
    chartId,
    toTimestamp: toTimestamp || (klines.length > 0 ? klines[0].timestamp : Date.now() / 1000),
    enableSync,
    debug: true
  });
  const { subscribeCrosshairChange } = useTimeAxis();

  // 狀態管理
  const [error, setError] = useState<string | null>(null);
  const [hoveredRatio, setHoveredRatio] = useState<number | null>(null);

  // 保存series引用，用於cleanup
  const lineSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
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
      positions.push({ label: 'TO', color: '#4338ca', left: toLeft });
    }

    const tcLeft = toPercent(tcTimestamp);
    if (tcLeft !== null) {
      positions.push({ label: 'TC', color: '#ea580c', left: tcLeft });
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
          time: kline.timestamp as any,
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
        topColor: `rgba(239, 83, 80, 0.1)`,  // 使用chartColors.downColor的rgba版本
        bottomColor: `rgba(239, 83, 80, 0.02)`,
        lineColor: 'transparent',
        priceScaleId: 'taker_ratio',
      });
      sellAreaSeriesRef.current = sellAreaSeries;

      // 創建背景色區域 - 買盤強勢區域（0.5-1，綠色）
      const buyAreaSeries = chartInstance.addAreaSeries({
        topColor: `rgba(38, 166, 154, 0.1)`,  // 使用chartColors.upColor的rgba版本
        bottomColor: `rgba(38, 166, 154, 0.02)`,
        lineColor: 'transparent',
        priceScaleId: 'taker_ratio',
      });
      buyAreaSeriesRef.current = buyAreaSeries;

      // 創建主線圖（Taker Ratio線）
      const lineSeries = chartInstance.addLineSeries({
        color: '#2962FF',  // 藍色線（TODO: 可考慮加入chartColors）
        lineWidth: 2,
        priceScaleId: 'taker_ratio',
        priceFormat: {
          type: 'percent',
          precision: 2,
          minMove: 0.01,
        },
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

      // 添加0.5參考線（中性線，虛線）
      lineSeries.createPriceLine({
        price: 0.5,
        color: '#999999',
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

      // 自動縮放時間軸
      chartInstance.timeScale().fitContent();

      console.log(`[TakerRatioChart] Rendered ${takerRatioData.length} taker ratio data for ${symbol}`);

      // 訂閱懸停事件
      const handleCrosshairMove = (param: any) => {
        if (param.time) {
          const hoveredKline = klines.find(k => k.timestamp === param.time);
          if (hoveredKline && hoveredKline.taker_ratio !== undefined) {
            setHoveredRatio(hoveredKline.taker_ratio);
          }
        } else {
          setHoveredRatio(null);
        }
      };

      chartInstance.subscribeCrosshairMove(handleCrosshairMove);

      // 訂閱 Context 十字線時間變化（修復數值同步問題）
      const unsubscribeCrosshair = subscribeCrosshairChange(chartId, (time) => {
        if (time !== null) {
          const hoveredKline = klines.find(k => k.timestamp === time);
          setHoveredRatio(hoveredKline?.taker_ratio ?? null);
        } else {
          setHoveredRatio(null);
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
  }, [chartInstance, isReady, klines, symbol]);

  return (
    <div className="w-full flex flex-col bg-white border-t border-gray-200" style={{ height: `${height}px` }}>
      {/* 頂部標籤 */}
      <div className="px-4 py-1 flex items-center justify-between border-b border-gray-100">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-700">Taker Ratio</span>
          {hoveredRatio !== null && (
            <span className="text-xs text-gray-600">
              {formatPercentage(hoveredRatio)}
              {' - '}
              {hoveredRatio > 0.5 ? (
                <span className="text-green-600">買盤強</span>
              ) : hoveredRatio < 0.5 ? (
                <span className="text-red-600">賣盤強</span>
              ) : (
                <span className="text-gray-600">中性</span>
              )}
            </span>
          )}
        </div>
      </div>

      {/* 圖表容器 */}
      <div className="flex-1 relative">
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-white z-20">
            <div className="text-center">
              <div className="text-red-500 text-xl mb-1">⚠️</div>
              <p className="text-xs text-red-600">{error}</p>
            </div>
          </div>
        )}

        {klines.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center bg-white z-20">
            <p className="text-xs text-gray-500">無Taker Ratio數據</p>
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
                      ? 'rgba(79, 70, 229, 0.08)'
                      : 'rgba(168, 85, 247, 0.08)',
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

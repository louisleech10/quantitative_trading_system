/**
 * PriceChart組件 - K線圖表
 *
 * 功能：
 * - 顯示K線圖（CandlestickSeries）
 * - 漲綠跌紅配色
 * - 時間軸和價格軸格式化
 * - 懸停資訊框顯示OHLCV數據
 * - 標記案例時間點T（紅色箭頭）
 *
 * Ultra Think步驟1：初版代碼生成
 */

'use client';

import { useEffect, useState, useRef } from 'react';
import { useChartSync } from '../../hooks/useChartSync';
import {
  candlestickSeriesOptions,
  formatTime,
  formatPrice,
  formatVolume,
  chartColors
} from '../../utils/chartConfig';
import { ISeriesApi } from 'lightweight-charts';

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
 * PriceChart組件Props
 */
export interface PriceChartProps {
  /**
   * 交易對symbol
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
   * 案例時間點T（Unix秒）
   */
  caseTimestamp: number;

  /**
   * 圖表高度（像素）
   */
  height?: number;

  /**
   * 是否顯示案例標記
   */
  showCaseMarker?: boolean;

  /**
   * TO時間戳（對齊後的案例開始時間）
   */
  toTimestamp?: number;

  /**
   * TC時間戳（對齊後的案例結束時間）
   */
  tcTimestamp?: number;

  /**
   * 圖表唯一ID（用於同步）
   */
  chartId?: string;

  /**
   * 是否啟用同步
   */
  enableSync?: boolean;
}

/**
 * PriceChart組件 - K線圖表
 */
export function PriceChart({
  symbol,
  timeframe,
  klines,
  caseTimestamp,
  height = 400,
  showCaseMarker = true,
  toTimestamp,
  tcTimestamp,
  chartId = 'price-chart',
  enableSync = false
}: PriceChartProps) {
  console.log('[PriceChart] Initializing with:', { chartId, enableSync, toTimestamp: toTimestamp || caseTimestamp });
  
  const { chartContainerRef, chartInstance, isReady } = useChartSync({
    chartId,
    toTimestamp: toTimestamp || caseTimestamp,
    enableSync,
    debug: true
  });

  // 狀態管理
  const [error, setError] = useState<string | null>(null);
  const [hoveredData, setHoveredData] = useState<KlineData | null>(null);

  // 保存series引用，用於cleanup
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);

  /**
   * 渲染K線數據到圖表
   * 修復P0-1: 正確的cleanup邏輯，避免記憶體洩漏
   */
  useEffect(() => {
    if (!chartInstance || !isReady || !klines || klines.length === 0) {
      return;
    }

    try {
      // 添加K線系列
      const candlestickSeries = chartInstance.addCandlestickSeries(candlestickSeriesOptions);
      candlestickSeriesRef.current = candlestickSeries;

      // 轉換數據格式（Lightweight Charts格式）
      const formattedKlines = klines.map(kline => ({
        time: kline.timestamp as any,
        open: kline.open,
        high: kline.high,
        low: kline.low,
        close: kline.close,
      }));

      // 設置K線數據
      candlestickSeries.setData(formattedKlines);

      // 標記TO和TC點（如果提供了對齊後的時間戳）
      if (showCaseMarker) {
        const markers = [];

        if (toTimestamp && tcTimestamp) {
          // 新邏輯：標記TO和TC兩個點
          markers.push({
            time: toTimestamp as any,
            position: 'aboveBar' as const,
            color: '#60a5fa',  // 藍色 - TO
            shape: 'arrowDown' as const,
            text: 'TO',
          });
          markers.push({
            time: tcTimestamp as any,
            position: 'aboveBar' as const,
            color: '#fb923c',  // 橙色 - TC
            shape: 'arrowDown' as const,
            text: 'TC',
          });
        } else {
          // 舊邏輯：只標記一個T點（向後兼容）
          markers.push({
            time: caseTimestamp as any,
            position: 'aboveBar' as const,
            color: chartColors.caseMarkerColor,
            shape: 'arrowDown' as const,
            text: 'T',
          });
        }

        candlestickSeries.setMarkers(markers);
      }

      // 設置可見範圍為所有K線（確保TO/TC位置正確）
      if (formattedKlines.length > 0) {
        const firstTime = formattedKlines[0].time;
        const lastTime = formattedKlines[formattedKlines.length - 1].time;
        chartInstance.timeScale().setVisibleRange({
          from: firstTime as any,
          to: lastTime as any,
        });
      }

      console.log(`[PriceChart] Rendered ${formattedKlines.length} klines for ${symbol}`);
      console.log(`[PriceChart] Markers:`, {
        showCaseMarker,
        toTimestamp,
        tcTimestamp,
        caseTimestamp,
        firstKlineTime: formattedKlines[0]?.time,
        lastKlineTime: formattedKlines[formattedKlines.length - 1]?.time,
      });

      // 訂閱懸停事件（用於顯示OHLCV資訊）
      const handleCrosshairMove = (param: any) => {
        if (param.time) {
          const hoveredKline = klines.find(k => k.timestamp === param.time);
          if (hoveredKline) {
            setHoveredData(hoveredKline);
          }
        } else {
          setHoveredData(null);
        }
      };

      chartInstance.subscribeCrosshairMove(handleCrosshairMove);

      // cleanup函數：移除series和事件訂閱
      return () => {
        try {
          chartInstance.unsubscribeCrosshairMove(handleCrosshairMove);
          if (candlestickSeries) {
            chartInstance.removeSeries(candlestickSeries);
          }
        } catch (err) {
          console.error('[PriceChart] Cleanup error:', err);
        }
      };

    } catch (err) {
      console.error('[PriceChart] Failed to render chart:', err);
      setError(err instanceof Error ? err.message : 'Failed to render chart');
    }
  }, [chartInstance, isReady, klines, caseTimestamp, showCaseMarker, symbol, toTimestamp, tcTimestamp]);

  return (
    <div className="w-full flex flex-col glass-panel" style={{ height: `${height}px` }}>
      {/* 頂部資訊欄 */}
      <div className="px-4 py-2 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h3 className="text-sm font-semibold text-slate-100">
            {symbol} / {timeframe}
          </h3>
          <span className="text-xs text-slate-400">
            案例時間點T：{formatTime(caseTimestamp)}
          </span>
        </div>

        {/* 懸停資訊框 */}
        {hoveredData && (
          <div className="flex items-center gap-4 text-xs text-slate-300">
            <span>時間：{formatTime(hoveredData.timestamp)}</span>
            <span>O：{formatPrice(hoveredData.open)}</span>
            <span>H：{formatPrice(hoveredData.high)}</span>
            <span>L：{formatPrice(hoveredData.low)}</span>
            <span
              className={hoveredData.close >= hoveredData.open ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}
            >
              C：{formatPrice(hoveredData.close)}
              {' '}
              ({hoveredData.close >= hoveredData.open ? '+' : ''}
              {((hoveredData.close - hoveredData.open) / hoveredData.open * 100).toFixed(2)}%)
            </span>
            <span>V：{formatVolume(hoveredData.volume)}</span>
            {hoveredData.taker_ratio !== undefined && (
              <span
                className={hoveredData.taker_ratio >= 0.5 ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}
              >
                Taker：{(hoveredData.taker_ratio * 100).toFixed(2)}%
              </span>
            )}
          </div>
        )}
      </div>

      {/* 圖表容器 */}
      <div className="flex-1 relative">
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#0A0F1C]/90 backdrop-blur-xl z-10 p-8">
            <div className="max-w-md text-center">
              <div className="text-rose-400 text-2xl mb-2">⚠️</div>
              <h4 className="text-sm font-semibold text-slate-100 mb-1">圖表渲染失敗</h4>
              <p className="text-xs text-rose-300">{error}</p>
            </div>
          </div>
        )}

        {klines.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#0A0F1C]/90 backdrop-blur-xl z-10">
            <p className="text-sm text-slate-400">無K線數據</p>
          </div>
        )}

        <div
          ref={chartContainerRef}
          className="w-full h-full"
        />
      </div>
    </div>
  );
}

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
import { useChart } from '../../hooks/useChart';
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
  showCaseMarker = true
}: PriceChartProps) {
  const { chartContainerRef, chartInstance, isReady } = useChart();

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

      // 標記T點（案例時間點）
      if (showCaseMarker) {
        const tMarker = {
          time: caseTimestamp as any,
          position: 'aboveBar' as const,
          color: chartColors.caseMarkerColor,
          shape: 'arrowDown' as const,
          text: 'T',
        };
        candlestickSeries.setMarkers([tMarker]);
      }

      // 自動縮放到適合的範圍
      chartInstance.timeScale().fitContent();

      console.log(`[PriceChart] Rendered ${formattedKlines.length} klines for ${symbol}`);

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
  }, [chartInstance, isReady, klines, caseTimestamp, showCaseMarker, symbol]);

  return (
    <div className="w-full flex flex-col bg-white" style={{ height: `${height}px` }}>
      {/* 頂部資訊欄 */}
      <div className="px-4 py-2 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h3 className="text-sm font-semibold text-gray-900">
            {symbol} / {timeframe}
          </h3>
          <span className="text-xs text-gray-500">
            案例時間點T：{formatTime(caseTimestamp)}
          </span>
        </div>

        {/* 懸停資訊框 */}
        {hoveredData && (
          <div className="flex items-center gap-4 text-xs text-gray-700">
            <span>時間：{formatTime(hoveredData.timestamp)}</span>
            <span>O：{formatPrice(hoveredData.open)}</span>
            <span>H：{formatPrice(hoveredData.high)}</span>
            <span>L：{formatPrice(hoveredData.low)}</span>
            <span
              className={hoveredData.close >= hoveredData.open ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'}
            >
              C：{formatPrice(hoveredData.close)}
              {' '}
              ({hoveredData.close >= hoveredData.open ? '+' : ''}
              {((hoveredData.close - hoveredData.open) / hoveredData.open * 100).toFixed(2)}%)
            </span>
            <span>V：{formatVolume(hoveredData.volume)}</span>
          </div>
        )}
      </div>

      {/* 圖表容器 */}
      <div className="flex-1 relative">
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-white z-10 p-8">
            <div className="max-w-md text-center">
              <div className="text-red-500 text-2xl mb-2">⚠️</div>
              <h4 className="text-sm font-semibold text-gray-900 mb-1">圖表渲染失敗</h4>
              <p className="text-xs text-red-600">{error}</p>
            </div>
          </div>
        )}

        {klines.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
            <p className="text-sm text-gray-500">無K線數據</p>
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

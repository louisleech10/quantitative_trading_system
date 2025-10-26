/**
 * VolumeChart組件 - 成交量柱狀圖
 *
 * 功能：
 * - 顯示成交量柱狀圖（HistogramSeries）
 * - 顏色跟隨價格漲跌（比較close和前一根的close）
 * - 高度約為Price圖的30%
 * - 懸停顯示成交量數值
 *
 * Ultra Think步驟1：初版代碼生成
 */

'use client';

import { useEffect, useState, useRef } from 'react';
import { useChartSync } from '../../hooks/useChartSync';
import { useTimeAxis } from '@/contexts/TimeAxisContext';
import {
  formatVolume,
  chartColors
} from '../../utils/chartConfig';
import { ISeriesApi } from 'lightweight-charts';
import { KlineData } from './PriceChart';

/**
 * 計算成交量柱的顏色（跟隨價格漲跌）
 * 修復P0-2: 移到組件外部，避免重複創建
 */
const calculateVolumeColor = (currentClose: number, prevClose: number | null, upColor: string, downColor: string): string => {
  if (prevClose === null) {
    // 第一根K線，默認綠色
    return upColor;
  }
  // 漲綠跌紅
  return currentClose >= prevClose ? upColor : downColor;
};

/**
 * VolumeChart組件Props
 */
export interface VolumeChartProps {
  /**
   * 交易對symbol
   */
  symbol: string;

  /**
   * 時間框架
   */
  timeframe: string;

  /**
   * K線數據數組（需要volume和close欄位）
   */
  klines: KlineData[];

  /**
   * 圖表高度（像素），預設120px（約為400px的30%）
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
}

/**
 * 成交量柱狀圖數據格式
 */
interface VolumeBarData {
  time: any;  // Lightweight Charts Time type
  value: number;
  color: string;
}

/**
 * VolumeChart組件 - 成交量柱狀圖
 */
export function VolumeChart({
  symbol,
  timeframe,
  klines,
  height = 120,
  chartId = 'volume-chart',
  enableSync = false,
  toTimestamp
}: VolumeChartProps) {
  console.log('[VolumeChart] Initializing with:', { chartId, enableSync, toTimestamp });
  
  const { chartContainerRef, chartInstance, isReady } = useChartSync({
    chartId,
    toTimestamp: toTimestamp || (klines.length > 0 ? klines[0].timestamp : Date.now() / 1000),
    enableSync,
    debug: true
  });
  const { subscribeCrosshairChange } = useTimeAxis();

  // 狀態管理
  const [error, setError] = useState<string | null>(null);
  const [hoveredVolume, setHoveredVolume] = useState<number | null>(null);

  // 保存series引用，用於cleanup
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  /**
   * 渲染成交量數據到圖表
   * 修復P0-1: 正確的cleanup邏輯
   * 修復P1-4: 配置priceScale選項
   */
  useEffect(() => {
    if (!chartInstance || !isReady || !klines || klines.length === 0) {
      return;
    }

    try {
      // 添加柱狀圖系列（使用默認的 right price scale）
      const volumeSeries = chartInstance.addHistogramSeries({
        color: chartColors.upColor,
        priceFormat: {
          type: 'volume',
        },
        // 移除 priceScaleId，使用默認的 'right'，這樣可以啟用 Y 軸拖曳縮放
      });
      volumeSeriesRef.current = volumeSeries;

      // 配置 right price scale 的顯示範圍和啟用拖曳
      chartInstance.priceScale('right').applyOptions({
        scaleMargins: {
          top: 0.1,    // 上方留 10% 空間
          bottom: 0.1, // 下方留 10% 空間（讓柱狀圖使用中間 80% 的高度）
        },
        // 預設已啟用拖曳和滾輪縮放（visible: true）
      });

      // 轉換數據格式並計算顏色
      const volumeData: VolumeBarData[] = klines.map((kline, index) => {
        const prevClose = index > 0 ? klines[index - 1].close : null;
        const color = calculateVolumeColor(kline.close, prevClose, chartColors.upColor, chartColors.downColor);

        return {
          time: kline.timestamp as any,
          value: kline.volume,
          color: color,
        };
      });

      // 設置成交量數據
      volumeSeries.setData(volumeData);

      // 自動縮放到適合的範圍
      chartInstance.timeScale().fitContent();

      console.log(`[VolumeChart] Rendered ${volumeData.length} volume bars for ${symbol}`);

      // 訂閱懸停事件（用於顯示成交量數值）
      const handleCrosshairMove = (param: any) => {
        if (param.time) {
          const hoveredKline = klines.find(k => k.timestamp === param.time);
          if (hoveredKline) {
            setHoveredVolume(hoveredKline.volume);
          }
        } else {
          setHoveredVolume(null);
        }
      };

      chartInstance.subscribeCrosshairMove(handleCrosshairMove);

      // 訂閱 Context 十字線時間變化（修復數值同步問題）
      const unsubscribeCrosshair = subscribeCrosshairChange(chartId, (time) => {
        if (time !== null) {
          const hoveredKline = klines.find(k => k.timestamp === time);
          setHoveredVolume(hoveredKline?.volume ?? null);
        } else {
          setHoveredVolume(null);
        }
      });

      // cleanup函數：移除series和事件訂閱（修復P0-1）
      return () => {
        try {
          chartInstance.unsubscribeCrosshairMove(handleCrosshairMove);
          unsubscribeCrosshair();
          if (volumeSeries) {
            chartInstance.removeSeries(volumeSeries);
          }
        } catch (err) {
          console.error('[VolumeChart] Cleanup error:', err);
        }
      };

    } catch (err) {
      console.error('[VolumeChart] Failed to render chart:', err);
      setError(err instanceof Error ? err.message : 'Failed to render volume chart');
    }
  }, [chartInstance, isReady, klines, symbol]);

  return (
    <div className="w-full flex flex-col bg-white border-t border-gray-200" style={{ height: `${height}px` }}>
      {/* 頂部標籤 */}
      <div className="px-4 py-1 flex items-center justify-between border-b border-gray-100">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-700">成交量</span>
          {hoveredVolume !== null && (
            <span className="text-xs text-gray-600">
              {formatVolume(hoveredVolume)}
            </span>
          )}
        </div>
      </div>

      {/* 圖表容器 */}
      <div className="flex-1 relative">
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
            <div className="text-center">
              <div className="text-red-500 text-xl mb-1">⚠️</div>
              <p className="text-xs text-red-600">{error}</p>
            </div>
          </div>
        )}

        {klines.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
            <p className="text-xs text-gray-500">無成交量數據</p>
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

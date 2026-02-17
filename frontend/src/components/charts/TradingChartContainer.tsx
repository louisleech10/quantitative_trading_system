/**
 * TradingChartContainer 組件 - 圖表容器整合
 *
 * 功能：
 * - 垂直堆疊三個圖表組件 (PriceChart, VolumeChart, TakerRatioChart)
 * - 實現響應式高度分配 (5:3:2 比例)
 * - 自定義十字線貫穿三個圖表
 * - 時間軸同步機制
 * - 圖表互動操作
 *
 * Ultra Think 步驟 1：初版代碼生成
 * Phase 2.3 步驟 2：圖表容器與佈局結構
 */

'use client';

import React, { useRef, useEffect, useState } from 'react';
import { PriceChart, KlineData } from './PriceChart';
import { VolumeChart } from './VolumeChart';
import { TakerRatioChart } from './TakerRatioChart';
import { TimeAxisProvider, useTimeAxis } from '@/contexts/TimeAxisContext';

/**
 * TradingChartContainer Props
 */
export interface TradingChartContainerProps {
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
   * TO 時間戳（對齊後的案例開始時間，Unix 秒）
   */
  toTimestamp: number;

  /**
   * TC 時間戳（對齊後的案例結束時間，Unix 秒，可選）
   */
  tcTimestamp?: number;

  /**
   * 容器總高度（像素），默認 640px
   */
  totalHeight?: number;

  /**
   * 是否顯示 TO 點標記
   */
  showToMarker?: boolean;
}

/**
 * TradingChartContainer 組件
 * 
 * 垂直堆疊三個圖表，實現統一的時間軸同步和 TO 點標記
 */
export function TradingChartContainer(props: TradingChartContainerProps) {
  console.log('[TradingChartContainer] Rendering with props:', {
    symbol: props.symbol,
    timeframe: props.timeframe,
    toTimestamp: props.toTimestamp,
    klinesCount: props.klines.length
  });
  
  return (
    <TimeAxisProvider debug={true}>
      <TradingChartContainerInner {...props} />
    </TimeAxisProvider>
  );
}

/**
 * 內部組件（可以使用 TimeAxisContext）
 */
function TradingChartContainerInner({
  symbol,
  timeframe,
  klines,
  toTimestamp,
  tcTimestamp,
  totalHeight = 640,
  showToMarker = true
}: TradingChartContainerProps) {
  void showToMarker;
  // ===== Refs =====
  const containerRef = useRef<HTMLDivElement>(null);
  
  // ===== Context =====
  const { updateCrosshair } = useTimeAxis();

  // ===== State =====
  const [, setContainerWidth] = useState<number>(0);
  const [crosshairX, setCrosshairX] = useState<number | null>(null); // 十字線 X 座標
  const [, setCrosshairTime] = useState<number | null>(null); // 十字線時間戳
  const [isInitialized, setIsInitialized] = useState(false); // 初始化狀態（避免刷新歪掉）

  // ===== 高度分配（5:3:2 比例）=====
  const priceHeight = Math.floor(totalHeight * 0.5); // 50% = 320px
  const volumeHeight = Math.floor(totalHeight * 0.3); // 30% = 192px
  const takerRatioHeight = Math.floor(totalHeight * 0.2); // 20% = 128px

  /**
   * 初始化延遲（避免刷新歪掉）
   */
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsInitialized(true);
    }, 50);
    return () => clearTimeout(timer);
  }, []);

  /**
   * 監聽容器寬度變化（響應式設計）
   */
  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });

    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  /**
   * 監聽滑鼠移動，實現十字線貫穿效果 + 廣播時間戳
   */
  useEffect(() => {
    if (!containerRef.current) return;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;

      const x = e.clientX - rect.left;
      
      // 只在圖表區域內顯示十字線（排除左側標籤和右側 padding）
      const chartStartX = 60; // 左側標籤寬度
      const chartEndX = rect.width - 80; // 右側價格標籤寬度
      
      if (x >= chartStartX && x <= chartEndX) {
        setCrosshairX(x);
        
        // 將 X 座標轉換為時間戳（粗略估算）
        // 使用第一個和最後一個 kline 的時間戳
        if (klines.length > 1) {
          const chartWidth = chartEndX - chartStartX;
          const relativeX = x - chartStartX;
          const ratio = relativeX / chartWidth;
          
          const firstTime = klines[0].timestamp;
          const lastTime = klines[klines.length - 1].timestamp;
          const estimatedTime = Math.floor(firstTime + (lastTime - firstTime) * ratio);
          
          setCrosshairTime(estimatedTime);
          // 廣播時間戳到 Context，讓其他圖表更新數值
          updateCrosshair(estimatedTime, 'container');
        }
      } else {
        setCrosshairX(null);
        setCrosshairTime(null);
        updateCrosshair(null, 'container');
      }
    };

    const handleMouseLeave = () => {
      setCrosshairX(null);
      setCrosshairTime(null);
      updateCrosshair(null, 'container');
    };

    const container = containerRef.current;
    container.addEventListener('mousemove', handleMouseMove);
    container.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      container.removeEventListener('mousemove', handleMouseMove);
      container.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [klines, updateCrosshair]);

  return (
    <div 
      ref={containerRef}
      className="relative w-full glass-panel rounded-xl overflow-hidden"
      style={{ height: `${totalHeight}px` }}
    >
      {/* 十字線疊層（貫穿三個圖表的灰色虛線） */}
      {crosshairX !== null && (
        <div
          className="absolute top-0 bottom-0 pointer-events-none z-10"
          style={{
            left: `${crosshairX}px`,
            width: '1px',
            borderLeft: '1px dashed rgba(255, 255, 255, 0.1)',
          }}
        />
      )}

      {/* 三個圖表垂直堆疊 */}
      <div className="relative w-full h-full flex flex-col">
        {!isInitialized ? (
          <div className="flex items-center justify-center w-full h-full">
            <div className="text-slate-400 text-sm">初始化中...</div>
          </div>
        ) : (
          <>
            {/* 1. Price Chart (K線圖) - 50% 高度 */}
            <div 
              className="w-full border-b border-white/10"
              style={{ height: `${priceHeight}px` }}
            >
              <PriceChart
            symbol={symbol}
            timeframe={timeframe}
            klines={klines}
            caseTimestamp={toTimestamp}
            toTimestamp={toTimestamp}
            tcTimestamp={tcTimestamp}
            height={priceHeight}
            showCaseMarker={true}
            chartId="price-chart"
            enableSync={true}
          />
        </div>

        {/* 2. Volume Chart (成交量圖) - 30% 高度 */}
        <div 
          className="w-full border-b border-white/10"
          style={{ height: `${volumeHeight}px` }}
        >
          <VolumeChart
            symbol={symbol}
            timeframe={timeframe}
            klines={klines}
            height={volumeHeight}
            chartId="volume-chart"
            enableSync={true}
            toTimestamp={toTimestamp}
          />
        </div>

        {/* 3. Taker Ratio Chart (Taker 比率圖) - 20% 高度 */}
        <div 
          className="w-full"
          style={{ height: `${takerRatioHeight}px` }}
        >
          <TakerRatioChart
            symbol={symbol}
            timeframe={timeframe}
            klines={klines}
            height={takerRatioHeight}
            chartId="taker-ratio-chart"
            enableSync={true}
            toTimestamp={toTimestamp}
          />
        </div>
          </>
        )}
      </div>
    </div>
  );
}

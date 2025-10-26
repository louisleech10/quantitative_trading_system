/**
 * useChartSync Hook
 *
 * 整合 useChart + TimeAxisContext 的高級 Hook
 * 
 * 功能：
 * - 包含 useChart 的所有功能（圖表初始化、resize）
 * - 自動整合 TimeAxisContext 的同步機制
 * - 監聽本地圖表變化並廣播到 Context
 * - 接收其他圖表的同步更新
 * - 雙擊重置到 TO 中心
 *
 * Phase 2.3 步驟 5：圖表互動操作整合
 */

import { useCallback, useEffect, useRef } from 'react';
import { useChart } from './useChart';
import { useTimeAxis, TimeRange } from '../contexts/TimeAxisContext';
import { MouseEventParams } from 'lightweight-charts';

/**
 * useChartSync Hook 參數（擴展 useChart）
 */
export interface UseChartSyncOptions {
  /**
   * 圖表唯一 ID（用於同步識別）
   */
  chartId: string;

  /**
   * TO 時間戳（用於雙擊重置）
   */
  toTimestamp?: number;

  /**
   * 是否啟用同步（默認 true）
   */
  enableSync?: boolean;

  /**
   * 是否啟用調試日誌
   */
  debug?: boolean;
}

/**
 * useChartSync - 帶同步功能的圖表 Hook
 */
export function useChartSync({
  chartId,
  toTimestamp,
  enableSync = true,
  debug = false
}: UseChartSyncOptions) {
  // 使用基礎 useChart
  const { chartContainerRef, chartInstance, isReady } = useChart();

  // 使用 TimeAxisContext
  const {
    updateVisibleRange,
    updateCrosshair,
    resetToCenter: contextResetToCenter,
    subscribeVisibleRangeChange,
    subscribeCrosshairChange
  } = useTimeAxis();

  // Refs
  const isApplyingExternalUpdateRef = useRef(false);
  const lastRangeRef = useRef<TimeRange | null>(null);
  const lockTimeoutRef = useRef<NodeJS.Timeout | null>(null); // 追蹤鎖釋放的 timeout

  /**
   * 訂閱時間範圍變化（從其他圖表同步過來）
   */
  useEffect(() => {
    if (!chartInstance || !isReady || !enableSync) return;

    const timeScale = chartInstance.timeScale();

    const unsubscribe = subscribeVisibleRangeChange(chartId, (range: TimeRange) => {
      if (debug) console.log(`[useChartSync:${chartId}] Received logical range update`, range);

      // 防止循環更新
      if (isApplyingExternalUpdateRef.current) {
        if (debug) console.log(`[useChartSync:${chartId}] Skipping update (applying external update)`);
        return;
      }

      isApplyingExternalUpdateRef.current = true;

      // 清除之前的 timeout（如果有）
      if (lockTimeoutRef.current) {
        clearTimeout(lockTimeoutRef.current);
      }

      try {
        // 檢查是否為重置信號（特殊標記）
        if (range.from === -999999 && range.to === -999999) {
          // 重置到 TO 中心
          if (toTimestamp) {
            const timeScale = chartInstance.timeScale();
            const coordinate = timeScale.timeToCoordinate(toTimestamp as any);
            
            if (coordinate !== null) {
              const logicalIndex = timeScale.coordinateToLogical(coordinate);
              
              if (logicalIndex !== null) {
                const halfRange = 50;
                timeScale.setVisibleLogicalRange({
                  from: logicalIndex - halfRange,
                  to: logicalIndex + halfRange
                });
                if (debug) console.log(`[useChartSync:${chartId}] Reset to TO center (logical)`, logicalIndex);
              }
            }
          }
        } else {
          // 使用邏輯範圍同步（關鍵修復）
          const currentRange = timeScale.getVisibleLogicalRange();
          
          // 只在真的不同時才更新（避免不必要的重繪）
          if (!currentRange || 
              Math.abs(currentRange.from - range.from) > 0.01 ||
              Math.abs(currentRange.to - range.to) > 0.01) {
            
            timeScale.setVisibleLogicalRange({
              from: range.from,
              to: range.to
            });
            
            // 強制觸發重繪（修復 #7：縮放同步）
            chartInstance.timeScale().applyOptions({});
            
            lastRangeRef.current = range;
            if (debug) console.log(`[useChartSync:${chartId}] Applied logical range with forced update`, range);
          }
        }
      } catch (err) {
        console.error(`[useChartSync:${chartId}] Failed to apply logical range:`, err);
      } finally {
        // 釋放鎖（使用 ref 追蹤 timeout）
        lockTimeoutRef.current = setTimeout(() => {
          isApplyingExternalUpdateRef.current = false;
          lockTimeoutRef.current = null;
          if (debug) console.log(`[useChartSync:${chartId}] Lock released`);
        }, 30);
      }
    });

    // Cleanup：清除 timeout 和訂閱
    return () => {
      if (lockTimeoutRef.current) {
        clearTimeout(lockTimeoutRef.current);
        lockTimeoutRef.current = null;
      }
      unsubscribe();
    };
  }, [chartInstance, isReady, enableSync, chartId, subscribeVisibleRangeChange, toTimestamp, debug]);

  /**
   * 訂閱十字遊標變化（從其他圖表同步過來）
   * 注意：虛線已由 TradingChartContainer 統一繪製，這裡只處理數值顯示
   */
  useEffect(() => {
    if (!chartInstance || !isReady || !enableSync) return;

    const unsubscribe = subscribeCrosshairChange(chartId, (time: number | null) => {
      if (debug) console.log(`[useChartSync:${chartId}] Received crosshair update`, time);

      // 不需要 setCrosshairPosition，因為虛線由容器統一繪製
      // 只需要觸發 crosshairMove 事件來更新數值顯示
      // 或者什麼都不做，讓 VolumeChart/TakerRatioChart 自己處理
      if (debug) console.log(`[useChartSync:${chartId}] Crosshair time synced`, time);
    });

    return unsubscribe;
  }, [chartInstance, isReady, enableSync, chartId, subscribeCrosshairChange, debug]);

  /**
   * 監聽本地時間範圍變化（拖曳/縮放）並發送到 Context
   */
  useEffect(() => {
    if (!chartInstance || !isReady || !enableSync) return;

    const timeScale = chartInstance.timeScale();

    const handleVisibleRangeChange = () => {
      // 防止循環更新
      if (isApplyingExternalUpdateRef.current) {
        if (debug) console.log(`[useChartSync:${chartId}] Skipping local change broadcast (external update in progress)`);
        return;
      }

      const logicalRange = timeScale.getVisibleLogicalRange();
      if (!logicalRange) {
        if (debug) console.log(`[useChartSync:${chartId}] No logical range available`);
        return;
      }

      const newRange: TimeRange = {
        from: logicalRange.from,
        to: logicalRange.to
      };

      // 檢查是否真的變化了（避免重複廣播）
      if (
        lastRangeRef.current &&
        Math.abs(lastRangeRef.current.from - newRange.from) < 0.01 &&
        Math.abs(lastRangeRef.current.to - newRange.to) < 0.01
      ) {
        return;
      }

      lastRangeRef.current = newRange;
      if (debug) console.log(`[useChartSync:${chartId}] Broadcasting logical range change`, newRange);

      // 發送到 Context（會同步到其他圖表）
      updateVisibleRange(newRange, chartId);
    };

    // 訂閱邏輯範圍變化事件（關鍵修復：使用 Logical 而非 Time）
    // subscribeVisibleLogicalRangeChange 會在縮放時保持正確的錨點
    timeScale.subscribeVisibleLogicalRangeChange(handleVisibleRangeChange);

    if (debug) console.log(`[useChartSync:${chartId}] Subscribed to local visible logical range changes`);

    return () => {
      timeScale.unsubscribeVisibleLogicalRangeChange(handleVisibleRangeChange);
      if (debug) console.log(`[useChartSync:${chartId}] Unsubscribed from local visible logical range changes`);
    };
  }, [chartInstance, isReady, enableSync, chartId, updateVisibleRange, debug]);

  /**
   * 監聽十字游標移動並發送到 Context
   */
  useEffect(() => {
    if (!chartInstance || !isReady || !enableSync) return;

    const handleCrosshairMove = (param: MouseEventParams) => {
      if (!param.time) {
        updateCrosshair(null, chartId);
        return;
      }

      const time = param.time as number;
      updateCrosshair(time, chartId);
    };

    chartInstance.subscribeCrosshairMove(handleCrosshairMove);

    return () => {
      chartInstance.unsubscribeCrosshairMove(handleCrosshairMove);
    };
  }, [chartInstance, isReady, enableSync, chartId, updateCrosshair]);

  /**
   * 手動觸發同步更新
   */
  const syncVisibleRange = useCallback((range: TimeRange) => {
    if (!chartInstance || !isReady) return;

    const timeScale = chartInstance.timeScale();
    timeScale.setVisibleLogicalRange({
      from: range.from,
      to: range.to
    });
  }, [chartInstance, isReady]);

  /**
   * 重置到 TO 中心
   */
  const resetToCenter = useCallback(() => {
    if (!toTimestamp) {
      console.warn(`[useChartSync:${chartId}] Cannot reset: toTimestamp not provided`);
      return;
    }

    if (debug) console.log(`[useChartSync:${chartId}] Resetting to TO center`, toTimestamp);
    contextResetToCenter(toTimestamp);
  }, [toTimestamp, chartId, contextResetToCenter, debug]);

  /**
   * 實現雙擊重置功能
   */
  useEffect(() => {
    if (!chartContainerRef.current || !toTimestamp || !enableSync) return;

    const containerElement = chartContainerRef.current;

    const handleDoubleClick = () => {
      if (debug) console.log(`[useChartSync:${chartId}] Double-click detected, resetting to TO center`);
      resetToCenter();
    };

    containerElement.addEventListener('dblclick', handleDoubleClick);

    return () => {
      containerElement.removeEventListener('dblclick', handleDoubleClick);
    };
  }, [chartContainerRef, toTimestamp, enableSync, resetToCenter, debug, chartId]);

  return {
    chartContainerRef,
    chartInstance,
    isReady,
    syncVisibleRange,
    resetToCenter
  };
}

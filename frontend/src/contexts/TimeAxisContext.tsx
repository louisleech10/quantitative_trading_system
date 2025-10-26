/**
 * TimeAxisContext - 時間軸同步 Context
 *
 * 功能：
 * - 管理三個圖表的時間軸同步狀態
 * - 防循環更新機制（isSyncing 鎖）
 * - 提供統一的同步操作方法
 * - 支援拖曳、縮放、十字游標同步
 * - 雙擊重置至 TO 中心
 *
 * Ultra Think 步驟 1：初版代碼生成
 * Phase 2.3 步驟 3：時間軸同步機制
 */

'use client';

import React, { createContext, useContext, useState, useCallback, useRef } from 'react';

/**
 * 時間範圍接口（與 Lightweight Charts 的 LogicalRange 完全對應）
 * 使用邏輯索引而非時間戳，確保精確同步
 */
export interface TimeRange {
  from: number; // 邏輯索引（數據點索引）
  to: number;   // 邏輯索引（數據點索引）
}

/**
 * 十字游標位置接口
 */
export interface CrosshairPosition {
  time: number | null;  // Unix timestamp (秒)，null 表示無十字游標
  point?: { x: number; y: number }; // 可選的像素坐標
}

/**
 * 圖表同步狀態
 */
export interface ChartSyncState {
  /**
   * 當前可見時間範圍
   */
  visibleRange: TimeRange | null;

  /**
   * 十字游標時間
   */
  crosshairTime: number | null;

  /**
   * 縮放級別（可選，用於記錄縮放狀態）
   */
  zoomLevel?: number;

  /**
   * 是否正在同步（防循環更新鎖）
   */
  isSyncing: boolean;
}

/**
 * Context 操作方法接口
 */
export interface TimeAxisContextValue {
  /**
   * 當前同步狀態
   */
  syncState: ChartSyncState;

  /**
   * 更新可見時間範圍（觸發其他圖表同步）
   */
  updateVisibleRange: (range: TimeRange, sourceChartId?: string) => void;

  /**
   * 更新十字游標位置（觸發其他圖表同步）
   */
  updateCrosshair: (time: number | null, sourceChartId?: string) => void;

  /**
   * 重置到 TO 中心（雙擊重置功能）
   */
  resetToCenter: (toTimestamp: number, lookbackBars?: number, forwardBars?: number) => void;

  /**
   * 訂閱可見範圍變化
   */
  subscribeVisibleRangeChange: (
    chartId: string,
    callback: (range: TimeRange) => void
  ) => () => void;

  /**
   * 訂閱十字游標變化
   */
  subscribeCrosshairChange: (
    chartId: string,
    callback: (time: number | null) => void
  ) => () => void;
}

/**
 * TimeAxisContext
 */
const TimeAxisContext = createContext<TimeAxisContextValue | null>(null);

/**
 * Hook：使用 TimeAxisContext
 */
export function useTimeAxis(): TimeAxisContextValue {
  const context = useContext(TimeAxisContext);
  if (!context) {
    throw new Error('useTimeAxis must be used within TimeAxisProvider');
  }
  return context;
}

/**
 * TimeAxisProvider Props
 */
export interface TimeAxisProviderProps {
  children: React.ReactNode;

  /**
   * 初始可見範圍（可選）
   */
  initialRange?: TimeRange;

  /**
   * 是否啟用調試日誌
   */
  debug?: boolean;
}

/**
 * TimeAxisProvider 組件
 * 
 * 提供時間軸同步功能給子組件
 */
export function TimeAxisProvider({
  children,
  initialRange,
  debug = false
}: TimeAxisProviderProps) {
  // ===== State =====
  const [syncState, setSyncState] = useState<ChartSyncState>({
    visibleRange: initialRange ?? null,
    crosshairTime: null,
    zoomLevel: 1,
    isSyncing: false
  });

  // ===== Refs =====
  // 訂閱者映射：chartId -> callback
  const rangeSubscribers = useRef<Map<string, (range: TimeRange) => void>>(new Map());
  const crosshairSubscribers = useRef<Map<string, (time: number | null) => void>>(new Map());
  
  // RAF (RequestAnimationFrame) ID，用於節流
  const rafId = useRef<number | null>(null);

  /**
   * 記錄調試日誌
   */
  const log = useCallback((message: string, ...args: any[]) => {
    if (debug) {
      console.log(`[TimeAxisContext] ${message}`, ...args);
    }
  }, [debug]);

  /**
   * 更新可見範圍（帶 RAF 節流）
   */
  const updateVisibleRange = useCallback((range: TimeRange, sourceChartId?: string) => {
    log('updateVisibleRange called', { range, sourceChartId });

    // 取消之前的 RAF（如果有）
    if (rafId.current !== null) {
      cancelAnimationFrame(rafId.current);
    }

    rafId.current = requestAnimationFrame(() => {
      // 更新 state
      setSyncState(prev => ({
        ...prev,
        visibleRange: range,
        isSyncing: true
      }));

      // 通知所有訂閱者（除了源圖表）
      rangeSubscribers.current.forEach((callback, chartId) => {
        if (chartId !== sourceChartId) {
          log(`Notifying chart ${chartId} of range change`);
          callback(range);
        }
      });

      // 延遲更新狀態
      setTimeout(() => {
        setSyncState(prev => ({ ...prev, isSyncing: false }));
        log('Sync complete');
      }, 50);
    });
  }, [log]);

  /**
   * 更新十字游標位置
   */
  const updateCrosshair = useCallback((time: number | null, sourceChartId?: string) => {
    log('updateCrosshair called', { time, sourceChartId });

    // 更新 state
    setSyncState(prev => ({
      ...prev,
      crosshairTime: time,
      isSyncing: true
    }));

    // 通知所有訂閱者（除了源圖表）
    crosshairSubscribers.current.forEach((callback, chartId) => {
      if (chartId !== sourceChartId) {
        log(`Notifying chart ${chartId} of crosshair change`);
        callback(time);
      }
    });

    // 釋放狀態
    setTimeout(() => {
      setSyncState(prev => ({ ...prev, isSyncing: false }));
    }, 10);
  }, [log]);

  /**
   * 重置到 TO 中心
   * 
   * 注意：廣播特殊重置信號，讓各圖表自行處理
   * 
   * @param toTimestamp - TO 時間戳（Unix 秒）
   * @param lookbackBars - 向前看幾根 K 線（默認 100）
   * @param forwardBars - 向後看幾根 K 線（默認 50）
   */
  const resetToCenter = useCallback((
    toTimestamp: number,
    lookbackBars: number = 100,
    forwardBars: number = 50
  ) => {
    log('resetToCenter called', { toTimestamp, lookbackBars, forwardBars });

    // 廣播特殊重置信號
    const resetSignal: TimeRange = { from: -999999, to: -999999 };

    setSyncState(prev => ({
      ...prev,
      isSyncing: true
    }));

    // 通知所有訂閱者執行重置
    rangeSubscribers.current.forEach((callback) => {
      callback(resetSignal);
    });

    setTimeout(() => {
      setSyncState(prev => ({ ...prev, isSyncing: false }));
    }, 10);
  }, [log]);

  /**
   * 訂閱可見範圍變化
   */
  const subscribeVisibleRangeChange = useCallback((
    chartId: string,
    callback: (range: TimeRange) => void
  ): (() => void) => {
    log(`Chart ${chartId} subscribed to visibleRange changes`);
    rangeSubscribers.current.set(chartId, callback);

    // 返回取消訂閱函數
    return () => {
      log(`Chart ${chartId} unsubscribed from visibleRange changes`);
      rangeSubscribers.current.delete(chartId);
    };
  }, [log]);

  /**
   * 訂閱十字游標變化
   */
  const subscribeCrosshairChange = useCallback((
    chartId: string,
    callback: (time: number | null) => void
  ): (() => void) => {
    log(`Chart ${chartId} subscribed to crosshair changes`);
    crosshairSubscribers.current.set(chartId, callback);

    // 返回取消訂閱函數
    return () => {
      log(`Chart ${chartId} unsubscribed from crosshair changes`);
      crosshairSubscribers.current.delete(chartId);
    };
  }, [log]);

  // ===== Context Value =====
  const contextValue: TimeAxisContextValue = {
    syncState,
    updateVisibleRange,
    updateCrosshair,
    resetToCenter,
    subscribeVisibleRangeChange,
    subscribeCrosshairChange
  };

  return (
    <TimeAxisContext.Provider value={contextValue}>
      {children}
    </TimeAxisContext.Provider>
  );
}

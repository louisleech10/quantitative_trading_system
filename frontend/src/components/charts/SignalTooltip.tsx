/**
 * SignalTooltip.tsx - 信號工具提示組件
 *
 * Phase 3.3+3.4 - Task C2: SignalTooltip 組件
 *
 * 功能:
 * - 懸停顯示信號詳情 (浮動面板)
 * - 顯示指標數值 (EMA short/mid/long 等)
 * - 顯示信號密度 (如果有)
 * - 顯示時間戳和價格
 * - 自動定位 (跟隨滑鼠游標)
 * - 優雅的動畫效果
 *
 * Ultra Think 記錄:
 * - 步驟 1: 初版代碼 (當前)
 * - 步驟 2: 審查優化 (待執行)
 * - 步驟 3: 最終優化 (待執行)
 */

"use client";

import { useEffect, useState } from "react";

/**
 * 信號工具提示數據接口
 */
export interface SignalTooltipData {
  timestamp: number;
  price: number;
  indicator_values: Record<string, number>;
  signal_density?: number;
}

/**
 * 滑鼠位置接口
 */
export interface MousePosition {
  x: number;
  y: number;
}

/**
 * SignalTooltip Props
 */
export interface SignalTooltipProps {
  /**
   * 信號數據 (null 時隱藏)
   */
  data: SignalTooltipData | null;

  /**
   * 滑鼠位置 (用於定位)
   */
  mousePosition?: MousePosition;

  /**
   * 自定義樣式類名
   */
  className?: string;

  /**
   * 是否顯示箭頭指示器
   */
  showArrow?: boolean;
}

/**
 * SignalTooltip 組件 - 信號工具提示
 */
export default function SignalTooltip({
  data,
  mousePosition,
  className = "",
  showArrow = true,
}: SignalTooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });

  // 控制顯示/隱藏動畫
  useEffect(() => {
    if (data) {
      // 延遲顯示,避免閃爍
      const timer = setTimeout(() => {
        setIsVisible(true);
      }, 100);
      return () => clearTimeout(timer);
    } else {
      setIsVisible(false);
    }
  }, [data]);

  // 更新位置
  useEffect(() => {
    if (mousePosition) {
      // 偏移量,避免遮擋滑鼠
      const offsetX = 15;
      const offsetY = 15;

      setPosition({
        x: mousePosition.x + offsetX,
        y: mousePosition.y + offsetY,
      });
    }
  }, [mousePosition]);

  // 如果沒有數據,不渲染
  if (!data) {
    return null;
  }

  // 格式化時間戳
  const formatTimestamp = (timestamp: number): string => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString("zh-TW", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  };

  // 格式化價格
  const formatPrice = (price: number): string => {
    if (price >= 1000) {
      return price.toFixed(2);
    } else if (price >= 1) {
      return price.toFixed(4);
    } else {
      return price.toFixed(8);
    }
  };

  // 指標顯示名稱映射
  const indicatorNameMap: Record<string, string> = {
    ema_short: "短期 EMA",
    ema_mid: "中期 EMA",
    ema_long: "長期 EMA",
    sma_short: "短期 SMA",
    sma_mid: "中期 SMA",
    sma_long: "長期 SMA",
    rsi: "RSI",
    macd: "MACD",
    signal: "Signal",
    histogram: "Histogram",
  };

  return (
    <div
      className={`
        fixed z-50 pointer-events-none
        transition-opacity duration-200
        ${isVisible ? "opacity-100" : "opacity-0"}
        ${className}
      `}
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        transform: "translate(0, 0)",
      }}
    >
      {/* 主容器 */}
      <div className="bg-white rounded-lg shadow-2xl border border-gray-200 overflow-hidden min-w-[280px] max-w-[400px]">
        {/* 標題欄 */}
        <div className="bg-gradient-to-r from-green-500 to-emerald-600 px-4 py-2">
          <div className="flex items-center gap-2">
            <span className="text-white text-sm font-semibold">
              📍 策略信號
            </span>
            {showArrow && (
              <span className="text-white text-xs">↑</span>
            )}
          </div>
        </div>

        {/* 內容區域 */}
        <div className="p-4 space-y-3">
          {/* 時間和價格 */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-500">時間</span>
              <span className="font-mono text-gray-900">
                {formatTimestamp(data.timestamp)}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-500">價格</span>
              <span className="font-mono text-gray-900 font-semibold">
                ${formatPrice(data.price)}
              </span>
            </div>
          </div>

          {/* 分隔線 */}
          <div className="border-t border-gray-200" />

          {/* 指標數值 */}
          <div>
            <div className="text-xs font-semibold text-gray-700 mb-2">
              指標數值
            </div>
            <div className="space-y-1.5">
              {Object.entries(data.indicator_values).map(([key, value]) => (
                <div
                  key={key}
                  className="flex items-center justify-between text-xs"
                >
                  <span className="text-gray-600">
                    {indicatorNameMap[key] || key}
                  </span>
                  <span className="font-mono text-gray-900 font-medium">
                    {typeof value === "number" ? value.toFixed(2) : value}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* 信號密度 (如果有) */}
          {data.signal_density !== undefined && (
            <>
              <div className="border-t border-gray-200" />
              <div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-600">信號密度</span>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-gray-900 font-medium">
                      {(data.signal_density * 100).toFixed(1)}%
                    </span>
                    {/* 密度條 */}
                    <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-green-400 to-emerald-500 transition-all duration-300"
                        style={{ width: `${data.signal_density * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
                {/* 密度等級文字 */}
                <div className="text-xs text-gray-500 mt-1 text-right">
                  {data.signal_density > 0.7
                    ? "高密度區域"
                    : data.signal_density > 0.4
                    ? "中等密度"
                    : "低密度區域"}
                </div>
              </div>
            </>
          )}

          {/* 提示文字 */}
          <div className="text-xs text-gray-400 italic pt-2 border-t border-gray-100">
            點擊信號標記查看詳細分析
          </div>
        </div>

        {/* 底部裝飾條 */}
        <div className="h-1 bg-gradient-to-r from-green-400 via-emerald-500 to-green-600" />
      </div>
    </div>
  );
}

/**
 * 簡化版 SignalTooltip (用於圖表內嵌顯示)
 */
export function CompactSignalTooltip({
  data,
  className = "",
}: {
  data: SignalTooltipData | null;
  className?: string;
}) {
  if (!data) {
    return null;
  }

  return (
    <div
      className={`
        inline-flex items-center gap-2 px-3 py-1.5
        bg-green-50 border border-green-200 rounded-md
        text-xs
        ${className}
      `}
    >
      <span className="text-green-700 font-semibold">📍</span>
      {Object.entries(data.indicator_values).map(([key, value], index) => (
        <span key={key} className="text-gray-700">
          {key.replace("ema_", "").replace("sma_", "")}:{" "}
          <span className="font-mono font-medium">
            {typeof value === "number" ? value.toFixed(1) : value}
          </span>
          {index < Object.keys(data.indicator_values).length - 1 && (
            <span className="text-gray-400 ml-1">|</span>
          )}
        </span>
      ))}
      {data.signal_density !== undefined && (
        <span className="text-green-600 font-medium">
          {(data.signal_density * 100).toFixed(0)}%
        </span>
      )}
    </div>
  );
}

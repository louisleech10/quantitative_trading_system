/**
 * DataSourceSelector.tsx - 數據源選擇組件
 *
 * Phase 3.3+3.4 - Task B1: 基礎選擇組件
 *
 * 功能:
 * - 提供 8 種數據源選擇 (收盤價/開盤價/最高價/最低價/成交量/主動買入量/主動買入比例/成交額)
 * - 單選模式,預設為收盤價
 * - 支援受控組件模式
 * - 提供清晰的視覺反饋
 *
 * Ultra Think 記錄:
 * - 步驟 1: 初版代碼 (當前)
 * - 步驟 2: 審查優化 (待執行)
 * - 步驟 3: 最終優化 (待執行)
 */

"use client";

import { useState } from "react";
void useState;

export interface DataSourceOption {
  value: string;
  label: string;
  description: string;
  category: "price" | "volume";
}

export interface DataSourceSelectorProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
}

/**
 * 數據源選項配置
 *
 * 對應後端 momentum/Indicators/types.py 的 DataSourceEnum
 */
const DATA_SOURCE_OPTIONS: DataSourceOption[] = [
  // 價格類數據源
  {
    value: "close",
    label: "收盤價",
    description: "K線收盤價 (最常用)",
    category: "price",
  },
  {
    value: "open",
    label: "開盤價",
    description: "K線開盤價",
    category: "price",
  },
  {
    value: "high",
    label: "最高價",
    description: "K線最高價",
    category: "price",
  },
  {
    value: "low",
    label: "最低價",
    description: "K線最低價",
    category: "price",
  },

  // 成交量類數據源
  {
    value: "volume",
    label: "成交量",
    description: "總成交量 (幣數)",
    category: "volume",
  },
  {
    value: "taker_buy_volume",
    label: "主動買入量",
    description: "Taker Buy Volume",
    category: "volume",
  },
  {
    value: "taker_ratio",
    label: "主動買入比例",
    description: "Taker Buy Volume / Total Volume",
    category: "volume",
  },
  {
    value: "quote_volume",
    label: "成交額",
    description: "總成交額 (USDT)",
    category: "volume",
  },
];

export default function DataSourceSelector({
  value,
  onChange,
  disabled = false,
  className = "",
}: DataSourceSelectorProps) {
  const selectedOption = DATA_SOURCE_OPTIONS.find((opt) => opt.value === value);

  return (
    <div className={`space-y-3 ${className}`}>
      {/* 標題 */}
      <div>
        <label className="block text-sm font-medium text-slate-200 mb-1">
          數據源選擇
        </label>
        <p className="text-xs text-slate-400">
          選擇用於計算指標的數據來源
        </p>
      </div>

      {/* 選項網格 */}
      <div className="grid grid-cols-2 gap-2">
        {DATA_SOURCE_OPTIONS.map((option) => {
          const isSelected = value === option.value;
          const isPriceCategory = option.category === "price";

          return (
            <button
              key={option.value}
              type="button"
              onClick={() => !disabled && onChange(option.value)}
              disabled={disabled}
              className={`
                relative p-3 rounded-lg border-2 text-left transition-all
                ${
                  isSelected
                    ? isPriceCategory
                      ? "border-sky-400/60 bg-sky-500/10"
                      : "border-emerald-400/60 bg-emerald-500/10"
                    : "border-white/10 bg-white/5 hover:border-white/20"
                }
                ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
              `}
            >
              {/* 選中指示器 */}
              {isSelected && (
                <div
                  className={`absolute top-2 right-2 w-2 h-2 rounded-full ${
                    isPriceCategory ? "bg-sky-400" : "bg-emerald-400"
                  }`}
                />
              )}

              {/* 標籤 */}
              <div
                className={`text-sm font-medium ${
                  isSelected
                    ? isPriceCategory
                      ? "text-sky-200"
                      : "text-emerald-200"
                    : "text-slate-100"
                }`}
              >
                {option.label}
              </div>

              {/* 描述 */}
              <div
                className={`text-xs mt-1 ${
                  isSelected
                    ? isPriceCategory
                      ? "text-sky-300"
                      : "text-emerald-300"
                    : "text-slate-400"
                }`}
              >
                {option.description}
              </div>
            </button>
          );
        })}
      </div>

      {/* 當前選擇摘要 */}
      {selectedOption && (
        <div className="text-xs text-slate-300 bg-white/5 border border-white/10 p-2 rounded">
          <span className="font-medium text-slate-200">當前選擇:</span>{" "}
          <span className="text-slate-100">{selectedOption.label}</span>
          {" - "}
          <span className="text-slate-400">{selectedOption.description}</span>
        </div>
      )}
    </div>
  );
}

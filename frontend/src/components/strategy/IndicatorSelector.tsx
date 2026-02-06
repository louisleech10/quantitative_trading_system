/**
 * IndicatorSelector.tsx - 指標類型選擇組件
 *
 * Phase 3.3+3.4 - Task B1: 基礎選擇組件
 *
 * 功能:
 * - 提供指標類型選擇 (目前僅 EMA,未來擴展至 20+ 種)
 * - 單選模式,預設為 EMA
 * - 支援擴展性設計,方便添加新指標
 * - 顯示指標說明和使用建議
 *
 * Ultra Think 記錄:
 * - 步驟 1: 初版代碼 (當前)
 * - 步驟 2: 審查優化 (待執行)
 * - 步驟 3: 最終優化 (待執行)
 */

"use client";

export interface IndicatorOption {
  value: string;
  label: string;
  description: string;
  fullName: string;
  available: boolean;
  comingSoon?: boolean;
}

export interface IndicatorSelectorProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
}

/**
 * 指標選項配置
 *
 * 對應後端 IndicatorEngine 支援的指標類型
 * Phase 3 僅實作 EMA,其他指標標記為 comingSoon
 */
const INDICATOR_OPTIONS: IndicatorOption[] = [
  // 已實作指標
  {
    value: "ema",
    label: "EMA",
    fullName: "Exponential Moving Average",
    description: "指數移動平均線,對近期價格賦予更高權重",
    available: true,
  },

  // 未來支援的指標 (Phase 4+)
  {
    value: "sma",
    label: "SMA",
    fullName: "Simple Moving Average",
    description: "簡單移動平均線,所有價格權重相同",
    available: false,
    comingSoon: true,
  },
  {
    value: "rsi",
    label: "RSI",
    fullName: "Relative Strength Index",
    description: "相對強弱指標,測量價格變動的速度和幅度",
    available: false,
    comingSoon: true,
  },
  {
    value: "macd",
    label: "MACD",
    fullName: "Moving Average Convergence Divergence",
    description: "平滑異同移動平均線,趨勢跟蹤動量指標",
    available: false,
    comingSoon: true,
  },
  {
    value: "bollinger",
    label: "布林帶",
    fullName: "Bollinger Bands",
    description: "價格通道指標,測量波動率和趨勢",
    available: false,
    comingSoon: true,
  },
  {
    value: "atr",
    label: "ATR",
    fullName: "Average True Range",
    description: "平均真實波幅,測量市場波動性",
    available: false,
    comingSoon: true,
  },
];

export default function IndicatorSelector({
  value,
  onChange,
  disabled = false,
  className = "",
}: IndicatorSelectorProps) {
  const selectedOption = INDICATOR_OPTIONS.find((opt) => opt.value === value);
  const availableOptions = INDICATOR_OPTIONS.filter((opt) => opt.available);
  const comingSoonOptions = INDICATOR_OPTIONS.filter((opt) => opt.comingSoon);

  return (
    <div className={`space-y-3 ${className}`}>
      {/* 標題 */}
      <div>
        <label className="block text-sm font-medium text-slate-200 mb-1">
          指標類型
        </label>
        <p className="text-xs text-slate-400">
          選擇用於策略分析的技術指標
        </p>
      </div>

      {/* 可用指標 */}
      <div className="space-y-2">
        <div className="text-xs font-medium text-slate-300">可用指標</div>
        <div className="grid grid-cols-1 gap-2">
          {availableOptions.map((option) => {
            const isSelected = value === option.value;

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
                      ? "border-blue-400/60 bg-blue-400/10"
                      : "border-white/10 bg-white/5 hover:border-white/20"
                  }
                  ${
                    disabled
                      ? "opacity-50 cursor-not-allowed"
                      : "cursor-pointer"
                  }
                `}
              >
                {/* 選中指示器 */}
                {isSelected && (
                  <div className="absolute top-3 right-3 w-2 h-2 rounded-full bg-blue-400" />
                )}

                <div className="flex items-start gap-3">
                  {/* 指標圖標 */}
                  <div
                    className={`
                    flex items-center justify-center w-10 h-10 rounded-lg
                    ${
                      isSelected
                        ? "bg-blue-400/20 text-blue-200"
                        : "bg-white/5 text-slate-300"
                    }
                  `}
                  >
                    <span className="text-sm font-bold">{option.label}</span>
                  </div>

                  {/* 指標資訊 */}
                  <div className="flex-1 min-w-0">
                    <div
                      className={`text-sm font-medium ${
                        isSelected ? "text-blue-100" : "text-slate-100"
                      }`}
                    >
                      {option.fullName}
                    </div>
                    <div
                      className={`text-xs mt-1 ${
                        isSelected ? "text-blue-300" : "text-slate-400"
                      }`}
                    >
                      {option.description}
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 即將推出的指標 */}
      {comingSoonOptions.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-medium text-slate-300 flex items-center gap-2">
            即將推出
            <span className="text-xs bg-white/5 text-slate-300 px-2 py-0.5 rounded border border-white/10">
              Phase 4+
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {comingSoonOptions.map((option) => (
              <div
                key={option.value}
                className="p-2 rounded-lg border border-dashed border-white/10 bg-white/5 opacity-70"
              >
                <div className="text-xs font-medium text-slate-300">
                  {option.label}
                </div>
                <div className="text-xs text-slate-400 mt-0.5">
                  {option.fullName}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 當前選擇摘要 */}
      {selectedOption && (
        <div className="text-xs text-slate-300 bg-white/5 border border-white/10 p-2 rounded">
          <span className="font-medium text-slate-200">當前選擇:</span>{" "}
          <span className="text-slate-100">{selectedOption.fullName}</span>
          {" - "}
          <span className="text-slate-400">{selectedOption.description}</span>
        </div>
      )}
    </div>
  );
}

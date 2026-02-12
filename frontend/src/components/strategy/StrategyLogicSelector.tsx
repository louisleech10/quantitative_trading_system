/**
 * Ultra Think 記錄:
 * - 步驟 1: 初版代碼 (當前)
 * - 步驟 2: 審查優化 (待執行)
 * - 步驟 3: 最終優化 (待執行)
 */

"use client";

export interface StrategyLogicOption {
  value: string;
  label: string;
  description: string;
  condition: string;
  parameters: string[];
  icon: string;
  recommendedFor: string;
}

export interface StrategyLogicSelectorProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
}

/**
 * 策略邏輯選項配置
 *
 * 對應後端 ChartSignalService 支援的策略邏輯
 */
const STRATEGY_LOGIC_OPTIONS: StrategyLogicOption[] = [
  {
    value: "three_line",
    label: "三線排列",
    description: "短期EMA > 中期EMA > 長期EMA,表示強勢上升趨勢",
    condition: "short > mid > long",
    parameters: ["ema_short", "ema_mid", "ema_long"],
    icon: "📈",
    recommendedFor: "強趨勢市場,適合捕捉明確上升趨勢",
  },
  {
    value: "short_long_cross",
    label: "短長交叉",
    description: "短期EMA > 長期EMA,快速反應價格變化",
    condition: "short > long",
    parameters: ["ema_short", "ema_long"],
    icon: "⚡",
    recommendedFor: "快速變動市場,適合短線交易",
  },
  {
    value: "mid_long_cross",
    label: "中長交叉",
    description: "中期EMA > 長期EMA,平衡靈敏度與穩定性",
    condition: "mid > long",
    parameters: ["ema_mid", "ema_long"],
    icon: "🎯",
    recommendedFor: "中等波動市場,適合中線持倉",
  },
];

export default function StrategyLogicSelector({
  value,
  onChange,
  disabled = false,
  className = "",
}: StrategyLogicSelectorProps) {
  const selectedOption = STRATEGY_LOGIC_OPTIONS.find(
    (opt) => opt.value === value
  );

  return (
    <div className={`space-y-3 ${className}`}>
      {/* 標題 */}
      <div>
        <label className="block text-sm font-medium text-slate-200 mb-1">
          策略邏輯
        </label>
        <p className="text-xs text-slate-400">
          選擇如何判斷策略信號的條件邏輯
        </p>
      </div>

      {/* 策略選項 */}
      <div className="space-y-2">
        {STRATEGY_LOGIC_OPTIONS.map((option) => {
          const isSelected = value === option.value;

          return (
            <button
              key={option.value}
              type="button"
              onClick={() => !disabled && onChange(option.value)}
              disabled={disabled}
              className={`
                w-full relative p-4 rounded-lg border-2 text-left transition-all
                ${
                  isSelected
                    ? "border-violet-400/60 bg-violet-500/10"
                    : "border-white/10 bg-white/5 hover:border-white/20"
                }
                ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
              `}
            >
              {/* 選中指示器 */}
              {isSelected && (
                <div className="absolute top-4 right-4 w-2 h-2 rounded-full bg-violet-400" />
              )}

              <div className="flex gap-3">
                {/* 圖標 */}
                <div
                  className={`
                    flex items-center justify-center w-12 h-12 rounded-lg text-2xl
                    ${isSelected ? "bg-violet-500/20" : "bg-white/5"}
                  `}
                >
                  {option.icon}
                </div>

                {/* 策略資訊 */}
                <div className="flex-1 min-w-0">
                  {/* 標籤 */}
                  <div
                    className={`text-sm font-semibold ${
                      isSelected ? "text-violet-100" : "text-slate-100"
                    }`}
                  >
                    {option.label}
                  </div>

                  {/* 條件公式 */}
                  <div
                    className={`text-xs font-mono mt-1 px-2 py-1 rounded inline-block ${
                      isSelected
                        ? "bg-violet-500/20 text-violet-200"
                        : "bg-white/10 text-slate-300"
                    }`}
                  >
                    {option.condition}
                  </div>

                  {/* 描述 */}
                  <div
                    className={`text-xs mt-2 ${
                      isSelected ? "text-violet-300" : "text-slate-400"
                    }`}
                  >
                    {option.description}
                  </div>

                  {/* 所需參數 */}
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs text-slate-400">需要參數:</span>
                    <div className="flex gap-1">
                      {option.parameters.map((param) => (
                        <span
                          key={param}
                          className={`text-xs px-2 py-0.5 rounded ${
                            isSelected
                              ? "bg-violet-500/20 text-violet-200"
                              : "bg-white/10 text-slate-300"
                          }`}
                        >
                          {param}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* 適用場景 */}
                  <div
                    className={`text-xs mt-2 italic ${
                      isSelected ? "text-violet-300" : "text-slate-400"
                    }`}
                  >
                    💡 {option.recommendedFor}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* 策略對比提示 */}
      <div className="bg-sky-500/10 border border-sky-500/30 rounded-lg p-3">
        <div className="flex items-start gap-2">
          <span className="text-sky-300 text-sm">ℹ️</span>
          <div className="text-xs text-sky-200">
            <div className="font-medium mb-1">策略選擇建議:</div>
            <ul className="space-y-1 text-sky-200/80">
              <li>
                • <strong>三線排列</strong>: 信號最嚴格,適合高勝率策略
              </li>
              <li>
                • <strong>短長交叉</strong>: 信號最靈敏,適合高頻交易
              </li>
              <li>
                • <strong>中長交叉</strong>: 平衡性最佳,適合穩健交易
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* 當前選擇摘要 */}
      {selectedOption && (
        <div className="text-xs text-slate-300 bg-white/5 border border-white/10 p-2 rounded">
          <span className="font-medium text-slate-200">當前策略:</span>{" "}
          <span className="text-slate-100">{selectedOption.label}</span>
          {" - "}
          <span className="font-mono text-violet-300">
            {selectedOption.condition}
          </span>
        </div>
      )}
    </div>
  );
}

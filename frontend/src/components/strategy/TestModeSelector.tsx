/**
 * TestModeSelector.tsx - 測試模式選擇組件
 *
 * Phase 3.3+3.4 - Task B2: 配置組件
 *
 * 功能:
 * - 選擇測試模式: 單次測試 vs Optuna 優化
 * - 顯示模式說明和適用場景
 * - Optuna 模式: 配置試驗次數
 * - 視覺化模式差異
 *
 * Ultra Think 記錄:
 * - 步驟 1: 初版代碼 (當前)
 * - 步驟 2: 審查優化 (待執行)
 * - 步驟 3: 最終優化 (待執行)
 */

"use client";

export interface TestModeConfig {
  mode: "single" | "optuna";
  optuna_trials?: number;
}

export interface TestModeSelectorProps {
  value: TestModeConfig;
  onChange: (value: TestModeConfig) => void;
  disabled?: boolean;
  className?: string;
}

const MODE_OPTIONS = [
  {
    value: "single" as const,
    label: "單次測試",
    icon: "🎯",
    description: "使用固定參數執行一次信號密度分析",
    features: [
      "快速測試特定參數組合",
      "適合驗證已知策略",
      "執行時間短 (通常 < 5秒)",
      "返回單一結果",
    ],
    color: "blue",
    estimatedTime: "< 5秒",
  },
  {
    value: "optuna" as const,
    label: "Optuna 優化",
    icon: "🔍",
    description: "自動搜索最佳參數組合,最大化信號密度差異",
    features: [
      "智能參數優化 (Bayesian Optimization)",
      "自動探索參數空間",
      "適合發現新策略",
      "返回最佳參數和優化歷史",
    ],
    color: "purple",
    estimatedTime: "1-5分鐘",
  },
];

export default function TestModeSelector({
  value,
  onChange,
  disabled = false,
  className = "",
}: TestModeSelectorProps) {
  const selectedMode = MODE_OPTIONS.find((opt) => opt.value === value.mode);

  const updateMode = (mode: "single" | "optuna") => {
    onChange({
      mode,
      optuna_trials: mode === "optuna" ? value.optuna_trials || 100 : undefined,
    });
  };

  const updateTrials = (trials: number) => {
    onChange({
      ...value,
      optuna_trials: trials,
    });
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 標題 */}
      <div>
        <label className="block text-sm font-medium text-slate-200 mb-1">
          測試模式
        </label>
        <p className="text-xs text-slate-400">
          選擇執行單次測試或參數優化
        </p>
      </div>

      {/* 模式選擇 */}
      <div className="space-y-3">
        {MODE_OPTIONS.map((option) => {
          const isSelected = value.mode === option.value;
          const borderColor =
            option.color === "blue"
              ? "border-sky-400/60 bg-sky-500/10"
              : "border-violet-400/60 bg-violet-500/10";
          const textColor =
            option.color === "blue" ? "text-sky-200" : "text-violet-200";

          return (
            <button
              key={option.value}
              type="button"
              onClick={() => !disabled && updateMode(option.value)}
              disabled={disabled}
              className={`
                w-full p-4 rounded-lg border-2 text-left transition-all
                ${
                  isSelected
                    ? borderColor
                    : "border-white/10 bg-white/5 hover:border-white/20"
                }
                ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
              `}
            >
              <div className="flex items-start gap-3">
                {/* 圖標 */}
                <div
                  className={`
                    flex items-center justify-center w-12 h-12 rounded-lg text-2xl
                    ${
                      isSelected
                        ? option.color === "blue"
                          ? "bg-sky-500/20"
                          : "bg-violet-500/20"
                        : "bg-white/5"
                    }
                  `}
                >
                  {option.icon}
                </div>

                {/* 內容 */}
                <div className="flex-1 min-w-0">
                  {/* 標籤和預估時間 */}
                  <div className="flex items-center justify-between">
                    <div
                      className={`text-sm font-semibold ${
                        isSelected ? textColor : "text-slate-100"
                      }`}
                    >
                      {option.label}
                    </div>
                    <div
                      className={`text-xs px-2 py-0.5 rounded ${
                        isSelected
                          ? option.color === "blue"
                            ? "bg-sky-500/20 text-sky-200"
                            : "bg-violet-500/20 text-violet-200"
                          : "bg-white/10 text-slate-300"
                      }`}
                    >
                      {option.estimatedTime}
                    </div>
                  </div>

                  {/* 描述 */}
                  <div
                    className={`text-xs mt-1 ${
                      isSelected
                        ? option.color === "blue"
                          ? "text-sky-200/80"
                          : "text-violet-200/80"
                        : "text-slate-400"
                    }`}
                  >
                    {option.description}
                  </div>

                  {/* 特性列表 */}
                  <div className="mt-2 space-y-1">
                    {option.features.map((feature, idx) => (
                      <div
                        key={idx}
                        className={`text-xs flex items-start gap-1 ${
                          isSelected
                            ? option.color === "blue"
                              ? "text-sky-200/80"
                              : "text-violet-200/80"
                            : "text-slate-400"
                        }`}
                      >
                        <span className="text-xs">•</span>
                        <span>{feature}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 選中指示器 */}
                {isSelected && (
                  <div
                    className={`w-2 h-2 rounded-full ${
                      option.color === "blue" ? "bg-sky-400" : "bg-violet-400"
                    }`}
                  />
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* Optuna 試驗次數配置 */}
      {value.mode === "optuna" && (
        <div className="bg-violet-500/10 border border-violet-400/30 rounded-lg p-4">
          <label className="block text-sm font-medium text-violet-100 mb-2">
            優化試驗次數
          </label>
          <p className="text-xs text-violet-200/80 mb-3">
            試驗次數越多,找到最佳參數的機率越高,但耗時也越長
          </p>

          {/* 試驗次數輸入 */}
          <div className="flex items-center gap-3">
            <input
              type="number"
              value={value.optuna_trials || 100}
              onChange={(e) => updateTrials(Number(e.target.value))}
              disabled={disabled}
              className="flex-1 px-3 py-2 border border-white/10 rounded-lg text-sm bg-white/5 text-slate-100 focus:border-violet-400 focus:outline-none focus:ring-2 focus:ring-violet-400/30"
              min={10}
              max={1000}
              step={10}
            />
            <span className="text-sm text-violet-200">次</span>
          </div>

          {/* 快速選擇 */}
          <div className="grid grid-cols-3 gap-2 mt-3">
            {[50, 100, 200].map((trials) => (
              <button
                key={trials}
                type="button"
                onClick={() => !disabled && updateTrials(trials)}
                disabled={disabled}
                className={`
                  px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
                  ${
                    value.optuna_trials === trials
                      ? "bg-violet-500 text-white"
                      : "bg-white/5 text-violet-200 border border-violet-400/40 hover:bg-violet-500/10"
                  }
                `}
              >
                {trials}次
              </button>
            ))}
          </div>

          {/* 預估時間 */}
          <div className="mt-3 text-xs text-violet-200 bg-violet-500/20 p-2 rounded">
            <span className="font-medium">預估執行時間:</span>{" "}
            {Math.round(((value.optuna_trials || 100) / 100) * 3)} - {Math.round(((value.optuna_trials || 100) / 100) * 5)} 分鐘
          </div>
        </div>
      )}

      {/* 模式對比表格 */}
      <div className="bg-white/5 border border-white/10 rounded-lg p-3">
        <div className="text-xs font-medium text-slate-200 mb-2">模式對比</div>
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left py-1 text-slate-300">項目</th>
              <th className="text-center py-1 text-sky-300">單次測試</th>
              <th className="text-center py-1 text-violet-300">Optuna優化</th>
            </tr>
          </thead>
          <tbody className="text-slate-300">
            <tr className="border-b border-white/10">
              <td className="py-1">執行時間</td>
              <td className="text-center text-sky-300">快 (&lt;5秒)</td>
              <td className="text-center text-violet-300">慢 (1-5分鐘)</td>
            </tr>
            <tr className="border-b border-white/10">
              <td className="py-1">參數設定</td>
              <td className="text-center text-sky-300">手動指定</td>
              <td className="text-center text-violet-300">自動搜索</td>
            </tr>
            <tr className="border-b border-white/10">
              <td className="py-1">結果數量</td>
              <td className="text-center text-sky-300">單一結果</td>
              <td className="text-center text-violet-300">多組結果</td>
            </tr>
            <tr>
              <td className="py-1">適用場景</td>
              <td className="text-center text-sky-300">驗證策略</td>
              <td className="text-center text-violet-300">發現策略</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* 當前選擇摘要 */}
      {selectedMode && (
        <div className="text-xs text-slate-300 bg-white/5 border border-white/10 p-2 rounded">
          <span className="font-medium text-slate-200">當前模式:</span>{" "}
          <span className="text-slate-100">{selectedMode.label}</span>
          {value.mode === "optuna" && value.optuna_trials && (
            <>
              {" - "}
              <span className="text-violet-300 font-medium">
                {value.optuna_trials} 次試驗
              </span>
            </>
          )}
        </div>
      )}
    </div>
  );
}

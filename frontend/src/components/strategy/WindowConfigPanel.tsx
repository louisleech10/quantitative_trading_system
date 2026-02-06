/**
 * WindowConfigPanel.tsx - 訓練窗口配置組件
 *
 * Phase 3.3+3.4 - Task B2: 配置組件
 *
 * 功能:
 * - 訓練窗口配置 (參考點: TO/TC, 往前N根, 往後M根)
 * - 視覺化時間軸示意圖
 * - 參數說明和使用建議
 * - 即時預覽窗口範圍
 *
 * Ultra Think 記錄:
 * - 步驟 1: 初版代碼 (當前)
 * - 步驟 2: 審查優化 (待執行)
 * - 步驟 3: 最終優化 (待執行)
 */

"use client";

export interface TrainingWindowConfig {
  reference_point: "TO" | "TC";
  lookback_bars: number;
  lookforward_bars: number;
  far_lookback_bars?: number;  // 遠期窗口配置 (雙密度模式)
  mode: "relative" | "full_range";
}

export interface WindowConfigPanelProps {
  value: TrainingWindowConfig;
  onChange: (value: TrainingWindowConfig) => void;
  disabled?: boolean;
  className?: string;
}

const REFERENCE_POINTS = [
  {
    value: "TO" as const,
    label: "TO (開單點)",
    description: "從開單時間點開始計算窗口",
    icon: "🎯",
    color: "blue",
  },
  {
    value: "TC" as const,
    label: "TC (平倉點)",
    description: "從平倉時間點開始計算窗口",
    icon: "🏁",
    color: "green",
  },
];

export default function WindowConfigPanel({
  value,
  onChange,
  disabled = false,
  className = "",
}: WindowConfigPanelProps) {
  const selectedRefPoint = REFERENCE_POINTS.find(
    (point) => point.value === value.reference_point
  );

  const updateField = <K extends keyof TrainingWindowConfig>(
    field: K,
    newValue: TrainingWindowConfig[K]
  ) => {
    onChange({
      ...value,
      [field]: newValue,
    });
  };

  // 計算窗口總數
  const totalBars = value.lookback_bars + value.lookforward_bars;

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 標題 */}
      <div>
        <label className="block text-sm font-medium text-slate-200 mb-1">
          訓練窗口配置
        </label>
        <p className="text-xs text-slate-400">
          定義從哪個參考點開始,往前/往後看多少根K線
        </p>
      </div>

      {/* 參考點選擇 */}
      <div className="space-y-2">
        <label className="block text-xs font-medium text-slate-300">
          參考點
        </label>
        <div className="grid grid-cols-2 gap-2">
          {REFERENCE_POINTS.map((point) => {
            const isSelected = value.reference_point === point.value;
            const colorClass =
              point.color === "blue"
                ? "border-sky-400/60 bg-sky-500/10 text-sky-200"
                : "border-emerald-400/60 bg-emerald-500/10 text-emerald-200";

            return (
              <button
                key={point.value}
                type="button"
                onClick={() =>
                  !disabled && updateField("reference_point", point.value)
                }
                disabled={disabled}
                className={`
                  p-3 rounded-lg border-2 text-left transition-all
                  ${
                    isSelected
                      ? colorClass
                      : "border-white/10 bg-white/5 hover:border-white/20"
                  }
                  ${
                    disabled
                      ? "opacity-50 cursor-not-allowed"
                      : "cursor-pointer"
                  }
                `}
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">{point.icon}</span>
                  <div className="flex-1">
                    <div
                      className={`text-sm font-medium ${
                        isSelected ? "" : "text-slate-100"
                      }`}
                    >
                      {point.label}
                    </div>
                    <div
                      className={`text-xs mt-0.5 ${
                        isSelected
                          ? point.color === "blue"
                            ? "text-sky-300"
                            : "text-emerald-300"
                          : "text-slate-400"
                      }`}
                    >
                      {point.description}
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 窗口參數 */}
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          {/* 往前看 (近期窗口) */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-2">
              近期窗口 (Lookback)
            </label>
            <div className="relative">
              <input
                type="number"
                value={value.lookback_bars}
                onChange={(e) =>
                  updateField("lookback_bars", Number(e.target.value))
                }
                disabled={disabled}
                className={`
                  w-full px-3 py-2 border border-white/10 rounded-lg text-sm
                  bg-white/5 text-slate-100 placeholder:text-slate-500
                  focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400/30
                  ${disabled ? "opacity-60 cursor-not-allowed" : ""}
                `}
                min={1}
                max={1000}
              />
              <div className="text-xs text-slate-400 mt-1">
                從參考點往前 N 根K線
              </div>
            </div>
          </div>

          {/* 往後看 */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-2">
              往後看 (Lookforward)
            </label>
            <div className="relative">
              <input
                type="number"
                value={value.lookforward_bars}
                onChange={(e) =>
                  updateField("lookforward_bars", Number(e.target.value))
                }
                disabled={disabled}
                className={`
                  w-full px-3 py-2 border border-white/10 rounded-lg text-sm
                  bg-white/5 text-slate-100 placeholder:text-slate-500
                  focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400/30
                  ${disabled ? "opacity-60 cursor-not-allowed" : ""}
                `}
                min={0}
                max={100}
              />
              <div className="text-xs text-slate-400 mt-1">
                從參考點往後 M 根K線
              </div>
            </div>
          </div>
        </div>

        {/* 遠期窗口 (雙密度模式) */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-2">
            遠期窗口 (Far Lookback) - 雙密度模式
          </label>
          <div className="relative">
            <input
              type="number"
              value={value.far_lookback_bars || ""}
              onChange={(e) => {
                const val = e.target.value;
                updateField("far_lookback_bars", val === "" ? undefined : Number(val));
              }}
              disabled={disabled}
              placeholder="不啟用雙密度模式"
              className={`
                w-full px-3 py-2 border border-white/10 rounded-lg text-sm
                bg-white/5 text-slate-100 placeholder:text-slate-500
                focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400/30
                ${disabled ? "opacity-60 cursor-not-allowed" : ""}
              `}
              min={value.lookback_bars + 1}
              max={1000}
            />
            <div className="text-xs text-slate-400 mt-1">
              從參考點往前 Z 根K線 (用於背景密度計算，必須 &gt; 近期窗口)
            </div>
          </div>
        </div>
      </div>

      {/* 視覺化時間軸 */}
      <div className="glass-panel p-4 rounded-lg">
        <div className="text-xs font-medium text-slate-200 mb-3">
          窗口視覺化示意圖 {value.far_lookback_bars ? "(雙密度模式)" : ""}
        </div>
        <div className="relative space-y-4">
          {/* 主時間軸 (近期窗口) */}
          <div className="relative">
            <div className="h-2 bg-white/10 rounded-full relative">
              {/* Lookback 區域 */}
              <div
                className="absolute left-0 h-full bg-sky-400 rounded-l-full"
                style={{
                  width: `${
                    (value.lookback_bars / (totalBars || 1)) * 100
                  }%`,
                }}
              />
              {/* Lookforward 區域 */}
              <div
                className="absolute right-0 h-full bg-amber-400 rounded-r-full"
                style={{
                  width: `${
                    (value.lookforward_bars / (totalBars || 1)) * 100
                  }%`,
                }}
              />
              {/* 參考點標記 */}
              <div
                className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-rose-400 rounded-full border-2 border-[#0b1220] shadow"
                style={{
                  left: `${(value.lookback_bars / (totalBars || 1)) * 100}%`,
                  transform: "translate(-50%, -50%)",
                }}
              />
            </div>

            {/* 標籤 */}
            <div className="flex justify-between mt-2 text-xs">
              <div className="text-sky-300 font-medium">
                ← {value.lookback_bars} 根 (近期)
              </div>
              <div className="text-rose-300 font-bold">
                {selectedRefPoint?.icon} {value.reference_point}
              </div>
              <div className="text-amber-300 font-medium">
                {value.lookforward_bars} 根 →
              </div>
            </div>
          </div>

          {/* 雙密度模式: 遠期窗口時間軸 */}
          {value.far_lookback_bars && value.far_lookback_bars > value.lookback_bars && (
            <div className="relative pt-2 border-t border-white/10">
              <div className="text-xs text-violet-300 font-medium mb-2">
                遠期窗口 (背景密度)
              </div>
              <div className="h-2 bg-white/10 rounded-full relative">
                {/* 遠期窗口區域 (排除近期部分) */}
                <div
                  className="absolute left-0 h-full bg-violet-400/70 rounded-l-full"
                  style={{
                    width: `${
                      ((value.far_lookback_bars - value.lookback_bars) / value.far_lookback_bars) * 100
                    }%`,
                  }}
                />
                {/* 近期窗口區域 (灰色顯示) */}
                <div
                  className="absolute right-0 h-full bg-white/20 rounded-r-full opacity-50"
                  style={{
                    width: `${
                      (value.lookback_bars / value.far_lookback_bars) * 100
                    }%`,
                  }}
                />
                {/* 參考點標記 */}
                <div
                  className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-rose-400 rounded-full border-2 border-[#0b1220] shadow"
                  style={{
                    right: "0%",
                    transform: "translate(50%, -50%)",
                  }}
                />
              </div>
              <div className="flex justify-between mt-2 text-xs">
                <div className="text-violet-300 font-medium">
                  ← {value.far_lookback_bars - value.lookback_bars} 根 (遠期)
                </div>
                <div className="text-slate-400">
                  排除近期 {value.lookback_bars} 根
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 窗口統計 */}
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
          <div className="bg-white/5 border border-white/10 p-2 rounded">
            <div className="text-slate-400">近期窗口總長</div>
            <div className="text-slate-100 font-semibold">{totalBars} 根K線</div>
          </div>
          {value.far_lookback_bars ? (
            <div className="bg-white/5 border border-white/10 p-2 rounded">
              <div className="text-slate-400">遠期窗口總長</div>
              <div className="text-violet-300 font-semibold">{value.far_lookback_bars} 根K線</div>
            </div>
          ) : (
            <div className="bg-white/5 border border-white/10 p-2 rounded">
              <div className="text-slate-400">窗口模式</div>
              <div className="text-slate-100 font-semibold">
                {value.mode === "relative" ? "嚴格模式" : "彈性模式"}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 常用預設配置 */}
      <div className="space-y-2">
        <label className="block text-xs font-medium text-slate-300">
          快速預設
        </label>
        <div className="grid grid-cols-3 gap-2">
          <button
            type="button"
            onClick={() =>
              !disabled &&
              onChange({
                reference_point: "TO",
                lookback_bars: 24,
                lookforward_bars: 0,
                mode: "relative",
              })
            }
            disabled={disabled}
            className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-xs text-slate-200 hover:bg-white/10 transition-colors"
          >
            <div className="font-medium text-slate-100">TO前24根</div>
            <div className="text-slate-400">單密度</div>
          </button>
          <button
            type="button"
            onClick={() =>
              !disabled &&
              onChange({
                reference_point: "TC",
                lookback_bars: 12,
                lookforward_bars: 12,
                mode: "relative",
              })
            }
            disabled={disabled}
            className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-xs text-slate-200 hover:bg-white/10 transition-colors"
          >
            <div className="font-medium text-slate-100">TC前後各12根</div>
            <div className="text-slate-400">對稱窗口</div>
          </button>
          <button
            type="button"
            onClick={() =>
              !disabled &&
              onChange({
                reference_point: "TO",
                lookback_bars: 24,
                lookforward_bars: 0,
                far_lookback_bars: 100,
                mode: "relative",
              })
            }
            disabled={disabled}
            className="px-3 py-2 bg-violet-500/10 border border-violet-400/40 rounded-lg text-xs text-violet-200 hover:bg-violet-500/20 transition-colors"
          >
            <div className="font-medium text-violet-100">雙窗口模式</div>
            <div className="text-violet-300">近24 / 遠100</div>
          </button>
        </div>
      </div>

      {/* 提示訊息 */}
      <div className="space-y-2">
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <span className="text-amber-300 text-sm">⚠️</span>
            <div className="text-xs text-amber-200">
              <div className="font-medium mb-1">未來函數洩漏警告:</div>
              <div className="text-amber-200/80">
                • lookforward_bars &gt; 0 可能導致未來函數洩漏
                <br />• 建議使用 lookforward_bars = 0 確保策略有效性
              </div>
            </div>
          </div>
        </div>

        {value.far_lookback_bars && value.far_lookback_bars > value.lookback_bars && (
          <div className="bg-violet-500/10 border border-violet-400/30 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <span className="text-violet-300 text-sm">💡</span>
              <div className="text-xs text-violet-200">
                <div className="font-medium mb-1">雙密度模式已啟用:</div>
                <div className="text-violet-200/80">
                  • 近期窗口: {value.reference_point}-{value.lookback_bars} 到 {value.reference_point}-1
                  <br />• 遠期窗口: {value.reference_point}-{value.far_lookback_bars} 到 {value.reference_point}-{value.lookback_bars + 1}
                  <br />• 優化目標: 正例 near/far ratio &gt;&gt; 反例 near/far ratio
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

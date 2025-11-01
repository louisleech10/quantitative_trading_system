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
        <label className="block text-sm font-medium text-gray-700 mb-1">
          訓練窗口配置
        </label>
        <p className="text-xs text-gray-500">
          定義從哪個參考點開始,往前/往後看多少根K線
        </p>
      </div>

      {/* 參考點選擇 */}
      <div className="space-y-2">
        <label className="block text-xs font-medium text-gray-600">
          參考點
        </label>
        <div className="grid grid-cols-2 gap-2">
          {REFERENCE_POINTS.map((point) => {
            const isSelected = value.reference_point === point.value;
            const colorClass =
              point.color === "blue"
                ? "border-blue-500 bg-blue-50 text-blue-900"
                : "border-green-500 bg-green-50 text-green-900";

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
                      : "border-gray-200 bg-white hover:border-gray-300"
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
                        isSelected ? "" : "text-gray-900"
                      }`}
                    >
                      {point.label}
                    </div>
                    <div
                      className={`text-xs mt-0.5 ${
                        isSelected
                          ? point.color === "blue"
                            ? "text-blue-600"
                            : "text-green-600"
                          : "text-gray-500"
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
      <div className="grid grid-cols-2 gap-4">
        {/* 往前看 */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-2">
            往前看 (Lookback)
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
                w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
                ${disabled ? "bg-gray-100 cursor-not-allowed" : ""}
              `}
              min={1}
              max={1000}
            />
            <div className="text-xs text-gray-500 mt-1">
              從參考點往前 N 根K線
            </div>
          </div>
        </div>

        {/* 往後看 */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-2">
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
                w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
                ${disabled ? "bg-gray-100 cursor-not-allowed" : ""}
              `}
              min={0}
              max={100}
            />
            <div className="text-xs text-gray-500 mt-1">
              從參考點往後 M 根K線
            </div>
          </div>
        </div>
      </div>

      {/* 視覺化時間軸 */}
      <div className="bg-gray-50 p-4 rounded-lg">
        <div className="text-xs font-medium text-gray-700 mb-3">
          窗口視覺化示意圖
        </div>
        <div className="relative">
          {/* 時間軸 */}
          <div className="h-2 bg-gray-200 rounded-full relative">
            {/* Lookback 區域 */}
            <div
              className="absolute left-0 h-full bg-blue-400 rounded-l-full"
              style={{
                width: `${
                  (value.lookback_bars / (totalBars || 1)) * 100
                }%`,
              }}
            />
            {/* Lookforward 區域 */}
            <div
              className="absolute right-0 h-full bg-orange-400 rounded-r-full"
              style={{
                width: `${
                  (value.lookforward_bars / (totalBars || 1)) * 100
                }%`,
              }}
            />
            {/* 參考點標記 */}
            <div
              className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-red-500 rounded-full border-2 border-white shadow"
              style={{
                left: `${(value.lookback_bars / (totalBars || 1)) * 100}%`,
                transform: "translate(-50%, -50%)",
              }}
            />
          </div>

          {/* 標籤 */}
          <div className="flex justify-between mt-2 text-xs">
            <div className="text-blue-600 font-medium">
              ← {value.lookback_bars} 根
            </div>
            <div className="text-red-600 font-bold">
              {selectedRefPoint?.icon} {value.reference_point}
            </div>
            <div className="text-orange-600 font-medium">
              {value.lookforward_bars} 根 →
            </div>
          </div>
        </div>

        {/* 窗口統計 */}
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
          <div className="bg-white p-2 rounded">
            <div className="text-gray-500">窗口總長</div>
            <div className="text-gray-900 font-semibold">{totalBars} 根K線</div>
          </div>
          <div className="bg-white p-2 rounded">
            <div className="text-gray-500">窗口模式</div>
            <div className="text-gray-900 font-semibold">
              {value.mode === "relative" ? "嚴格模式" : "彈性模式"}
            </div>
          </div>
        </div>
      </div>

      {/* 常用預設配置 */}
      <div className="space-y-2">
        <label className="block text-xs font-medium text-gray-600">
          快速預設
        </label>
        <div className="grid grid-cols-2 gap-2">
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
            className="px-3 py-2 bg-white border border-gray-300 rounded-lg text-xs hover:bg-gray-50 transition-colors"
          >
            <div className="font-medium text-gray-900">TO前24根</div>
            <div className="text-gray-500">常用配置</div>
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
            className="px-3 py-2 bg-white border border-gray-300 rounded-lg text-xs hover:bg-gray-50 transition-colors"
          >
            <div className="font-medium text-gray-900">TC前後各12根</div>
            <div className="text-gray-500">對稱窗口</div>
          </button>
        </div>
      </div>

      {/* 提示訊息 */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
        <div className="flex items-start gap-2">
          <span className="text-yellow-600 text-sm">⚠️</span>
          <div className="text-xs text-yellow-700">
            <div className="font-medium mb-1">未來函數洩漏警告:</div>
            <div className="text-yellow-600">
              • lookforward_bars &gt; 0 可能導致未來函數洩漏
              <br />• 建議使用 lookforward_bars = 0 確保策略有效性
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

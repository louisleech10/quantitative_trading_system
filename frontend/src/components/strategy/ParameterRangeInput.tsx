/**
 * ParameterRangeInput.tsx - 參數範圍輸入組件
 *
 * Phase 3.3+3.4 - Task B2: 配置組件
 *
 * 功能:
 * - EMA 短中長期參數範圍設定 (min, max, step)
 * - 即時參數驗證 (短 < 中 < 長)
 * - 視覺化範圍指示器
 * - 支援單次測試模式 (固定值) 和 Optuna 優化模式 (範圍)
 *
 * Ultra Think 記錄:
 * - 步驟 1: 初版代碼 (當前)
 * - 步驟 2: 審查優化 (待執行)
 * - 步驟 3: 最終優化 (待執行)
 */

"use client";

import { useState, useEffect } from "react";

export interface ParameterRange {
  min: number;
  max: number;
  step: number;
}

export interface EMAParameters {
  ema_short: ParameterRange | number;
  ema_mid: ParameterRange | number;
  ema_long: ParameterRange | number;
}

export interface ParameterRangeInputProps {
  value: EMAParameters;
  onChange: (value: EMAParameters) => void;
  mode: "single" | "optuna"; // 單次測試 vs Optuna 優化
  disabled?: boolean;
  className?: string;
}

interface ValidationError {
  field: string;
  message: string;
}

export default function ParameterRangeInput({
  value,
  onChange,
  mode,
  disabled = false,
  className = "",
}: ParameterRangeInputProps) {
  const [errors, setErrors] = useState<ValidationError[]>([]);

  // 驗證參數範圍
  useEffect(() => {
    const newErrors: ValidationError[] = [];

    if (mode === "optuna") {
      const short = value.ema_short as ParameterRange;
      const mid = value.ema_mid as ParameterRange;
      const long = value.ema_long as ParameterRange;

      // 驗證 min < max
      if (short.min >= short.max) {
        newErrors.push({
          field: "ema_short",
          message: "最小值必須小於最大值",
        });
      }
      if (mid.min >= mid.max) {
        newErrors.push({
          field: "ema_mid",
          message: "最小值必須小於最大值",
        });
      }
      if (long.min >= long.max) {
        newErrors.push({
          field: "ema_long",
          message: "最小值必須小於最大值",
        });
      }

      // 驗證 short.max < mid.min
      if (short.max >= mid.min) {
        newErrors.push({
          field: "ema_mid",
          message: `中期最小值(${mid.min})必須大於短期最大值(${short.max})`,
        });
      }

      // 驗證 mid.max < long.min
      if (mid.max >= long.min) {
        newErrors.push({
          field: "ema_long",
          message: `長期最小值(${long.min})必須大於中期最大值(${mid.max})`,
        });
      }
    } else {
      // 單次模式: 驗證 short < mid < long
      const short = value.ema_short as number;
      const mid = value.ema_mid as number;
      const long = value.ema_long as number;

      if (short >= mid) {
        newErrors.push({
          field: "ema_mid",
          message: `中期(${mid})必須大於短期(${short})`,
        });
      }
      if (mid >= long) {
        newErrors.push({
          field: "ema_long",
          message: `長期(${long})必須大於中期(${mid})`,
        });
      }
    }

    setErrors(newErrors);
  }, [value, mode]);

  const hasError = (field: string) =>
    errors.some((err) => err.field === field);
  const getError = (field: string) =>
    errors.find((err) => err.field === field)?.message;

  // 單次模式: 固定值輸入
  const renderSingleMode = () => {
    const short = value.ema_short as number;
    const mid = value.ema_mid as number;
    const long = value.ema_long as number;

    return (
      <div className="grid grid-cols-3 gap-4">
        {/* 短期 EMA */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            短期 EMA
          </label>
          <input
            type="number"
            value={short}
            onChange={(e) =>
              onChange({
                ...value,
                ema_short: Number(e.target.value),
              })
            }
            disabled={disabled}
            className={`
              w-full px-3 py-2 border rounded-lg text-sm
              ${
                hasError("ema_short")
                  ? "border-rose-400/60 bg-rose-500/10"
                  : "border-white/10 bg-white/5"
              }
              text-slate-100 placeholder:text-slate-500
              focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400/30
              ${disabled ? "opacity-60 cursor-not-allowed" : ""}
            `}
            min={1}
            max={200}
          />
          <div className="text-xs text-slate-400 mt-1">建議: 5-10</div>
        </div>

        {/* 中期 EMA */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            中期 EMA
          </label>
          <input
            type="number"
            value={mid}
            onChange={(e) =>
              onChange({
                ...value,
                ema_mid: Number(e.target.value),
              })
            }
            disabled={disabled}
            className={`
              w-full px-3 py-2 border rounded-lg text-sm
              ${
                hasError("ema_mid")
                  ? "border-rose-400/60 bg-rose-500/10"
                  : "border-white/10 bg-white/5"
              }
              text-slate-100 placeholder:text-slate-500
              focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400/30
              ${disabled ? "opacity-60 cursor-not-allowed" : ""}
            `}
            min={1}
            max={200}
          />
          <div className="text-xs text-slate-400 mt-1">建議: 15-20</div>
          {hasError("ema_mid") && (
            <div className="text-xs text-rose-300 mt-1">
              {getError("ema_mid")}
            </div>
          )}
        </div>

        {/* 長期 EMA */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            長期 EMA
          </label>
          <input
            type="number"
            value={long}
            onChange={(e) =>
              onChange({
                ...value,
                ema_long: Number(e.target.value),
              })
            }
            disabled={disabled}
            className={`
              w-full px-3 py-2 border rounded-lg text-sm
              ${
                hasError("ema_long")
                  ? "border-rose-400/60 bg-rose-500/10"
                  : "border-white/10 bg-white/5"
              }
              text-slate-100 placeholder:text-slate-500
              focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400/30
              ${disabled ? "opacity-60 cursor-not-allowed" : ""}
            `}
            min={1}
            max={200}
          />
          <div className="text-xs text-slate-400 mt-1">建議: 30-40</div>
          {hasError("ema_long") && (
            <div className="text-xs text-rose-300 mt-1">
              {getError("ema_long")}
            </div>
          )}
        </div>
      </div>
    );
  };

  // Optuna 模式: 範圍輸入
  const renderOptunaMode = () => {
    const short = value.ema_short as ParameterRange;
    const mid = value.ema_mid as ParameterRange;
    const long = value.ema_long as ParameterRange;

    const renderRangeInput = (
      label: string,
      field: "ema_short" | "ema_mid" | "ema_long",
      range: ParameterRange,
      suggestion: string
    ) => (
      <div className={hasError(field) ? "bg-rose-500/10 border border-rose-500/30 p-3 rounded-lg" : ""}>
        <label className="block text-xs font-medium text-slate-300 mb-2">
          {label}
        </label>
        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="block text-xs text-slate-400 mb-1">最小值</label>
            <input
              type="number"
              value={range.min}
              onChange={(e) =>
                onChange({
                  ...value,
                  [field]: { ...range, min: Number(e.target.value) },
                })
              }
              disabled={disabled}
              className="w-full px-2 py-1.5 border border-white/10 rounded text-sm bg-white/5 text-slate-100 focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400/30"
              min={1}
              max={200}
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">最大值</label>
            <input
              type="number"
              value={range.max}
              onChange={(e) =>
                onChange({
                  ...value,
                  [field]: { ...range, max: Number(e.target.value) },
                })
              }
              disabled={disabled}
              className="w-full px-2 py-1.5 border border-white/10 rounded text-sm bg-white/5 text-slate-100 focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400/30"
              min={1}
              max={200}
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">步長</label>
            <input
              type="number"
              value={range.step}
              onChange={(e) =>
                onChange({
                  ...value,
                  [field]: { ...range, step: Number(e.target.value) },
                })
              }
              disabled={disabled}
              className="w-full px-2 py-1.5 border border-white/10 rounded text-sm bg-white/5 text-slate-100 focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400/30"
              min={1}
              max={10}
            />
          </div>
        </div>
        <div className="flex items-center justify-between mt-1">
          <div className="text-xs text-slate-400">{suggestion}</div>
          <div className="text-xs text-slate-300">
            範圍: {range.min} - {range.max}
          </div>
        </div>
        {hasError(field) && (
          <div className="text-xs text-rose-300 mt-2 font-medium">
            ⚠️ {getError(field)}
          </div>
        )}
      </div>
    );

    return (
      <div className="space-y-3">
        {renderRangeInput("短期 EMA", "ema_short", short, "建議: 5-10")}
        {renderRangeInput("中期 EMA", "ema_mid", mid, "建議: 15-20")}
        {renderRangeInput("長期 EMA", "ema_long", long, "建議: 30-40")}
      </div>
    );
  };

  return (
    <div className={`space-y-3 ${className}`}>
      {/* 標題 */}
      <div>
        <label className="block text-sm font-medium text-slate-200 mb-1">
          EMA 參數{mode === "optuna" ? "範圍" : "設定"}
        </label>
        <p className="text-xs text-slate-400">
          {mode === "optuna"
            ? "設定 Optuna 優化的參數搜索範圍"
            : "設定固定的 EMA 參數值"}
        </p>
      </div>

      {/* 參數輸入 */}
      {mode === "single" ? renderSingleMode() : renderOptunaMode()}

      {/* 驗證狀態 */}
      {errors.length === 0 ? (
        <div className="flex items-center gap-2 text-xs text-emerald-200 bg-emerald-500/10 border border-emerald-500/30 p-2 rounded">
          <span>✅</span>
          <span>參數驗證通過</span>
        </div>
      ) : (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-2">
          <div className="text-xs font-medium text-rose-200 mb-1">
            ⚠️ 參數驗證失敗
          </div>
          <ul className="text-xs text-rose-200/80 space-y-1">
            {errors.map((err, idx) => (
              <li key={idx}>• {err.message}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 約束條件提示 */}
      <div className="bg-sky-500/10 border border-sky-500/30 rounded-lg p-2">
        <div className="text-xs text-sky-200">
          <div className="font-medium mb-1">參數約束條件:</div>
          <div className="text-sky-200/80">
            {mode === "optuna" ? (
              <>
                • 短期最大值 &lt; 中期最小值 &lt; 中期最大值 &lt; 長期最小值
                <br />• 確保參數範圍不重疊,保證優化結果有效性
              </>
            ) : (
              <>• 短期 &lt; 中期 &lt; 長期 (如: 7 &lt; 18 &lt; 35)</>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

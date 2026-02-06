"use client";

import React from "react";

interface StatMetricCardProps {
  label: string;
  value: number | null | undefined;
  std?: number | null;
  helper?: string;
  source?: string;  // 數據來源/計算公式說明
  format?: "percent" | "decimal" | "ratio" | "number";
  showConfidence?: boolean;
  colorCode?: boolean; // Color code based on CV (coefficient of variation)
}

/**
 * Statistical Metric Card Component
 *
 * Displays a metric value with optional standard deviation (± std)
 * Supports different formats and color coding based on stability
 */
export default function StatMetricCard({
  label,
  value,
  std,
  helper,
  source,
  format = "decimal",
  showConfidence = false,
  colorCode = false,
}: StatMetricCardProps) {
  // Format value based on type
  const formatValue = (val: number | null | undefined): string => {
    // Handle null, undefined, and NaN values
    if (val === null || val === undefined || Number.isNaN(val)) {
      return "—";
    }
    switch (format) {
      case "percent":
        return `${(val * 100).toFixed(2)}%`;
      case "ratio":
        return val.toFixed(4);
      case "number":
        return val.toFixed(0);
      case "decimal":
      default:
        return val.toFixed(4);
    }
  };

  // Helper to check if a value is valid for calculations
  const isValidNumber = (val: number | null | undefined): val is number => {
    return val !== null && val !== undefined && !Number.isNaN(val);
  };

  // Calculate coefficient of variation for color coding
  const getStabilityColor = (): string => {
    if (!colorCode || !isValidNumber(std) || !isValidNumber(value) || value === 0) {
      return "text-slate-100";
    }

    const cv = Math.abs(std / value);

    if (cv < 0.3) return "text-emerald-400"; // Stable
    if (cv < 0.5) return "text-amber-400"; // Moderate
    return "text-rose-400"; // Unstable
  };

  // Calculate 95% confidence interval (mean ± 1.96 * std)
  const confidenceInterval = isValidNumber(std) && isValidNumber(value)
    ? {
        lower: value - 1.96 * std,
        upper: value + 1.96 * std,
      }
    : null;

  return (
    <div className="glass-panel rounded-xl p-4">
      {/* Label */}
      <div className="text-sm font-medium text-slate-400 mb-1">{label}</div>

      {/* Value with Standard Deviation */}
      <div className={`text-2xl font-semibold ${getStabilityColor()}`}>
        {formatValue(value)}
        {isValidNumber(std) && std > 0 && (
          <span className="text-base font-normal text-slate-400 ml-2">
            (± {formatValue(std)})
          </span>
        )}
      </div>

      {/* Confidence Interval */}
      {showConfidence && confidenceInterval && (
        <div className="text-xs text-slate-400 mt-1">
          95% CI: [{formatValue(confidenceInterval.lower)}, {formatValue(confidenceInterval.upper)}]
        </div>
      )}

      {/* Helper Text / Tooltip */}
      {helper && (
        <div className="text-xs text-slate-500 mt-2 leading-tight">
          {helper}
        </div>
      )}

      {/* Source / Formula */}
      {source && (
        <div className="text-xs text-blue-400 mt-1 leading-tight font-mono">
          {source}
        </div>
      )}

      {/* Stability Indicator */}
      {colorCode && isValidNumber(std) && isValidNumber(value) && value !== 0 && (
        <div className="mt-2 flex items-center text-xs">
          <div className="flex-1">
            <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
              <div
                className={`h-full ${
                  Math.abs(std / value) < 0.3
                    ? "bg-emerald-400"
                    : Math.abs(std / value) < 0.5
                    ? "bg-amber-400"
                    : "bg-rose-400"
                }`}
                style={{
                  width: `${Math.min(100, (Math.abs(std / value) / 0.5) * 100)}%`,
                }}
              />
            </div>
          </div>
          <span className="ml-2 text-slate-400">
            CV: {((Math.abs(std / value)) * 100).toFixed(1)}%
          </span>
        </div>
      )}
    </div>
  );
}

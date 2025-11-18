"use client";

import React from "react";

interface StatMetricCardProps {
  label: string;
  value: number;
  std?: number;
  helper?: string;
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
  format = "decimal",
  showConfidence = false,
  colorCode = false,
}: StatMetricCardProps) {
  // Format value based on type
  const formatValue = (val: number): string => {
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

  // Calculate coefficient of variation for color coding
  const getStabilityColor = (): string => {
    if (!colorCode || !std || value === 0) return "text-gray-900";

    const cv = Math.abs(std / value);

    if (cv < 0.3) return "text-green-600"; // Stable
    if (cv < 0.5) return "text-yellow-600"; // Moderate
    return "text-red-600"; // Unstable
  };

  // Calculate 95% confidence interval (mean ± 1.96 * std)
  const confidenceInterval = std
    ? {
        lower: value - 1.96 * std,
        upper: value + 1.96 * std,
      }
    : null;

  return (
    <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
      {/* Label */}
      <div className="text-sm font-medium text-gray-600 mb-1">{label}</div>

      {/* Value with Standard Deviation */}
      <div className={`text-2xl font-bold ${getStabilityColor()}`}>
        {formatValue(value)}
        {std !== undefined && std > 0 && (
          <span className="text-base font-normal text-gray-500 ml-2">
            (± {formatValue(std)})
          </span>
        )}
      </div>

      {/* Confidence Interval */}
      {showConfidence && confidenceInterval && (
        <div className="text-xs text-gray-500 mt-1">
          95% CI: [{formatValue(confidenceInterval.lower)}, {formatValue(confidenceInterval.upper)}]
        </div>
      )}

      {/* Helper Text / Tooltip */}
      {helper && (
        <div className="text-xs text-gray-400 mt-2 leading-tight">
          {helper}
        </div>
      )}

      {/* Stability Indicator */}
      {colorCode && std && value !== 0 && (
        <div className="mt-2 flex items-center text-xs">
          <div className="flex-1">
            <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full ${
                  Math.abs(std / value) < 0.3
                    ? "bg-green-500"
                    : Math.abs(std / value) < 0.5
                    ? "bg-yellow-500"
                    : "bg-red-500"
                }`}
                style={{
                  width: `${Math.min(100, (Math.abs(std / value) / 0.5) * 100)}%`,
                }}
              />
            </div>
          </div>
          <span className="ml-2 text-gray-500">
            CV: {((Math.abs(std / value)) * 100).toFixed(1)}%
          </span>
        </div>
      )}
    </div>
  );
}

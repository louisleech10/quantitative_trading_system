"use client";

import React, { useMemo } from "react";

interface DensityDistributionChartProps {
  caseLevelDensities: Record<string, number>;
  positiveCases: string[];
  negativeCases: string[];
  title?: string;
  mode?: "near" | "far" | "ratio";
}

interface BoxPlotStats {
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  outliers: number[];
  mean: number;
  std: number;
}

/**
 * Calculate boxplot statistics from an array of values
 */
function calculateBoxPlotStats(values: number[]): BoxPlotStats {
  if (values.length === 0) {
    return {
      min: 0,
      q1: 0,
      median: 0,
      q3: 0,
      max: 0,
      outliers: [],
      mean: 0,
      std: 0,
    };
  }

  const sorted = [...values].sort((a, b) => a - b);
  const n = sorted.length;

  // Calculate quartiles
  const q1Index = Math.floor(n * 0.25);
  const medianIndex = Math.floor(n * 0.5);
  const q3Index = Math.floor(n * 0.75);

  const q1 = sorted[q1Index];
  const median = sorted[medianIndex];
  const q3 = sorted[q3Index];
  const iqr = q3 - q1;

  // Calculate outliers (values beyond 1.5 * IQR from quartiles)
  const lowerFence = q1 - 1.5 * iqr;
  const upperFence = q3 + 1.5 * iqr;

  const outliers = sorted.filter((v) => v < lowerFence || v > upperFence);
  const nonOutliers = sorted.filter((v) => v >= lowerFence && v <= upperFence);

  const min = nonOutliers.length > 0 ? nonOutliers[0] : sorted[0];
  const max =
    nonOutliers.length > 0 ? nonOutliers[nonOutliers.length - 1] : sorted[n - 1];

  // Calculate mean and std
  const mean = values.reduce((sum, v) => sum + v, 0) / n;
  const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / n;
  const std = Math.sqrt(variance);

  return { min, q1, median, q3, max, outliers, mean, std };
}

/**
 * Density Distribution Chart with Boxplot
 *
 * Displays boxplot comparison between positive and negative cases
 * Shows min, Q1, median, Q3, max, and outliers
 */
export default function DensityDistributionChart({
  caseLevelDensities,
  positiveCases,
  negativeCases,
  title = "密度分佈對比 (Boxplot)",
  mode = "near",
}: DensityDistributionChartProps) {
  // Calculate boxplot data
  const { positiveStats, negativeStats } = useMemo(() => {
    // Extract positive densities
    const positiveDensities = positiveCases
      .map((caseId) => {
        // Handle dual density mode prefixes
        const key =
          mode === "far"
            ? `__far_${caseId}`
            : mode === "near"
            ? `__near_${caseId}`
            : caseId;
        return caseLevelDensities[key] ?? caseLevelDensities[caseId];
      })
      .filter((v) => v !== undefined);

    // Extract negative densities
    const negativeDensities = negativeCases
      .map((caseId) => {
        const key =
          mode === "far"
            ? `__far_${caseId}`
            : mode === "near"
            ? `__near_${caseId}`
            : caseId;
        return caseLevelDensities[key] ?? caseLevelDensities[caseId];
      })
      .filter((v) => v !== undefined);

    return {
      positiveStats: calculateBoxPlotStats(positiveDensities),
      negativeStats: calculateBoxPlotStats(negativeDensities),
    };
  }, [caseLevelDensities, positiveCases, negativeCases, mode]);

  // Find global min/max for Y-axis
  const globalMin = Math.min(positiveStats.min, negativeStats.min);
  const globalMax = Math.max(positiveStats.max, negativeStats.max);
  const padding = (globalMax - globalMin) * 0.1;
  const yMin = Math.max(0, globalMin - padding);
  const yMax = globalMax + padding;

  // Chart dimensions
  const chartWidth = 600;
  const chartHeight = 400;
  const margin = { top: 40, right: 40, bottom: 80, left: 60 };
  const plotWidth = chartWidth - margin.left - margin.right;
  const plotHeight = chartHeight - margin.top - margin.bottom;

  // Scale function for Y-axis
  const scaleY = (value: number) => {
    return plotHeight - ((value - yMin) / (yMax - yMin)) * plotHeight;
  };

  // Boxplot positions (X-axis)
  const positiveX = plotWidth * 0.25;
  const negativeX = plotWidth * 0.75;
  const boxWidth = 60;

  // Render a single boxplot
  const renderBoxplot = (
    stats: BoxPlotStats,
    x: number,
    color: string,
    label: string
  ) => {
    const q1Y = scaleY(stats.q1);
    const q3Y = scaleY(stats.q3);
    const medianY = scaleY(stats.median);
    const minY = scaleY(stats.min);
    const maxY = scaleY(stats.max);
    const meanY = scaleY(stats.mean);

    return (
      <g key={label}>
        {/* Upper whisker */}
        <line
          x1={x}
          y1={maxY}
          x2={x}
          y2={q3Y}
          stroke="#374151"
          strokeWidth={1.5}
        />
        <line
          x1={x - 10}
          y1={maxY}
          x2={x + 10}
          y2={maxY}
          stroke="#374151"
          strokeWidth={1.5}
        />

        {/* Box (Q1 to Q3) */}
        <rect
          x={x - boxWidth / 2}
          y={q3Y}
          width={boxWidth}
          height={q1Y - q3Y}
          fill={color}
          fillOpacity={0.7}
          stroke={color}
          strokeWidth={2}
          rx={4}
        />

        {/* Median line */}
        <line
          x1={x - boxWidth / 2}
          y1={medianY}
          x2={x + boxWidth / 2}
          y2={medianY}
          stroke="#1e293b"
          strokeWidth={3}
        />

        {/* Mean marker (circle) */}
        <circle cx={x} cy={meanY} r={5} fill="#f59e0b" stroke="#fff" strokeWidth={2} />

        {/* Lower whisker */}
        <line
          x1={x}
          y1={q1Y}
          x2={x}
          y2={minY}
          stroke="#374151"
          strokeWidth={1.5}
        />
        <line
          x1={x - 10}
          y1={minY}
          x2={x + 10}
          y2={minY}
          stroke="#374151"
          strokeWidth={1.5}
        />

        {/* Outliers */}
        {stats.outliers.map((outlier, i) => (
          <circle
            key={i}
            cx={x}
            cy={scaleY(outlier)}
            r={3}
            fill="none"
            stroke={color}
            strokeWidth={1.5}
          />
        ))}

        {/* Label */}
        <text
          x={x}
          y={plotHeight + 30}
          textAnchor="middle"
          fontSize={14}
          fill="#64748b"
          fontWeight="500"
        >
          {label}
        </text>
      </g>
    );
  };

  // Y-axis ticks
  const yTicks = [];
  const tickCount = 6;
  for (let i = 0; i <= tickCount; i++) {
    const value = yMin + ((yMax - yMin) / tickCount) * i;
    yTicks.push(value);
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
        <p className="text-sm text-slate-500">
          箱型圖顯示數據分佈: 箱體 (Q1-Q3)、中位數 (黑線)、平均值 (橘點)、鬚線
          (min-max)、離群值 (空心圓)
        </p>
      </div>

      {/* SVG Boxplot */}
      <div className="flex justify-center">
        <svg
          width={chartWidth}
          height={chartHeight}
          className="overflow-visible"
          style={{ fontFamily: "sans-serif" }}
        >
          <g transform={`translate(${margin.left},${margin.top})`}>
            {/* Grid lines */}
            {yTicks.map((tick, i) => (
              <line
                key={i}
                x1={0}
                y1={scaleY(tick)}
                x2={plotWidth}
                y2={scaleY(tick)}
                stroke="#e5e7eb"
                strokeDasharray="3 3"
              />
            ))}

            {/* Y-axis */}
            <line
              x1={0}
              y1={0}
              x2={0}
              y2={plotHeight}
              stroke="#9ca3af"
              strokeWidth={2}
            />

            {/* Y-axis ticks and labels */}
            {yTicks.map((tick, i) => (
              <g key={i}>
                <line
                  x1={-5}
                  y1={scaleY(tick)}
                  x2={0}
                  y2={scaleY(tick)}
                  stroke="#9ca3af"
                  strokeWidth={2}
                />
                <text
                  x={-10}
                  y={scaleY(tick)}
                  textAnchor="end"
                  dominantBaseline="middle"
                  fontSize={12}
                  fill="#64748b"
                >
                  {tick.toFixed(3)}
                </text>
              </g>
            ))}

            {/* X-axis */}
            <line
              x1={0}
              y1={plotHeight}
              x2={plotWidth}
              y2={plotHeight}
              stroke="#9ca3af"
              strokeWidth={2}
            />

            {/* Y-axis label */}
            <text
              x={-40}
              y={plotHeight / 2}
              textAnchor="middle"
              fontSize={12}
              fill="#64748b"
              fontWeight="500"
              transform={`rotate(-90, -40, ${plotHeight / 2})`}
            >
              密度 Density
            </text>

            {/* Boxplots */}
            {renderBoxplot(positiveStats, positiveX, "#10b981", "正例 Positive")}
            {renderBoxplot(negativeStats, negativeX, "#ef4444", "反例 Negative")}
          </g>

          {/* Legend */}
          <g transform={`translate(${margin.left + plotWidth / 2 - 150}, 10)`}>
            <rect x={0} y={0} width={15} height={15} fill="#10b981" opacity={0.7} />
            <text x={20} y={12} fontSize={12} fill="#64748b">
              正例 Positive
            </text>

            <rect x={120} y={0} width={15} height={15} fill="#ef4444" opacity={0.7} />
            <text x={140} y={12} fontSize={12} fill="#64748b">
              反例 Negative
            </text>

            <line x1={250} y1={7} x2={265} y2={7} stroke="#1e293b" strokeWidth={3} />
            <text x={270} y={12} fontSize={12} fill="#64748b">
              中位數
            </text>

            <circle cx={340} cy={7} r={5} fill="#f59e0b" />
            <text x={350} y={12} fontSize={12} fill="#64748b">
              平均值
            </text>
          </g>
        </svg>
      </div>

      {/* Statistics Summary */}
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-green-200 bg-green-50 p-4">
          <h4 className="mb-2 font-semibold text-green-900">正例統計</h4>
          <div className="space-y-1 text-xs text-green-700">
            <p>
              <span className="font-medium">中位數:</span> {positiveStats.median.toFixed(4)}
            </p>
            <p>
              <span className="font-medium">平均值:</span>{" "}
              {positiveStats.mean.toFixed(4)} (± {positiveStats.std.toFixed(4)})
            </p>
            <p>
              <span className="font-medium">四分位距 IQR:</span>{" "}
              [{positiveStats.q1.toFixed(4)}, {positiveStats.q3.toFixed(4)}]
            </p>
            <p>
              <span className="font-medium">範圍:</span> [{positiveStats.min.toFixed(4)},{" "}
              {positiveStats.max.toFixed(4)}]
            </p>
            {positiveStats.outliers.length > 0 && (
              <p className="text-amber-600">
                <span className="font-medium">離群值:</span> {positiveStats.outliers.length}{" "}
                個
              </p>
            )}
          </div>
        </div>
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <h4 className="mb-2 font-semibold text-red-900">反例統計</h4>
          <div className="space-y-1 text-xs text-red-700">
            <p>
              <span className="font-medium">中位數:</span> {negativeStats.median.toFixed(4)}
            </p>
            <p>
              <span className="font-medium">平均值:</span>{" "}
              {negativeStats.mean.toFixed(4)} (± {negativeStats.std.toFixed(4)})
            </p>
            <p>
              <span className="font-medium">四分位距 IQR:</span>{" "}
              [{negativeStats.q1.toFixed(4)}, {negativeStats.q3.toFixed(4)}]
            </p>
            <p>
              <span className="font-medium">範圍:</span> [{negativeStats.min.toFixed(4)},{" "}
              {negativeStats.max.toFixed(4)}]
            </p>
            {negativeStats.outliers.length > 0 && (
              <p className="text-amber-600">
                <span className="font-medium">離群值:</span> {negativeStats.outliers.length}{" "}
                個
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

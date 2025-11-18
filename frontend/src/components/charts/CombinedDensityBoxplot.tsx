"use client";

import React, { useMemo } from "react";

interface CombinedDensityBoxplotProps {
  caseLevelDensities: Record<string, number>;
  positiveCases: string[];
  negativeCases: string[];
  title?: string;
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
 * Combined Density Boxplot Chart
 *
 * Displays three side-by-side boxplots for Near, Far, and Ratio densities
 */
export default function CombinedDensityBoxplot({
  caseLevelDensities,
  positiveCases,
  negativeCases,
  title = "密度分佈對比 (Near / Far / Ratio)",
}: CombinedDensityBoxplotProps) {
  // Calculate boxplot data for all three metrics
  const allStats = useMemo(() => {
    // Helper function to extract densities by mode
    const extractDensities = (cases: string[], mode: "near" | "far" | "ratio") => {
      return cases
        .map((caseId) => {
          if (mode === "ratio") {
            // Calculate ratio from near/far
            const nearKey = `__near_${caseId}`;
            const farKey = `__far_${caseId}`;
            const near = caseLevelDensities[nearKey] ?? caseLevelDensities[caseId];
            const far = caseLevelDensities[farKey];

            if (near !== undefined && far !== undefined && far > 0.0001) {
              return near / far;
            }
            return undefined;
          } else {
            const key = mode === "far" ? `__far_${caseId}` : `__near_${caseId}`;
            return caseLevelDensities[key] ?? caseLevelDensities[caseId];
          }
        })
        .filter((v) => v !== undefined) as number[];
    };

    return {
      near: {
        positive: calculateBoxPlotStats(extractDensities(positiveCases, "near")),
        negative: calculateBoxPlotStats(extractDensities(negativeCases, "near")),
      },
      far: {
        positive: calculateBoxPlotStats(extractDensities(positiveCases, "far")),
        negative: calculateBoxPlotStats(extractDensities(negativeCases, "far")),
      },
      ratio: {
        positive: calculateBoxPlotStats(extractDensities(positiveCases, "ratio")),
        negative: calculateBoxPlotStats(extractDensities(negativeCases, "ratio")),
      },
    };
  }, [caseLevelDensities, positiveCases, negativeCases]);

  // Calculate independent Y-axis ranges for each metric
  const yRanges = useMemo(() => {
    const calculateRange = (positiveStats: BoxPlotStats, negativeStats: BoxPlotStats) => {
      // Include outliers in the range calculation
      const allValues = [
        positiveStats.min,
        positiveStats.max,
        negativeStats.min,
        negativeStats.max,
        ...positiveStats.outliers,
        ...negativeStats.outliers,
      ];

      const min = Math.min(...allValues);
      const max = Math.max(...allValues);
      const padding = (max - min) * 0.15; // Slightly more padding for outliers

      return {
        min: Math.max(0, min - padding),
        max: max + padding,
      };
    };

    return {
      near: calculateRange(allStats.near.positive, allStats.near.negative),
      far: calculateRange(allStats.far.positive, allStats.far.negative),
      ratio: calculateRange(allStats.ratio.positive, allStats.ratio.negative),
    };
  }, [allStats]);

  // Chart dimensions
  const chartWidth = 1200;
  const chartHeight = 500;
  const margin = { top: 40, right: 40, bottom: 100, left: 60 };
  const plotWidth = chartWidth - margin.left - margin.right;
  const plotHeight = chartHeight - margin.top - margin.bottom;

  // Divide plot into 3 sections (Near, Far, Ratio)
  const sectionWidth = plotWidth / 3;
  const boxWidth = 50;

  // Positions for each metric section with their Y-axis ranges
  const sections = [
    { name: "Near Density", x: 0, stats: allStats.near, range: yRanges.near },
    { name: "Far Density", x: sectionWidth, stats: allStats.far, range: yRanges.far },
    { name: "Ratio (Near/Far)", x: sectionWidth * 2, stats: allStats.ratio, range: yRanges.ratio },
  ];

  // Create scale function for a specific Y-axis range
  const createScaleY = (yMin: number, yMax: number) => {
    return (value: number) => {
      return plotHeight - ((value - yMin) / (yMax - yMin)) * plotHeight;
    };
  };

  // Render a single boxplot with its own scale function
  const renderBoxplot = (
    stats: BoxPlotStats,
    x: number,
    color: string,
    label: string,
    scaleY: (value: number) => number
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
          y={plotHeight + 25}
          textAnchor="middle"
          fontSize={12}
          fill="#64748b"
          fontWeight="500"
        >
          {label}
        </text>
      </g>
    );
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
        <p className="text-sm text-slate-500">
          橫向對比三種密度指標的分佈情況 (各有獨立Y軸): Near (近期密度), Far (遠期密度), Ratio (近遠比)
        </p>
      </div>

      {/* SVG Combined Boxplot */}
      <div className="flex justify-center">
        <svg
          width={chartWidth}
          height={chartHeight}
          className="overflow-visible"
          style={{ fontFamily: "sans-serif" }}
        >
          <g transform={`translate(${margin.left},${margin.top})`}>
            {/* X-axis */}
            <line
              x1={0}
              y1={plotHeight}
              x2={plotWidth}
              y2={plotHeight}
              stroke="#9ca3af"
              strokeWidth={2}
            />

            {/* Render each section with independent Y-axis */}
            {sections.map((section, idx) => {
              const positiveX = section.x + sectionWidth * 0.35;
              const negativeX = section.x + sectionWidth * 0.65;
              const scaleY = createScaleY(section.range.min, section.range.max);

              // Generate Y-axis ticks for this section
              const tickCount = 6;
              const yTicks = [];
              for (let i = 0; i <= tickCount; i++) {
                const value = section.range.min + ((section.range.max - section.range.min) / tickCount) * i;
                yTicks.push(value);
              }

              return (
                <g key={section.name}>
                  {/* Clipping region for this section */}
                  <clipPath id={`clip-${idx}`}>
                    <rect x={section.x} y={0} width={sectionWidth} height={plotHeight} />
                  </clipPath>

                  {/* Grid lines for this section */}
                  <g clipPath={`url(#clip-${idx})`}>
                    {yTicks.map((tick, i) => (
                      <line
                        key={i}
                        x1={section.x}
                        y1={scaleY(tick)}
                        x2={section.x + sectionWidth}
                        y2={scaleY(tick)}
                        stroke="#e5e7eb"
                        strokeDasharray="3 3"
                      />
                    ))}
                  </g>

                  {/* Y-axis for this section */}
                  <line
                    x1={section.x}
                    y1={0}
                    x2={section.x}
                    y2={plotHeight}
                    stroke="#9ca3af"
                    strokeWidth={2}
                  />

                  {/* Y-axis ticks and labels for this section */}
                  {yTicks.map((tick, i) => (
                    <g key={i}>
                      <line
                        x1={section.x - 5}
                        y1={scaleY(tick)}
                        x2={section.x}
                        y2={scaleY(tick)}
                        stroke="#9ca3af"
                        strokeWidth={1.5}
                      />
                      <text
                        x={section.x - 8}
                        y={scaleY(tick)}
                        textAnchor="end"
                        dominantBaseline="middle"
                        fontSize={10}
                        fill="#64748b"
                      >
                        {tick.toFixed(2)}
                      </text>
                    </g>
                  ))}

                  {/* Section divider (except after last section) */}
                  {idx < sections.length - 1 && (
                    <line
                      x1={section.x + sectionWidth}
                      y1={0}
                      x2={section.x + sectionWidth}
                      y2={plotHeight}
                      stroke="#d1d5db"
                      strokeWidth={1}
                      strokeDasharray="5 5"
                    />
                  )}

                  {/* Section title */}
                  <text
                    x={section.x + sectionWidth / 2}
                    y={plotHeight + 50}
                    textAnchor="middle"
                    fontSize={14}
                    fill="#1e293b"
                    fontWeight="600"
                  >
                    {section.name}
                  </text>

                  {/* Boxplots */}
                  {renderBoxplot(section.stats.positive, positiveX, "#10b981", "正例", scaleY)}
                  {renderBoxplot(section.stats.negative, negativeX, "#ef4444", "反例", scaleY)}
                </g>
              );
            })}
          </g>

          {/* Legend */}
          <g transform={`translate(${margin.left + 20}, 10)`}>
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

      {/* Statistics Summary - Three Columns */}
      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {/* Near Density Stats */}
        <div className="space-y-3">
          <h4 className="text-center font-semibold text-slate-700 border-b pb-2">
            近期密度 (Near)
          </h4>
          <div className="rounded-lg border border-green-200 bg-green-50 p-3">
            <h5 className="mb-1 text-sm font-semibold text-green-900">正例</h5>
            <div className="space-y-0.5 text-xs text-green-700">
              <p>中位數: {allStats.near.positive.median.toFixed(4)}</p>
              <p>
                平均值: {allStats.near.positive.mean.toFixed(4)} (±
                {allStats.near.positive.std.toFixed(4)})
              </p>
              <p>
                範圍: [{allStats.near.positive.min.toFixed(4)},{" "}
                {allStats.near.positive.max.toFixed(4)}]
              </p>
            </div>
          </div>
          <div className="rounded-lg border border-red-200 bg-red-50 p-3">
            <h5 className="mb-1 text-sm font-semibold text-red-900">反例</h5>
            <div className="space-y-0.5 text-xs text-red-700">
              <p>中位數: {allStats.near.negative.median.toFixed(4)}</p>
              <p>
                平均值: {allStats.near.negative.mean.toFixed(4)} (±
                {allStats.near.negative.std.toFixed(4)})
              </p>
              <p>
                範圍: [{allStats.near.negative.min.toFixed(4)},{" "}
                {allStats.near.negative.max.toFixed(4)}]
              </p>
            </div>
          </div>
        </div>

        {/* Far Density Stats */}
        <div className="space-y-3">
          <h4 className="text-center font-semibold text-slate-700 border-b pb-2">
            遠期密度 (Far)
          </h4>
          <div className="rounded-lg border border-green-200 bg-green-50 p-3">
            <h5 className="mb-1 text-sm font-semibold text-green-900">正例</h5>
            <div className="space-y-0.5 text-xs text-green-700">
              <p>中位數: {allStats.far.positive.median.toFixed(4)}</p>
              <p>
                平均值: {allStats.far.positive.mean.toFixed(4)} (±
                {allStats.far.positive.std.toFixed(4)})
              </p>
              <p>
                範圍: [{allStats.far.positive.min.toFixed(4)},{" "}
                {allStats.far.positive.max.toFixed(4)}]
              </p>
            </div>
          </div>
          <div className="rounded-lg border border-red-200 bg-red-50 p-3">
            <h5 className="mb-1 text-sm font-semibold text-red-900">反例</h5>
            <div className="space-y-0.5 text-xs text-red-700">
              <p>中位數: {allStats.far.negative.median.toFixed(4)}</p>
              <p>
                平均值: {allStats.far.negative.mean.toFixed(4)} (±
                {allStats.far.negative.std.toFixed(4)})
              </p>
              <p>
                範圍: [{allStats.far.negative.min.toFixed(4)},{" "}
                {allStats.far.negative.max.toFixed(4)}]
              </p>
            </div>
          </div>
        </div>

        {/* Ratio Stats */}
        <div className="space-y-3">
          <h4 className="text-center font-semibold text-slate-700 border-b pb-2">
            近遠比 (Ratio)
          </h4>
          <div className="rounded-lg border border-green-200 bg-green-50 p-3">
            <h5 className="mb-1 text-sm font-semibold text-green-900">正例</h5>
            <div className="space-y-0.5 text-xs text-green-700">
              <p>中位數: {allStats.ratio.positive.median.toFixed(4)}</p>
              <p>
                平均值: {allStats.ratio.positive.mean.toFixed(4)} (±
                {allStats.ratio.positive.std.toFixed(4)})
              </p>
              <p>
                範圍: [{allStats.ratio.positive.min.toFixed(4)},{" "}
                {allStats.ratio.positive.max.toFixed(4)}]
              </p>
            </div>
          </div>
          <div className="rounded-lg border border-red-200 bg-red-50 p-3">
            <h5 className="mb-1 text-sm font-semibold text-red-900">反例</h5>
            <div className="space-y-0.5 text-xs text-red-700">
              <p>中位數: {allStats.ratio.negative.median.toFixed(4)}</p>
              <p>
                平均值: {allStats.ratio.negative.mean.toFixed(4)} (±
                {allStats.ratio.negative.std.toFixed(4)})
              </p>
              <p>
                範圍: [{allStats.ratio.negative.min.toFixed(4)},{" "}
                {allStats.ratio.negative.max.toFixed(4)}]
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

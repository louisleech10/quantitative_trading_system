'use client';

import { useMemo, useRef } from 'react';
import html2canvas from 'html2canvas';
import type { CPCVResult } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface CPCVPathChartProps {
  data: CPCVResult;
  onExportPNG?: () => void;
}

interface BoxStats {
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  mean: number;
  std: number;
}

function computeBoxStats(values: number[]): BoxStats {
  const sorted = [...values].sort((left, right) => left - right);
  const size = sorted.length;

  const at = (ratio: number) => sorted[Math.min(size - 1, Math.floor((size - 1) * ratio))] ?? 0;
  const mean = sorted.reduce((sum, value) => sum + value, 0) / size;
  const std = Math.sqrt(sorted.reduce((sum, value) => sum + (value - mean) ** 2, 0) / size);

  return {
    min: sorted[0],
    q1: at(0.25),
    median: at(0.5),
    q3: at(0.75),
    max: sorted[size - 1],
    mean,
    std,
  };
}

export default function CPCVPathChart({ data, onExportPNG }: CPCVPathChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  const validAucs = useMemo(() => data.path_aucs.filter((value) => Number.isFinite(value)), [data.path_aucs]);
  const stats = useMemo(() => {
    if (validAucs.length === 0) {
      return null;
    }
    return computeBoxStats(validAucs);
  }, [validAucs]);

  const handleExportPNG = async () => {
    if (onExportPNG) {
      onExportPNG();
      return;
    }

    if (!containerRef.current || validAucs.length === 0) {
      return;
    }

    try {
      const canvas = await html2canvas(containerRef.current);
      const link = document.createElement('a');
      link.download = `cpcv_path_chart_${Date.now()}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (error) {
      console.error('CPCVPathChart PNG 匯出失敗', error);
    }
  };

  const renderBoxPlot = () => {
    if (!stats) {
      return null;
    }

    const width = 480;
    const height = 220;
    const left = 80;
    const right = 430;
    const top = 25;
    const bottom = 185;

    const yMin = Math.max(0, stats.min - 0.03);
    const yMax = Math.min(1, stats.max + 0.03);
    const scaleY = (value: number) => {
      if (yMax === yMin) {
        return (top + bottom) / 2;
      }
      return bottom - ((value - yMin) / (yMax - yMin)) * (bottom - top);
    };

    const centerX = (left + right) / 2;
    const boxWidth = 120;

    return (
      <svg width={width} height={height} className="mx-auto">
        <line x1={left} y1={bottom} x2={right} y2={bottom} stroke="#64748b" strokeWidth="1" />
        <line x1={left} y1={top} x2={left} y2={bottom} stroke="#64748b" strokeWidth="1" />

        <line x1={centerX} y1={scaleY(stats.max)} x2={centerX} y2={scaleY(stats.q3)} stroke="#cbd5e1" strokeWidth="2" />
        <line x1={centerX} y1={scaleY(stats.q1)} x2={centerX} y2={scaleY(stats.min)} stroke="#cbd5e1" strokeWidth="2" />

        <rect
          x={centerX - boxWidth / 2}
          y={scaleY(stats.q3)}
          width={boxWidth}
          height={Math.max(2, scaleY(stats.q1) - scaleY(stats.q3))}
          fill="#38bdf833"
          stroke="#38bdf8"
          strokeWidth="2"
          rx="6"
        />

        <line
          x1={centerX - boxWidth / 2}
          y1={scaleY(stats.median)}
          x2={centerX + boxWidth / 2}
          y2={scaleY(stats.median)}
          stroke="#f8fafc"
          strokeWidth="2"
        />

        <circle cx={centerX} cy={scaleY(stats.mean)} r="4" fill="#f59e0b" />

        {validAucs.map((auc, index) => {
          const jitter = ((index % 7) - 3) * 8;
          return <circle key={`${auc}-${index}`} cx={centerX + jitter} cy={scaleY(auc)} r="2" fill="#22c55e99" />;
        })}
      </svg>
    );
  };

  return (
    <div ref={containerRef}>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base">C26 CPCV Path Chart</CardTitle>
            <CardDescription>Path AUC 分佈（Box Plot）</CardDescription>
          </div>
          <button
            type="button"
            onClick={handleExportPNG}
            disabled={validAucs.length === 0}
            className="text-xs text-cyan-300 disabled:text-slate-500 disabled:cursor-not-allowed"
          >
            PNG
          </button>
        </CardHeader>
        <CardContent>
          {validAucs.length === 0 || !stats ? (
            <div className="h-[240px] flex items-center justify-center text-slate-400">暫無 path AUC 分佈資料</div>
          ) : (
            <>
              {renderBoxPlot()}
              <div className="mt-4 grid grid-cols-2 gap-3 text-xs text-slate-300">
                <div>Mean: {stats.mean.toFixed(4)}</div>
                <div>Std: {stats.std.toFixed(4)}</div>
                <div>Min: {stats.min.toFixed(4)}</div>
                <div>Max: {stats.max.toFixed(4)}</div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

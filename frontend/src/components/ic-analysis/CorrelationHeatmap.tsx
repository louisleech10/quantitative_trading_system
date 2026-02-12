'use client';

import { useMemo } from 'react';
import { CorrelationMatrix } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface CorrelationHeatmapProps {
  matrix?: CorrelationMatrix | null;
  maxFeatures?: number;
}

const getCellColor = (value: number) => {
  const intensity = Math.min(Math.abs(value), 1);
  const alpha = 0.15 + intensity * 0.75;
  if (value >= 0) {
    return `rgba(52, 211, 153, ${alpha})`;
  }
  return `rgba(251, 113, 133, ${alpha})`;
};

export default function CorrelationHeatmap({ matrix, maxFeatures = 18 }: CorrelationHeatmapProps) {
  const safeMatrix = matrix?.matrix ?? [];
  const features = matrix?.features ?? [];

  const trimmed = useMemo(() => {
    const size = Math.min(features.length, maxFeatures);
    const trimmedFeatures = features.slice(0, size);
    const trimmedMatrix = safeMatrix.slice(0, size).map((row) => row.slice(0, size));
    return { trimmedFeatures, trimmedMatrix };
  }, [features, maxFeatures, safeMatrix]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">相關性熱力圖</CardTitle>
        <CardDescription>顯示 Top 特徵相關性矩陣</CardDescription>
      </CardHeader>
      <CardContent>
        {trimmed.trimmedFeatures.length === 0 ? (
          <div className="flex items-center justify-center h-[240px] text-slate-400">
            暫無相關性矩陣
          </div>
        ) : (
          <div className="space-y-3">
            <div
              className="grid gap-1"
              style={{
                gridTemplateColumns: `120px repeat(${trimmed.trimmedFeatures.length}, minmax(32px, 1fr))`,
              }}
            >
              <div></div>
              {trimmed.trimmedFeatures.map((feature) => (
                <div key={`col-${feature}`} className="text-[10px] text-slate-400 truncate">
                  {feature}
                </div>
              ))}
              {trimmed.trimmedFeatures.map((feature, rowIndex) => (
                <div key={`row-${feature}`} className="contents">
                  <div className="text-[10px] text-slate-400 truncate pr-2">{feature}</div>
                  {trimmed.trimmedMatrix[rowIndex]?.map((value, colIndex) => (
                    <div
                      key={`cell-${rowIndex}-${colIndex}`}
                      title={`${feature} vs ${trimmed.trimmedFeatures[colIndex]}: ${value.toFixed(3)}`}
                      className="h-6 rounded-sm"
                      style={{ backgroundColor: getCellColor(value) }}
                    />
                  ))}
                </div>
              ))}
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>負相關</span>
              <span>正相關</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

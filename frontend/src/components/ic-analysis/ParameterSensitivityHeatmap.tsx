'use client';

import { useMemo, useRef } from 'react';
import html2canvas from 'html2canvas';
import { ParameterSensitivityData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface ParameterSensitivityHeatmapProps {
  data?: ParameterSensitivityData;
}

function getColor(value: number) {
  if (value > 0.05) return 'bg-emerald-500/50';
  if (value < -0.05) return 'bg-rose-500/50';
  return 'bg-slate-500/40';
}

export default function ParameterSensitivityHeatmap({ data }: ParameterSensitivityHeatmapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const families = useMemo(() => Object.entries(data?.families || {}), [data?.families]);

  const handleExportPNG = async () => {
    if (!containerRef.current) return;
    const canvas = await html2canvas(containerRef.current);
    const link = document.createElement('a');
    link.download = `parameter_sensitivity_${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  return (
    <Card ref={containerRef}>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-base">C17 Parameter Sensitivity</CardTitle>
          <CardDescription>熱力圖與穩健性等級</CardDescription>
        </div>
        <button type="button" onClick={handleExportPNG} className="text-xs text-cyan-300">PNG</button>
      </CardHeader>
      <CardContent>
        {families.length === 0 ? (
          <div className="h-[240px] flex items-center justify-center text-slate-400">暫無參數敏感性資料</div>
        ) : (
          <div className="space-y-3">
            {families.map(([family, payload]) => (
              <div key={family} className="rounded-md border border-white/10 p-3 bg-white/5">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-slate-200">{family}</span>
                  <span className="text-xs text-slate-300">{payload.stability_metrics?.overfitting_risk || 'unknown'}</span>
                </div>
                <div className="grid grid-cols-6 gap-1">
                  {(payload.sensitivity_table || []).slice(0, 12).map((item) => (
                    <div key={item.variant} className={`h-6 rounded ${getColor(item.ic_mean)} text-[10px] text-center text-white leading-6`}>
                      {item.param_value}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

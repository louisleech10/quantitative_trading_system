'use client';

import { useMemo } from 'react';
import { GroupedICData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Tooltip } from 'recharts';

interface RegimeRadarChartProps {
  groupedIC?: GroupedICData | null;
  featureName?: string | null;
}

export default function RegimeRadarChart({ groupedIC, featureName }: RegimeRadarChartProps) {
  const chartData = useMemo(() => {
    const regimeData = groupedIC?.by_regime || {};
    return Object.entries(regimeData).map(([regime, value]) => {
      if (typeof value === 'number') {
        // NaN/非有限 → null（禁 ?? 0 假零）
        return { regime, value: Number.isFinite(value) ? value : null };
      }
      if (value && typeof value === 'object' && featureName) {
        const raw = (value as Record<string, number | null | undefined>)[featureName];
        if (raw === undefined || raw === null) {
          return { regime, value: null };
        }
        const num = typeof raw === 'number' ? raw : Number(raw);
        return { regime, value: Number.isFinite(num) ? num : null };
      }
      return { regime, value: null };
    });
  }, [groupedIC, featureName]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Regime 雷達圖</CardTitle>
        <CardDescription>
          {featureName ? `特徵：${featureName}` : '尚未選擇特徵'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* B3-FE-01：暴露生產 chartData 供 DOM 斷言（禁測試內複製 mapping） */}
        <div
          data-testid="regime-radar-chart-payload"
          data-chart={JSON.stringify(chartData)}
          hidden
          aria-hidden
        />
        {chartData.length === 0 ? (
          <div className="flex items-center justify-center h-[240px] text-slate-400">
            暫無 Regime 數據
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <RadarChart data={chartData}>
              <PolarGrid stroke="rgba(255,255,255,0.1)" />
              <PolarAngleAxis dataKey="regime" tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  background: '#1a233a',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                }}
              />
              <Radar dataKey="value" stroke="#22d3ee" fill="#22d3ee" fillOpacity={0.35} />
            </RadarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

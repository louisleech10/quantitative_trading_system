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
        return { regime, value };
      }
      if (value && typeof value === 'object' && featureName) {
        return { regime, value: (value as Record<string, number>)[featureName] ?? 0 };
      }
      return { regime, value: 0 };
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

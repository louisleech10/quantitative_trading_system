'use client';

import { useMemo } from 'react';
import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer } from 'recharts';
import { FactorExposureData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface FactorExposureRadarProps {
  data?: FactorExposureData;
}

export default function FactorExposureRadar({ data }: FactorExposureRadarProps) {
  const activeExposure = data?.neutralized_portfolio_exposure || data?.portfolio_exposure || data?.factor_attribution?.factor_betas;

  const chartData = useMemo(() => {
    return Object.entries(activeExposure || {}).map(([factor, value]) => ({
      factor,
      exposure: Math.abs(value),
    }));
  }, [activeExposure]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">C20 Factor Exposure Radar</CardTitle>
        <CardDescription>
          因子曝險雷達圖
          {data?.neutralization_mode && data.neutralization_mode !== 'none'
            ? `（${data.neutralization_mode}）`
            : ''}
          {typeof data?.neutralization_delta_hhi === 'number'
            ? `，ΔHHI=${data.neutralization_delta_hhi.toFixed(4)}`
            : ''}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="h-[240px] flex items-center justify-center text-slate-400">暫無曝險資料</div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <RadarChart data={chartData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="factor" />
              <Radar dataKey="exposure" stroke="#60a5fa" fill="#60a5fa55" />
            </RadarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

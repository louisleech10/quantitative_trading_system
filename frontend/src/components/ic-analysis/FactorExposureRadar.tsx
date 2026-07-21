'use client';

import { useMemo } from 'react';
import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer } from 'recharts';
import { FactorExposureData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface FactorExposureRadarProps {
  data?: FactorExposureData;
}

export default function FactorExposureRadar({ data }: FactorExposureRadarProps) {
  // B5：exposure 僅 portfolio_exposure / neutralized，不讀幽靈 factor_attribution.factor_betas。
  // factor_attribution 三態：unavailable | ok | legacy；無 exposure 時空態。
  const activeExposure =
    data?.neutralized_portfolio_exposure || data?.portfolio_exposure;

  const chartData = useMemo(() => {
    return Object.entries(activeExposure || {}).map(([factor, value]) => ({
      factor,
      exposure: Math.abs(value),
    }));
  }, [activeExposure]);

  const fa = data?.factor_attribution;
  const isAttributionUnavailable =
    fa !== undefined && fa !== null && 'status' in fa && fa.status === 'unavailable';
  // unavailable 專屬文案（測試以 /因子歸因不可用/ 唯一斷言；通用空態不得含此字串）
  const emptyNotice = isAttributionUnavailable
    ? '因子歸因不可用，暫無曝險資料'
    : '暫無曝險資料';

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
          <div
            className="h-[240px] flex items-center justify-center text-slate-400"
            data-testid="factor-exposure-radar-empty"
          >
            {emptyNotice}
          </div>
        ) : (
          <div
            data-testid="factor-exposure-radar-chart"
            data-exposure-source="portfolio_or_neutralized"
            data-active-factors={chartData.map((d) => d.factor).join('|')}
          >
            <ResponsiveContainer width="100%" height={240}>
              <RadarChart data={chartData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="factor" />
                <Radar dataKey="exposure" stroke="#60a5fa" fill="#60a5fa55" />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

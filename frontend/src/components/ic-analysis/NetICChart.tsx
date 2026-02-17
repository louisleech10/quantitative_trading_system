'use client';

import { useMemo, useState } from 'react';
import { Scatter, ScatterChart, ResponsiveContainer, Tooltip, XAxis, YAxis, ZAxis, ReferenceLine } from 'recharts';
import { NetICAnalysisData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface NetICChartProps {
  data?: NetICAnalysisData;
}

export default function NetICChart({ data }: NetICChartProps) {
  const [costBps, setCostBps] = useState<number>(5);

  const chartData = useMemo(() => {
    const features = data?.features || {};
    return Object.entries(features)
      .filter(([, value]) => !value.skipped)
      .map(([feature, value]) => {
        const scenario = (value.cost_sensitivity || []).find((item) => item.cost_bps === costBps);
        return {
          feature,
          gross_ic: value.gross_ic ?? 0,
          net_ic: scenario?.net_ic ?? value.net_ic ?? 0,
          turnover: value.turnover ?? 0.1,
          profitable: scenario ? scenario.net_ic > 0 : Boolean(value.profitable_after_cost),
        };
      });
  }, [costBps, data?.features]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">C22 Net IC Chart</CardTitle>
            <CardDescription>Gross vs Net IC（成本情境可切換）</CardDescription>
          </div>
          <select
            value={costBps}
            onChange={(event) => setCostBps(Number(event.target.value))}
            className="bg-white/5 border border-white/10 rounded px-2 py-1 text-xs text-slate-200"
          >
            {[1, 3, 5, 10, 20].map((item) => (
              <option key={item} value={item}>{item} bps</option>
            ))}
          </select>
        </div>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="h-[260px] flex items-center justify-center text-slate-400">暫無 Net IC 資料</div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <ScatterChart>
              <XAxis dataKey="gross_ic" name="Gross IC" type="number" />
              <YAxis dataKey="net_ic" name="Net IC" type="number" />
              <ZAxis dataKey="turnover" range={[40, 300]} />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} />
              <ReferenceLine segment={[{ x: -1, y: -1 }, { x: 1, y: 1 }]} stroke="#94a3b8" strokeDasharray="3 3" />
              <Scatter data={chartData} fill="#38bdf8" />
            </ScatterChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

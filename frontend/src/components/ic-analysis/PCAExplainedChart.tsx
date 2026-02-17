'use client';

import { useMemo } from 'react';
import { Bar, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { FactorCentralityData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface PCAExplainedChartProps {
  data?: FactorCentralityData;
}

export default function PCAExplainedChart({ data }: PCAExplainedChartProps) {
  const chartData = useMemo(() => {
    const explained = data?.pca_summary?.explained_variance_ratio || [];
    let cumulative = 0;
    return explained.map((ratio, index) => {
      cumulative += ratio;
      return {
        component: `PC${index + 1}`,
        explained: ratio,
        cumulative,
      };
    });
  }, [data?.pca_summary?.explained_variance_ratio]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">C15 PCA Explained Variance</CardTitle>
        <CardDescription>單一解釋比例 + 累積比例</CardDescription>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="h-[240px] flex items-center justify-center text-slate-400">暫無 PCA 資料</div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <ComposedChart data={chartData}>
              <XAxis dataKey="component" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="explained" fill="#60a5fa" />
              <Line type="monotone" dataKey="cumulative" stroke="#34d399" dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

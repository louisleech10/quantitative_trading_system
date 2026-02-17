'use client';

import { useMemo } from 'react';
import { TrendAnalysisData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface TrendDashboardProps {
  data?: TrendAnalysisData;
}

const getBadge = (value?: string) => {
  if (value === '危險') return 'bg-rose-500/20 text-rose-200';
  if (value === '警告') return 'bg-amber-500/20 text-amber-200';
  return 'bg-emerald-500/20 text-emerald-200';
};

export default function TrendDashboard({ data }: TrendDashboardProps) {
  const rows = useMemo(() => Object.entries(data || {}), [data]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">C16 Trend Dashboard</CardTitle>
        <CardDescription>多維趨勢與綜合訊號</CardDescription>
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <div className="h-[240px] flex items-center justify-center text-slate-400">暫無 Trend 資料</div>
        ) : (
          <div className="space-y-2">
            {rows.map(([feature, result]) => (
              <div key={feature} className="rounded-md border border-white/10 bg-white/5 p-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-slate-200">{feature}</span>
                  <span className={`px-2 py-0.5 rounded text-xs ${getBadge(result.combined_signal?.recommendation)}`}>
                    {result.combined_signal?.recommendation || '正常'}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1">{result.combined_signal?.reason || '無'} / {result.combined_signal?.action || '無'}</p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

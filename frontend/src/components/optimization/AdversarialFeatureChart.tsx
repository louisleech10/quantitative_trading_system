'use client';

import { useMemo, useState } from 'react';
import { Bar, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis, BarChart } from 'recharts';
import type { AdversarialResult } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface AdversarialFeatureChartProps {
  data: AdversarialResult;
}

type SortMode = 'ks' | 'name';
type FeatureStatus = 'stable' | 'warning' | 'severe';
interface FeatureRow {
  feature: string;
  ks: number;
  status: FeatureStatus;
  color: string;
  psi?: number;
}

export default function AdversarialFeatureChart({ data }: AdversarialFeatureChartProps) {
  const [sortMode, setSortMode] = useState<SortMode>('ks');

  const { chartData, skippedCount } = useMemo(() => {
    let missingCount = 0;

    const entries: FeatureRow[] = [];
    Object.entries(data.feature_level_tests).forEach(([feature, result]) => {
      const ks = result.ks_statistic;
      if (typeof ks !== 'number') {
        missingCount += 1;
        return;
      }

      const status = result.status;
      const color = status === 'severe' ? '#ef4444' : status === 'warning' ? '#eab308' : '#22c55e';
      entries.push({
        feature,
        ks,
        status,
        color,
        psi: result.psi,
      });
    });

    entries.sort((left, right) => {
      if (sortMode === 'name') {
        return left.feature.localeCompare(right.feature);
      }
      return right.ks - left.ks;
    });

    return {
      chartData: entries,
      skippedCount: missingCount,
    };
  }, [data.feature_level_tests, sortMode]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-base">C25 Adversarial Feature Chart</CardTitle>
          <CardDescription>Feature-level KS 分佈（含 status 顏色）</CardDescription>
        </div>
        <select
          className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200"
          value={sortMode}
          onChange={(event) => setSortMode(event.target.value as SortMode)}
        >
          <option value="ks">依 KS 排序</option>
          <option value="name">依名稱排序</option>
        </select>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="h-[260px] flex items-center justify-center text-slate-400">暫無可用特徵 KS 資料</div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData}>
              <XAxis dataKey="feature" hide />
              <YAxis domain={[0, 'auto']} />
              <Tooltip
                labelFormatter={(label, payload) => {
                  const row = payload?.[0]?.payload as { status?: string; psi?: number } | undefined;
                  const psiText = typeof row?.psi === 'number' ? row.psi.toFixed(4) : '--';
                  return `${String(label)} | status=${row?.status ?? '--'} | psi=${psiText}`;
                }}
              />
              <Bar dataKey="ks" name="KS Statistic">
                {chartData.map((row) => (
                  <Cell key={row.feature} fill={row.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}

        {skippedCount > 0 && (
          <div className="mt-3 text-xs text-amber-300">已略過 {skippedCount} 筆缺少 KS/PSI 欄位的特徵資料。</div>
        )}
      </CardContent>
    </Card>
  );
}

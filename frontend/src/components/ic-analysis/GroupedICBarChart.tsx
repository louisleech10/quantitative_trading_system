'use client';

import { useEffect, useMemo, useState } from 'react';
import { GroupedICData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface GroupedICBarChartProps {
  groupedIC?: GroupedICData | null;
  featureName?: string | null;
}

const groupLabels: Record<string, string> = {
  by_year: '年度分組',
  by_regime: 'Regime 分組',
  by_category: '類別分組',
  by_data_source: '資料源分組',
  by_layer: '層級分組',
};

export default function GroupedICBarChart({ groupedIC, featureName }: GroupedICBarChartProps) {
  const groupKeys = useMemo(() => Object.keys(groupedIC || {}), [groupedIC]);
  const [selectedGroup, setSelectedGroup] = useState<string>('');

  useEffect(() => {
    if (groupKeys.length > 0) {
      setSelectedGroup((prev) => (groupKeys.includes(prev) ? prev : groupKeys[0]));
    } else {
      setSelectedGroup('');
    }
  }, [groupKeys]);

  const chartData = useMemo(() => {
    if (!groupedIC || !selectedGroup) {
      return [];
    }

    const groupData = groupedIC[selectedGroup] || {};
    return Object.entries(groupData).map(([group, value]) => {
      if (typeof value === 'number') {
        return { group, ic: value };
      }
      if (value && typeof value === 'object' && featureName) {
        const featureValue = (value as Record<string, number>)[featureName] ?? 0;
        return { group, ic: featureValue };
      }
      return { group, ic: 0 };
    });
  }, [groupedIC, selectedGroup, featureName]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">分組 IC</CardTitle>
            <CardDescription>
              {featureName ? `特徵：${featureName}` : '尚未選擇特徵'}
            </CardDescription>
          </div>
          {groupKeys.length > 0 && (
            <Select value={selectedGroup} onValueChange={setSelectedGroup}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="選擇分組" />
              </SelectTrigger>
              <SelectContent>
                {groupKeys.map((key) => (
                  <SelectItem key={key} value={key}>
                    {groupLabels[key] || key}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="flex items-center justify-center h-[240px] text-slate-400">
            暫無分組結果
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-white/10" />
              <XAxis dataKey="group" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip
                contentStyle={{
                  background: '#1a233a',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                }}
              />
              <Bar dataKey="ic" fill="#a855f7" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

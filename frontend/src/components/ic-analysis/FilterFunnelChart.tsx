'use client';

import { useMemo } from 'react';
import { FilterLogFunnel } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface FilterFunnelChartProps {
  /**
   * ICRESULT_PAGING §C-6 (iv)：後端 `filter_log_funnel`（每 stage `{input, output}`，皆可 null）。
   * null ⇒ 該 stage 顯示「不適用」，**不補 0**（改前讀 `filter_log.*.input/output` 之鍵名錯配已由 adapter 修正）。
   */
  funnel?: FilterLogFunnel | null;
}

export default function FilterFunnelChart({ funnel }: FilterFunnelChartProps) {
  const { chartData, notApplicable } = useMemo(() => {
    if (!funnel) {
      return { chartData: [], notApplicable: [] as string[] };
    }
    const rows: Array<{ stage: string; input: number; output: number; removed: number }> = [];
    const na: string[] = [];
    for (const [stage, values] of Object.entries(funnel)) {
      if (stage.startsWith('_')) continue; // 合成 probe stage 不畫
      const input = values?.input;
      const output = values?.output;
      if (typeof output !== 'number') {
        na.push(stage);
        continue;
      }
      rows.push({
        stage,
        input: typeof input === 'number' ? input : output,
        output,
        removed: typeof input === 'number' ? Math.max(input - output, 0) : 0,
      });
    }
    return { chartData: rows, notApplicable: na };
  }, [funnel]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">篩選漏斗</CardTitle>
        <CardDescription>各階段特徵數變化</CardDescription>
        {notApplicable.length > 0 && (
          <div className="text-[11px] text-slate-500" data-testid="funnel-not-applicable">
            不適用（該階段無特徵計數）：{notApplicable.join('、')}
          </div>
        )}
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="flex items-center justify-center h-[240px] text-slate-400">
            暫無漏斗數據
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-white/10" />
              <XAxis dataKey="stage" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip
                contentStyle={{
                  background: '#1a233a',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                }}
              />
              <Bar dataKey="output" fill="#34d399" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

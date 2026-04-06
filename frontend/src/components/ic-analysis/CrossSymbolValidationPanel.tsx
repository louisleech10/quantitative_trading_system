'use client';

import { useMemo } from 'react';
import { CrossSymbolValidationSummary } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface CrossSymbolValidationPanelProps {
  data?: CrossSymbolValidationSummary | null;
}

const formatScore = (value: number | null | undefined, digits = 3): string => {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '--';
  }
  return value.toFixed(digits);
};

export default function CrossSymbolValidationPanel({ data }: CrossSymbolValidationPanelProps) {
  const symbolRanking = useMemo(() => {
    const entries = Object.entries(data?.symbol_scores || {});
    entries.sort((a, b) => b[1] - a[1]);
    return entries;
  }, [data?.symbol_scores]);

  if (!data) {
    return null;
  }

  if (data.status === 'skipped') {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">CrossSymbolValidator</CardTitle>
          <CardDescription>跨 Symbol 泛化驗證</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Badge variant="outline" className="border-amber-400/40 text-amber-200">Skipped</Badge>
          <p className="text-sm text-slate-300">{data.reason || '未提供可驗證資料'}</p>
        </CardContent>
      </Card>
    );
  }

  const consistency = data.consistency_score ?? null;
  const consistencyClass =
    typeof consistency !== 'number' || !Number.isFinite(consistency)
      ? 'text-slate-200'
      : consistency >= 0.7
        ? 'text-emerald-300'
        : consistency >= 0.4
          ? 'text-amber-300'
          : 'text-rose-300';

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">CrossSymbolValidator</CardTitle>
        <CardDescription>跨 Symbol 一致性與泛化摘要</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="rounded-md border border-white/10 bg-white/5 p-3">
            <p className="text-xs text-slate-400">一致性分數</p>
            <p className={`text-lg font-semibold ${consistencyClass}`}>{formatScore(consistency)}</p>
          </div>
          <div className="rounded-md border border-white/10 bg-white/5 p-3">
            <p className="text-xs text-slate-400">最佳 Symbol</p>
            <p className="text-sm font-medium text-slate-100">{data.best_symbol || '--'}</p>
          </div>
          <div className="rounded-md border border-white/10 bg-white/5 p-3">
            <p className="text-xs text-slate-400">最弱 Symbol</p>
            <p className="text-sm font-medium text-slate-100">{data.worst_symbol || '--'}</p>
          </div>
        </div>

        {symbolRanking.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-slate-400">Symbol 強度排序（平均 |IC|）</p>
            <div className="space-y-1">
              {symbolRanking.slice(0, 8).map(([symbol, score]) => (
                <div key={symbol} className="flex items-center justify-between rounded bg-white/5 px-3 py-1.5 text-xs">
                  <span className="text-slate-300">{symbol}</span>
                  <span className="font-mono text-slate-200">{score.toFixed(4)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-2">
          <p className="text-xs text-slate-400">建議</p>
          {(data.suggestions && data.suggestions.length > 0) ? (
            <div className="space-y-1">
              {data.suggestions.map((item, index) => (
                <p key={`${item}-${index}`} className="text-sm text-slate-300">- {item}</p>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-400">暫無建議</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

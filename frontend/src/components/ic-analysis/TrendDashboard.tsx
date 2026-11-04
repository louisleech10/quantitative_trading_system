'use client';

import { useMemo } from 'react';
import { TrendAnalysisData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  HAC_PERSISTENCE_NOT_ESTIMABLE_TIP,
  HAC_WARNING_NOT_EVALUATED_TIP,
  TREND_DIM_LABELS,
  TREND_STATUS_LABELS,
  trendDataWarningTip,
} from '@/components/ic-analysis/icSettingsText';

interface TrendDashboardProps {
  data?: TrendAnalysisData;
}

// ICPERF ㊺ B(6)：「資訊不足」與未知值用中性色（不得以綠色暗示正常）；只有明確「正常」才用綠色
const getBadge = (value?: string) => {
  if (value === '危險') return 'bg-rose-500/20 text-rose-200';
  if (value === '警告') return 'bg-amber-500/20 text-amber-200';
  if (value === '正常') return 'bg-emerald-500/20 text-emerald-200';
  return 'bg-slate-500/20 text-slate-200';
};

type TrendRow = NonNullable<TrendAnalysisData>[string];
const DIM_KEYS = ['ic_trend', 'centrality_trend', 'factor_return_trend', 'ls_spread_trend'] as const;

/**
 * ICPERF ㊺ B：各維之檢定法揭露——非 ok 狀態列短原因；資料不足警示以 ⚠ 標示（ⓘ 為警示內容）；
 * 持續性不可估／判定未執行以 ? 標示。分類照常顯示（警示不封鎖）。
 */
interface DimNote {
  key: (typeof DIM_KEYS)[number];
  text: string;
  tip: string | undefined;
  warn: boolean;
}

function TrendDimensionNotes({ result }: { result: TrendRow }) {
  const notes = DIM_KEYS.flatMap((key): DimNote[] => {
    const dim = result[key];
    if (!dim) return [];
    const label = TREND_DIM_LABELS[key];
    const status = dim.inference_status;
    if (status && status !== 'ok') {
      return [{ key, text: `${label}：${TREND_STATUS_LABELS[status] ?? status}`, tip: undefined, warn: false }];
    }
    if (dim.data_warning === 'small_effective_sample' && dim.data_warning_detail) {
      return [{ key, text: `${label}：⚠ 資料不足`, tip: trendDataWarningTip(dim.data_warning_detail), warn: true }];
    }
    if (dim.data_warning === 'persistence_not_estimable') {
      return [{ key, text: `${label}：?`, tip: HAC_PERSISTENCE_NOT_ESTIMABLE_TIP, warn: false }];
    }
    if (dim.data_warning === 'warning_not_evaluated') {
      return [{ key, text: `${label}：?`, tip: HAC_WARNING_NOT_EVALUATED_TIP, warn: false }];
    }
    return [];
  });
  if (notes.length === 0) return null;
  return (
    <p className="text-xs mt-1 flex flex-wrap gap-x-3" data-testid="trend-dimension-notes">
      {notes.map((n) => (
        <span
          key={n.key}
          data-testid={`trend-note-${n.key}`}
          title={n.tip}
          aria-label={n.tip}
          className={n.warn ? 'text-amber-300' : 'text-slate-400'}
        >
          {n.text}
        </span>
      ))}
    </p>
  );
}

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
                    {result.combined_signal?.recommendation || '資訊不足'}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1">{result.combined_signal?.reason || '無'} / {result.combined_signal?.action || '無'}</p>
                <TrendDimensionNotes result={result} />
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

'use client';

import { useMemo, useState } from 'react';
import { FeatureQualityDiagnosticsData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface FeatureQualityDashboardProps {
  data?: FeatureQualityDiagnosticsData;
}

export default function FeatureQualityDashboard({ data }: FeatureQualityDashboardProps) {
  const [expanded, setExpanded] = useState(false);

  const summary = data?.summary;
  const lowCoverageCount = useMemo(() => data?.quality_flags?.low_coverage?.length || 0, [data?.quality_flags?.low_coverage]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">C21 Feature Quality Dashboard</CardTitle>
        <CardDescription>品質摘要與低品質因子</CardDescription>
      </CardHeader>
      <CardContent>
        {!data ? (
          <div className="h-[240px] flex items-center justify-center text-slate-400">暫無品質診斷資料</div>
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
              <div className="rounded-md border border-white/10 bg-white/5 p-3 text-slate-200">定態率：{((summary?.stationary_rate || 0) * 100).toFixed(1)}%</div>
              <div className="rounded-md border border-white/10 bg-white/5 p-3 text-slate-200">平均覆蓋率：{((summary?.mean_coverage || 0) * 100).toFixed(1)}%</div>
              <div className="rounded-md border border-white/10 bg-white/5 p-3 text-slate-200">低品質數：{summary?.low_quality_count ?? 0}</div>
            </div>
            <div className="text-xs text-slate-400">低覆蓋警示：{lowCoverageCount}</div>
            <button
              type="button"
              onClick={() => setExpanded((prev) => !prev)}
              className="text-xs text-cyan-300"
            >
              {expanded ? '收合詳細' : '展開詳細'}
            </button>
            {expanded && (
              <div className="rounded-md border border-white/10 bg-white/5 p-3 text-xs text-slate-300 space-y-1">
                <div>non_stationary: {(data.quality_flags?.non_stationary || []).join(', ') || '無'}</div>
                <div>high_autocorrelation: {(data.quality_flags?.high_autocorrelation || []).join(', ') || '無'}</div>
                <div>drifted: {(data.quality_flags?.drifted || []).join(', ') || '無'}</div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

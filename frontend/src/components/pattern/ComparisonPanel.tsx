'use client';

import React, { useMemo, useRef } from 'react';
import type { ComparisonReportResponse } from '@/lib/patternTypes';
import EmptyState from '@/components/pattern/details/shared/EmptyState';
import ChartExportButton from '@/components/pattern/details/shared/ChartExportButton';
import RecommendationBanner from '@/components/pattern/comparison/RecommendationBanner';
import ComparisonMetricsTable from '@/components/pattern/comparison/ComparisonMetricsTable';
import ConsensusCard from '@/components/pattern/comparison/ConsensusCard';
import ComparisonFeatureChart from '@/components/pattern/comparison/ComparisonFeatureChart';

interface ComparisonPanelProps {
  report: ComparisonReportResponse | null;
  loading?: boolean;
}

export default function ComparisonPanel({ report, loading = false }: ComparisonPanelProps) {
  const exportRef = useRef<HTMLDivElement>(null);

  const csvContent = useMemo(() => {
    if (!report) return '';
    const rows = [
      ['recommended_engine', report.recommended_engine],
      ['recommendation_reason', report.recommendation_reason],
      ['consensus_rate', String(report.consensus_rate)],
      ['feature_rank_correlation', String(report.feature_rank_correlation)]
    ];
    return rows.map((r) => `${r[0]},"${String(r[1]).replace(/"/g, '""')}"`).join('\n');
  }, [report]);

  const exportCSV = () => {
    if (!csvContent) return;
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `comparison_report_${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return <div className="text-slate-400">載入對比報告中...</div>;
  }

  if (!report) {
    return <EmptyState message="尚未執行雙引擎對比" />;
  }

  return (
    <div className="space-y-4" ref={exportRef}>
      <RecommendationBanner recommendedEngine={report.recommended_engine} reason={report.recommendation_reason} />
      <ComparisonMetricsTable report={report} />
      <ConsensusCard consensusRate={report.consensus_rate} spearman={report.feature_rank_correlation} />
      <div className="rounded-lg border border-slate-700 bg-slate-900/40 p-4">
        <div className="text-slate-200 mb-2">Top 指標對比</div>
        <ComparisonFeatureChart report={report} />
      </div>
      <div className="flex gap-2">
        <ChartExportButton targetRef={exportRef} filename="engine_comparison" className="px-3 py-2 bg-emerald-500/20 border border-emerald-400/40 rounded text-emerald-100 hover:bg-emerald-500/30" />
        <button onClick={exportCSV} className="px-3 py-2 bg-slate-900/60 border border-slate-700 rounded text-slate-200 hover:bg-slate-900">匯出 CSV</button>
      </div>
    </div>
  );
}

'use client';

import { FeatureBrowserCatalogSummary } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';


interface DashboardOverviewProps {
  summary: FeatureBrowserCatalogSummary | null;
}


export default function DashboardOverview({ summary }: DashboardOverviewProps) {
  if (!summary) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Dashboard 概覽</CardTitle>
        </CardHeader>
        <CardContent className="text-slate-400 text-sm">尚未載入資料</CardContent>
      </Card>
    );
  }

  const cards = [
    ['特徵數', summary.total_features.toString()],
    ['類別數', summary.total_categories.toString()],
    ['平均覆蓋率', `${(summary.avg_coverage * 100).toFixed(2)}%`],
    ['定態率', `${(summary.stationary_ratio * 100).toFixed(2)}%`],
    ['低品質數', summary.low_quality_count.toString()],
    ['冗餘對數', summary.redundant_pairs.toString()],
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {cards.map(([label, value]) => (
        <Card key={label}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-slate-400">{label}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-slate-100">{value}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

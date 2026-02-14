import React from 'react';
import type { ComparisonReportResponse, ModelPerformanceResponse } from '@/lib/patternTypes';

interface ComparisonMetricsTableProps {
  report: ComparisonReportResponse;
}

const metricMap: Array<{ key: keyof ModelPerformanceResponse; label: string; lowerIsBetter?: boolean }> = [
  { key: 'cv_auc_mean', label: 'CV AUC' },
  { key: 'precision', label: 'Precision' },
  { key: 'recall', label: 'Recall' },
  { key: 'f1_score', label: 'F1 Score' },
  { key: 'overfitting_score', label: 'Overfitting', lowerIsBetter: true },
  { key: 'brier_score', label: 'Brier Score', lowerIsBetter: true },
  { key: 'training_time_seconds', label: 'Train Time(s)', lowerIsBetter: true }
];

export default function ComparisonMetricsTable({ report }: ComparisonMetricsTableProps) {
  const entries = Object.entries(report.engine_performances);
  const xgboost = entries.find(([name]) => name.toLowerCase().includes('xgboost'))?.[1] || entries[0]?.[1];
  const lightgbm = entries.find(([name]) => name.toLowerCase().includes('lightgbm'))?.[1] || entries[1]?.[1];

  if (!xgboost || !lightgbm) {
    return null;
  }

  return (
    <div className="rounded-lg border border-slate-700 overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-slate-900/60 text-slate-300">
          <tr>
            <th className="text-left p-3">指標</th>
            <th className="text-right p-3">XGBoost</th>
            <th className="text-right p-3">LightGBM</th>
            <th className="text-right p-3">差異</th>
            <th className="text-right p-3">勝方</th>
          </tr>
        </thead>
        <tbody>
          {metricMap.map((metric) => {
            const xv = Number(xgboost[metric.key] ?? 0);
            const lv = Number(lightgbm[metric.key] ?? 0);
            const diff = lv - xv;
            const better = metric.lowerIsBetter ? (diff < 0 ? 'LGB' : diff > 0 ? 'XGB' : '≈') : (diff > 0 ? 'LGB' : diff < 0 ? 'XGB' : '≈');

            return (
              <tr key={metric.key} className="border-t border-slate-800 text-slate-200">
                <td className="p-3">{metric.label}</td>
                <td className="p-3 text-right">{xv.toFixed(4)}</td>
                <td className="p-3 text-right">{lv.toFixed(4)}</td>
                <td className={`p-3 text-right ${diff > 0 ? 'text-emerald-300' : diff < 0 ? 'text-rose-300' : 'text-slate-300'}`}>
                  {diff >= 0 ? '+' : ''}{diff.toFixed(4)}
                </td>
                <td className="p-3 text-right">{better === '≈' ? '≈ 相當' : `✅ ${better}`}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

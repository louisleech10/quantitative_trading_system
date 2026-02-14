'use client';

import React from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { ComparisonReportResponse } from '@/lib/patternTypes';

interface ComparisonFeatureChartProps {
  report: ComparisonReportResponse;
}

export default function ComparisonFeatureChart({ report }: ComparisonFeatureChartProps) {
  const entries = Object.entries(report.engine_performances);
  const xgbName = entries.find(([name]) => name.toLowerCase().includes('xgboost'))?.[0] || entries[0]?.[0];
  const lgbName = entries.find(([name]) => name.toLowerCase().includes('lightgbm'))?.[0] || entries[1]?.[0];

  const xgb = report.engine_performances[xgbName || ''];
  const lgb = report.engine_performances[lgbName || ''];

  const data = [
    { metric: 'AUC', xgb: xgb?.cv_auc_mean ?? 0, lgb: lgb?.cv_auc_mean ?? 0 },
    { metric: 'Precision', xgb: xgb?.precision ?? 0, lgb: lgb?.precision ?? 0 },
    { metric: 'Recall', xgb: xgb?.recall ?? 0, lgb: lgb?.recall ?? 0 },
    { metric: 'F1', xgb: xgb?.f1_score ?? 0, lgb: lgb?.f1_score ?? 0 }
  ];

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="metric" stroke="#94a3b8" />
          <YAxis stroke="#94a3b8" />
          <Tooltip />
          <Bar dataKey="xgb" name="XGBoost" fill="#60a5fa" radius={[4, 4, 0, 0]} />
          <Bar dataKey="lgb" name="LightGBM" fill="#34d399" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

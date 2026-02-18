'use client';

import { useMemo, useState } from 'react';
import { Area, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { LearningCurveResult } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface LearningCurveChartProps {
  data: LearningCurveResult;
}

type CurveMode = 'data' | 'feature';

interface DataCurvePoint {
  x: number;
  train: number | null;
  cv: number | null;
  cvUpper: number | null;
  cvLower: number | null;
  cvStdBand: number | null;
}

interface FeatureCurvePoint {
  x: number;
  cv: number | null;
}

export default function LearningCurveChart({ data }: LearningCurveChartProps) {
  const [mode, setMode] = useState<CurveMode>('data');

  const dataCurve = useMemo(() => {
    const fractions = data.data_curve?.fractions ?? [];
    const trainScores = data.data_curve?.train_scores ?? [];
    const cvScores = data.data_curve?.cv_scores ?? [];
    const cvStds = data.data_curve?.cv_stds ?? [];

    return fractions.map((fraction, index) => {
      const cvScore = cvScores[index] ?? null;
      const std = cvStds[index];
      const upper = typeof cvScore === 'number' && typeof std === 'number' ? cvScore + std : null;
      const lower = typeof cvScore === 'number' && typeof std === 'number' ? cvScore - std : null;
      const stdBand = typeof upper === 'number' && typeof lower === 'number' ? upper - lower : null;

      const point: DataCurvePoint = {
        x: fraction,
        train: trainScores[index] ?? null,
        cv: cvScore,
        cvUpper: upper,
        cvLower: lower,
        cvStdBand: stdBand,
      };
      return point;
    });
  }, [data.data_curve]);

  const featureCurve = useMemo(() => {
    const counts = data.feature_curve?.feature_counts ?? [];
    const scores = data.feature_curve?.cv_scores ?? [];
    return counts.map((count, index): FeatureCurvePoint => ({
      x: count,
      cv: scores[index] ?? null,
    }));
  }, [data.feature_curve]);

  const chartData = mode === 'data' ? dataCurve : featureCurve;

  const yDomain = useMemo<[number, number]>(() => {
    if (chartData.length === 0) {
      return [0, 1];
    }

    const values =
      mode === 'data'
        ? dataCurve
            .flatMap((row) => [row.train, row.cv, row.cvUpper, row.cvLower])
            .filter((value): value is number => typeof value === 'number')
        : featureCurve
            .map((row) => row.cv)
            .filter((value): value is number => typeof value === 'number');

    if (values.length === 0) {
      return [0, 1];
    }

    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const lower = Math.max(0, minValue - 0.05);
    const upper = Math.min(1, maxValue + 0.05);
    return [lower, upper];
  }, [chartData, dataCurve, featureCurve, mode]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-base">C27 Learning Curve</CardTitle>
          <CardDescription>Data curve / Feature curve 切換檢視</CardDescription>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setMode('data')}
            className={`text-xs px-2 py-1 rounded ${mode === 'data' ? 'bg-cyan-500/20 text-cyan-300' : 'bg-slate-800 text-slate-300'}`}
          >
            Data
          </button>
          <button
            type="button"
            onClick={() => setMode('feature')}
            className={`text-xs px-2 py-1 rounded ${mode === 'feature' ? 'bg-cyan-500/20 text-cyan-300' : 'bg-slate-800 text-slate-300'}`}
          >
            Feature
          </button>
        </div>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="h-[260px] flex items-center justify-center text-slate-400">暫無 learning curve 資料</div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <ComposedChart data={chartData}>
              <XAxis dataKey="x" />
              <YAxis domain={yDomain} />
              <Tooltip />

              {mode === 'data' && (
                <>
                  <Area type="monotone" dataKey="cvLower" stackId="std" stroke="none" fillOpacity={0} name="CV-STD-Lower" />
                  <Area type="monotone" dataKey="cvStdBand" stackId="std" stroke="none" fill="#38bdf833" name="CV STD" />
                  <Line type="monotone" dataKey="train" stroke="#22c55e" strokeWidth={2} dot={{ r: 2 }} name="Train" connectNulls={false} />
                </>
              )}

              <Line type="monotone" dataKey="cv" stroke="#f59e0b" strokeWidth={2} dot={{ r: 2 }} name="CV" connectNulls={false} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

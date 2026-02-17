'use client';

import { useEffect, useMemo, useState } from 'react';
import { CartesianGrid, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts';

import CorrelationHeatmap from '@/components/ic-analysis/CorrelationHeatmap';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  FeatureBrowserCorrelationResponse,
  FeatureBrowserDataTableResponse,
} from '@/lib/types';


const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';


interface FeatureCorrelationPanelProps {
  featuresPath: string;
  selectedFeatures: string[];
}


export default function FeatureCorrelationPanel({ featuresPath, selectedFeatures }: FeatureCorrelationPanelProps) {
  const [data, setData] = useState<FeatureBrowserCorrelationResponse | null>(null);
  const [scatterData, setScatterData] = useState<Array<{ x: number; y: number }>>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!featuresPath || selectedFeatures.length === 0) {
      setData(null);
      return;
    }

    setError(null);
    const query = new URLSearchParams({
      features_path: featuresPath,
      features: selectedFeatures.join(','),
      method: 'spearman',
      max_features: '100',
    });

    fetch(`${API_BASE_URL}/api/v1/features/correlation?${query.toString()}`)
      .then(async (response) => {
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload?.detail || response.statusText);
        }
        return response.json() as Promise<FeatureBrowserCorrelationResponse>;
      })
      .then((payload) => setData(payload))
      .catch((fetchError: unknown) => {
        setError(fetchError instanceof Error ? fetchError.message : '載入相關性失敗');
      });
  }, [featuresPath, selectedFeatures]);

  useEffect(() => {
    if (!featuresPath || selectedFeatures.length < 2) {
      setScatterData([]);
      return;
    }

    const pair = selectedFeatures.slice(0, 2);
    const query = new URLSearchParams({
      features_path: featuresPath,
      page: '1',
      page_size: '300',
      columns: pair.join(','),
    });

    fetch(`${API_BASE_URL}/api/v1/features/data-table?${query.toString()}`)
      .then(async (response) => {
        if (!response.ok) {
          return null;
        }
        return response.json() as Promise<FeatureBrowserDataTableResponse>;
      })
      .then((payload) => {
        if (!payload) {
          setScatterData([]);
          return;
        }
        const rows = payload.rows.map((row) => ({
          x: Number(row[pair[0]]),
          y: Number(row[pair[1]]),
        })).filter((row) => Number.isFinite(row.x) && Number.isFinite(row.y));
        setScatterData(rows);
      })
      .catch(() => setScatterData([]));
  }, [featuresPath, selectedFeatures]);

  const correlationMatrix = useMemo(() => {
    if (!data) {
      return null;
    }
    return {
      features: data.features,
      matrix: data.matrix,
    };
  }, [data]);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">相關性熱力圖</CardTitle>
        </CardHeader>
        <CardContent>
          {error ? <div className="text-rose-300 text-sm">{error}</div> : <CorrelationHeatmap matrix={correlationMatrix} />}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Pair Scatter（前兩個特徵）</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" dataKey="x" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <YAxis type="number" dataKey="y" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                <ReferenceLine x={0} stroke="#64748b" />
                <ReferenceLine y={0} stroke="#64748b" />
                <Scatter data={scatterData} fill="#38bdf8" />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

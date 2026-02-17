'use client';

import { useEffect, useMemo, useRef, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { FeatureBrowserQualityItem, FeatureBrowserQualityResponse } from '@/lib/types';


const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';


interface DataQualityPanelProps {
  featuresPath: string;
  selectedFeatures: string[];
}


export default function DataQualityPanel({ featuresPath, selectedFeatures }: DataQualityPanelProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [results, setResults] = useState<FeatureBrowserQualityItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runQualityCheck = async () => {
    if (!featuresPath) {
      setError('請先輸入 features_path');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/features/quality-check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          features_path: featuresPath,
          selected_features: selectedFeatures.length > 0 ? selectedFeatures : undefined,
        }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || response.statusText);
      }

      const payload: FeatureBrowserQualityResponse = await response.json();
      setResults(payload.results);
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : '品質檢測失敗');
    } finally {
      setLoading(false);
    }
  };

  const coverageLevels = useMemo(
    () => results.map((item) => Math.max(0, Math.min(1, item.coverage))),
    [results]
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext('2d');
    if (!context) return;

    const width = canvas.width;
    const height = canvas.height;
    context.clearRect(0, 0, width, height);

    if (coverageLevels.length === 0) {
      context.fillStyle = '#64748b';
      context.font = '12px sans-serif';
      context.fillText('尚無覆蓋率資料', 12, 18);
      return;
    }

    const cellWidth = Math.max(4, Math.floor(width / coverageLevels.length));
    coverageLevels.forEach((value, idx) => {
      const green = Math.round(80 + value * 160);
      const red = Math.round(220 - value * 180);
      context.fillStyle = `rgb(${red}, ${green}, 120)`;
      context.fillRect(idx * cellWidth, 0, cellWidth, height);
    });
  }, [coverageLevels]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">品質檢測</CardTitle>
        <Button onClick={runQualityCheck} disabled={loading}>
          {loading ? '執行中...' : '執行品質檢測'}
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <div className="text-rose-300 text-sm">{error}</div>}
        <div className="rounded border border-white/10 p-3">
          <div className="text-sm text-slate-300 mb-2">覆蓋率熱力圖（Canvas）</div>
          <canvas ref={canvasRef} width={960} height={40} className="w-full h-10 bg-slate-900 rounded" />
        </div>

        <div className="rounded border border-white/10 overflow-auto max-h-[320px]">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>feature</TableHead>
                <TableHead>coverage</TableHead>
                <TableHead>NaN%</TableHead>
                <TableHead>ADF p-value</TableHead>
                <TableHead>stationary</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {results.map((item) => (
                <TableRow key={item.feature}>
                  <TableCell>{item.feature}</TableCell>
                  <TableCell>{(item.coverage * 100).toFixed(2)}%</TableCell>
                  <TableCell>{item.nan_pct.toFixed(2)}%</TableCell>
                  <TableCell>{item.adf_pvalue?.toFixed(6) ?? '--'}</TableCell>
                  <TableCell>{item.is_stationary ? 'Yes' : 'No'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

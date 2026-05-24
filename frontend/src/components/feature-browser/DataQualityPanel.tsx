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

        <details className="rounded border border-sky-400/20 bg-sky-500/5 p-3 text-sm text-sky-100/90">
          <summary className="cursor-pointer font-medium text-sky-200">
            為什麼會出現高 NaN 比例的特徵？（2026-05-21 修復後）
          </summary>
          <div className="mt-2 space-y-2 text-sky-100/80 leading-relaxed">
            <p>
              先前版本中，TA-Lib pattern 類別（~99% 為零的 CDL* 訊號）會被送入 L2 ratio/momentum
              算子，公式 <code className="px-1 rounded bg-white/10 font-mono text-xs">(x − x.shift) / shifted.replace(0, NaN)</code>
              產生 99.77% NaN 的輸出，再經 L3 (10 windows × 10 aggregators) 串接，造成
              <strong className="text-sky-200"> 120,377 個高 NaN 特徵</strong>。
            </p>
            <p>
              修復方案：於 L2 / L3 / L6.5 三層各加入 <code className="px-1 rounded bg-white/10 font-mono text-xs">RATIO_UNSAFE_CATEGORIES = {`{"pattern"}`}</code>
              黑名單守門，並新增 <code className="px-1 rounded bg-white/10 font-mono text-xs">effective_n &lt; 30</code> 過濾條件。修復後 pattern
              類別衍生欄位為 0，預期高 NaN 特徵數應 &lt; 1,000。
            </p>
            <div className="flex flex-wrap gap-3 pt-1 text-xs text-sky-300/80">
              <span>📄 docs/NAN_POISONING_INVESTIGATION.md</span>
              <span>📄 docs/FEATURE_DEVELOPER_CHECKLIST.md</span>
            </div>
          </div>
        </details>

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

'use client';

import { useEffect, useMemo, useState } from 'react';

import type { CorrelationMatrix } from '@/lib/types';

interface CorrelationHeatmapProps {
  featuresPath: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface VIFRow {
  feature_name: string;
  vif: number;
  status: 'stable' | 'warning' | 'severe';
}

export default function CorrelationHeatmap({ featuresPath }: CorrelationHeatmapProps) {
  const [matrix, setMatrix] = useState<CorrelationMatrix | null>(null);
  const [vifRows, setVifRows] = useState<VIFRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!featuresPath.trim()) {
      return;
    }

    const run = async () => {
      setError(null);
      try {
        const matrixQuery = new URLSearchParams({ features_path: featuresPath, max_features: '40', method: 'spearman' });
        const matrixResp = await fetch(`${API_BASE_URL}/api/v1/feature-browser/correlation-matrix?${matrixQuery.toString()}`);
        if (!matrixResp.ok) {
          const payload = await matrixResp.json().catch(() => ({}));
          throw new Error(payload?.detail || matrixResp.statusText);
        }
        const matrixPayload: CorrelationMatrix = await matrixResp.json();
        setMatrix(matrixPayload);

        const vifQuery = new URLSearchParams({ features_path: featuresPath, max_features: '80' });
        const vifResp = await fetch(`${API_BASE_URL}/api/v1/feature-browser/vif?${vifQuery.toString()}`);
        if (!vifResp.ok) {
          const payload = await vifResp.json().catch(() => ({}));
          throw new Error(payload?.detail || vifResp.statusText);
        }
        const vifPayload = await vifResp.json();
        setVifRows((vifPayload?.items || []) as VIFRow[]);
      } catch (err) {
        setError(err instanceof Error ? err.message : '讀取相關性資料失敗');
        setMatrix(null);
        setVifRows([]);
      }
    };

    void run();
  }, [featuresPath]);

  const gridItems = useMemo(() => {
    if (!matrix || matrix.features.length === 0) {
      return [];
    }

    const features = matrix.features.slice(0, 20);
    const idxMap = new Map(features.map((name, idx) => [name, idx]));
    return features.flatMap((rowFeature) =>
      features.map((colFeature) => {
        const row = idxMap.get(rowFeature) ?? 0;
        const col = idxMap.get(colFeature) ?? 0;
        const value = matrix.matrix[row]?.[col] ?? 0;
        return {
          key: `${rowFeature}-${colFeature}`,
          rowFeature,
          colFeature,
          value,
        };
      }),
    );
  }, [matrix]);

  if (!featuresPath.trim()) {
    return <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 text-sm text-slate-300">請先輸入 features_path 並載入資料。</div>;
  }

  if (error) {
    return <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 text-sm text-rose-300">{error}</div>;
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C39 CorrelationHeatmap</h3>
        {!matrix || gridItems.length === 0 ? (
          <div className="mt-3 text-sm text-slate-300">沒有相關矩陣資料。</div>
        ) : (
          <>
            {matrix.truncated && (
              <div className="mt-2 text-xs text-amber-300">
                已縮減特徵數：原始 {matrix.original_feature_count}，目前顯示 {matrix.features.length}
              </div>
            )}
            <div
              className="mt-3 grid gap-1 overflow-auto"
              style={{ gridTemplateColumns: 'repeat(20, minmax(0, 1fr))' }}
            >
              {gridItems.map((item) => {
                const intensity = Math.min(1, Math.abs(item.value));
                const positive = item.value >= 0;
                const bgColor = positive
                  ? `rgba(59,130,246,${0.12 + intensity * 0.75})`
                  : `rgba(244,63,94,${0.12 + intensity * 0.75})`;

                return (
                  <div
                    key={item.key}
                    title={`${item.rowFeature} vs ${item.colFeature}: ${item.value.toFixed(3)}`}
                    className="h-4 w-4 rounded-[2px] border border-white/5"
                    style={{ backgroundColor: bgColor }}
                  />
                );
              })}
            </div>
          </>
        )}
      </div>

      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C40 VIFTable</h3>
        <div className="mt-4 max-h-72 overflow-auto">
          <table className="min-w-full text-xs">
            <thead className="text-slate-300">
              <tr>
                <th className="px-2 py-1 text-left">Feature</th>
                <th className="px-2 py-1 text-right">VIF</th>
                <th className="px-2 py-1 text-right">Status</th>
              </tr>
            </thead>
            <tbody>
              {vifRows.slice(0, 120).map((row) => (
                <tr key={row.feature_name}>
                  <td className="px-2 py-1 text-slate-100">{row.feature_name}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{row.vif.toFixed(3)}</td>
                  <td className="px-2 py-1 text-right">
                    <span
                      className={
                        row.status === 'stable'
                          ? 'text-emerald-300'
                          : row.status === 'warning'
                            ? 'text-amber-300'
                            : 'text-rose-300'
                      }
                    >
                      {row.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

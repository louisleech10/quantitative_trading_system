'use client';

import { useEffect, useMemo, useState } from 'react';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import { exportChartToPNG } from '@/lib/exportUtils';

interface FeatureCorrelationHeatmapProps {
  taskId: string;
}

const methods: Array<'pearson' | 'spearman' | 'kendall'> = ['pearson', 'spearman', 'kendall'];

export default function FeatureCorrelationHeatmap({ taskId }: FeatureCorrelationHeatmapProps) {
  const { explorerSelectedFeatures, setExplorerSelectedFeatures } = useFeatureFactoryStore();
  const { browseCorrelation, browseFeatures } = useFeatureFactory();
  const [method, setMethod] = useState<'pearson' | 'spearman' | 'kendall'>('pearson');
  const [available, setAvailable] = useState<string[]>([]);
  const [matrix, setMatrix] = useState<number[][]>([]);
  const [labels, setLabels] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    browseFeatures(taskId, { offset: 0, limit: 200, sortBy: 'std', sortOrder: 'desc' })
      .then((resp) => {
        if (!active) return;
        setAvailable(resp.features.map((item) => item.name));
      })
      .catch(() => {
        if (!active) return;
        setAvailable([]);
      });

    return () => {
      active = false;
    };
  }, [browseFeatures, taskId]);

  const selected = useMemo(() => Array.from(new Set(explorerSelectedFeatures)).slice(0, 50), [explorerSelectedFeatures]);

  useEffect(() => {
    if (selected.length < 2) {
      setMatrix([]);
      setLabels([]);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

    browseCorrelation(taskId, selected, method)
      .then((resp) => {
        if (!active) return;
        setLabels(resp.features);
        setMatrix(resp.matrix);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : '載入相關矩陣失敗');
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [browseCorrelation, taskId, selected, method]);

  const toggleFeature = (feature: string) => {
    const current = new Set(explorerSelectedFeatures);
    if (current.has(feature)) {
      current.delete(feature);
      setExplorerSelectedFeatures(Array.from(current));
      return;
    }
    if (current.size >= 50) return;
    current.add(feature);
    setExplorerSelectedFeatures(Array.from(current));
  };

  return (
    <div className="glass-panel rounded-2xl p-4 space-y-3">
      <div className="flex items-center gap-2">
        <div className="text-sm text-slate-300">Correlation Heatmap（最多 50）</div>
        <button
          onClick={() => {
            const picks = available.filter((name) => name.startsWith('ms_')).slice(0, 50);
            setExplorerSelectedFeatures(picks);
          }}
          className="text-xs px-2 py-1 rounded border border-white/10 text-slate-200"
        >
          選取 Microstructure
        </button>
        <button
          onClick={() => {
            setExplorerSelectedFeatures(available.slice(0, 20));
          }}
          className="text-xs px-2 py-1 rounded border border-white/10 text-slate-200"
        >
          Top 20 by Std
        </button>
        <select
          value={method}
          onChange={(e) => setMethod(e.target.value as 'pearson' | 'spearman' | 'kendall')}
          className="ml-auto rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-100"
        >
          {methods.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <button
          onClick={() => exportChartToPNG('feature-correlation-heatmap', 'feature_correlation', taskId)}
          className="text-xs px-2 py-1 rounded border border-white/10 text-slate-200"
        >
          匯出 PNG
        </button>
      </div>

      <div className="flex flex-wrap gap-2 max-h-28 overflow-auto">
        {available.slice(0, 200).map((name) => (
          <button
            key={name}
            onClick={() => toggleFeature(name)}
            className={`text-xs px-2 py-1 rounded-full border ${
              selected.includes(name) ? 'bg-amber-400/20 border-amber-300/40 text-amber-200' : 'border-white/10 text-slate-300'
            }`}
          >
            {name}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-xs text-slate-400">載入中...</div>
      ) : error ? (
        <div className="text-xs text-rose-300">{error}</div>
      ) : matrix.length === 0 ? (
        <div className="text-xs text-slate-400">請至少選擇 2 個特徵。</div>
      ) : (
        <div id="feature-correlation-heatmap" className="overflow-auto">
          <div
            className="grid gap-[2px]"
            style={{ gridTemplateColumns: `repeat(${labels.length}, minmax(18px, 1fr))`, minWidth: 400 }}
          >
            {matrix.flatMap((row, rowIndex) =>
              row.map((value, colIndex) => {
                const abs = Math.abs(value);
                const bg = value >= 0 ? `rgba(239,68,68,${abs})` : `rgba(37,99,235,${abs})`;
                const warn = rowIndex !== colIndex && abs > 0.95;
                return (
                  <div
                    key={`${rowIndex}-${colIndex}`}
                    title={`${labels[rowIndex]} ↔ ${labels[colIndex]}: ${value.toFixed(4)}`}
                    className={`h-5 ${warn ? 'ring-1 ring-amber-300' : ''}`}
                    style={{ backgroundColor: bg }}
                  />
                );
              })
            )}
          </div>
          <div className="text-[11px] text-slate-400 mt-2">選中 {labels.length} 個特徵</div>
        </div>
      )}
    </div>
  );
}

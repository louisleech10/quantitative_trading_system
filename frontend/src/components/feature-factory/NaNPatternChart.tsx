'use client';

import { useEffect, useState } from 'react';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import { exportChartToPNG } from '@/lib/exportUtils';

interface NaNPatternChartProps {
  taskId: string;
}

export default function NaNPatternChart({ taskId }: NaNPatternChartProps) {
  const { browseNanPattern } = useFeatureFactory();
  const [sampleFeatures, setSampleFeatures] = useState(50);
  const [payload, setPayload] = useState<{
    features: string[];
    matrix: boolean[][];
    nan_ratios: number[];
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    browseNanPattern(taskId, sampleFeatures)
      .then((resp) => {
        if (!active) return;
        setPayload({
          features: resp.features,
          matrix: resp.matrix,
          nan_ratios: resp.nan_ratios,
        });
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : '載入 NaN pattern 失敗');
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [browseNanPattern, taskId, sampleFeatures]);

  const dangerous = (payload?.features || []).filter((_, idx) => (payload?.nan_ratios[idx] || 0) > 0.1);

  const classifyPattern = (featureIndex: number) => {
    if (!payload || payload.matrix.length === 0) return 'unknown';
    const values = payload.matrix.map((row) => row[featureIndex] ?? false);
    const firstHalf = values.slice(0, Math.max(1, Math.floor(values.length * 0.3)));
    const rest = values.slice(Math.max(1, Math.floor(values.length * 0.3)));
    const firstRatio = firstHalf.filter(Boolean).length / Math.max(1, firstHalf.length);
    const restRatio = rest.filter(Boolean).length / Math.max(1, rest.length);
    if (firstRatio > 0.5 && restRatio < 0.2) return 'warmup';
    if (restRatio > 0.2) return 'random';
    return 'stable';
  };

  return (
    <div className="glass-panel rounded-2xl p-4 space-y-3">
      <div className="flex items-center gap-2">
        <div className="text-sm text-slate-300">NaN Pattern</div>
        <div className="ml-auto text-xs text-slate-300">sample: {sampleFeatures}</div>
        <input
          type="range"
          min={10}
          max={200}
          step={1}
          value={sampleFeatures}
          onChange={(e) => setSampleFeatures(Number(e.target.value))}
        />
        <button
          onClick={() => exportChartToPNG('feature-nan-pattern-chart', 'feature_nan_pattern', taskId)}
          className="text-xs px-2 py-1 rounded border border-white/10 text-slate-200"
        >
          匯出 PNG
        </button>
      </div>

      {loading ? (
        <div className="text-xs text-slate-400">載入中...</div>
      ) : error ? (
        <div className="text-xs text-rose-300">{error}</div>
      ) : !payload || payload.features.length === 0 ? (
        <div className="text-xs text-emerald-300">所有特徵完整，無 NaN pattern。</div>
      ) : (
        <>
          <div id="feature-nan-pattern-chart" className="overflow-auto border border-white/10 rounded-lg p-2">
            <div className="space-y-[2px] min-w-[640px]">
              {payload.features.map((feature, rowIdx) => (
                <div key={feature} className="flex items-center gap-[2px]">
                  <div className="w-52 truncate text-[10px] text-slate-400">
                    {feature}
                    <span className="ml-1 text-slate-500">[{classifyPattern(rowIdx)}]</span>
                  </div>
                  <div className="flex gap-[1px]">
                    {(payload.matrix || []).slice(0, 400).map((row, colIdx) => {
                      const isNan = row[rowIdx] ?? false;
                      return (
                        <div
                          key={`${feature}-${colIdx}`}
                          className="w-[2px] h-3"
                          style={{ backgroundColor: isNan ? '#f8fafc' : '#0f172a' }}
                          title={`${feature} @ ${colIdx}: ${isNan ? 'NaN' : 'valid'}`}
                        />
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="rounded-lg border border-white/10 bg-white/5 p-3">
              <div className="text-xs text-slate-300 mb-1">危險特徵（NaN &gt; 10%）</div>
              <div className="text-xs text-rose-200 max-h-24 overflow-auto">
                {dangerous.length === 0 ? '無' : dangerous.join(', ')}
              </div>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/5 p-3">
              <div className="text-xs text-slate-300 mb-1">平均完整率</div>
              <div className="text-sm text-slate-100">
                {`${(((payload.nan_ratios.reduce((acc, value) => acc + (1 - value), 0) / Math.max(1, payload.nan_ratios.length)) * 100).toFixed(2))}%`}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

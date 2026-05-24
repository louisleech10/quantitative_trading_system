'use client';

import { useEffect, useRef, useState } from 'react';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import { exportChartToPNG } from '@/lib/exportUtils';

interface NaNPatternChartProps {
  taskId: string;
}

// Canvas row height (px). Needs to be tall enough to be visible on screen.
const CANVAS_H = 16;

// ── Canvas renderer for a single feature row ─────────────────────────────────
// Sets intrinsic width/height via HTML attributes at render time so the browser
// never auto-scales the canvas to the wrong size before useEffect fires.
// (Without explicit attrs, CSS height:12px on a default 300×150 canvas causes
//  it to display as 24px wide = 300×12/150, making all bars look short.)
function NaNRowCanvas({ nanArray }: { nanArray: boolean[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const n = nanArray.length;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || n === 0) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Resizing clears the canvas — redraw immediately after.
    canvas.width = n * 2;
    canvas.height = CANVAS_H;

    // Valid data = slate-700 (visible against dark background)
    ctx.fillStyle = '#334155';
    ctx.fillRect(0, 0, n * 2, CANVAS_H);

    // NaN positions = white
    ctx.fillStyle = '#f8fafc';
    for (let i = 0; i < n; i++) {
      if (nanArray[i]) ctx.fillRect(i * 2, 0, 2, CANVAS_H);
    }
  }, [nanArray, n]);

  if (n === 0) return <div className="flex-1" />;

  // CSS width:100% scales the canvas to fill the flex row regardless of n.
  // The intrinsic canvas size is set in useEffect (canvas.width = n*2), so
  // the NaN pattern is painted at correct resolution and then stretched/
  // compressed by CSS to always span the full available width.
  return (
    <div className="flex-1 min-w-0">
      <canvas
        ref={canvasRef}
        style={{ display: 'block', width: '100%', height: `${CANVAS_H}px` }}
      />
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function NaNPatternChart({ taskId }: NaNPatternChartProps) {
  const { browseNanPattern } = useFeatureFactory();

  // Slider state (immediate) + debounced state (triggers API call)
  const [sampleFeatures, setSampleFeatures] = useState(50);
  const [debouncedSample, setDebouncedSample] = useState(50);

  const [payload, setPayload] = useState<{
    features: string[];
    matrix: boolean[][];     // [N_features, T_sampled] — one row per feature
    nan_ratios: number[];
    timestamps: string[];
    timestamps_total?: number;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Debounce: fire API call 500 ms after slider stops dragging
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSample(sampleFeatures), 500);
    return () => clearTimeout(timer);
  }, [sampleFeatures]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    browseNanPattern(taskId, debouncedSample)
      .then((resp) => {
        if (!active) return;
        setPayload({
          features: resp.features,
          matrix: resp.matrix,
          nan_ratios: resp.nan_ratios,
          timestamps: resp.timestamps ?? [],
          timestamps_total: resp.timestamps_total,
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
  }, [browseNanPattern, taskId, debouncedSample]);

  const dangerous = (payload?.features ?? []).filter(
    (_, idx) => (payload?.nan_ratios[idx] ?? 0) > 0.1,
  );

  // matrix is now [N, T] — matrix[featureIndex] = boolean array over time
  const classifyPattern = (featureIndex: number): string => {
    if (!payload || payload.matrix.length === 0) return 'unknown';
    const values = payload.matrix[featureIndex] ?? [];
    if (values.length === 0) return 'unknown';
    const cut = Math.max(1, Math.floor(values.length * 0.3));
    const firstRatio = values.slice(0, cut).filter(Boolean).length / cut;
    const restRatio =
      values.slice(cut).filter(Boolean).length / Math.max(1, values.length - cut);
    if (firstRatio > 0.5 && restRatio < 0.2) return 'warmup';
    if (restRatio > 0.2) return 'random';
    return 'stable';
  };

  const shownSteps = payload?.timestamps?.length ?? 0;
  const totalSteps = payload?.timestamps_total;
  const samplingNote =
    totalSteps && totalSteps > shownSteps
      ? `（每 ${Math.round(totalSteps / shownSteps)} 步取樣，顯示 ${shownSteps} / ${totalSteps} 時間點）`
      : '';

  return (
    <div className="glass-panel rounded-2xl p-4 space-y-3">
      {/* ── Header ── */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="text-sm text-slate-300">NaN Pattern</div>
        {samplingNote && (
          <div className="text-xs text-slate-500">{samplingNote}</div>
        )}
        <div className="ml-auto text-xs text-slate-300">
          sample: {sampleFeatures}
          {sampleFeatures !== debouncedSample && (
            <span className="ml-1 text-slate-500">（確認中…）</span>
          )}
        </div>
        <input
          type="range"
          min={10}
          max={200}
          step={1}
          value={sampleFeatures}
          onChange={(e) => setSampleFeatures(Number(e.target.value))}
        />
        <button
          onClick={() =>
            exportChartToPNG('feature-nan-pattern-chart', 'feature_nan_pattern', taskId)
          }
          className="text-xs px-2 py-1 rounded border border-white/10 text-slate-200"
        >
          匯出 PNG
        </button>
      </div>

      {/* ── 圖例說明 ── */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400">
        <span className="font-medium text-slate-300">圖例：</span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-5 h-4 rounded-sm bg-[#334155]" />
          有效資料
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-5 h-4 rounded-sm bg-slate-100" />
          NaN（缺失）
        </span>
        <span className="mx-1 text-slate-600">|</span>
        <span className="text-slate-400">[stable] 全段有效</span>
        <span className="text-slate-400">[warmup] 初期缺失（滾動窗口需暖身）</span>
        <span className="text-slate-400">[random] 散落缺失</span>
      </div>

      {/* ── 選擇說明 ── */}
      <div className="text-xs text-slate-400">
        顯示 NaN 比例最高的前 {debouncedSample} 個特徵（由高至低排序）。若所有特徵完整，顯示前 {debouncedSample} 個。
      </div>

      {loading ? (
        <div className="text-xs text-slate-400">載入中…</div>
      ) : error ? (
        <div className="text-xs text-rose-300">{error}</div>
      ) : !payload || payload.features.length === 0 ? (
        <div className="text-xs text-emerald-300">所有特徵完整，無 NaN pattern。</div>
      ) : (
        <>
          {/* ── Heatmap ── */}
          <div
            id="feature-nan-pattern-chart"
            className="overflow-auto border border-white/10 rounded-lg p-2"
          >
            <div className="min-w-[640px]">
              {/* ── 欄位標題 ── */}
              <div className="flex items-center gap-2 mb-2 border-b border-white/5 pb-1">
                <div className="w-56 shrink-0 text-[10px] text-slate-500">特徵名稱</div>
                <div className="w-10 shrink-0 text-[10px] text-slate-500 text-right" title="缺失資料比例">
                  NaN%
                </div>
                <div className="flex-1 text-[10px] text-slate-600 text-center">
                  ← 時間軸（左 = 早、右 = 晚）→
                </div>
              </div>
              <div className="space-y-[3px]">
              {payload.features.map((feature, rowIdx) => (
                <div key={feature} className="flex items-center gap-2">
                  <div className="w-56 truncate text-xs text-slate-300 shrink-0" title={feature}>
                    {feature}
                    <span className="ml-1 text-[10px] text-slate-500">[{classifyPattern(rowIdx)}]</span>
                  </div>
                  <div className="text-[10px] text-slate-500 w-10 shrink-0 text-right">
                    {((payload.nan_ratios[rowIdx] ?? 0) * 100).toFixed(1)}%
                  </div>
                  {/* Canvas replaces 400 individual divs per feature */}
                  <NaNRowCanvas nanArray={payload.matrix[rowIdx] ?? []} />
                </div>
              ))}
              </div>{/* close space-y-[3px] */}
            </div>{/* close min-w-[640px] */}
          </div>{/* close overflow-auto */}

          {/* ── Stats ── */}
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
                {`${(
                  (payload.nan_ratios.reduce((acc, v) => acc + (1 - v), 0) /
                    Math.max(1, payload.nan_ratios.length)) *
                  100
                ).toFixed(2)}%`}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

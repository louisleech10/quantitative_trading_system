'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Brush,
} from 'recharts';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import { exportChartToPNG } from '@/lib/exportUtils';
import FeatureNameSegmentFilter from '@/components/feature-factory/FeatureNameSegmentFilter';

interface FeatureTimeSeriesChartProps {
  taskId: string;
}

const COLORS = ['#34d399', '#60a5fa', '#f59e0b', '#f472b6', '#a78bfa'];
const ROLLING_WINDOW_MIN = 5;
const ROLLING_WINDOW_MAX = 200;
const ROLLING_WINDOW_DEFAULT = 20;

/** ISO/Unix timestamp → "YYYY/MM/DD" */
function formatTimestamp(val: string | number): string {
  if (!val) return '';
  const d = new Date(typeof val === 'number' ? val : val);
  if (isNaN(d.getTime())) return String(val).slice(0, 10);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}/${m}/${day}`;
}

/** 依資料筆數決定 X 軸 interval，目標約 10~14 個 tick */
function calcXInterval(dataLen: number): number {
  if (dataLen <= 0) return 0;
  return Math.max(1, Math.floor(dataLen / 12));
}

export default function FeatureTimeSeriesChart({ taskId }: FeatureTimeSeriesChartProps) {
  const { explorerSelectedFeatures, explorerSelectedFeature, setExplorerSelectedFeatures } = useFeatureFactoryStore();
  const { browseData, browseFeatures } = useFeatureFactory();
  const [options, setOptions] = useState<string[]>([]);
  const [filteredOptions, setFilteredOptions] = useState<string[]>([]);
  const [rows, setRows] = useState<Array<Record<string, string | number | null>>>([]);
  const [showCloseOverlay, setShowCloseOverlay] = useState(false);
  const [showRollingBand, setShowRollingBand] = useState(true);
  const [rollingWindow, setRollingWindow] = useState(ROLLING_WINDOW_DEFAULT);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // X Brush 可視範圍 → 驅動 Y 軸自動 fit
  const [brushIndices, setBrushIndices] = useState<{ start: number; end: number } | null>(null);
  // 遞增 key 讓 Brush 強制重新掛載（雙擊重置用）
  const [brushKey, setBrushKey] = useState(0);

  useEffect(() => {
    let active = true;
    browseFeatures(taskId, { offset: 0, limit: 5000, sortBy: 'name', sortOrder: 'asc', detailLevel: 'table' })
      .then((resp) => {
        if (!active) return;
        setOptions(resp.features.map((item) => item.name));
      })
      .catch(() => {
        if (!active) return;
        setOptions([]);
      });

    return () => {
      active = false;
    };
  }, [browseFeatures, taskId]);

  const selected = useMemo(() => {
    const uniq = Array.from(new Set(explorerSelectedFeatures)).slice(0, 5);
    if (uniq.length > 0) return uniq;
    if (explorerSelectedFeature) return [explorerSelectedFeature];
    const candidate = filteredOptions.length > 0 ? filteredOptions[0] : options[0];
    if (candidate) return [candidate];
    return [];
  }, [explorerSelectedFeatures, explorerSelectedFeature, filteredOptions, options]);

  useEffect(() => {
    if (selected.length === 0) {
      setRows([]);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);
    browseData(taskId, selected, 0, 3000)
      .then((resp) => {
        if (!active) return;
        setRows(resp.rows as Array<Record<string, string | number | null>>);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : '載入時間序列失敗');
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [browseData, taskId, selected]);

  /**
   * Rolling mean ± 1σ band（僅對第一條特徵）
   * 使用 stackId 疊加方式：
   *   _roll_lower      = mean - std （透明基底，把帶抬到正確 Y 位置）
   *   _roll_band_height = 2 * std    （帶的高度，填色）
   * 這樣 Area stack 後恰好覆蓋 [mean-σ, mean+σ]，不影響下方圖層。
   */
  const chartData = useMemo(() => {
    if (rows.length === 0) return rows;
    const primaryFeature = selected[0];
    if (!primaryFeature || !showRollingBand) return rows;

    const values = rows.map((r) => (typeof r[primaryFeature] === 'number' ? (r[primaryFeature] as number) : null));

    return rows.map((row, i) => {
      const start = Math.max(0, i - rollingWindow + 1);
      const slice = values.slice(start, i + 1).filter((v): v is number => v !== null);
      if (slice.length < 3) return row;

      const mean = slice.reduce((a, b) => a + b, 0) / slice.length;
      const std = Math.sqrt(slice.reduce((a, b) => a + (b - mean) ** 2, 0) / slice.length);
      return {
        ...row,
        _roll_upper: mean + std,  // 上緣（絕對值）
        _roll_lower: mean - std,  // 下緣（絕對值）
        _roll_mean: mean,         // tooltip 用
      };
    });
  }, [rows, selected, showRollingBand, rollingWindow]);

  /**
   * Y 軸 domain：依 Brush 可視窗口內的資料自動 fit，加 5% padding
   * 雙擊圖表 → brushIndices = null → 回到全量 auto domain
   */
  const { yLeftDomain, yRightDomain } = useMemo(() => {
    const slice =
      brushIndices && chartData.length > 0
        ? chartData.slice(brushIndices.start, brushIndices.end + 1)
        : chartData;
    if (slice.length === 0) return { yLeftDomain: undefined, yRightDomain: undefined };

    // left axis：第一條特徵 + rolling band
    let lMin = Infinity, lMax = -Infinity;
    const leftFeat = selected[0];
    slice.forEach((row) => {
      if (leftFeat) {
        const v = row[leftFeat];
        if (typeof v === 'number') { lMin = Math.min(lMin, v); lMax = Math.max(lMax, v); }
      }
      if (showRollingBand) {
        const lower = row['_roll_lower'];
        const upper = row['_roll_upper'];
        if (typeof lower === 'number') lMin = Math.min(lMin, lower);
        if (typeof upper === 'number') lMax = Math.max(lMax, upper);
      }
    });

    // right axis：其餘特徵 + close overlay
    let rMin = Infinity, rMax = -Infinity;
    selected.slice(1).forEach((feat) => {
      slice.forEach((row) => {
        const v = row[feat];
        if (typeof v === 'number') { rMin = Math.min(rMin, v); rMax = Math.max(rMax, v); }
      });
    });
    if (showCloseOverlay) {
      slice.forEach((row) => {
        const v = row['close'];
        if (typeof v === 'number') { rMin = Math.min(rMin, v); rMax = Math.max(rMax, v); }
      });
    }

    const pad = (min: number, max: number) => (max - min) * 0.05;
    return {
      yLeftDomain:
        lMax !== -Infinity
          ? ([lMin - pad(lMin, lMax), lMax + pad(lMin, lMax)] as [number, number])
          : undefined,
      yRightDomain:
        rMax !== -Infinity
          ? ([rMin - pad(rMin, rMax), rMax + pad(rMin, rMax)] as [number, number])
          : undefined,
    };
  }, [chartData, brushIndices, selected, showRollingBand, showCloseOverlay]);

  const handleDoubleClick = () => {
    setBrushIndices(null);
    setBrushKey((k) => k + 1);
  };

  const toggleFeature = (feature: string) => {    const current = new Set(explorerSelectedFeatures);
    if (current.has(feature)) {
      current.delete(feature);
      setExplorerSelectedFeatures(Array.from(current));
      return;
    }
    if (current.size >= 5) return;
    current.add(feature);
    setExplorerSelectedFeatures(Array.from(current));
  };

  return (
    <div className="glass-panel rounded-2xl p-4 space-y-3">
      {/* 標題列：標題 + 清除按鈕 */}
      <div className="flex items-center justify-between gap-2">
        <div className="text-sm text-slate-300">
          Feature Time Series
          <span className="ml-2 text-xs text-slate-500">(最多 5 條，筆數：{options.length.toLocaleString()})</span>
        </div>
        {explorerSelectedFeatures.length > 0 && (
          <button
            onClick={() => setExplorerSelectedFeatures([])}
            className="text-xs px-2.5 py-1 rounded border border-rose-400/50 bg-rose-400/10 text-rose-300 hover:bg-rose-400/20 font-medium"
            title="取消所有已選特徵"
          >
            ✕ 清除選取（{explorerSelectedFeatures.length}）
          </button>
        )}
      </div>

      {/* 控制列 */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Rolling ±1σ 控制組 */}
        <label className="text-xs text-slate-300 inline-flex items-center gap-1">
          <input
            type="checkbox"
            checked={showRollingBand}
            onChange={(e) => setShowRollingBand(e.target.checked)}
          />
          Rolling ±1σ
        </label>
        {showRollingBand && (
          <div className="inline-flex items-center gap-1">
            <span className="text-xs text-slate-400">W=</span>
            <input
              type="number"
              min={ROLLING_WINDOW_MIN}
              max={ROLLING_WINDOW_MAX}
              value={rollingWindow}
              onChange={(e) => {
                const v = Math.min(ROLLING_WINDOW_MAX, Math.max(ROLLING_WINDOW_MIN, Number(e.target.value)));
                setRollingWindow(v);
              }}
              className="w-14 text-xs text-center rounded border border-white/10 bg-slate-800 text-slate-200 px-1 py-0.5"
            />
            <input
              type="range"
              min={ROLLING_WINDOW_MIN}
              max={ROLLING_WINDOW_MAX}
              value={rollingWindow}
              onChange={(e) => setRollingWindow(Number(e.target.value))}
              className="w-20 accent-cyan-400"
            />
          </div>
        )}

        <label className="text-xs text-slate-300 inline-flex items-center gap-1">
          <input
            type="checkbox"
            checked={showCloseOverlay}
            onChange={(e) => setShowCloseOverlay(e.target.checked)}
          />
          Close Overlay
        </label>
        <button
          onClick={() => exportChartToPNG('feature-timeseries-chart', 'feature_timeseries', taskId)}
          className="ml-auto text-xs px-2 py-1 rounded border border-white/10 text-slate-200"
        >
          匯出 PNG
        </button>
      </div>

      <FeatureNameSegmentFilter features={options} onFilteredFeaturesChange={setFilteredOptions} />

      <div className="flex flex-wrap gap-2 max-h-28 overflow-auto">
        {/* 已選但不在前 500 可見清單裡的特徵：固定置頂，確保可點選取消 */}
        {explorerSelectedFeatures
          .filter((name) => !filteredOptions.slice(0, 500).includes(name))
          .map((name) => (
            <button
              key={`pinned-${name}`}
              onClick={() => toggleFeature(name)}
              title={`${name}（點擊取消選取）`}
              className="text-xs px-2 py-1 rounded-full border bg-cyan-400/20 border-cyan-300/40 text-cyan-200 ring-1 ring-cyan-300/30"
            >
              {name} ✕
            </button>
          ))}
        {/* 篩選後的選項（前 500）*/}
        {filteredOptions.slice(0, 500).map((name) => {
          const active = selected.includes(name);
          return (
            <button
              key={name}
              onClick={() => toggleFeature(name)}
              className={`text-xs px-2 py-1 rounded-full border ${
                active ? 'bg-cyan-400/20 border-cyan-300/40 text-cyan-200' : 'border-white/10 text-slate-300'
              }`}
            >
              {name}
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="text-xs text-slate-400">載入中...</div>
      ) : error ? (
        <div className="text-xs text-rose-300">{error}</div>
      ) : rows.length === 0 ? (
        <div className="text-xs text-slate-400">尚無資料。</div>
      ) : (
        <div
          id="feature-timeseries-chart"
          className="h-[420px] relative bg-[#0d1117] rounded-lg overflow-hidden"
          onDoubleClick={handleDoubleClick}
          title="雙擊圖表可重置縮放"
        >
          <span className="absolute top-1 right-2 text-[10px] text-slate-600 select-none pointer-events-none">
            雙擊重置
          </span>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={formatTimestamp}
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                interval={calcXInterval(chartData.length)}
              />
              <YAxis
                yAxisId="left"
                domain={yLeftDomain ?? ['auto', 'auto']}
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                tickFormatter={(v: number) => {
                  if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(1)}k`;
                  return v.toFixed(2);
                }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                domain={yRightDomain ?? ['auto', 'auto']}
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                tickFormatter={(v: number) => {
                  if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(1)}k`;
                  return v.toFixed(2);
                }}
              />
              <Tooltip content={<SeriesTooltip selected={selected} showBand={showRollingBand} />} />
              <Legend
                formatter={(value) => {
                  if (value === '_roll_lower' || value === '_roll_band_height') return null;
                  return <span className="text-xs text-slate-300">{value}</span>;
                }}
              />

              {/*
               * Rolling ±1σ Band — 夾心法（無 stackId）
               *
               * Recharts stackId 會強制 Y 軸基準從 0，即使設了 explicit domain 也無效。
               * 夾心法：
               *   Step1 Upper Area (先宣告 = 在下層): 0 → mean+σ，填淡綠色
               *   Step2 Lower Area (後宣告 = 在上層): 0 → mean-σ，填與 chart bg 相同的深色
               *         → 蓋住 mean-σ 以下的綠色，只剩 [mean-σ, mean+σ] 帶狀可見
               *   explicit domain + ComposedChart clipPath 確保 Y 軸不從 0 開始
               */}
              {showRollingBand && selected.length > 0 && (
                <Area
                  yAxisId="left"
                  type="monotone"
                  dataKey="_roll_upper"
                  stroke="rgba(52,211,153,0.5)"
                  strokeDasharray="4 3"
                  strokeWidth={1}
                  fill="rgba(52,211,153,0.22)"
                  dot={false}
                  isAnimationActive={false}
                  legendType="none"
                  name="_roll_upper"
                />
              )}
              {showRollingBand && selected.length > 0 && (
                <Area
                  yAxisId="left"
                  type="monotone"
                  dataKey="_roll_lower"
                  stroke="rgba(52,211,153,0.5)"
                  strokeDasharray="4 3"
                  strokeWidth={1}
                  fill="#0d1117"      // 與 chart container bg-[#0d1117] 相同 → 遮蓋下方綠色
                  fillOpacity={1}
                  dot={false}
                  isAnimationActive={false}
                  legendType="none"
                  name="_roll_lower"
                />
              )}

              {selected.map((feature, idx) => (
                <Line
                  key={feature}
                  yAxisId={idx === 0 ? 'left' : 'right'}
                  type="monotone"
                  dataKey={feature}
                  stroke={COLORS[idx % COLORS.length]}
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
              ))}
              {showCloseOverlay && chartData.length > 0 && 'close' in chartData[0] && (
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="close"
                  stroke="#f8fafc"
                  dot={false}
                  strokeDasharray="6 3"
                  isAnimationActive={false}
                />
              )}
              <Brush
                key={brushKey}
                dataKey="timestamp"
                height={24}
                stroke="#475569"
                fill="#1e293b"
                travellerWidth={8}
                tickFormatter={formatTimestamp}
                onChange={(e: { startIndex?: number; endIndex?: number }) => {
                  const s = e.startIndex ?? 0;
                  const en = e.endIndex ?? Math.max(0, chartData.length - 1);
                  setBrushIndices({ start: s, end: en });
                }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

function SeriesTooltip({
  active,
  payload,
  label,
  selected,
  showBand,
}: {
  active?: boolean;
  payload?: Array<{ name?: string; value?: number }>;
  label?: string;
  selected: string[];
  showBand?: boolean;
}) {
  if (!active || !payload || payload.length === 0) return null;

  // 從 payload 取 rolling band 資訊
  const rollLower = payload.find((p) => p.name === '_roll_lower')?.value;
  const rollUpper = payload.find((p) => p.name === '_roll_upper')?.value;

  return (
    <div className="rounded-lg border border-white/10 bg-slate-900/90 px-3 py-2 text-xs text-slate-100 space-y-1">
      <div className="text-slate-400 font-mono">{label || '-'}</div>
      {selected.map((feature) => {
        const item = payload.find((entry) => entry.name === feature);
        return (
          <div key={feature} className="flex justify-between gap-4">
            <span className="text-slate-300">{feature}</span>
            <span className="font-mono tabular-nums">
              {typeof item?.value === 'number' ? item.value.toFixed(6) : '-'}
            </span>
          </div>
        );
      })}
      {showBand && rollLower !== undefined && rollUpper !== undefined && (
        <div className="border-t border-white/10 pt-1 mt-1 space-y-0.5 text-slate-400">
          <div className="flex justify-between gap-4">
            <span>+1σ 上緣</span>
            <span className="font-mono tabular-nums text-emerald-400">{rollUpper.toFixed(6)}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span>−1σ 下緣</span>
            <span className="font-mono tabular-nums text-emerald-400">{rollLower.toFixed(6)}</span>
          </div>
        </div>
      )}
    </div>
  );
}

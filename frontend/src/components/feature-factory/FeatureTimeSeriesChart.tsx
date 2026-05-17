'use client';

import { useEffect, useMemo, useState, useRef, useCallback } from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
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
const FEATURE_NAME_LIMIT = 1000000;
/** 主圖每次最多渲染的資料點數（確保平移流暢）*/
const DISPLAY_LIMIT = 1000;

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

/** Y 軸 tick 格式：k suffix / 科學記號 / 一般兩位小數 */
function formatYAxis(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1000) return `${(v / 1000).toFixed(1)}k`;
  if (abs > 0 && abs < 0.001) return v.toExponential(2); // e.g. 1.23e-7
  return v.toFixed(2);
}

/** 依資料筆數決定 X 軸 interval，目標約 10~14 個 tick */
function calcXInterval(dataLen: number): number {
  if (dataLen <= 0) return 0;
  return Math.max(1, Math.floor(dataLen / 12));
}

export default function FeatureTimeSeriesChart({ taskId }: FeatureTimeSeriesChartProps) {
  const { explorerSelectedFeatures, explorerSelectedFeature, setExplorerSelectedFeatures } = useFeatureFactoryStore();
  const sharedFeatureNames = useFeatureFactoryStore((state) => state.explorerFeatureNamesByTask[taskId]);
  const { browseData, browseFeatures } = useFeatureFactory();
  const [options, setOptions] = useState<string[]>([]);
  const [filteredOptions, setFilteredOptions] = useState<string[]>([]);
  const [rows, setRows] = useState<Array<Record<string, string | number | null>>>([]);
  const [showCloseOverlay, setShowCloseOverlay] = useState(false);
  const [showRollingBand, setShowRollingBand] = useState(true);
  const [rollingWindow, setRollingWindow] = useState(ROLLING_WINDOW_DEFAULT);
  // rawWindow 讓輸入框可自由鍵入中間狀態（如 "2" → "20"），onBlur 才夾值
  const [rawWindow, setRawWindow] = useState(String(ROLLING_WINDOW_DEFAULT));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // 受控可見範圍（絕對 index，對應 chartData）
  const [brushRange, setBrushRange] = useState<{ start: number; end: number } | null>(null);
  // 拖曳平移用：記錄按下時的 clientX + brushRange 快照
  const dragRef = useRef<{ x: number; range: { start: number; end: number } } | null>(null);
  // chart div ref：掛載 non-passive wheel listener，阻止頁面捲動
  const chartDivRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    if (sharedFeatureNames) {
      setOptions(sharedFeatureNames);
      return;
    }

    browseFeatures(taskId, { offset: 0, limit: FEATURE_NAME_LIMIT, sortBy: 'name', sortOrder: 'asc', detailLevel: 'names' })
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
  }, [browseFeatures, taskId, sharedFeatureNames]);

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
    browseData(taskId, selected, 0, 100000)
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
        _roll_upper: mean + std,        // 上緣（絕對值，給虛線 Line 用）
        _roll_lower: mean - std,        // 下緣（絕對值，Area stackId 透明基底）
        _roll_band_height: 2 * std,     // 帶的高度（Area stackId 填色層）
        _roll_outer_lower: mean - 2 * std,     // ±2σ 外圈帶：下環基底（mean-2σ）
        _roll_outer_height: std,               // ±2σ 外圈帶：下環高度（mean-2σ → mean-σ）
        _roll_outer_top_base: mean + std,      // ±2σ 外圈帶：上環基底（mean+σ）
        _roll_outer_top_height: std,           // ±2σ 外圈帶：上環高度（mean+σ → mean+2σ）
        _roll_outer_upper: mean + 2 * std,     // +2σ 上緣線
        _roll_mean: mean,               // tooltip 用
      };
    });
  }, [rows, selected, showRollingBand, rollingWindow]);

  /**
   * 可見資料：依 brushRange 切片 + 均勻下揇至 DISPLAY_LIMIT 點
   * 主圖永遠只渲染 ≤ DISPLAY_LIMIT 個 SVG 點，平移縮放重繪速度發提
   */
  const visibleData = useMemo(() => {
    if (chartData.length === 0) return chartData;
    const start = brushRange?.start ?? 0;
    const end = brushRange?.end ?? chartData.length - 1;
    const slice = chartData.slice(start, end + 1);
    if (slice.length <= DISPLAY_LIMIT) return slice;
    // 均勻下揇：保留首尾點，中間均勻取樣
    const step = (slice.length - 1) / (DISPLAY_LIMIT - 1);
    return Array.from({ length: DISPLAY_LIMIT }, (_, i) =>
      slice[Math.min(slice.length - 1, Math.round(i * step))],
    );
  }, [chartData, brushRange]);
  const { yLeftDomain, yRightDomain } = useMemo(() => {
    if (visibleData.length === 0) return { yLeftDomain: undefined, yRightDomain: undefined };
    const slice = visibleData;

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
  }, [visibleData, selected, showRollingBand, showCloseOverlay]);

  const handleDoubleClick = () => {
    setBrushRange(null);
  };

  /** 滾輪縮放：以當前可見中心點為基準，向內/向外縮放 */
  /* 掛載 { passive: false } 原生 wheel 監聽器，確保 preventDefault() 生效 */
  useEffect(() => {
    const el = chartDivRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      if (chartData.length === 0) return;
      const total = chartData.length;
      const cur = brushRange ?? { start: 0, end: total - 1 };
      const span = cur.end - cur.start;
      const center = (cur.start + cur.end) / 2;
      const factor = e.deltaY > 0 ? 1.25 : 0.8;
      const newSpan = Math.round(Math.max(20, Math.min(total - 1, span * factor)));
      const newStart = Math.max(0, Math.round(center - newSpan / 2));
      const newEnd = Math.min(total - 1, newStart + newSpan);
      const finalStart = newEnd === total - 1 ? Math.max(0, newEnd - newSpan) : newStart;
      setBrushRange({ start: finalStart, end: newEnd });
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [chartData.length, brushRange]);

  const handleWheel = useCallback(
    (e: React.WheelEvent<HTMLDivElement>) => {
      // 由原生 listener 處理，此處保留以防 ref 尚未掛載
      e.preventDefault();
      if (chartData.length === 0) return;
      const total = chartData.length;
      const cur = brushRange ?? { start: 0, end: total - 1 };
      const span = cur.end - cur.start;
      const center = (cur.start + cur.end) / 2;
      // deltaY > 0 滾輪向下 = 縮小（看更多），< 0 = 放大（看更少）
      const factor = e.deltaY > 0 ? 1.25 : 0.8;
      const newSpan = Math.round(Math.max(20, Math.min(total - 1, span * factor)));
      const newStart = Math.max(0, Math.round(center - newSpan / 2));
      const newEnd = Math.min(total - 1, newStart + newSpan);
      const finalStart = newEnd === total - 1 ? Math.max(0, newEnd - newSpan) : newStart;
      setBrushRange({ start: finalStart, end: newEnd });
    },
    [chartData.length, brushRange],
  );

  /** 拖曳平移：mousedown 記錄快照，mousemove 計算偏移，mouseup 釋放 */
  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (chartData.length === 0 || e.button !== 0) return;
      const cur = brushRange ?? { start: 0, end: chartData.length - 1 };
      dragRef.current = { x: e.clientX, range: { ...cur } };
    },
    [chartData.length, brushRange],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!dragRef.current) return;
      const total = chartData.length;
      const { x, range } = dragRef.current;
      const span = range.end - range.start;
      const chartWidth = e.currentTarget.clientWidth;
      // 向左拖 = 時間前進（正偏移）
      const shift = Math.round(((dragRef.current.x - e.clientX) / chartWidth) * span);
      if (Math.abs(shift) < 1) return;
      let newStart = range.start + shift;
      let newEnd = range.end + shift;
      if (newStart < 0) { newEnd = span; newStart = 0; }
      if (newEnd > total - 1) { newEnd = total - 1; newStart = total - 1 - span; }
      setBrushRange({ start: newStart, end: newEnd });
    },
    [chartData.length],
  );

  const handleMouseUp = useCallback(() => {
    dragRef.current = null;
  }, []);

  /** Range Selector：跳到最近 N 個月或全量，透過 remount Brush 套用初始位置 */
  const jumpToRange = (months: number | null) => {
    if (!months || chartData.length === 0) {
      setBrushRange({ start: 0, end: Math.max(0, chartData.length - 1) });
      return;
    }
    const endIdx = chartData.length - 1;
    const endTs = chartData[endIdx]?.timestamp;
    if (!endTs) return;
    const cutoff = new Date(endTs as string | number);
    cutoff.setMonth(cutoff.getMonth() - months);
    const cutoffMs = cutoff.getTime();
    let startIdx = chartData.findIndex(
      (r) => new Date(r.timestamp as string | number).getTime() >= cutoffMs,
    );
    if (startIdx < 0) startIdx = 0;
    setBrushRange({ start: startIdx, end: endIdx });
  };

  const missingSummaries = useMemo(() => {
    if (rows.length === 0) return [];
    return selected.map((feature) => {
      const validCount = rows.reduce((count, row) => (typeof row[feature] === 'number' ? count + 1 : count), 0);
      const missingCount = rows.length - validCount;
      return {
        feature,
        validCount,
        missingCount,
        missingRatio: rows.length > 0 ? missingCount / rows.length : 0,
      };
    }).filter((item) => item.missingCount > 0);
  }, [rows, selected]);

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
              value={rawWindow}
              onChange={(e) => setRawWindow(e.target.value)}
              onBlur={(e) => {
                const parsed = parseInt(e.target.value, 10);
                const clamped = isNaN(parsed)
                  ? ROLLING_WINDOW_DEFAULT
                  : Math.min(ROLLING_WINDOW_MAX, Math.max(ROLLING_WINDOW_MIN, parsed));
                setRollingWindow(clamped);
                setRawWindow(String(clamped));
              }}
              className="w-14 text-xs text-center rounded border border-white/10 bg-slate-800 text-slate-200 px-1 py-0.5"
            />
            <input
              type="range"
              min={ROLLING_WINDOW_MIN}
              max={ROLLING_WINDOW_MAX}
              value={rollingWindow}
              onChange={(e) => {
                const v = Number(e.target.value);
                setRollingWindow(v);
                setRawWindow(String(v));
              }}
              className="w-20 accent-cyan-400"
            />
          </div>
        )}

        {/* Range Selector */}
        <div className="inline-flex items-center gap-0.5">
          {([1, 3, 6, null] as Array<number | null>).map((months) => (
            <button
              key={months ?? 'all'}
              onClick={() => jumpToRange(months)}
              className="text-[10px] px-1.5 py-0.5 rounded border border-white/10 text-slate-400 hover:text-slate-200 hover:border-white/20"
            >
              {months ? `${months}M` : 'ALL'}
            </button>
          ))}
        </div>

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
      <div className="flex gap-3 min-w-0">
        <div className="w-72 shrink-0">
          <div className="max-h-[540px] overflow-y-auto rounded border border-white/5 bg-black/20 py-1">
            {/* 已選但不在前 500 可見清單裡的特徵：固定置頂，確保可點選取消 */}
            {explorerSelectedFeatures
              .filter((name) => !filteredOptions.slice(0, 500).includes(name))
              .map((name) => (
                <button
                  key={`pinned-${name}`}
                  onClick={() => toggleFeature(name)}
                  title={name}
                  className="w-full text-left truncate text-xs px-2 py-1 rounded bg-cyan-400/20 text-cyan-200"
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
                  title={name}
                  className={`w-full text-left truncate text-xs px-2 py-1 rounded ${
                    active ? 'bg-cyan-400/20 text-cyan-200' : 'text-slate-300 hover:bg-white/5'
                  }`}
                >
                  {name}
                </button>
              );
            })}
          </div>
        </div>
        <div className="flex-1 min-w-0 flex flex-col gap-2">
          {missingSummaries.length > 0 && (
            <div className="rounded-lg border border-amber-300/20 bg-amber-400/10 px-3 py-2 text-xs text-amber-100">
              圖線中斷代表原始特徵值為 NaN/缺值，系統不會插值以免扭曲時間序列。{missingSummaries.slice(0, 3).map((item) => (
                <span key={item.feature} className="ml-2 font-mono">
                  {item.feature}: {(item.missingRatio * 100).toFixed(1)}% 缺值
                </span>
              ))}
            </div>
          )}
          {loading ? (
            <div className="text-xs text-slate-400">載入中...</div>
          ) : error ? (
            <div className="text-xs text-rose-300">{error}</div>
          ) : rows.length === 0 ? (
            <div className="text-xs text-slate-400">尚無資料。</div>
          ) : (
            <div
              ref={chartDivRef}
              id="feature-timeseries-chart"
              className="h-[680px] relative bg-[#0d1117] rounded-lg overflow-hidden cursor-grab active:cursor-grabbing"
              onDoubleClick={handleDoubleClick}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              title="滾輪縮放 · 拖曳平移 · 雙擊重置"
            >
          <span className="absolute top-1 right-2 text-[10px] text-slate-600 select-none pointer-events-none">
            滾輪縮放 · 拖曳平移 · 雙擊重置
          </span>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={visibleData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={formatTimestamp}
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                interval={calcXInterval(visibleData.length)}
              />
              <YAxis
                yAxisId="left"
                domain={yLeftDomain ?? ['auto', 'auto']}
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                tickFormatter={formatYAxis}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                domain={yRightDomain ?? ['auto', 'auto']}
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                tickFormatter={formatYAxis}
              />
              <Tooltip
                cursor={{ stroke: '#64748b', strokeWidth: 1 }}
                content={<SeriesTooltip selected={selected} showBand={showRollingBand} />}
              />
              <Legend
                formatter={(value) => {
                  if (['_roll_lower', '_roll_band_height', '_roll_outer_lower', '_roll_outer_height', '_roll_outer_top_base', '_roll_outer_top_height', '_roll_outer_upper'].includes(value)) return null;
                  return <span className="text-xs text-slate-300">{value}</span>;
                }}
              />

                            {/* ±2σ 外圈帶：分上下兩段環形（只填 ±1σ→±2σ，不覆蓋內圈） */}
              {/* 下環：mean-2σ → mean-σ */}
              {showRollingBand && selected.length > 0 && (
                <Area yAxisId="left" type="monotone" dataKey="_roll_outer_lower"
                  stackId="band_ob" fill="none" stroke="none"
                  isAnimationActive={false} legendType="none" connectNulls={false} />
              )}
              {showRollingBand && selected.length > 0 && (
                <Area yAxisId="left" type="monotone" dataKey="_roll_outer_height"
                  stackId="band_ob" fill="rgba(220, 138, 75, 0.3)" stroke="none"
                  isAnimationActive={false} legendType="none" connectNulls={false} />
              )}
              {/* 上環：mean+σ → mean+2σ */}
              {showRollingBand && selected.length > 0 && (
                <Area yAxisId="left" type="monotone" dataKey="_roll_outer_top_base"
                  stackId="band_ot" fill="none" stroke="none"
                  isAnimationActive={false} legendType="none" connectNulls={false} />
              )}
              {showRollingBand && selected.length > 0 && (
                <Area yAxisId="left" type="monotone" dataKey="_roll_outer_top_height"
                  stackId="band_ot" fill="rgba(220, 138, 75, 0.3)" stroke="none"
                  isAnimationActive={false} legendType="none" connectNulls={false} />
              )}
              {/* ±2σ 邊界虛線 */}
              {showRollingBand && selected.length > 0 && (
                <Line yAxisId="left" type="monotone" dataKey="_roll_outer_upper"
                  stroke="rgba(220, 138, 75,0.50)" strokeDasharray="2 4" strokeWidth={1}
                  dot={false} isAnimationActive={false} legendType="none" name="_roll_outer_upper" />
              )}
              {showRollingBand && selected.length > 0 && (
                <Line yAxisId="left" type="monotone" dataKey="_roll_outer_lower"
                  stroke="rgba(220, 138, 75,0.50)" strokeDasharray="2 4" strokeWidth={1}
                  dot={false} isAnimationActive={false} legendType="none" name="_roll_outer_lower_line" />
              )}
              {/* ±1σ 內圈帶：兩層 Area stackId 疊加（透明基底 + 填色層），上下邊界用虛線 Line */}
              {showRollingBand && selected.length > 0 && (
                <Area
                  yAxisId="left"
                  type="monotone"
                  dataKey="_roll_lower"
                  stackId="band"
                  fill="none"
                  stroke="none"
                  isAnimationActive={false}
                  legendType="none"
                  connectNulls={false}
                />
              )}
              {showRollingBand && selected.length > 0 && (
                <Area
                  yAxisId="left"
                  type="monotone"
                  dataKey="_roll_band_height"
                  stackId="band"
                  fill="rgba(52,211,153,0.30)"
                  stroke="none"
                  isAnimationActive={false}
                  legendType="none"
                  connectNulls={false}
                />
              )}
              {showRollingBand && selected.length > 0 && (
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="_roll_upper"
                  stroke="rgba(52,211,153,0.75)"
                  strokeDasharray="4 3"
                  strokeWidth={1}
                  dot={false}
                  isAnimationActive={false}
                  legendType="none"
                  name="_roll_upper"
                />
              )}
              {showRollingBand && selected.length > 0 && (
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="_roll_lower"
                  stroke="rgba(52,211,153,0.75)"
                  strokeDasharray="4 3"
                  strokeWidth={1}
                  dot={false}
                  isAnimationActive={false}
                  legendType="none"
                  name="_roll_lower"
                />
              )}

              {/* 零基準線 */}
              <ReferenceLine yAxisId="left" y={0} stroke="#475569" strokeDasharray="4 2" strokeWidth={1} />

              {selected.map((feature, idx) => (
                <Line
                  key={feature}
                  yAxisId={idx === 0 ? 'left' : 'right'}
                  type="monotone"
                  dataKey={feature}
                  stroke={COLORS[idx % COLORS.length]}
                  strokeWidth={1.5}
                  dot={false}
                  connectNulls={false}
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
                dataKey="timestamp"
                height={0}
                stroke="transparent"
                fill="transparent"
                travellerWidth={0}
                startIndex={0}
                endIndex={Math.max(0, visibleData.length - 1)}
                tickFormatter={() => ''}
              />
              {/* 小型時間隄尺列（顯示可見範圍在全量資料中的位置）*/}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
          )}
        </div>
      </div>
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

  // 從上下緣反推 mean 和 std（不需額外傳入 _roll_mean）
  const rollStd =
    showBand && rollUpper !== undefined && rollLower !== undefined
      ? (rollUpper - rollLower) / 2
      : undefined;
  const rollMean =
    showBand && rollUpper !== undefined && rollLower !== undefined
      ? (rollUpper + rollLower) / 2
      : undefined;

  return (
    <div className="rounded-lg border border-white/10 bg-slate-900/90 px-3 py-2 text-xs text-slate-100 space-y-1 max-w-xs">
      <div className="text-slate-400 font-mono">{label || '-'}</div>
      {selected.map((feature) => {
        const item = payload.find((entry) => entry.name === feature);
        const val = item?.value;
        const z =
          typeof val === 'number' && rollStd !== undefined && rollStd > 0 && rollMean !== undefined
            ? (val - rollMean) / rollStd
            : null;
        return (
          <div key={feature} className="flex justify-between gap-4">
            <span className="text-slate-300 truncate max-w-[160px]" title={feature}>{feature}</span>
            <span className="font-mono tabular-nums whitespace-nowrap">
              {typeof val === 'number' ? val.toFixed(6) : '-'}
              {z !== null && (
                <span className={`ml-1.5 text-[10px] ${Math.abs(z) > 2 ? 'text-amber-400' : 'text-slate-500'}`}>
                  ({z >= 0 ? '+' : ''}{z.toFixed(1)}σ)
                </span>
              )}
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

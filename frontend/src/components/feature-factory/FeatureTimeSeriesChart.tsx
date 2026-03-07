'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
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

export default function FeatureTimeSeriesChart({ taskId }: FeatureTimeSeriesChartProps) {
  const { explorerSelectedFeatures, explorerSelectedFeature, setExplorerSelectedFeatures } = useFeatureFactoryStore();
  const { browseData, browseFeatures } = useFeatureFactory();
  const [options, setOptions] = useState<string[]>([]);
  const [filteredOptions, setFilteredOptions] = useState<string[]>([]);
  const [rows, setRows] = useState<Array<Record<string, string | number | null>>>([]);
  const [showCloseOverlay, setShowCloseOverlay] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    browseFeatures(taskId, { offset: 0, limit: 200, sortBy: 'name', sortOrder: 'asc' })
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
    browseData(taskId, selected, 0, 500)
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

  const toggleFeature = (feature: string) => {
    const current = new Set(explorerSelectedFeatures);
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
      <div className="flex items-center gap-2">
        <div className="text-sm text-slate-300">Feature Time Series（最多 5 條）</div>
        <label className="ml-auto text-xs text-slate-300 inline-flex items-center gap-1">
          <input
            type="checkbox"
            checked={showCloseOverlay}
            onChange={(e) => setShowCloseOverlay(e.target.checked)}
          />
          Close Overlay
        </label>
        <button
          onClick={() => exportChartToPNG('feature-timeseries-chart', 'feature_timeseries', taskId)}
          className="text-xs px-2 py-1 rounded border border-white/10 text-slate-200"
        >
          匯出 PNG
        </button>
      </div>

      <FeatureNameSegmentFilter features={options} onFilteredFeaturesChange={setFilteredOptions} />

      <div className="flex flex-wrap gap-2 max-h-28 overflow-auto">
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
        <div id="feature-timeseries-chart" className="h-[420px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rows}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="timestamp" hide />
              <YAxis yAxisId="left" />
              <YAxis yAxisId="right" orientation="right" />
              <Tooltip content={<SeriesTooltip selected={selected} />} />
              <Legend />
              {selected.map((feature, idx) => (
                <Line
                  key={feature}
                  yAxisId={idx === 0 ? 'left' : 'right'}
                  type="monotone"
                  dataKey={feature}
                  stroke={COLORS[idx % COLORS.length]}
                  dot={false}
                  isAnimationActive={false}
                />
              ))}
              {showCloseOverlay && rows.length > 0 && 'close' in rows[0] && (
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
              <Brush dataKey="timestamp" height={20} stroke="#94a3b8" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

function SeriesTooltip({ active, payload, label, selected }: { active?: boolean; payload?: Array<{ name?: string; value?: number }>; label?: string; selected: string[] }) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-lg border border-white/10 bg-slate-900/90 px-3 py-2 text-xs text-slate-100">
      <div className="text-slate-300 mb-1">{label || '-'}</div>
      {selected.map((feature) => {
        const item = payload.find((entry) => entry.name === feature);
        return (
          <div key={feature} className="flex justify-between gap-3">
            <span>{feature}</span>
            <span>{typeof item?.value === 'number' ? item.value.toFixed(6) : '-'}</span>
          </div>
        );
      })}
    </div>
  );
}

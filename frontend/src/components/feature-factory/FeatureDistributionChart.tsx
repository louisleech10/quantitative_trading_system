'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import { exportChartToPNG } from '@/lib/exportUtils';
import FeatureNameSegmentFilter from '@/components/feature-factory/FeatureNameSegmentFilter';

interface FeatureDistributionChartProps {
  taskId: string;
}

export default function FeatureDistributionChart({ taskId }: FeatureDistributionChartProps) {
  const { explorerSelectedFeature, setExplorerActiveTab } = useFeatureFactoryStore();
  const { browseDistribution, browseFeatures } = useFeatureFactory();
  const [feature, setFeature] = useState<string>('');
  const [featureOptions, setFeatureOptions] = useState<string[]>([]);
  const [filteredFeatureOptions, setFilteredFeatureOptions] = useState<string[]>([]);
  const [bins, setBins] = useState(50);
  const [payload, setPayload] = useState<{
    bins: number[];
    edges: number[];
    stats: Record<string, number | null | boolean>;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    browseFeatures(taskId, { offset: 0, limit: 5000, sortBy: 'name', sortOrder: 'asc', detailLevel: 'table' })
      .then((resp) => {
        if (!active) return;
        const options = resp.features.map((item) => item.name);
        setFeatureOptions(options);
        setFeature(explorerSelectedFeature || options[0] || '');
      })
      .catch(() => {
        if (!active) return;
        setFeatureOptions([]);
      });

    return () => {
      active = false;
    };
  }, [browseFeatures, taskId, explorerSelectedFeature]);

  useEffect(() => {
    if (!feature && filteredFeatureOptions.length > 0) {
      setFeature(filteredFeatureOptions[0]);
      return;
    }
    if (feature && filteredFeatureOptions.length > 0 && !filteredFeatureOptions.includes(feature)) {
      setFeature(filteredFeatureOptions[0]);
    }
  }, [feature, filteredFeatureOptions]);

  useEffect(() => {
    if (!feature) return;
    let active = true;
    setLoading(true);
    setError(null);

    browseDistribution(taskId, feature, bins)
      .then((resp) => {
        if (!active) return;
        setPayload({
          bins: resp.bins,
          edges: resp.edges,
          stats: resp.stats as unknown as Record<string, number | null | boolean>
        });
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : '載入分佈失敗');
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [browseDistribution, taskId, feature, bins]);

  const histogramData = useMemo(() => {
    if (!payload || payload.bins.length === 0 || payload.edges.length <= 1) return [];
    const mean = typeof payload.stats.mean === 'number' ? payload.stats.mean : 0;
    const std = typeof payload.stats.std === 'number' && payload.stats.std > 0 ? payload.stats.std : 1;
    const maxCount = Math.max(...payload.bins, 1);

    return payload.bins.map((count, idx) => {
      const x = payload.edges[idx];
      const density = Math.exp(-0.5 * ((x - mean) / std) ** 2) / (std * Math.sqrt(2 * Math.PI));
      return {
        x,
        count,
        normal: density * maxCount,
      };
    });
  }, [payload]);

  const qqData = useMemo(() => {
    if (!payload || payload.bins.length === 0) return [];
    const sortedBins = [...payload.bins].sort((a, b) => a - b);
    const n = sortedBins.length;
    return sortedBins.map((value, idx) => ({
      theoretical: idx / Math.max(1, n - 1),
      empirical: value,
    }));
  }, [payload]);

  const qqMax = useMemo(() => {
    if (qqData.length === 0) return 1;
    return Math.max(...qqData.map((item) => item.empirical), 1);
  }, [qqData]);

  return (
    <div id="feature-distribution-chart" className="glass-panel rounded-2xl p-4 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="text-sm text-slate-300">Distribution</div>
        <select
          value={feature}
          onChange={(e) => {
            setFeature(e.target.value);
            setExplorerActiveTab('distribution', e.target.value);
          }}
          className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-100"
        >
          {filteredFeatureOptions.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
        <div className="ml-auto text-xs text-slate-300">bins: {bins}</div>
        <input
          type="range"
          min={10}
          max={200}
          step={1}
          value={bins}
          onChange={(e) => setBins(Number(e.target.value))}
        />
        <button
          onClick={() => exportChartToPNG('feature-distribution-chart', 'feature_distribution', taskId)}
          className="text-xs px-2 py-1 rounded border border-white/10 text-slate-200"
        >
          匯出 PNG
        </button>
      </div>

      <FeatureNameSegmentFilter features={featureOptions} onFilteredFeaturesChange={setFilteredFeatureOptions} />

      {loading ? (
        <div className="text-xs text-slate-400">載入中...</div>
      ) : error ? (
        <div className="text-xs text-rose-300">{error}</div>
      ) : !payload ? (
        <div className="text-xs text-slate-400">尚無資料。</div>
      ) : (
        <>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={histogramData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="x" hide />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" fill="#60a5fa" />
                  <Line type="monotone" dataKey="normal" stroke="#f59e0b" dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="theoretical" type="number" name="theoretical" />
                  <YAxis dataKey="empirical" type="number" name="empirical" />
                  <Tooltip />
                  <ReferenceLine
                    segment={[
                      { x: 0, y: 0 },
                      { x: 1, y: qqMax },
                    ]}
                    stroke="#94a3b8"
                    strokeDasharray="4 4"
                  />
                  <Scatter data={qqData} fill="#f59e0b" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            <Stat label="Mean" value={payload.stats.mean} />
            <Stat label="Std" value={payload.stats.std} />
            <Stat label="Skew" value={payload.stats.skewness} />
            <Stat label="Kurt" value={payload.stats.kurtosis} />
            <Stat label="ADF p-value" value={payload.stats.adf_pvalue} />
            <Stat label="NaN ratio" value={payload.stats.nan_ratio} percentage />
          </div>
        </>
      )}
    </div>
  );
}

function Stat({ label, value, percentage = false }: { label: string; value: unknown; percentage?: boolean }) {
  const number = typeof value === 'number' ? value : null;
  const formatted = number === null ? '-' : percentage ? `${(number * 100).toFixed(2)}%` : number.toFixed(4);
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 px-2 py-2">
      <div className="text-slate-400">{label}</div>
      <div className="text-slate-100">{formatted}</div>
    </div>
  );
}

'use client';

import { useEffect, useMemo, useState } from 'react';
import { FeatureSummary, ExplorerTab } from '@/lib/types';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import OverviewDashboard from '@/components/feature-factory/OverviewDashboard';
import FeatureTable from '@/components/feature-factory/FeatureTable';
import FeatureTimeSeriesChart from '@/components/feature-factory/FeatureTimeSeriesChart';
import FeatureCorrelationHeatmap from '@/components/feature-factory/FeatureCorrelationHeatmap';
import FeatureDistributionChart from '@/components/feature-factory/FeatureDistributionChart';
import NaNPatternChart from '@/components/feature-factory/NaNPatternChart';

interface FeatureExplorerProps {
  taskId: string;
  /** 傳入目前任務狀態；若為 'completed' 或省略才開始載入資料 */
  taskStatus?: string | null;
}

const TABS: Array<{ key: ExplorerTab; label: string }> = [
  { key: 'overview', label: 'Overview' },
  { key: 'table', label: 'Feature Table' },
  { key: 'timeseries', label: 'Time Series' },
  { key: 'correlation', label: 'Correlation' },
  { key: 'distribution', label: 'Distribution' },
  { key: 'nan', label: 'NaN Pattern' },
];

export default function FeatureExplorer({ taskId, taskStatus }: FeatureExplorerProps) {
  const { browseSummary } = useFeatureFactory();
  // Use individual selectors to return stable primitives/references.
  // A combined object selector `(state) => ({ ... })` creates a new object every render,
  // which triggers React 18 concurrent-mode's "getSnapshot should be cached" infinite loop.
  const explorerTaskId = useFeatureFactoryStore((state) => state.explorerTaskId);
  const explorerActiveTab = useFeatureFactoryStore((state) => state.explorerActiveTab);
  const explorerSummary = useFeatureFactoryStore((state) => state.explorerSummary);
  const setExplorerTaskId = useFeatureFactoryStore((state) => state.setExplorerTaskId);
  const setExplorerActiveTab = useFeatureFactoryStore((state) => state.setExplorerActiveTab);
  const setExplorerSelectedFeatures = useFeatureFactoryStore((state) => state.setExplorerSelectedFeatures);

  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [summaryCache, setSummaryCache] = useState<Record<string, FeatureSummary>>({});
  const hasCachedSummary = Boolean(summaryCache[taskId]);
  // 只有在任務已完成（或未傳 taskStatus）時才允許載入
  const isTaskReady = !taskStatus || taskStatus === 'completed';

  useEffect(() => {
    if (explorerTaskId !== taskId) {
      setExplorerTaskId(taskId);
      setExplorerSelectedFeatures([]);
      setExplorerActiveTab('overview', null);
    }
  }, [explorerTaskId, taskId, setExplorerTaskId, setExplorerSelectedFeatures, setExplorerActiveTab]);

  useEffect(() => {
    let active = true;
    if (hasCachedSummary || !isTaskReady) {
      return;
    }

    setSummaryLoading(true);
    setSummaryError(null);

    browseSummary(taskId)
      .then((payload) => {
        if (!active) return;
        setSummaryCache((prev) => ({ ...prev, [taskId]: payload }));
      })
      .catch((err) => {
        if (!active) return;
        setSummaryError(err instanceof Error ? err.message : '載入 summary 失敗');
      })
      .finally(() => {
        if (!active) return;
        setSummaryLoading(false);
      });

    return () => {
      active = false;
    };
  }, [browseSummary, taskId, hasCachedSummary, isTaskReady]);

  const summary = useMemo(() => summaryCache[taskId] || explorerSummary, [summaryCache, taskId, explorerSummary]);

  // ——— 生成中：顯示等待狀態 ———
  if (!isTaskReady) {
    return (
      <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-3">
        <div className="text-lg font-semibold text-slate-100">Feature Explorer</div>
        <div className="flex items-center gap-3 text-slate-400 text-sm">
          <span className="inline-block w-4 h-4 rounded-full border-2 border-amber-400/60 border-t-amber-300 animate-spin shrink-0" />
          特徵生成中，完成後自動載入…
        </div>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4">
      <div className="flex flex-col lg:flex-row lg:items-center gap-2">
        <div>
          <div className="text-lg font-semibold text-slate-100">Feature Explorer</div>
          <div className="text-xs text-slate-400">Task: {taskId}</div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setExplorerActiveTab(tab.key)}
            className={`rounded-full px-3 py-1 text-xs border ${
              explorerActiveTab === tab.key
                ? 'bg-cyan-400/20 border-cyan-300/40 text-cyan-200'
                : 'border-white/10 text-slate-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div>
        {explorerActiveTab === 'overview' && (
          <OverviewDashboard summary={summary || null} loading={summaryLoading} error={summaryError} taskId={taskId} />
        )}

        {explorerActiveTab === 'table' && (
          <FeatureTable
            taskId={taskId}
            totalCount={summary?.total_features}
            onOpenDistribution={(feature) => {
              setExplorerActiveTab('distribution', feature);
            }}
            onOpenCorrelation={(features) => {
              setExplorerSelectedFeatures(features);
              setExplorerActiveTab('correlation');
            }}
          />
        )}

        {explorerActiveTab === 'timeseries' && <FeatureTimeSeriesChart taskId={taskId} />}
        {explorerActiveTab === 'correlation' && <FeatureCorrelationHeatmap taskId={taskId} />}
        {explorerActiveTab === 'distribution' && <FeatureDistributionChart taskId={taskId} />}
        {explorerActiveTab === 'nan' && <NaNPatternChart taskId={taskId} />}
      </div>
    </div>
  );
}

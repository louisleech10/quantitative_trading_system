'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { ExplorerTab } from '@/lib/types';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import OverviewDashboard from '@/components/feature-factory/OverviewDashboard';
import FeatureTable from '@/components/feature-factory/FeatureTable';
import FeatureTimeSeriesChart from '@/components/feature-factory/FeatureTimeSeriesChart';
import FeatureCorrelationHeatmap from '@/components/feature-factory/FeatureCorrelationHeatmap';
import FeatureDistributionChart from '@/components/feature-factory/FeatureDistributionChart';
import NaNPatternChart from '@/components/feature-factory/NaNPatternChart';

interface FeatureExplorerProps {
  taskId?: string | null;
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

export default function FeatureExplorer({ taskId: propTaskId, taskStatus }: FeatureExplorerProps) {
  const { browseSummary } = useFeatureFactory();
  // Use individual selectors to return stable primitives/references.
  // A combined object selector `(state) => ({ ... })` creates a new object every render,
  // which triggers React 18 concurrent-mode's "getSnapshot should be cached" infinite loop.
  const explorerTaskId = useFeatureFactoryStore((state) => state.explorerTaskId);
  const explorerActiveTab = useFeatureFactoryStore((state) => state.explorerActiveTab);
  const explorerSummary = useFeatureFactoryStore((state) => state.explorerSummary);
  const explorerSummaryByTask = useFeatureFactoryStore((state) => state.explorerSummaryByTask);
  const explorerRecentTasks = useFeatureFactoryStore((state) => state.explorerRecentTasks);
  const setExplorerTaskId = useFeatureFactoryStore((state) => state.setExplorerTaskId);
  const setExplorerActiveTab = useFeatureFactoryStore((state) => state.setExplorerActiveTab);
  const setExplorerSelectedFeatures = useFeatureFactoryStore((state) => state.setExplorerSelectedFeatures);
  const setExplorerSummaryForTask = useFeatureFactoryStore((state) => state.setExplorerSummaryForTask);
  const pushExplorerRecentTask = useFeatureFactoryStore((state) => state.pushExplorerRecentTask);
  const removeExplorerRecentTask = useFeatureFactoryStore((state) => state.removeExplorerRecentTask);

  // 允許使用者在沒有進行中任務時手動輸入 task ID 瀏覽歷史結果
  const [manualTaskId, setManualTaskId] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const taskId: string = propTaskId || manualTaskId;

  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const cachedSummary = taskId ? explorerSummaryByTask[taskId] : undefined;
  const hasCachedSummary = Boolean(cachedSummary);
  // Only auto-load when task is fully ready.
  const isTaskReady = !taskStatus || taskStatus === 'completed';

  useEffect(() => {
    if (!taskId) return;
    if (explorerTaskId !== taskId) {
      setExplorerTaskId(taskId);
      setExplorerSelectedFeatures([]);
      setExplorerActiveTab('overview', null);
    }
  }, [explorerTaskId, taskId, setExplorerTaskId, setExplorerSelectedFeatures, setExplorerActiveTab]);

  useEffect(() => {
    let active = true;
    if (!taskId || hasCachedSummary || !isTaskReady) {
      return;
    }

    setSummaryLoading(true);
    setSummaryError(null);

    browseSummary(taskId)
      .then((payload) => {
        if (!active) return;
        setExplorerSummaryForTask(taskId, payload);
        pushExplorerRecentTask(taskId);
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
  }, [browseSummary, taskId, hasCachedSummary, isTaskReady, setExplorerSummaryForTask, pushExplorerRecentTask]);

  // When summary loads from cache (no fetch needed), still mark as recent.
  useEffect(() => {
    if (taskId && hasCachedSummary) {
      pushExplorerRecentTask(taskId);
    }
  }, [taskId, hasCachedSummary, pushExplorerRecentTask]);

  const summary = useMemo(() => cachedSummary || explorerSummary, [cachedSummary, explorerSummary]);

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4">
      <div className="flex flex-col lg:flex-row lg:items-center gap-3">
        <div className="flex-1">
          <div className="text-lg font-semibold text-slate-100">Feature Explorer</div>
          {taskId
            ? <div className="text-xs text-slate-400">Task: {taskId}</div>
            : <div className="text-xs text-slate-500">尚無進行中的任務，可貼入 Task ID 瀏覽歷史結果</div>
          }
        </div>
        {/* 手動輸入 Task ID + Recent Tasks 下拉（無進行中任務時顯示） */}
        {!propTaskId && (
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              type="text"
              value={manualTaskId}
              onChange={(e) => setManualTaskId(e.target.value.trim())}
              placeholder="貼入 Task ID…"
              className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-300/40 w-64"
            />
            {manualTaskId && (
              <button
                type="button"
                onClick={() => { setManualTaskId(''); setSummaryError(null); }}
                className="text-slate-500 hover:text-slate-300 text-xs"
              >✕</button>
            )}
            {explorerRecentTasks.length > 0 && (
              <select
                value=""
                onChange={(e) => {
                  const v = e.target.value;
                  if (v) setManualTaskId(v);
                }}
                className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-100 focus:outline-none focus:ring-1 focus:ring-cyan-300/40 max-w-[200px]"
                title="切換最近瀏覽的 Task"
              >
                <option value="">最近瀏覽 ({explorerRecentTasks.length})…</option>
                {explorerRecentTasks.map((tid) => (
                  <option key={tid} value={tid}>
                    {tid.length > 20 ? `${tid.slice(0, 8)}…${tid.slice(-8)}` : tid}
                  </option>
                ))}
              </select>
            )}
            {manualTaskId && explorerRecentTasks.includes(manualTaskId) && (
              <button
                type="button"
                onClick={() => { removeExplorerRecentTask(manualTaskId); setManualTaskId(''); }}
                className="text-rose-400/70 hover:text-rose-300 text-xs"
                title="從最近清單移除"
              >移除</button>
            )}
          </div>
        )}
      </div>

      {/* ——— 生成中：顯示等待狀態 ——— */}
      {!isTaskReady && (
        <div className="flex items-center gap-3 text-slate-400 text-sm">
          <span className="inline-block w-4 h-4 rounded-full border-2 border-amber-400/60 border-t-amber-300 animate-spin shrink-0" />
          特徵生成中，完成後自動載入…
        </div>
      )}

      {/* ——— 無任務且無手動輸入：空白提示 ——— */}
      {!taskId && (
        <div className="rounded-xl border border-white/5 bg-white/3 p-6 text-center text-xs text-slate-500">
          生成特徵後結果將自動顯示，或貼入過去的 Task ID 直接瀏覽
        </div>
      )}

      {/* ——— 有 taskId 且任務已完成：顯示 Tabs 與內容 ——— */}
      {taskId && isTaskReady && (
        <>
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
        </>
      )}
    </div>
  );
}

'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, Table2 } from 'lucide-react';
import { ExplorerTab, FeatureValidationSummary } from '@/lib/types';
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
  /** 傳入目前任務的 L7 品質摘要（由 page.tsx 從 currentTask 取出後傳入） */
  validationSummary?: FeatureValidationSummary | null;
}

const TABS: Array<{ key: ExplorerTab; label: string }> = [
  { key: 'overview', label: 'Overview' },
  { key: 'table', label: 'Feature Table' },
  { key: 'timeseries', label: 'Time Series' },
  { key: 'correlation', label: 'Correlation' },
  { key: 'distribution', label: 'Distribution' },
  { key: 'nan', label: 'NaN Pattern' },
];

export default function FeatureExplorer({ taskId: propTaskId, taskStatus, validationSummary }: FeatureExplorerProps) {
  const { browseSummary, browseFeatures, listAvailableTasks } = useFeatureFactory();
  // Use individual selectors to return stable primitives/references.
  // A combined object selector `(state) => ({ ... })` creates a new object every render,
  // which triggers React 18 concurrent-mode's "getSnapshot should be cached" infinite loop.
  const explorerTaskId = useFeatureFactoryStore((state) => state.explorerTaskId);
  const explorerActiveTab = useFeatureFactoryStore((state) => state.explorerActiveTab);
  const explorerSummary = useFeatureFactoryStore((state) => state.explorerSummary);
  const explorerSummaryByTask = useFeatureFactoryStore((state) => state.explorerSummaryByTask);
  const explorerFeatureNamesByTask = useFeatureFactoryStore((state) => state.explorerFeatureNamesByTask);
  const explorerRecentTasks = useFeatureFactoryStore((state) => state.explorerRecentTasks);
  const setExplorerTaskId = useFeatureFactoryStore((state) => state.setExplorerTaskId);
  const setExplorerActiveTab = useFeatureFactoryStore((state) => state.setExplorerActiveTab);
  const setExplorerSelectedFeatures = useFeatureFactoryStore((state) => state.setExplorerSelectedFeatures);
  const setExplorerSummaryForTask = useFeatureFactoryStore((state) => state.setExplorerSummaryForTask);
  const setExplorerFeatureNamesForTask = useFeatureFactoryStore((state) => state.setExplorerFeatureNamesForTask);
  const pushExplorerRecentTask = useFeatureFactoryStore((state) => state.pushExplorerRecentTask);
  const removeExplorerRecentTask = useFeatureFactoryStore((state) => state.removeExplorerRecentTask);
  const validationSummaryByTask = useFeatureFactoryStore((state) => state.validationSummaryByTask);
  const setValidationSummaryForTask = useFeatureFactoryStore((state) => state.setValidationSummaryForTask);

  // 允許使用者在沒有進行中任務時手動輸入 task ID 瀏覽歷史結果
  const [manualTaskId, setManualTaskId] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const taskId: string = manualTaskId || propTaskId || '';

  // prop 優先（當前 session 剛完成的任務），fallback 到 per-task localStorage 快取（refresh 後瀏覽歷史任務）
  const effectiveValidationSummary = validationSummary ?? (taskId ? validationSummaryByTask[taskId] : undefined);

  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  // Available tasks for recovery when the current task_id is no longer in API memory
  const [availableTasks, setAvailableTasks] = useState<Array<{ task_id: string; symbol: string; timeframe: string; feature_count: number | null; created_at: string }>>([]);
  const [isLoadingAvailable, setIsLoadingAvailable] = useState(false);
  const cachedSummary = taskId ? explorerSummaryByTask[taskId] : undefined;
  const hasCachedSummary = Boolean(cachedSummary);
  const cachedFeatureNames = taskId ? explorerFeatureNamesByTask[taskId] : undefined;
  const hasCachedFeatureNames = Array.isArray(cachedFeatureNames);
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
    if (!taskId || !isTaskReady) {
      setSummaryLoading(false);
      if (!taskId) setSummaryError(null);
      return;
    }

    if (hasCachedSummary) {
      setSummaryLoading(false);
      setSummaryError(null);
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

  // 當 taskId 切換到歷史任務（或 refresh 後），且該任務的 validation_summary 尚未快取時，
  // 主動呼叫 /result/{taskId} 取得 L7 品質摘要並寫入 per-task localStorage 快取。
  useEffect(() => {
    if (!taskId || !isTaskReady) return;
    // prop 已有（當前 session 剛完成的任務）或快取命中 → 不需再 fetch
    if (validationSummary != null || validationSummaryByTask[taskId] != null) return;

    let active = true;
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    fetch(`${API_BASE}/api/v1/features/result/${taskId}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((result: { metadata?: { validation?: Record<string, unknown> } }) => {
        if (!active) return;
        const v = result?.metadata?.validation;
        if (v && typeof v === 'object') {
          setValidationSummaryForTask(taskId, {
            has_nan: Boolean(v.has_nan),
            has_inf: Boolean(v.has_inf),
            coverage: Number(v.coverage ?? 0),
            inf_count: Number(v.inf_count ?? 0),
            inf_ratio: Number(v.inf_ratio ?? 0),
            groups_with_inf: Number(v.groups_with_inf ?? 0),
            warnings: Array.isArray(v.warnings) ? (v.warnings as string[]) : undefined,
          });
        }
      })
      .catch(() => { /* silent — L7 卡片只是不顯示，不應影響主流程 */ });

    return () => { active = false; };
  }, [taskId, isTaskReady, validationSummary, validationSummaryByTask, setValidationSummaryForTask]);

  // When task_id is not found in API memory (happens after restart), fetch the
  // list of available browse tasks so the user can pick one to recover.
  useEffect(() => {
    if (!summaryError || !summaryError.includes('Result not found')) {
      setAvailableTasks([]);
      return;
    }
    let active = true;
    setIsLoadingAvailable(true);
    listAvailableTasks()
      .then((tasks) => { if (active) setAvailableTasks(tasks); })
      .catch(() => { if (active) setAvailableTasks([]); })
      .finally(() => { if (active) setIsLoadingAvailable(false); });
    return () => { active = false; };
  }, [summaryError, listAvailableTasks]);

  useEffect(() => {
    let active = true;
    if (!taskId || !isTaskReady || hasCachedFeatureNames) {
      return;
    }

    browseFeatures(taskId, {
      offset: 0,
      limit: 1000000,
      sortBy: 'name',
      sortOrder: 'asc',
      detailLevel: 'names',
    })
      .then((payload) => {
        if (!active) return;
        const names = payload.features
          .map((item) => item.name)
          .filter((name): name is string => typeof name === 'string' && name.length > 0);
        setExplorerFeatureNamesForTask(taskId, names);
      })
      .catch(() => {
        // Summary carries the user-facing failure state. A missing names catalog
        // should not block Overview/Table rendering.
      });

    return () => {
      active = false;
    };
  }, [browseFeatures, taskId, isTaskReady, hasCachedFeatureNames, setExplorerFeatureNamesForTask]);

  // When summary loads from cache (no fetch needed), still mark as recent.
  useEffect(() => {
    if (taskId && hasCachedSummary) {
      pushExplorerRecentTask(taskId);
    }
  }, [taskId, hasCachedSummary, pushExplorerRecentTask]);

  const summary = useMemo(() => cachedSummary || (explorerTaskId === taskId ? explorerSummary : null), [cachedSummary, explorerSummary, explorerTaskId, taskId]);

  return (
    <div className="glass-panel rounded-2xl border border-white/10">
      {/* 頂部區：左欄（標題 + task controls）與右欄（L7 卡片）stretch 同高 */}
      <div className="flex items-stretch gap-4 px-5 py-4">
        {/* 左欄：Feature Explorer 標題堆疊在 task controls 上方 */}
        <div className="flex flex-col justify-between gap-3 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-violet-400/15 flex items-center justify-center flex-shrink-0">
              <Table2 className="w-5 h-5 text-violet-200" />
            </div>
            <div>
              <div className="text-base font-semibold text-slate-100">Feature Explorer</div>
              {taskId
                ? <div className="text-sm text-slate-400 mt-0.5">Task: {taskId}</div>
                : <div className="text-sm text-slate-500 mt-0.5">尚無進行中的任務，可貼入 Task ID 瀏覽歷史結果</div>
              }
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
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
                title={propTaskId ? '回到目前任務' : '清除手動 Task'}
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
        </div>

        {/* 右欄：L7 品質卡片，自動撐滿左欄高度（items-stretch） */}
        {taskId && isTaskReady && effectiveValidationSummary && (
          (() => {
            const v = effectiveValidationSummary;
            const coveragePct = (v.coverage * 100).toFixed(2);
            const infRatioPct = (v.inf_ratio * 100).toFixed(4);
            const hasIssue = v.has_inf || v.coverage < 0.95;
            const borderCls = v.has_inf
              ? 'border-rose-400/40'
              : v.coverage < 0.95
                ? 'border-amber-400/30'
                : 'border-emerald-400/30';
            const titleCls = v.has_inf
              ? 'text-rose-300'
              : v.coverage < 0.95
                ? 'text-amber-300'
                : 'text-emerald-300';
            return (
              <div className={`flex-1 min-w-0 glass-panel rounded-lg p-2.5 border ${borderCls} flex flex-col justify-between`}>
                <div className={`flex items-center gap-1.5 text-sm ${titleCls}`}>
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>L7 資料品質摘要 {hasIssue ? '— 偵測到輸入病理性訊號' : '— 通過'}</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2">
                  <div className="rounded border border-white/10 bg-[#141b2d]/60 px-2.5 py-1.5">
                    <div className="text-[11px] text-slate-400">Coverage</div>
                    <div className="text-sm font-semibold text-slate-100">{coveragePct}%</div>
                    <div className="text-[10px] text-slate-500">非 NaN 比例</div>
                  </div>
                  <div className="rounded border border-white/10 bg-[#141b2d]/60 px-2.5 py-1.5">
                    <div className="text-[11px] text-slate-400">Inf Count</div>
                    <div className={`text-sm font-semibold ${v.inf_count > 0 ? 'text-rose-300' : 'text-emerald-300'}`}>
                      {v.inf_count.toLocaleString()}
                    </div>
                    <div className="text-[10px] text-slate-500">Float32 溢位次數</div>
                  </div>
                  <div className="rounded border border-white/10 bg-[#141b2d]/60 px-2.5 py-1.5">
                    <div className="text-[11px] text-slate-400">Inf Ratio</div>
                    <div className={`text-sm font-semibold ${v.inf_ratio > 0 ? 'text-rose-300' : 'text-emerald-300'}`}>
                      {infRatioPct}%
                    </div>
                    <div className="text-[10px] text-slate-500">Inf / 總值</div>
                  </div>
                  <div className="rounded border border-white/10 bg-[#141b2d]/60 px-2.5 py-1.5">
                    <div className="text-[11px] text-slate-400">Groups w/ Inf</div>
                    <div className={`text-sm font-semibold ${v.groups_with_inf > 0 ? 'text-amber-300' : 'text-emerald-300'}`}>
                      {v.groups_with_inf}
                    </div>
                    <div className="text-[10px] text-slate-500">受影響 group 數</div>
                  </div>
                </div>
                {v.has_inf && (
                  <div className="text-xs text-rose-200/80 mt-2">
                    💡 Inf 通常源自比值類指標分母趨近 0 或回歸視窗常數。已套用 epsilon mask
                    + 1e30 cap，並由 L6.5 winsorization 進一步處理。詳細位置見後端 log 的 Top-5 offending groups。
                  </div>
                )}
              </div>
            );
          })()
        )}
      </div>

      <div className="px-6 pb-6 space-y-4 border-t border-white/5">

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

      {/* ——— Task ID 不存在（API 重啟後記憶體清空）：提供可用任務清單供切換 ——— */}
      {summaryError && summaryError.includes('Result not found') && (
        <div className="rounded-xl border border-amber-400/20 bg-amber-400/5 p-4 space-y-3">
          <div className="flex items-center gap-2 text-amber-300 text-sm font-medium">
            <span>⚠</span>
            <span>Task 已失效（API 重啟後記憶體清空）</span>
          </div>
          <div className="text-xs text-slate-400">Task ID: <code className="text-slate-300">{taskId}</code></div>
          {isLoadingAvailable && (
            <div className="text-xs text-slate-500">搜尋可用任務中…</div>
          )}
          {!isLoadingAvailable && availableTasks.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs text-slate-400">偵測到以下可用的歷史特徵任務，請選擇切換：</div>
              <div className="flex flex-col gap-1.5">
                {availableTasks.map((t) => (
                  <button
                    key={t.task_id}
                    type="button"
                    onClick={() => { setManualTaskId(t.task_id); setSummaryError(null); setAvailableTasks([]); }}
                    className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-200 hover:bg-cyan-400/10 hover:border-cyan-400/30 text-left"
                  >
                    <span>
                      {t.symbol && t.timeframe ? (
                        <span className="text-cyan-300 font-medium">{t.symbol} / {t.timeframe}</span>
                      ) : null}
                      {' '}
                      <span className="text-slate-400 font-mono">{t.task_id.length > 24 ? `${t.task_id.slice(0, 12)}…` : t.task_id}</span>
                    </span>
                    <span className="text-slate-500 shrink-0 ml-3">
                      {t.feature_count != null ? `${t.feature_count.toLocaleString()} 特徵` : ''}
                      {t.created_at ? ` · ${t.created_at.slice(0, 10)}` : ''}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
          {!isLoadingAvailable && availableTasks.length === 0 && (
            <div className="text-xs text-slate-500">
              目前無可用歷史任務。請重新執行特徵生成，或重啟 API 後再試（伺服器啟動時會自動還原磁碟上的特徵）。
            </div>
          )}
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
    </div>
  );
}

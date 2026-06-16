'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, ChevronDown, Table2 } from 'lucide-react';
import { ExplorerTab, FeatureValidationSummary, RunInfo } from '@/lib/types';
import { formatRunLabel, formatRunTimestamp, pickDefaultRun } from '@/lib/runExplorer';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import { runKey, useFeatureFactoryStore } from '@/store/featureFactoryStore';
import OverviewDashboard from '@/components/feature-factory/OverviewDashboard';
import FeatureTable from '@/components/feature-factory/FeatureTable';
import FeatureTimeSeriesChart from '@/components/feature-factory/FeatureTimeSeriesChart';
import FeatureCorrelationHeatmap from '@/components/feature-factory/FeatureCorrelationHeatmap';
import FeatureDistributionChart from '@/components/feature-factory/FeatureDistributionChart';
import DataQualityDashboard from '@/components/feature-factory/DataQualityDashboard';
import CollapsibleSection from '@/components/feature-factory/CollapsibleSection';

const FEATURE_EXPLORER_EXPANDED_KEY = 'ff-feature-explorer-expanded';

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
  { key: 'nan', label: '資料品質' },
];

export default function FeatureExplorer({
  taskId: propTaskId,
  taskStatus,
  validationSummary,
}: FeatureExplorerProps) {
  const { browseSummary, browseFeatures, listAvailableTasks } = useFeatureFactory();
  const explorerTaskId = useFeatureFactoryStore((state) => state.explorerTaskId);
  const explorerActiveTab = useFeatureFactoryStore((state) => state.explorerActiveTab);
  const explorerSummary = useFeatureFactoryStore((state) => state.explorerSummary);
  const explorerSummaryByTask = useFeatureFactoryStore((state) => state.explorerSummaryByTask);
  const explorerFeatureNamesByTask = useFeatureFactoryStore((state) => state.explorerFeatureNamesByTask);
  const explorerRecentTasks = useFeatureFactoryStore((state) => state.explorerRecentTasks);
  const runs = useFeatureFactoryStore((state) => state.runs);
  const runsLoading = useFeatureFactoryStore((state) => state.runsLoading);
  const selectedRunKey = useFeatureFactoryStore((state) => state.selectedRunKey);
  const currentTask = useFeatureFactoryStore((state) => state.currentTask);
  const batchTask = useFeatureFactoryStore((state) => state.batchTask);
  const fetchRuns = useFeatureFactoryStore((state) => state.fetchRuns);
  const setSelectedRun = useFeatureFactoryStore((state) => state.setSelectedRun);
  const ensureBrowseTaskForRun = useFeatureFactoryStore((state) => state.ensureBrowseTaskForRun);
  const setExplorerTaskId = useFeatureFactoryStore((state) => state.setExplorerTaskId);
  const setExplorerActiveTab = useFeatureFactoryStore((state) => state.setExplorerActiveTab);
  const setExplorerSelectedFeatures = useFeatureFactoryStore((state) => state.setExplorerSelectedFeatures);
  const setExplorerSummaryForTask = useFeatureFactoryStore((state) => state.setExplorerSummaryForTask);
  const setExplorerFeatureNamesForTask = useFeatureFactoryStore((state) => state.setExplorerFeatureNamesForTask);
  const pushExplorerRecentTask = useFeatureFactoryStore((state) => state.pushExplorerRecentTask);
  const validationSummaryByTask = useFeatureFactoryStore((state) => state.validationSummaryByTask);
  const setValidationSummaryForTask = useFeatureFactoryStore((state) => state.setValidationSummaryForTask);

  const [manualTaskId, setManualTaskId] = useState('');
  const [showAdvancedTaskInput, setShowAdvancedTaskInput] = useState(false);
  const [symbolFilter, setSymbolFilter] = useState('');
  const [timeframeFilter, setTimeframeFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [ensuringBrowse, setEnsuringBrowse] = useState(false);
  const [resolvedBrowseTaskId, setResolvedBrowseTaskId] = useState<string | null>(null);
  const ensureAttemptedRef = useRef<string | null>(null);
  const selectionSourceRef = useRef<'auto' | 'manual'>('auto');

  const selectedRun = useMemo(
    () => runs.find((run) => runKey(run) === selectedRunKey) ?? null,
    [runs, selectedRunKey],
  );

  const symbolOptions = useMemo(
    () => Array.from(new Set(runs.map((run) => run.symbol))).sort(),
    [runs],
  );
  const timeframeOptions = useMemo(
    () => Array.from(new Set(runs.map((run) => run.timeframe))).sort(),
    [runs],
  );

  const filteredRuns = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return runs.filter((run) => {
      if (symbolFilter && run.symbol !== symbolFilter) return false;
      if (timeframeFilter && run.timeframe !== timeframeFilter) return false;
      if (!query) return true;
      const haystack = [
        run.alias,
        run.batch_alias,
        run.symbol,
        run.timeframe,
        run.config_hash,
        run.browse_task_id,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [runs, searchQuery, symbolFilter, timeframeFilter]);

  const taskId: string = manualTaskId || resolvedBrowseTaskId || propTaskId || '';
  const effectiveValidationSummary =
    validationSummary ?? (taskId ? validationSummaryByTask[taskId] : undefined);

  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [availableTasks, setAvailableTasks] = useState<
    Array<{ task_id: string; symbol: string; timeframe: string; feature_count: number | null; created_at: string }>
  >([]);
  const [isLoadingAvailable, setIsLoadingAvailable] = useState(false);
  const cachedSummary = taskId ? explorerSummaryByTask[taskId] : undefined;
  const hasCachedSummary = Boolean(cachedSummary);
  const cachedFeatureNames = taskId ? explorerFeatureNamesByTask[taskId] : undefined;
  const hasCachedFeatureNames = Array.isArray(cachedFeatureNames);
  const isTaskReady = !taskStatus || taskStatus === 'completed';

  useEffect(() => {
    void fetchRuns();
  }, [fetchRuns]);

  useEffect(() => {
    if (manualTaskId || runs.length === 0) return;
    if (selectionSourceRef.current === 'manual') return;

    const defaultRun = pickDefaultRun(runs, currentTask, batchTask);
    if (!defaultRun) return;

    const defaultKey = runKey(defaultRun);
    if (selectedRunKey !== defaultKey) {
      setSelectedRun(defaultRun);
      selectionSourceRef.current = 'auto';
    }
  }, [manualTaskId, selectedRunKey, runs, currentTask, batchTask, setSelectedRun]);

  useEffect(() => {
    if (manualTaskId) {
      setResolvedBrowseTaskId(null);
      return;
    }
    if (!selectedRun) {
      setResolvedBrowseTaskId(null);
      return;
    }
    setResolvedBrowseTaskId(selectedRun.browse_ready ? selectedRun.browse_task_id : null);
    ensureAttemptedRef.current = null;
  }, [manualTaskId, selectedRun]);

  const loadSummary = useCallback(
    async (activeTaskId: string, runForEnsure: RunInfo | null) => {
      setSummaryLoading(true);
      setSummaryError(null);
      try {
        const payload = await browseSummary(activeTaskId);
        setExplorerSummaryForTask(activeTaskId, payload);
        pushExplorerRecentTask(activeTaskId);
      } catch (err) {
        const message = err instanceof Error ? err.message : '載入 summary 失敗';
        const shouldEnsure =
          runForEnsure?.browse_ready &&
          message.includes('Result not found') &&
          ensureAttemptedRef.current !== runKey(runForEnsure);
        if (shouldEnsure) {
          ensureAttemptedRef.current = runKey(runForEnsure);
          setEnsuringBrowse(true);
          const ensuredId = await ensureBrowseTaskForRun(
            runForEnsure.symbol,
            runForEnsure.timeframe,
            runForEnsure.config_hash,
          );
          setEnsuringBrowse(false);
          if (ensuredId) {
            setResolvedBrowseTaskId(ensuredId);
            const payload = await browseSummary(ensuredId);
            setExplorerSummaryForTask(ensuredId, payload);
            pushExplorerRecentTask(ensuredId);
            return;
          }
        }
        setSummaryError(message);
      } finally {
        setSummaryLoading(false);
      }
    },
    [
      browseSummary,
      ensureBrowseTaskForRun,
      pushExplorerRecentTask,
      setExplorerSummaryForTask,
    ],
  );

  useEffect(() => {
    if (!taskId) return;
    if (explorerTaskId !== taskId) {
      setExplorerTaskId(taskId);
      setExplorerSelectedFeatures([]);
      setExplorerActiveTab('overview', null);
    }
  }, [explorerTaskId, taskId, setExplorerTaskId, setExplorerSelectedFeatures, setExplorerActiveTab]);

  useEffect(() => {
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
    void loadSummary(taskId, manualTaskId ? null : selectedRun);
  }, [taskId, isTaskReady, hasCachedSummary, loadSummary, manualTaskId, selectedRun]);

  useEffect(() => {
    if (!taskId || !isTaskReady) return;
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
      .catch(() => {});

    return () => {
      active = false;
    };
  }, [taskId, isTaskReady, validationSummary, validationSummaryByTask, setValidationSummaryForTask]);

  useEffect(() => {
    if (!summaryError || !summaryError.includes('Result not found')) {
      setAvailableTasks([]);
      return;
    }
    let active = true;
    setIsLoadingAvailable(true);
    listAvailableTasks()
      .then((tasks) => {
        if (active) setAvailableTasks(tasks);
      })
      .catch(() => {
        if (active) setAvailableTasks([]);
      })
      .finally(() => {
        if (active) setIsLoadingAvailable(false);
      });
    return () => {
      active = false;
    };
  }, [summaryError, listAvailableTasks]);

  useEffect(() => {
    let active = true;
    if (!taskId || !isTaskReady || hasCachedFeatureNames) {
      return;
    }
    const TABS_NEEDING_NAMES: ReadonlyArray<typeof explorerActiveTab> = [
      'table',
      'timeseries',
      'correlation',
      'distribution',
    ];
    if (!TABS_NEEDING_NAMES.includes(explorerActiveTab)) {
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
      .catch(() => {});

    return () => {
      active = false;
    };
  }, [
    browseFeatures,
    taskId,
    isTaskReady,
    hasCachedFeatureNames,
    setExplorerFeatureNamesForTask,
    explorerActiveTab,
  ]);

  useEffect(() => {
    if (taskId && hasCachedSummary) {
      pushExplorerRecentTask(taskId);
    }
  }, [taskId, hasCachedSummary, pushExplorerRecentTask]);

  const summary = useMemo(
    () => cachedSummary || (explorerTaskId === taskId ? explorerSummary : null),
    [cachedSummary, explorerSummary, explorerTaskId, taskId],
  );

  const handleRunSelect = (run: RunInfo) => {
    setManualTaskId('');
    setSummaryError(null);
    selectionSourceRef.current = 'manual';
    setSelectedRun(run);
  };

  const explorerSubtitle = taskId
    ? (selectedRun ? formatRunLabel(selectedRun) : `Task: ${taskId}`)
    : '從 registry 選擇 run，或使用進階 Task ID 瀏覽歷史結果';

  return (
    <CollapsibleSection
      storageKey={FEATURE_EXPLORER_EXPANDED_KEY}
      title="Feature Explorer"
      description={explorerSubtitle}
      leading={(
        <div className="h-10 w-10 rounded-xl bg-violet-400/15 flex items-center justify-center flex-shrink-0">
          <Table2 className="w-5 h-5 text-violet-200" />
        </div>
      )}
      expandedClassName="glass-panel rounded-2xl border border-white/10"
      collapsedClassName="glass-panel rounded-xl border border-white/10 px-4 py-3"
      headerClassName="px-5 py-4"
    >
      <div className="flex items-stretch gap-4 px-5 py-4 border-t border-white/5">
        <div className="flex flex-col justify-between gap-3 flex-shrink-0 min-w-0 flex-1">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜尋 alias / symbol / hash…"
                className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-300/40 w-52"
              />
              <select
                value={symbolFilter}
                onChange={(e) => setSymbolFilter(e.target.value)}
                className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-100 focus:outline-none focus:ring-1 focus:ring-cyan-300/40"
              >
                <option value="">全部 Symbol</option>
                {symbolOptions.map((symbol) => (
                  <option key={symbol} value={symbol}>
                    {symbol}
                  </option>
                ))}
              </select>
              <select
                value={timeframeFilter}
                onChange={(e) => setTimeframeFilter(e.target.value)}
                className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-100 focus:outline-none focus:ring-1 focus:ring-cyan-300/40"
              >
                <option value="">全部 Timeframe</option>
                {timeframeOptions.map((tf) => (
                  <option key={tf} value={tf}>
                    {tf}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => setShowAdvancedTaskInput((value) => !value)}
                className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-2 py-1 text-xs text-slate-400 hover:text-slate-200"
              >
                <ChevronDown className={`w-3 h-3 transition ${showAdvancedTaskInput ? 'rotate-180' : ''}`} />
                進階 Task ID
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <select
                value={selectedRunKey ?? ''}
                onChange={(e) => {
                  const run = runs.find((item) => runKey(item) === e.target.value);
                  if (run) handleRunSelect(run);
                }}
                disabled={runsLoading || filteredRuns.length === 0}
                className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-100 focus:outline-none focus:ring-1 focus:ring-cyan-300/40 min-w-[280px] max-w-full"
              >
                <option value="">
                  {runsLoading ? '載入 Runs…' : filteredRuns.length === 0 ? '尚無可用 Run' : '選擇 Run…'}
                </option>
                {filteredRuns.map((run) => (
                  <option key={runKey(run)} value={runKey(run)}>
                    {formatRunLabel(run)}
                    {run.browse_ready ? '' : ' (未就緒)'}
                    {run.active ? ' · 使用中' : ''}
                  </option>
                ))}
              </select>
              {ensuringBrowse && (
                <span className="text-xs text-slate-400">確保 browse 任務中…</span>
              )}
            </div>

            {showAdvancedTaskInput && (
              <div className="flex flex-wrap items-center gap-2">
                <input
                  type="text"
                  value={manualTaskId}
                  onChange={(e) => {
                    setManualTaskId(e.target.value.trim());
                    setSummaryError(null);
                  }}
                  placeholder="貼入 Task ID…"
                  className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-300/40 w-64"
                />
                {manualTaskId && (
                  <button
                    type="button"
                    onClick={() => {
                      setManualTaskId('');
                      setSummaryError(null);
                    }}
                    className="text-slate-500 hover:text-slate-300 text-xs"
                  >
                    清除
                  </button>
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
              </div>
            )}
          </div>
        </div>

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
                    Inf 通常源自比值類指標分母趨近 0 或回歸視窗常數。已套用 epsilon mask
                    + 1e30 cap，並由 L6.5 winsorization 進一步處理。詳細位置見後端 log 的 Top-5 offending groups。
                  </div>
                )}
              </div>
            );
          })()
        )}
      </div>

      <div className="px-6 pb-6 space-y-4 border-t border-white/5">
        {!isTaskReady && (
          <div className="flex items-center gap-3 text-slate-400 text-sm">
            <span className="inline-block w-4 h-4 rounded-full border-2 border-amber-400/60 border-t-amber-300 animate-spin shrink-0" />
            特徵生成中，完成後自動載入…
          </div>
        )}

        {!taskId && (
          <div className="rounded-xl border border-white/5 bg-white/3 p-6 text-center text-xs text-slate-500">
            從上方選擇 registry run，或展開進階 Task ID 瀏覽歷史結果
          </div>
        )}

        {summaryError && summaryError.includes('Result not found') && (
          <div className="rounded-xl border border-amber-400/20 bg-amber-400/5 p-4 space-y-3">
            <div className="flex items-center gap-2 text-amber-300 text-sm font-medium">
              <span>⚠</span>
              <span>Task 已失效（API 重啟後記憶體清空）</span>
            </div>
            <div className="text-xs text-slate-400">
              Task ID: <code className="text-slate-300">{taskId}</code>
            </div>
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
                      onClick={() => {
                        setManualTaskId(t.task_id);
                        setSummaryError(null);
                        setAvailableTasks([]);
                      }}
                      className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-200 hover:bg-cyan-400/10 hover:border-cyan-400/30 text-left"
                    >
                      <span>
                        {t.symbol && t.timeframe ? (
                          <span className="text-cyan-300 font-medium">{t.symbol} / {t.timeframe}</span>
                        ) : null}
                        {' '}
                        <span className="text-slate-400 font-mono">
                          {t.task_id.length > 24 ? `${t.task_id.slice(0, 12)}…` : t.task_id}
                        </span>
                      </span>
                      <span className="text-slate-500 shrink-0 ml-3">
                        {t.feature_count != null ? `${t.feature_count.toLocaleString()} 特徵` : ''}
                        {t.created_at ? ` · ${formatRunTimestamp(t.created_at)}` : ''}
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
              {explorerActiveTab === 'nan' && <DataQualityDashboard taskId={taskId} />}
            </div>
          </>
        )}
      </div>
    </CollapsibleSection>
  );
}

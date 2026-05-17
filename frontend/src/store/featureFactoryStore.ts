import { create } from 'zustand';
import {
  FeatureFactoryConfig,
  FeatureRegistryEntry,
  FeaturePreview,
  FeatureTask,
  BatchTaskStatus,
  FeatureFactoryPreset,
  FeatureIndicatorSpec,
  FeatureGenerationProgress,
  FeatureNLResult,
  AutoResearchStatus,
  AutoResearchLogEntry,
  FeatureSummary,
  FeatureValidationSummary,
  ExplorerTab,
  FeatureSchema,
  BatchItemRss,
  BatchOutputPath,
} from '@/lib/types';

type BatchConnectionStatus = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'lost';
type BatchPayload = Partial<BatchTaskStatus> & Record<string, unknown>;

interface FeatureFactoryState {
  config: FeatureFactoryConfig | null;
  presets: FeatureFactoryPreset[];
  dataSources: string[];
  indicators: FeatureIndicatorSpec[];
  preview: FeaturePreview | null;
  currentTask: FeatureTask | null;
  progress: FeatureGenerationProgress | null;
  featureList: string[];
  isGenerating: boolean;
  isPreviewLoading: boolean;
  error: string | null;
  selectedPreset: string | null;
  lastNLResult: FeatureNLResult | null;
  autoResearchStatus: AutoResearchStatus | null;
  autoResearchLogs: AutoResearchLogEntry[];
  explorerTaskId: string | null;
  explorerActiveTab: ExplorerTab;
  explorerSelectedFeature: string | null;
  explorerSelectedFeatures: string[];
  explorerSummary: FeatureSummary | null;
  // Per-task summary cache so switching back to a recently visited task is
  // instantaneous (avoids re-hitting /browse/{taskId}/summary).
  explorerSummaryByTask: Record<string, FeatureSummary>;
  // LRU list of recently visited explorer task IDs (most-recent first, max 10).
  // Persisted to localStorage so the dropdown survives page reloads.
  explorerRecentTasks: string[];
  // Complete feature-name catalog per task. Shared by all explorer tabs so
  // segment filters show the same complete options everywhere.
  explorerFeatureNamesByTask: Record<string, string[]>;
  // Per-task L7 validation summary cache. Persisted to localStorage so the
  // KPI cards survive page reloads when browsing historical tasks.
  validationSummaryByTask: Record<string, FeatureValidationSummary>;
  // Phase C: schema and search
  schema: FeatureSchema | null;
  indicatorSearch: string;
  batchTask: BatchTaskStatus | null;
  batchStartedAtMs: number | null;
  batchConnectionStatus: BatchConnectionStatus;
  batchConnectionMessage: string | null;
  registryEntries: FeatureRegistryEntry[];
  registryLoading: boolean;
  alignmentMode: 'open_minus' | 'close_time';
  trainingTimeframes: string[];
  setConfig: (config: FeatureFactoryConfig) => void;
  updateConfigPartial: (partial: Record<string, unknown>) => void;
  setPresets: (presets: FeatureFactoryPreset[]) => void;
  setDataSources: (sources: string[]) => void;
  setIndicators: (indicators: FeatureIndicatorSpec[]) => void;
  setPreview: (preview: FeaturePreview | null) => void;
  setCurrentTask: (task: FeatureTask | null) => void;
  updateCurrentTaskPartial: (patch: Partial<FeatureTask>) => void;
  setProgress: (progress: FeatureGenerationProgress | null) => void;
  setFeatureList: (features: string[]) => void;
  setIsGenerating: (value: boolean) => void;
  setIsPreviewLoading: (value: boolean) => void;
  setError: (error: string | null) => void;
  setSelectedPreset: (preset: string | null) => void;
  setLastNLResult: (result: FeatureNLResult | null) => void;
  setAutoResearchStatus: (status: AutoResearchStatus | null) => void;
  setAutoResearchLogs: (logs: AutoResearchLogEntry[]) => void;
  setExplorerTaskId: (taskId: string | null) => void;
  setExplorerActiveTab: (tab: ExplorerTab, selectedFeature?: string | null) => void;
  setExplorerSelectedFeatures: (features: string[]) => void;
  setExplorerSummary: (summary: FeatureSummary | null) => void;
  setExplorerSummaryForTask: (taskId: string, summary: FeatureSummary) => void;
  clearExplorerSummaryForTask: (taskId: string) => void;
  pushExplorerRecentTask: (taskId: string) => void;
  removeExplorerRecentTask: (taskId: string) => void;
  setExplorerFeatureNamesForTask: (taskId: string, featureNames: string[]) => void;
  setValidationSummaryForTask: (taskId: string, summary: FeatureValidationSummary) => void;
  setBatchTask: (task: BatchTaskStatus | null) => void;
  applyBatchEvent: (payload: BatchPayload) => void;
  setBatchConnectionState: (status: BatchConnectionStatus, message?: string | null) => void;
  resumeBatch: (batchId?: string) => Promise<boolean>;
  fetchRegistry: () => Promise<void>;
  startBatchGeneration: (
    symbols: string[],
    timeframe: string,
    config?: Record<string, unknown>,
    options?: { forceRegenerate?: boolean; maxWorkers?: number }
  ) => Promise<void>;
  pollBatchStatus: (taskId: string) => Promise<void>;
  setAlignmentMode: (mode: 'open_minus' | 'close_time') => void;
  setTrainingTimeframes: (tfs: string[]) => void;
  // Phase C: new actions
  setSchema: (schema: FeatureSchema | null) => void;
  setIndicatorSearch: (search: string) => void;
  toggleIndicator: (category: string, indicatorName: string, enabled: boolean) => void;
  toggleAllInCategory: (category: string, enabled: boolean) => void;
  toggleCategory: (category: string, enabled: boolean) => void;
  toggleAggregator: (name: string, enabled: boolean) => void;
  toggleAllAggregators: (enabled: boolean) => void;
  toggleMetaSubEngine: (name: string, enabled: boolean) => void;
  toggleCrossFeature: (name: string, enabled: boolean) => void;
  toggleOperator: (name: string, enabled: boolean) => void;
}

const mergeDeep = (
  target: Record<string, unknown>,
  source: Record<string, unknown>
) => {
  const output: Record<string, unknown> = { ...target };
  Object.keys(source).forEach((key) => {
    const sourceValue = source[key];
    if (sourceValue && typeof sourceValue === 'object' && !Array.isArray(sourceValue)) {
      const targetValue = output[key];
      output[key] = mergeDeep(
        (targetValue as Record<string, unknown>) || {},
        sourceValue as Record<string, unknown>
      );
    } else {
      output[key] = sourceValue;
    }
  });
  return output;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1/features';

function toNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function isResumeAvailable(status: string, explicitValue: unknown): boolean {
  if (typeof explicitValue === 'boolean') {
    return explicitValue;
  }
  return ['failed', 'partial', 'paused', 'paused_ram_gate'].includes(status);
}

function normalizeOutputPaths(payload: BatchPayload, previous?: BatchTaskStatus | null): BatchOutputPath[] {
  const existing = new Map<string, BatchOutputPath>();

  for (const item of previous?.output_paths ?? []) {
    existing.set(`${item.symbol}:${item.timeframe}:${item.path}`, item);
  }

  const rawOutputPaths = payload.output_paths;
  if (Array.isArray(rawOutputPaths)) {
    rawOutputPaths.forEach((item) => {
      if (!item || typeof item !== 'object') return;
      const record = item as Record<string, unknown>;
      const symbol = String(record.symbol ?? '');
      const timeframe = String(record.timeframe ?? payload.current_timeframe ?? '');
      const path = String(record.path ?? record.hdf5_path ?? '');
      if (!symbol || !path) return;
      existing.set(`${symbol}:${timeframe}:${path}`, {
        symbol,
        timeframe,
        path,
        download_url: typeof record.download_url === 'string' ? record.download_url : undefined,
      });
    });
  }

  const results = (payload.results ?? previous?.results ?? {}) as Record<string, string>;
  Object.entries(results).forEach(([symbol, path]) => {
    if (!path) return;
    const knownTimeframe = previous?.output_paths?.find((item) => item.symbol === symbol && item.path === path)?.timeframe;
    const timeframe = String(knownTimeframe ?? payload.current_timeframe ?? previous?.current_timeframe ?? '');
    existing.set(`${symbol}:${timeframe}:${path}`, { symbol, timeframe, path });
  });

  return Array.from(existing.values());
}

function normalizePerItemRss(payload: BatchPayload, previous?: BatchTaskStatus | null): BatchItemRss[] {
  const existing = new Map<string, BatchItemRss>();

  for (const item of previous?.per_item_rss ?? []) {
    existing.set(`${item.symbol}:${item.timeframe}`, item);
  }

  const rawItems = payload.per_item_rss;
  if (Array.isArray(rawItems)) {
    rawItems.forEach((item) => {
      if (!item || typeof item !== 'object') return;
      const record = item as Record<string, unknown>;
      const symbol = String(record.symbol ?? '');
      const timeframe = String(record.timeframe ?? '');
      const rssPeakMB = toNumber(record.rssPeakMB ?? record.rss_peak_item_mb, NaN);
      const rssAfterGcMB = toNumber(record.rssAfterGcMB ?? record.rss_after_gc_mb, NaN);
      if (!symbol || !timeframe || !Number.isFinite(rssPeakMB) || !Number.isFinite(rssAfterGcMB)) return;
      existing.set(`${symbol}:${timeframe}`, {
        symbol,
        timeframe,
        rssBeforeItemMB: toNumber(record.rssBeforeItemMB ?? record.rss_before_item_mb, 0),
        rssPeakMB,
        rssAfterGcMB,
      });
    });
  }

  const metrics = payload.last_item_metrics;
  if (metrics && typeof metrics === 'object') {
    const record = metrics as Record<string, unknown>;
    const symbol = String(record.current_symbol ?? payload.current_symbol ?? '');
    const timeframe = String(record.current_timeframe ?? payload.current_timeframe ?? '');
    const rssPeakMB = toNumber(record.rss_peak_item_mb, NaN);
    const rssAfterGcMB = toNumber(record.rss_after_gc_mb, NaN);
    if (symbol && timeframe && Number.isFinite(rssPeakMB) && Number.isFinite(rssAfterGcMB)) {
      existing.set(`${symbol}:${timeframe}`, {
        symbol,
        timeframe,
        rssBeforeItemMB: toNumber(record.rss_before_item_mb, 0),
        rssPeakMB,
        rssAfterGcMB,
      });
    }
  }

  return Array.from(existing.values());
}

function normalizeBatchTask(
  payload: BatchPayload,
  previous: BatchTaskStatus | null,
  startedAtMs: number | null
): BatchTaskStatus {
  const status = String(payload.status ?? previous?.status ?? 'idle') as BatchTaskStatus['status'];
  const total = toNumber(payload.total ?? payload.total_items, previous?.total ?? 0);
  const completed = toNumber(payload.completed ?? payload.completed_items, previous?.completed ?? 0);
  const failed = toNumber(payload.failed ?? payload.failed_items, previous?.failed ?? 0);
  const progress = toNumber(payload.progress, total > 0 ? (completed + failed) / total : previous?.progress ?? 0);
  const elapsedSeconds = startedAtMs ? Math.max(0, Math.round((Date.now() - startedAtMs) / 1000)) : 0;
  const etaFromAverage = completed > 0 && total > completed + failed
    ? Math.round((total - completed - failed) * (elapsedSeconds / completed))
    : 0;

  return {
    ...previous,
    ...payload,
    task_id: String(payload.task_id ?? payload.batch_id ?? previous?.task_id ?? ''),
    batch_id: String(payload.batch_id ?? payload.task_id ?? previous?.batch_id ?? previous?.task_id ?? ''),
    status,
    total,
    completed,
    failed,
    progress,
    current_symbol: (payload.current_symbol as string | null | undefined) ?? previous?.current_symbol ?? null,
    current_timeframe: (payload.current_timeframe as string | null | undefined) ?? previous?.current_timeframe ?? null,
    queued: toNumber(payload.queued, Math.max(total - completed - failed, 0)),
    concurrent_symbols: toNumber(payload.concurrent_symbols, previous?.concurrent_symbols ?? 1),
    memory_sanity_failed: Boolean(payload.memory_sanity_failed ?? previous?.memory_sanity_failed ?? false),
    eta_seconds: toNumber(payload.eta_seconds, etaFromAverage),
    resume_available: isResumeAvailable(status, payload.resume_available ?? previous?.resume_available),
    output_paths: normalizeOutputPaths(payload, previous),
    per_item_rss: normalizePerItemRss(payload, previous),
    last_item_metrics: (payload.last_item_metrics as BatchTaskStatus['last_item_metrics']) ?? previous?.last_item_metrics ?? null,
    results: (payload.results as Record<string, string> | undefined) ?? previous?.results ?? {},
    errors: (payload.errors as Record<string, string> | undefined) ?? previous?.errors ?? {},
  };
}

export const useFeatureFactoryStore = create<FeatureFactoryState>((set, get) => ({
  config: null,
  presets: [],
  dataSources: [],
  indicators: [],
  preview: null,
  currentTask: null,
  progress: null,
  featureList: [],
  isGenerating: false,
  isPreviewLoading: false,
  error: null,
  selectedPreset: null,
  lastNLResult: null,
  autoResearchStatus: null,
  autoResearchLogs: [],
  explorerTaskId: null,
  explorerActiveTab: 'overview',
  explorerSelectedFeature: null,
  explorerSelectedFeatures: [],
  explorerSummary: null,
  explorerSummaryByTask: {},
  explorerFeatureNamesByTask: {},
  validationSummaryByTask:
    typeof window !== 'undefined'
      ? (() => {
          try {
            const raw = window.localStorage.getItem('ff:validationSummaryByTask');
            return raw ? (JSON.parse(raw) as Record<string, FeatureValidationSummary>) : {};
          } catch {
            return {};
          }
        })()
      : {},
  explorerRecentTasks:
    typeof window !== 'undefined'
      ? (() => {
          try {
            const raw = window.localStorage.getItem('ff:explorerRecentTasks');
            const parsed = raw ? JSON.parse(raw) : [];
            return Array.isArray(parsed) ? parsed.filter((v) => typeof v === 'string').slice(0, 10) : [];
          } catch {
            return [];
          }
        })()
      : [],
  schema: null,
  indicatorSearch: '',
  batchTask: null,
  batchStartedAtMs: null,
  batchConnectionStatus: 'idle',
  batchConnectionMessage: null,
  registryEntries: [],
  registryLoading: false,
  alignmentMode: 'open_minus',
  trainingTimeframes: ['12h'],
  setConfig: (config) =>
    set({
      config,
      alignmentMode: config.timeframes.alignment_mode ?? 'open_minus',
      trainingTimeframes: config.timeframes.training,
    }),
  updateConfigPartial: (partial) =>
    set((state) => ({
      config: state.config
        ? (mergeDeep(
            state.config as unknown as Record<string, unknown>,
            partial
          ) as unknown as FeatureFactoryConfig)
        : (partial as unknown as FeatureFactoryConfig),
    })),
  setPresets: (presets) => set({ presets }),
  setDataSources: (dataSources) => set({ dataSources }),
  setIndicators: (indicators) => set({ indicators }),
  setPreview: (preview) => set({ preview }),
  setCurrentTask: (task) =>
    set((state) => {
      if (task?.status === 'completed' && task.validation_summary && task.task_id) {
        const next = { ...state.validationSummaryByTask, [task.task_id]: task.validation_summary };
        try {
          window.localStorage.setItem('ff:validationSummaryByTask', JSON.stringify(next));
        } catch { /* ignore quota errors */ }
        return { currentTask: task, validationSummaryByTask: next };
      }
      return { currentTask: task };
    }),
  updateCurrentTaskPartial: (patch) =>
    set((state) => {
      const updated = state.currentTask ? { ...state.currentTask, ...patch } : null;
      if (updated?.status === 'completed' && updated.validation_summary && updated.task_id) {
        const next = { ...state.validationSummaryByTask, [updated.task_id]: updated.validation_summary };
        try {
          window.localStorage.setItem('ff:validationSummaryByTask', JSON.stringify(next));
        } catch { /* ignore quota errors */ }
        return { currentTask: updated, validationSummaryByTask: next };
      }
      return { currentTask: updated };
    }),
  setProgress: (progress) => set({ progress }),
  setFeatureList: (features) => set({ featureList: features }),
  setIsGenerating: (value) => set({ isGenerating: value }),
  setIsPreviewLoading: (value) => set({ isPreviewLoading: value }),
  setError: (error) => set({ error }),
  setSelectedPreset: (selectedPreset) => set({ selectedPreset }),
  setLastNLResult: (result) => set({ lastNLResult: result }),
  setAutoResearchStatus: (status) => set({ autoResearchStatus: status }),
  setAutoResearchLogs: (logs) => set({ autoResearchLogs: logs }),
  setExplorerTaskId: (taskId) => set({ explorerTaskId: taskId }),
  setExplorerActiveTab: (tab, selectedFeature) =>
    set((state) => ({
      explorerActiveTab: tab,
      explorerSelectedFeature:
        typeof selectedFeature === 'undefined' ? state.explorerSelectedFeature : selectedFeature,
    })),
  setExplorerSelectedFeatures: (features) => set({ explorerSelectedFeatures: features }),
  setExplorerSummary: (summary) => set({ explorerSummary: summary }),
  setExplorerSummaryForTask: (taskId, summary) =>
    set((state) => ({
      explorerSummaryByTask: { ...state.explorerSummaryByTask, [taskId]: summary },
      explorerSummary: summary,
    })),
  clearExplorerSummaryForTask: (taskId) =>
    set((state) => {
      if (!(taskId in state.explorerSummaryByTask)) return state;
      const next = { ...state.explorerSummaryByTask };
      delete next[taskId];
      return { explorerSummaryByTask: next };
    }),
  pushExplorerRecentTask: (taskId) =>
    set((state) => {
      if (!taskId) return state;
      const next = [taskId, ...state.explorerRecentTasks.filter((t) => t !== taskId)].slice(0, 10);
      if (typeof window !== 'undefined') {
        try {
          window.localStorage.setItem('ff:explorerRecentTasks', JSON.stringify(next));
        } catch {
          /* ignore quota errors */
        }
      }
      return { explorerRecentTasks: next };
    }),
  removeExplorerRecentTask: (taskId) =>
    set((state) => {
      const next = state.explorerRecentTasks.filter((t) => t !== taskId);
      if (typeof window !== 'undefined') {
        try {
          window.localStorage.setItem('ff:explorerRecentTasks', JSON.stringify(next));
        } catch {
          /* ignore */
        }
      }
      const summaries = { ...state.explorerSummaryByTask };
      delete summaries[taskId];
      const featureNames = { ...state.explorerFeatureNamesByTask };
      delete featureNames[taskId];
      const validationSummaries = { ...state.validationSummaryByTask };
      delete validationSummaries[taskId];
      try {
        window.localStorage.setItem('ff:validationSummaryByTask', JSON.stringify(validationSummaries));
      } catch { /* ignore */ }
      return { explorerRecentTasks: next, explorerSummaryByTask: summaries, explorerFeatureNamesByTask: featureNames, validationSummaryByTask: validationSummaries };
    }),
  setExplorerFeatureNamesForTask: (taskId, featureNames) =>
    set((state) => ({
      explorerFeatureNamesByTask: { ...state.explorerFeatureNamesByTask, [taskId]: featureNames },
    })),
  setValidationSummaryForTask: (taskId, summary) =>
    set((state) => {
      const next = { ...state.validationSummaryByTask, [taskId]: summary };
      try {
        window.localStorage.setItem('ff:validationSummaryByTask', JSON.stringify(next));
      } catch { /* ignore quota errors */ }
      return { validationSummaryByTask: next };
    }),
  setBatchTask: (batchTask) =>
    set((state) => ({
      batchTask: batchTask
        ? normalizeBatchTask(batchTask, state.batchTask, state.batchStartedAtMs ?? Date.now())
        : null,
      batchStartedAtMs: batchTask ? state.batchStartedAtMs ?? Date.now() : null,
      batchConnectionStatus: batchTask ? state.batchConnectionStatus : 'idle',
      batchConnectionMessage: batchTask ? state.batchConnectionMessage : null,
    })),
  applyBatchEvent: (payload) =>
    set((state) => {
      const startedAtMs = state.batchStartedAtMs ?? Date.now();
      return {
        batchTask: normalizeBatchTask(payload, state.batchTask, startedAtMs),
        batchStartedAtMs: startedAtMs,
      };
    }),
  setBatchConnectionState: (status, message = null) =>
    set({ batchConnectionStatus: status, batchConnectionMessage: message }),
  resumeBatch: async (batchId) => {
    const targetBatchId = batchId ?? get().batchTask?.batch_id ?? get().batchTask?.task_id;
    if (!targetBatchId) {
      set({ error: '找不到可 resume 的批次任務' });
      return false;
    }

    try {
      set({ error: null });
      const response = await fetch(`${API_BASE_URL}${API_PREFIX}/batch/${encodeURIComponent(targetBatchId)}/resume`, {
        method: 'POST',
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || payload?.error || response.statusText);
      }
      const payload = await response.json() as {
        batch_id: string;
        status: string;
        skipped_items: number;
        queued_items: number;
      };
      set((state) => ({
        batchTask: normalizeBatchTask(
          {
            batch_id: payload.batch_id,
            task_id: payload.batch_id,
            status: payload.status as BatchTaskStatus['status'],
            completed: payload.skipped_items,
            queued: payload.queued_items,
            progress: state.batchTask?.total
              ? payload.skipped_items / Math.max(state.batchTask.total, 1)
              : state.batchTask?.progress ?? 0,
          },
          state.batchTask,
          Date.now()
        ),
        batchStartedAtMs: Date.now(),
        batchConnectionStatus: 'connecting',
        batchConnectionMessage: null,
      }));
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : '批次 resume 失敗';
      set({ error: message });
      return false;
    }
  },
  fetchRegistry: async () => {
    set({ registryLoading: true });
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/feature-registry/entries`);
      if (!response.ok) {
        throw new Error(response.statusText);
      }

      const payload = (await response.json()) as { entries?: FeatureRegistryEntry[] };
      set({ registryEntries: payload.entries || [], registryLoading: false });
    } catch {
      set({ registryLoading: false });
    }
  },
  startBatchGeneration: async (symbols, timeframe, config, options) => {
    const normalizedSymbols = Array.from(
      new Set(
        symbols
          .map((symbol) => symbol.trim().toUpperCase())
          .filter((symbol) => symbol.length > 0)
      )
    );

    if (normalizedSymbols.length === 0) {
      set({ error: '請至少提供一個標的' });
      return;
    }

    try {
      set({ error: null });

      const response = await fetch(`${API_BASE_URL}${API_PREFIX}/batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          symbols: normalizedSymbols,
          timeframe,
          config_override: config,
          force_regenerate: options?.forceRegenerate ?? true,
          max_workers: options?.maxWorkers ?? 4,
        }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || payload?.error || response.statusText);
      }

      const payload = (await response.json()) as {
        task_id: string;
        status: 'pending' | 'running' | 'completed' | 'failed' | 'partial';
        total: number;
      };

      set({
        batchTask: {
          task_id: payload.task_id,
          batch_id: payload.task_id,
          status: payload.status,
          total: payload.total,
          completed: 0,
          failed: 0,
          progress: 0,
          current_timeframe: timeframe,
          queued: payload.total,
          eta_seconds: 0,
          resume_available: false,
          output_paths: [],
          per_item_rss: [],
          results: {},
          errors: {},
        },
        batchStartedAtMs: Date.now(),
        batchConnectionStatus: 'connecting',
        batchConnectionMessage: null,
      });

      await get().pollBatchStatus(payload.task_id);
    } catch (err) {
      const message = err instanceof Error ? err.message : '批次任務啟動失敗';
      set({ error: message });
    }
  },
  pollBatchStatus: async (taskId) => {
    const pollIntervalMs = 1200;
    const maxAttempts = 600;

    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      const response = await fetch(`${API_BASE_URL}${API_PREFIX}/batch/${taskId}`);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || payload?.error || response.statusText);
      }

      const status = (await response.json()) as BatchTaskStatus;
      set({ batchTask: status });

      if (['completed', 'failed', 'partial'].includes(status.status)) {
        return;
      }

      await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
    }

    set({ error: '批次任務輪詢逾時' });
  },
  setAlignmentMode: (mode) =>
    set((state) => ({
      alignmentMode: mode,
      config: state.config
        ? {
            ...state.config,
            timeframes: {
              ...state.config.timeframes,
              alignment_mode: mode,
            },
          }
        : state.config,
    })),
  setTrainingTimeframes: (tfs) => {
    const uniqueTfs = Array.from(new Set(tfs));
    set((state) => ({
      trainingTimeframes: uniqueTfs,
      config: state.config
        ? {
            ...state.config,
            timeframes: {
              ...state.config.timeframes,
              training: uniqueTfs,
            },
          }
        : state.config,
    }));
  },
  // Phase C: new actions
  setSchema: (schema) => set({ schema }),
  setIndicatorSearch: (indicatorSearch) => set({ indicatorSearch }),
  toggleIndicator: (category, indicatorName, enabled) =>
    set((state) => {
      if (!state.config) return {};
      const catCfg = state.config.atomic_indicators[category];
      if (!catCfg) return {};
      // For categories with indicators array (TA-Lib types)
      if (catCfg.indicators) {
        const updatedIndicators = catCfg.indicators.map((ind) =>
          ind.name === indicatorName ? { ...ind, enabled } : ind
        );
        return {
          config: {
            ...state.config,
            atomic_indicators: {
              ...state.config.atomic_indicators,
              [category]: { ...catCfg, indicators: updatedIndicators },
            },
          },
        };
      }
      // For categories with features dict (microstructure/entropy/tail_risk)
      if (catCfg.features) {
        const feat = catCfg.features[indicatorName];
        if (!feat) return {};
        return {
          config: {
            ...state.config,
            atomic_indicators: {
              ...state.config.atomic_indicators,
              [category]: {
                ...catCfg,
                features: { ...catCfg.features, [indicatorName]: { ...feat, enabled } },
              },
            },
          },
        };
      }
      return {};
    }),
  toggleAllInCategory: (category, enabled) =>
    set((state) => {
      if (!state.config) return {};
      const catCfg = state.config.atomic_indicators[category];
      if (!catCfg) return {};
      if (catCfg.indicators) {
        const updatedIndicators = catCfg.indicators.map((ind) => ({ ...ind, enabled }));
        return {
          config: {
            ...state.config,
            atomic_indicators: {
              ...state.config.atomic_indicators,
              [category]: { ...catCfg, indicators: updatedIndicators },
            },
          },
        };
      }
      if (catCfg.features) {
        const updatedFeatures: Record<string, { enabled: boolean; [key: string]: unknown }> = {};
        for (const [k, v] of Object.entries(catCfg.features)) {
          updatedFeatures[k] = { ...v, enabled };
        }
        return {
          config: {
            ...state.config,
            atomic_indicators: {
              ...state.config.atomic_indicators,
              [category]: { ...catCfg, features: updatedFeatures },
            },
          },
        };
      }
      return {};
    }),
  toggleCategory: (category, enabled) =>
    set((state) => {
      if (!state.config) return {};
      const catCfg = state.config.atomic_indicators[category];
      if (!catCfg) return {};
      return {
        config: {
          ...state.config,
          atomic_indicators: {
            ...state.config.atomic_indicators,
            [category]: { ...catCfg, enabled },
          },
        },
      };
    }),
  toggleAggregator: (name, enabled) =>
    set((state) => {
      if (!state.config?.rolling_aggregation) return {};
      const aggs = state.config.rolling_aggregation.aggregators;
      if (!aggs || Array.isArray(aggs)) return {};
      const aggCfg = aggs[name];
      if (!aggCfg) return {};
      return {
        config: {
          ...state.config,
          rolling_aggregation: {
            ...state.config.rolling_aggregation,
            aggregators: { ...aggs, [name]: { ...aggCfg, enabled } },
          },
        },
      };
    }),
  toggleAllAggregators: (enabled) =>
    set((state) => {
      if (!state.config?.rolling_aggregation) return {};
      const aggs = state.config.rolling_aggregation.aggregators;
      if (!aggs || Array.isArray(aggs)) return {};
      const updated: Record<string, { enabled: boolean; [key: string]: unknown }> = {};
      for (const [k, v] of Object.entries(aggs)) {
        updated[k] = { ...v, enabled };
      }
      return {
        config: {
          ...state.config,
          rolling_aggregation: {
            ...state.config.rolling_aggregation,
            aggregators: updated,
          },
        },
      };
    }),
  toggleMetaSubEngine: (name, enabled) =>
    set((state) => {
      if (!state.config) return {};
      return {
        config: {
          ...state.config,
          meta_features: {
            ...state.config.meta_features,
            [name]: enabled,
          },
        },
      };
    }),
  toggleCrossFeature: (name, enabled) =>
    set((state) => {
      if (!state.config?.cross_sectional) return {};
      const feats = state.config.cross_sectional.features;
      if (!feats || Array.isArray(feats)) return {};
      const feat = feats[name];
      if (!feat) return {};
      return {
        config: {
          ...state.config,
          cross_sectional: {
            ...state.config.cross_sectional,
            features: { ...feats, [name]: { ...feat, enabled } },
          },
        },
      };
    }),
  toggleOperator: (name, enabled) =>
    set((state) => {
      if (!state.config?.operators) return {};
      const opCfg = state.config.operators[name];
      if (!opCfg || typeof opCfg !== 'object') return {};
      return {
        config: {
          ...state.config,
          operators: {
            ...state.config.operators,
            [name]: { ...opCfg, enabled },
          },
        },
      };
    }),
}));

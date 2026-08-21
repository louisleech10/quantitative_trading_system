import { useCallback, useEffect, useRef } from 'react';
import {
  DeepAnalysisConfig,
  DeepAnalysisResponse,
  FeatureListItem,
  ICAnalysisConfig,
  ICReport,
} from '@/lib/types';
import { useICAnalysisStore } from '@/store/icAnalysisStore';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
const API_PREFIX = '/api/v1/ic';

const requestJson = async <T>(path: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload?.detail || payload?.error || response.statusText);
  }

  return response.json();
};

const buildConfigOverride = (config: ICAnalysisConfig) => {
  const thresholds: Record<string, number> = {
    ic_mean_min: config.thresholds.ic_mean_min,
    icir_min: config.thresholds.icir_min,
    p_value_max: config.thresholds.p_value_max,
  };

  if (typeof config.thresholds.monotonicity_score_min === 'number') {
    thresholds.monotonicity_score_min = config.thresholds.monotonicity_score_min;
  }

  return {
    thresholds,
    redundancy: {
      correlation_threshold: config.thresholds.correlation_threshold,
    },
    labels: {
      horizons: config.horizons,
    },
  };
};

const buildRefilterPayload = (thresholds: ICAnalysisConfig['thresholds']) => ({
  ic_mean_min: thresholds.ic_mean_min,
  icir_min: thresholds.icir_min,
  p_value_max: thresholds.p_value_max,
  monotonicity_score_min: thresholds.monotonicity_score_min,
  correlation_threshold: thresholds.correlation_threshold,
});

export function useICAnalysis() {
  const {
    setTask,
    setProgress,
    setStatus,
    setError,
    setReport,
  } = useICAnalysisStore();

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const retryCountRef = useRef(0);
  const terminalRef = useRef(false);

  const clearTimers = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  const fetchResult = useCallback(
    async (taskId: string) => {
      const result = await requestJson<ICReport>(`/result/${taskId}`);
      setReport(result);
      return result;
    },
    [setReport]
  );

  const fetchTaskStatus = useCallback(
    async (taskId: string) => {
      const status = await requestJson<{
        task_id: string;
        status: string;
        progress: number;
        current_stage?: string | null;
        error?: string | null;
      }>(`/task/${taskId}`);
      setStatus(status.status as 'pending' | 'running' | 'completed' | 'failed');
      setProgress(status.progress ?? 0, status.current_stage ?? null);

      if (status.status === 'failed') {
        terminalRef.current = true;
        clearTimers();
        setError(status.error || 'IC analysis failed');
      } else if (status.status === 'completed') {
        terminalRef.current = true;
        clearTimers();
        await fetchResult(taskId);
      }

      return status;
    },
    [clearTimers, fetchResult, setError, setProgress, setStatus]
  );

  const startPolling = useCallback(
    (taskId: string) => {
      if (pollIntervalRef.current || terminalRef.current) {
        return;
      }
      setError(null);
      pollIntervalRef.current = setInterval(() => {
        void fetchTaskStatus(taskId).catch((err) => {
          setError(err instanceof Error ? err.message : 'IC analysis polling failed');
        });
      }, 2000);
    },
    [fetchTaskStatus, setError]
  );

  const connectProgress = useCallback((taskId: string) => {
    if (!taskId) {
      return;
    }

    terminalRef.current = false;

    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
    }

    const ws = new WebSocket(`${WS_BASE_URL}/ws/ic-analysis/${taskId}`);

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message?.event === 'progress' && message?.data) {
          const payload = message.data;
          // 收到有效進度 = 連線健康，清掉先前的 transient「連線失敗」誤報
          if (payload.status !== 'failed') {
            setError(null);
          }
          setProgress(payload.progress ?? 0, payload.stage ?? payload.current_stage ?? null);
          if (payload.status) {
            setStatus(payload.status);
          }
          if (payload.status === 'failed') {
            terminalRef.current = true;
            clearTimers();
            setError(payload.message || payload.error || 'IC analysis failed');
            ws.close();
            return;
          }
          if (payload.status === 'completed') {
            terminalRef.current = true;
            clearTimers();
            void fetchResult(taskId);
            ws.close();
            return;
          }
          return;
        }

        if (message?.event === 'ping') {
          ws.send(JSON.stringify({ type: 'pong' }));
          return;
        }
      } catch (err) {
        console.error('[useICAnalysis] Failed to parse message', err);
      }
    };

    ws.onerror = () => {
      // 不在 transient onerror 喊通用「連線失敗」(會誤報且不清除)。
      // 交給 onclose retry(≤3)→ poll fallback;真失敗由 poll/status.error 顯真錯誤(U-2)。
    };

    ws.onclose = () => {
      if (terminalRef.current) {
        return;
      }

      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }

      if (retryCountRef.current >= 3) {
        startPolling(taskId);
        return;
      }

      retryCountRef.current += 1;
      reconnectTimerRef.current = setTimeout(() => {
        connectProgress(taskId);
      }, 3000);
    };

    wsRef.current = ws;
  }, [clearTimers, fetchResult, setError, setProgress, setStatus, startPolling]);

  const startAnalysis = useCallback(
    async (config: ICAnalysisConfig) => {
      const hasLibrarySelection = Boolean(
        config.symbol && config.timeframe && config.config_hash
      );
      const hasCrossSectionSelection = Boolean(
        config.mode === 'cross_sectional' &&
        config.timeframe &&
        (config.cross_sectional_runs?.length || 0) >= 2
      );

      if (!hasLibrarySelection && !hasCrossSectionSelection) {
        throw new Error('請選擇 Run 或橫截面批次');
      }

      const effectiveConfig = useICAnalysisStore.getState().getEffectiveConfig();
      const featureFilter = useICAnalysisStore.getState().featureFilter;
      const isCrossSectionalMode = config.mode === 'cross_sectional';

      const normalizedFeatureFilter = {
        include_features:
          featureFilter.include_features && featureFilter.include_features.length > 0
            ? featureFilter.include_features
            : undefined,
        exclude_features:
          featureFilter.exclude_features && featureFilter.exclude_features.length > 0
            ? featureFilter.exclude_features
            : undefined,
        include_pattern: featureFilter.include_pattern?.trim() || undefined,
        include_categories:
          featureFilter.include_categories && featureFilter.include_categories.length > 0
            ? featureFilter.include_categories
            : undefined,
        include_data_sources:
          featureFilter.include_data_sources && featureFilter.include_data_sources.length > 0
            ? featureFilter.include_data_sources
            : undefined,
        include_families:
          featureFilter.include_families && featureFilter.include_families.length > 0
            ? featureFilter.include_families
            : undefined,
        max_features:
          typeof featureFilter.max_features === 'number' && featureFilter.max_features > 0
            ? featureFilter.max_features
            : undefined,
      };

      const hasFeatureFilter = Object.values(normalizedFeatureFilter).some((value) => value !== undefined);

      const payload = {
        mode: isCrossSectionalMode ? 'cross_sectional' : 'longitudinal',
        symbol: isCrossSectionalMode ? undefined : config.symbol || undefined,
        symbols: isCrossSectionalMode ? config.cross_sectional_symbols || [] : undefined,
        cross_sectional_runs: isCrossSectionalMode ? config.cross_sectional_runs || [] : undefined,
        timeframe: config.timeframe || undefined,
        config_hash: isCrossSectionalMode ? undefined : config.config_hash || undefined,
        config_override: {
          ...buildConfigOverride(config),
          ...(effectiveConfig.feature_tiers ? { feature_tiers: effectiveConfig.feature_tiers } : {}),
        },
        feature_tiers: effectiveConfig.feature_tiers,
        feature_filter: hasFeatureFilter ? normalizedFeatureFilter : undefined,
        event_query: config.mode === 'event' ? config.event_query?.trim() || undefined : undefined,
        // GAP-3 B5.2：從已匯入案例選事件 ⇒ 帶 event_timestamps（bar open 秒；picker 已 ms→秒）
        event_timestamps:
          config.mode === 'event' && config.event_timestamps && config.event_timestamps.length > 0
            ? config.event_timestamps
            : undefined,
      };

      const result = await requestJson<{ task_id: string; status: string }>('/analyze', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      setTask(result.task_id, result.status === 'running' ? 'running' : 'pending');
      setStatus(result.status === 'running' ? 'running' : 'pending');
      retryCountRef.current = 0;
      connectProgress(result.task_id);

      return result.task_id;
    },
    [connectProgress, setStatus, setTask]
  );

  const fetchSummary = useCallback(async (taskId: string) => {
    const data = await requestJson<{ task_id: string; summary: string }>(`/summary/${taskId}`);
    return data.summary;
  }, []);

  const fetchAvailableFeatures = useCallback(
    async (symbol: string, timeframe: string, configHash: string) => {
      const params = new URLSearchParams({
        symbol,
        timeframe,
        config_hash: configHash,
      });
      const data = await requestJson<{ total: number; features: FeatureListItem[] }>(
        `/features/list?${params.toString()}`
      );
      return data.features;
    },
    []
  );

  const startDeepAnalysis = useCallback(
    async (taskId: string, config: DeepAnalysisConfig) => {
      // request 欄名 net_ic;模組鍵 net_ic_analysis — service 負責映射
      const payload = {
        selected_features: config.selected_features,
        top_n: config.top_n ?? 30,
        modules: config.modules,
        config_override: config.config_override,
        net_ic: config.net_ic ?? { cost_enabled: false, cost_bps: null },
      };
      const result = await requestJson<{ task_id: string; status: string }>(`/deep-analysis/${taskId}`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      setTask(result.task_id, result.status === 'running' ? 'running' : 'pending');
      setStatus(result.status === 'running' ? 'running' : 'pending');
      retryCountRef.current = 0;
      connectProgress(result.task_id);

      return result.task_id;
    },
    [connectProgress, setStatus, setTask]
  );

  const fetchDeepAnalysisResult = useCallback(async (taskId: string) => {
    return requestJson<DeepAnalysisResponse>(`/deep-analysis/${taskId}/result`);
  }, []);

  const refilter = useCallback(
    async (taskId: string, thresholds: ICAnalysisConfig['thresholds']) => {
      const result = await requestJson<ICReport>(`/refilter?task_id=${taskId}`, {
        method: 'POST',
        body: JSON.stringify({ thresholds: buildRefilterPayload(thresholds) }),
      });
      setReport(result);
      return result;
    },
    [setReport]
  );

  const applyTransforms = useCallback(
    async (
      taskId: string,
      payload: {
        selected_features: string[];
        rank: boolean;
        zscore: boolean;
        gaussian: boolean;
        rank_window?: number;
        zscore_windows?: number[];
      }
    ) => {
      return requestJson<{
        task_id: string;
        selected_feature_count: number;
        transforms_applied: string[];
        output_path: string;
        output_rows: number;
        output_cols: number;
      }>(`/apply-transforms/${taskId}`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },
    []
  );

  useEffect(() => {
    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, []);

  return {
    startAnalysis,
    fetchTaskStatus,
    fetchResult,
    fetchSummary,
    fetchAvailableFeatures,
    startDeepAnalysis,
    fetchDeepAnalysisResult,
    refilter,
    applyTransforms,
    connectProgress,
  };
}

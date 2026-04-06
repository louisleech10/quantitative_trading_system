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

  const connectProgress = useCallback((taskId: string) => {
    if (!taskId) {
      return;
    }

    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(`${WS_BASE_URL}/ws/ic-analysis/${taskId}`);

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message?.event === 'progress' && message?.data) {
          const payload = message.data;
          setProgress(payload.progress ?? 0, payload.stage ?? payload.current_stage ?? null);
          if (payload.status) {
            setStatus(payload.status);
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
      setError('WebSocket 連線失敗');
    };

    ws.onclose = () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }

      reconnectTimerRef.current = setTimeout(() => {
        connectProgress(taskId);
      }, 3000);
    };

    wsRef.current = ws;
  }, [setError, setProgress, setStatus]);

  const startAnalysis = useCallback(
    async (config: ICAnalysisConfig) => {
      const featuresPath = config.features_path.trim();
      const hasLibrarySelection = Boolean(config.symbol && config.timeframe);
      const hasCrossSectionSelection = Boolean(
        config.mode === 'cross_sectional' &&
        config.timeframe &&
        (config.cross_sectional_symbols?.length || 0) >= 2
      );

      if (!featuresPath && !hasLibrarySelection && !hasCrossSectionSelection) {
        throw new Error('請提供特徵檔案路徑，或選擇 Symbol/Timeframe');
      }

      const effectiveConfig = useICAnalysisStore.getState().getEffectiveConfig();
      const featureFilter = useICAnalysisStore.getState().featureFilter;
      const isCrossSectionalMode = config.mode === 'cross_sectional';

      const normalizedFeatureFilter = {
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
        features_path: featuresPath || undefined,
        symbol: isCrossSectionalMode ? undefined : config.symbol || undefined,
        symbols: isCrossSectionalMode ? config.cross_sectional_symbols || [] : undefined,
        timeframe: config.timeframe || undefined,
        labels_path: config.labels_path?.trim() || undefined,
        meta_path: config.meta_path?.trim() || undefined,
        config_override: {
          ...buildConfigOverride(config),
          ...(effectiveConfig.feature_tiers ? { feature_tiers: effectiveConfig.feature_tiers } : {}),
        },
        feature_tiers: effectiveConfig.feature_tiers,
        feature_filter: hasFeatureFilter ? normalizedFeatureFilter : undefined,
        event_query: config.mode === 'event' ? config.event_query?.trim() || undefined : undefined,
      };

      const result = await requestJson<{ task_id: string; status: string }>('/analyze', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      setTask(result.task_id, result.status === 'running' ? 'running' : 'pending');
      setStatus(result.status === 'running' ? 'running' : 'pending');
      connectProgress(result.task_id);

      return result.task_id;
    },
    [connectProgress, setStatus, setTask]
  );

  const fetchTaskStatus = useCallback(
    async (taskId: string) => {
      const status = await requestJson<{ task_id: string; status: string; progress: number; current_stage?: string }>(
        `/task/${taskId}`
      );
      setStatus(status.status as 'pending' | 'running' | 'completed' | 'failed');
      setProgress(status.progress ?? 0, status.current_stage ?? null);
      return status;
    },
    [setProgress, setStatus]
  );

  const fetchResult = useCallback(
    async (taskId: string) => {
      const result = await requestJson<ICReport>(`/result/${taskId}`);
      setReport(result);
      return result;
    },
    [setReport]
  );

  const fetchSummary = useCallback(async (taskId: string) => {
    const data = await requestJson<{ task_id: string; summary: string }>(`/summary/${taskId}`);
    return data.summary;
  }, []);

  const fetchAvailableFeatures = useCallback(async (featuresPath: string, metaPath?: string) => {
    const params = new URLSearchParams({ features_path: featuresPath });
    if (metaPath) {
      params.set('meta_path', metaPath);
    }
    const data = await requestJson<{ total: number; features: FeatureListItem[] }>(`/features/list?${params.toString()}`);
    return data.features;
  }, []);

  const startDeepAnalysis = useCallback(
    async (taskId: string, config: DeepAnalysisConfig) => {
      const payload = {
        selected_features: config.selected_features,
        top_n: config.top_n ?? 30,
        modules: config.modules,
        config_override: config.config_override,
      };
      const result = await requestJson<{ task_id: string; status: string }>(`/deep-analysis/${taskId}`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      setTask(result.task_id, result.status === 'running' ? 'running' : 'pending');
      setStatus(result.status === 'running' ? 'running' : 'pending');
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

  useEffect(() => {
    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
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
    connectProgress,
  };
}

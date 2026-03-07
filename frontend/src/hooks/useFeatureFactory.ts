import { useCallback } from 'react';
import {
  FeatureFactoryConfig,
  FeatureFactoryPreset,
  FeatureIndicatorSpec,
  FeaturePreview,
  FeatureTask,
  FeatureNLResult,
  FeatureGenerationResult,
  BrowseFeaturesResponse,
  FeatureSummary,
  BrowseCorrelationMatrix,
  DistributionData,
  NanPatternData,
  BrowseFeatureDataResponse,
} from '@/lib/types';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1/features';

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

const normalizeConfig = (config: FeatureFactoryConfig): FeatureFactoryConfig => {
  const raw = config as FeatureFactoryConfig & {
    global?: FeatureFactoryConfig['global_settings'];
  };

  if (!raw.global_settings && raw.global) {
    return {
      ...raw,
      global_settings: raw.global,
    };
  }

  return raw;
};

const normalizeConfigPatch = (patch: Record<string, unknown>) => {
  if ('global' in patch && !('global_settings' in patch)) {
    return {
      ...patch,
      global_settings: patch.global,
    };
  }

  return patch;
};

export function useFeatureFactory() {
  const {
    setConfig,
    setPresets,
    setDataSources,
    setIndicators,
    setPreview,
    setCurrentTask,
    setIsGenerating,
    setIsPreviewLoading,
    setError,
    setFeatureList,
    setLastNLResult,
    updateConfigPartial,
    setExplorerSummary,
  } = useFeatureFactoryStore();

  const loadInitial = useCallback(async () => {
    try {
      const [config, presets, indicators, dataSources] = await Promise.all([
        requestJson<FeatureFactoryConfig>('/config'),
        requestJson<FeatureFactoryPreset[]>('/presets'),
        requestJson<FeatureIndicatorSpec[]>('/indicators'),
        requestJson<unknown[]>('/data-sources'),
      ]);

      const normalizedSources = dataSources
        .map((source) => {
          if (typeof source === 'string') {
            return source;
          }
          if (source && typeof source === 'object' && 'name' in source) {
            const name = (source as { name?: unknown }).name;
            return typeof name === 'string' ? name : null;
          }
          return null;
        })
        .filter((source): source is string => Boolean(source));

      const normalizedPresets = presets.map((preset) => ({
        ...preset,
        config: preset.config ? normalizeConfig(preset.config) : undefined,
      }));

      setConfig(normalizeConfig(config));
      setPresets(normalizedPresets);
      setIndicators(indicators);
      setDataSources(normalizedSources);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : '載入初始化資料失敗';
      setError(message);
    }
  }, [setConfig, setPresets, setIndicators, setDataSources, setError]);

  const previewConfig = useCallback(
    async (configOverride: FeatureFactoryConfig) => {
      setIsPreviewLoading(true);
      try {
        const preview = await requestJson<FeaturePreview>('/preview', {
          method: 'POST',
          body: JSON.stringify({ config_override: configOverride }),
        });
        setPreview(preview);
        setError(null);
      } catch (err) {
        const message = err instanceof Error ? err.message : '預覽失敗';
        setError(message);
      } finally {
        setIsPreviewLoading(false);
      }
    },
    [setPreview, setIsPreviewLoading, setError]
  );

  const startGeneration = useCallback(
    async (symbol: string, timeframe: string, configOverride: FeatureFactoryConfig) => {
      setIsGenerating(true);
      try {
        const payload = await requestJson<{ task_id: string; status: string }>('/generate', {
          method: 'POST',
          body: JSON.stringify({
            symbol,
            timeframe,
            config_override: configOverride,
          }),
        });

        const task: FeatureTask = {
          task_id: payload.task_id,
          status: payload.status,
          progress: 0,
          current_stage: null,
          completed_stages: [],
          error: null,
        };

        setCurrentTask(task);
      } catch (err) {
        const message = err instanceof Error ? err.message : '生成啟動失敗';
        setError(message);
      } finally {
        setIsGenerating(false);
      }
    },
    [setCurrentTask, setIsGenerating, setError]
  );

  const requestNL2Config = useCallback(
    async (text: string) => {
      try {
        const result = await requestJson<FeatureNLResult>('/nl2config', {
          method: 'POST',
          body: JSON.stringify({ text }),
        });
        setLastNLResult(result);
        if (result.config_patch) {
          updateConfigPartial(normalizeConfigPatch(result.config_patch));
        }
        setError(null);
      } catch (err) {
        const message = err instanceof Error ? err.message : '自然語言解析失敗';
        setError(message);
      }
    },
    [setLastNLResult, updateConfigPartial, setError]
  );

  const loadTaskResult = useCallback(
    async (taskId: string) => {
      try {
        const result = await requestJson<FeatureGenerationResult>(`/result/${taskId}`);
        setFeatureList(result.feature_names || []);
      } catch (err) {
        const message = err instanceof Error ? err.message : '結果載入失敗';
        setError(message);
      }
    },
    [setFeatureList, setError]
  );

  const browseFeatures = useCallback(
    async (
      taskId: string,
      params: {
        offset?: number;
        limit?: number;
        cursor?: string;
        sortBy?: string;
        sortOrder?: 'asc' | 'desc';
        category?: string;
        level?: 'L1' | 'L2' | 'L3';
        search?: string;
        detailLevel?: 'full' | 'table';
      }
    ) => {
      const query = new URLSearchParams();
      query.set('offset', String(params.offset ?? 0));
      query.set('limit', String(params.limit ?? 50));
      if (params.cursor) query.set('cursor', params.cursor);
      if (params.sortBy) query.set('sort_by', params.sortBy);
      if (params.sortOrder) query.set('sort_order', params.sortOrder);
      if (params.category) query.set('category', params.category);
      if (params.level) query.set('level', params.level);
      if (params.search) query.set('search', params.search);
      if (params.detailLevel) query.set('detail_level', params.detailLevel);
      return requestJson<BrowseFeaturesResponse>(`/browse/${taskId}/features?${query.toString()}`);
    },
    []
  );

  const browseSummary = useCallback(
    async (taskId: string) => {
      const summary = await requestJson<FeatureSummary>(`/browse/${taskId}/summary`);
      setExplorerSummary(summary);
      return summary;
    },
    [setExplorerSummary]
  );

  const browseCorrelation = useCallback(
    async (taskId: string, features: string[], method: 'pearson' | 'spearman' | 'kendall' = 'pearson') => {
      const query = new URLSearchParams({
        features: features.join(','),
        method,
      });
      return requestJson<BrowseCorrelationMatrix>(`/browse/${taskId}/correlation?${query.toString()}`);
    },
    []
  );

  const browseDistribution = useCallback(
    async (taskId: string, feature: string, nBins = 50) => {
      const query = new URLSearchParams({ feature, n_bins: String(nBins) });
      return requestJson<DistributionData>(`/browse/${taskId}/distribution?${query.toString()}`);
    },
    []
  );

  const browseNanPattern = useCallback(
    async (taskId: string, sampleFeatures = 50) => {
      const query = new URLSearchParams({ sample_features: String(sampleFeatures) });
      return requestJson<NanPatternData>(`/browse/${taskId}/nan-pattern?${query.toString()}`);
    },
    []
  );

  const browseData = useCallback(
    async (taskId: string, features: string[], offset = 0, limit = 200) => {
      const query = new URLSearchParams({
        features: features.join(','),
        offset: String(offset),
        limit: String(limit),
      });
      return requestJson<BrowseFeatureDataResponse>(`/browse/${taskId}/data?${query.toString()}`);
    },
    []
  );

  return {
    loadInitial,
    previewConfig,
    startGeneration,
    requestNL2Config,
    loadTaskResult,
    browseFeatures,
    browseSummary,
    browseCorrelation,
    browseDistribution,
    browseNanPattern,
    browseData,
  };
}

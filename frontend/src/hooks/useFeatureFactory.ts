import { useCallback } from 'react';
import {
  FeatureFactoryConfig,
  FeatureFactoryPreset,
  FeatureIndicatorSpec,
  FeaturePreview,
  FeatureTask,
  FeatureNLResult,
  FeatureGenerationResult,
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

      setConfig(normalizeConfig(config));
      setPresets(presets);
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

  return {
    loadInitial,
    previewConfig,
    startGeneration,
    requestNL2Config,
    loadTaskResult,
  };
}

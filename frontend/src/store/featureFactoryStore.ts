import { create } from 'zustand';
import {
  FeatureFactoryConfig,
  FeaturePreview,
  FeatureTask,
  FeatureFactoryPreset,
  FeatureIndicatorSpec,
  FeatureGenerationProgress,
  FeatureNLResult,
  AutoResearchStatus,
  AutoResearchLogEntry,
  FeatureSummary,
  ExplorerTab,
  FeatureSchema,
} from '@/lib/types';

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
  // Phase C: schema and search
  schema: FeatureSchema | null;
  indicatorSearch: string;
  setConfig: (config: FeatureFactoryConfig) => void;
  updateConfigPartial: (partial: Record<string, unknown>) => void;
  setPresets: (presets: FeatureFactoryPreset[]) => void;
  setDataSources: (sources: string[]) => void;
  setIndicators: (indicators: FeatureIndicatorSpec[]) => void;
  setPreview: (preview: FeaturePreview | null) => void;
  setCurrentTask: (task: FeatureTask | null) => void;
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

export const useFeatureFactoryStore = create<FeatureFactoryState>((set) => ({
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
  schema: null,
  indicatorSearch: '',
  setConfig: (config) => set({ config }),
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
  setCurrentTask: (task) => set({ currentTask: task }),
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
      if (!opCfg) return {};
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

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
}));

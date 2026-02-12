import { create } from 'zustand';
import { ICAnalysisConfig, ICReport } from '@/lib/types';

type ICAnalysisStatus = 'idle' | 'pending' | 'running' | 'completed' | 'failed';

interface ICAnalysisState {
  config: ICAnalysisConfig;
  taskId: string | null;
  status: ICAnalysisStatus;
  progress: number;
  currentStage: string | null;
  error: string | null;
  report: ICReport | null;
  selectedFeature: string | null;
  setConfig: (config: ICAnalysisConfig) => void;
  updateConfig: (patch: Partial<ICAnalysisConfig>) => void;
  setTask: (taskId: string | null, status?: ICAnalysisStatus) => void;
  setProgress: (progress: number, currentStage?: string | null) => void;
  setStatus: (status: ICAnalysisStatus) => void;
  setReport: (report: ICReport | null) => void;
  setError: (error: string | null) => void;
  setSelectedFeature: (featureName: string | null) => void;
  resetReport: () => void;
}

const defaultConfig: ICAnalysisConfig = {
  features_path: '',
  labels_path: '',
  meta_path: '',
  mode: 'global',
  event_query: '',
  horizons: [1, 2, 3, 5, 8, 13, 21],
  thresholds: {
    ic_mean_min: 0.02,
    icir_min: 0.5,
    p_value_max: 0.05,
    monotonicity_score_min: 0.6,
    correlation_threshold: 0.7,
  },
};

export const useICAnalysisStore = create<ICAnalysisState>((set) => ({
  config: defaultConfig,
  taskId: null,
  status: 'idle',
  progress: 0,
  currentStage: null,
  error: null,
  report: null,
  selectedFeature: null,
  setConfig: (config) => set({ config }),
  updateConfig: (patch) =>
    set((state) => ({
      config: {
        ...state.config,
        ...patch,
        thresholds: {
          ...state.config.thresholds,
          ...(patch.thresholds || {}),
        },
      },
    })),
  setTask: (taskId, status) =>
    set({
      taskId,
      status: status ?? (taskId ? 'pending' : 'idle'),
      progress: taskId ? 0 : 0,
      currentStage: null,
    }),
  setProgress: (progress, currentStage) => set({ progress, currentStage }),
  setStatus: (status) => set({ status }),
  setReport: (report) => set({ report }),
  setError: (error) => set({ error }),
  setSelectedFeature: (featureName) => set({ selectedFeature: featureName }),
  resetReport: () =>
    set({
      report: null,
      selectedFeature: null,
      progress: 0,
      currentStage: null,
      error: null,
    }),
}));

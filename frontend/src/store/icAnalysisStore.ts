import { create } from 'zustand';
import {
  DeepAnalysisConfig,
  FeatureTierLevel,
  FeatureFilterConfig,
  FeatureListItem,
  ICAnalysisConfig,
  ICEventScanDisclosure,
  ICReport,
  ModuleStatus,
  NetICAnalysisRequest,
} from '@/lib/types';

type ICAnalysisStatus = 'idle' | 'pending' | 'running' | 'completed' | 'failed';

interface ICAnalysisState {
  config: ICAnalysisConfig;
  taskId: string | null;
  status: ICAnalysisStatus;
  progress: number;
  currentStage: string | null;
  /** GAP-3 UX Task 6.3：這個 run 有幾個特徵；解析不到為 null（**不填假值**）。 */
  featureCount: number | null;
  /**
   * `G3-D2` D4.2／D4.3：**後端**回傳之事件分析揭露（兩上界、k 雙值、掃描結果）。
   * 🔴 尚未分析 ⇒ `null`，前端**不猜數字**（上界之公式住 producer，重算即第二份實作）。
   */
  eventScanDisclosure: ICEventScanDisclosure | null;
  error: string | null;
  report: ICReport | null;
  selectedFeature: string | null;
  availableFeatures: FeatureListItem[];
  featureFilter: FeatureFilterConfig;
  selectedFeatures: string[];
  deepAnalysisModules: DeepAnalysisConfig['modules'];
  /** 成本參數(request 欄 net_ic);預設關閉、無寫死 bps。 */
  netIcConfig: NetICAnalysisRequest;
  deepAnalysisStatus: 'idle' | 'running' | 'completed' | 'failed';
  deepAnalysisProgress: number;
  deepAnalysisReport: ICReport | null;
  deepAnalysisModuleStatus: ModuleStatus[];
  activeTab: 'basic' | 'deep';
  featureTier: FeatureTierLevel;
  featureToggles: Record<string, boolean>;
  setConfig: (config: ICAnalysisConfig) => void;
  updateConfig: (patch: Partial<ICAnalysisConfig>) => void;
  setTask: (taskId: string | null, status?: ICAnalysisStatus) => void;
  setProgress: (progress: number, currentStage?: string | null) => void;
  setFeatureCount: (featureCount: number | null) => void;
  setEventScanDisclosure: (d: ICEventScanDisclosure | null) => void;
  setStatus: (status: ICAnalysisStatus) => void;
  setReport: (report: ICReport | null) => void;
  setError: (error: string | null) => void;
  setSelectedFeature: (featureName: string | null) => void;
  setAvailableFeatures: (features: FeatureListItem[]) => void;
  setFeatureFilter: (filter: FeatureFilterConfig) => void;
  setSelectedFeatures: (featureNames: string[]) => void;
  setDeepAnalysisModules: (modules: DeepAnalysisConfig['modules']) => void;
  setNetIcConfig: (config: NetICAnalysisRequest) => void;
  setDeepAnalysisStatus: (status: ICAnalysisState['deepAnalysisStatus']) => void;
  setDeepAnalysisProgress: (progress: number) => void;
  setDeepAnalysisReport: (report: ICReport | null) => void;
  setDeepAnalysisModuleStatus: (moduleStatus: ModuleStatus[]) => void;
  setActiveTab: (tab: 'basic' | 'deep') => void;
  setFeatureTier: (tier: FeatureTierLevel) => void;
  toggleFeature: (key: string) => void;
  getEffectiveConfig: () => Partial<ICAnalysisConfig>;
  /** 組 deep-analysis request body(含 net_ic)。 */
  buildDeepAnalysisRequest: (opts: {
    selected_features?: string[];
    top_n?: number;
    config_override?: Record<string, unknown>;
  }) => DeepAnalysisConfig;
  resetReport: () => void;
}

const PRESET_TOGGLES: Record<'foundation' | 'intermediate' | 'advanced', Record<string, boolean>> = {
  foundation: {
    ic_calculation: true,
    ic_method_selection: true,
    winsorization_method: true,
    monotonicity_test: true,
    ai_summary: true,
    return_type_selection: false,
    ic_decay: false,
    grouped_ic: false,
    ic_autocorrelation: false,
    event_filtering: false,
    redundancy_method_selection: false,
    turnover_analysis: false,
    // F5.2 tier truth: foundation 不含 factor_return(仍 false)
    factor_return: false,
    trend_analysis: false,
    parameter_sensitivity: false,
    rolling_oos: false,
    long_short_analysis: false,
    feature_quality_diagnostics: false,
    net_ic_analysis: false,
    fdr_correction: true,
    marginal_ic: true,
    vif_filter: false,
    factor_centrality: false,
    factor_orthogonalization: false,
    factor_exposure: false,
  },
  intermediate: {
    ic_calculation: true,
    ic_method_selection: true,
    winsorization_method: true,
    monotonicity_test: true,
    ai_summary: true,
    return_type_selection: true,
    ic_decay: true,
    grouped_ic: true,
    ic_autocorrelation: true,
    event_filtering: true,
    redundancy_method_selection: true,
    turnover_analysis: true,
    // F5.2 tier truth: intermediate 含 factor_return(schema enabled=True)
    factor_return: true,
    trend_analysis: true,
    parameter_sensitivity: true,
    rolling_oos: true,
    long_short_analysis: true,
    feature_quality_diagnostics: true,
    net_ic_analysis: true,
    fdr_correction: true,
    marginal_ic: true,
    vif_filter: false,
    factor_centrality: true,
    factor_orthogonalization: false,
    factor_exposure: false,
  },
  advanced: {
    ic_calculation: true,
    ic_method_selection: true,
    winsorization_method: true,
    monotonicity_test: true,
    ai_summary: true,
    return_type_selection: true,
    ic_decay: true,
    grouped_ic: true,
    ic_autocorrelation: true,
    event_filtering: true,
    redundancy_method_selection: true,
    turnover_analysis: true,
    // F5.2 tier truth: advanced 含 factor_return(schema enabled=True)
    factor_return: true,
    trend_analysis: true,
    parameter_sensitivity: true,
    rolling_oos: true,
    long_short_analysis: true,
    feature_quality_diagnostics: true,
    net_ic_analysis: true,
    fdr_correction: true,
    marginal_ic: true,
    vif_filter: true,
    factor_centrality: true,
    factor_orthogonalization: true,
    factor_exposure: true,
  },
};

const LOCKED_TOGGLES = new Set(['ic_calculation', 'monotonicity_test', 'ai_summary']);

const defaultDeepAnalysisModules: DeepAnalysisConfig['modules'] = {
  // F5.2 tier truth: custom/default 含 factor_return(schema enabled=True)
  factor_return: true,
  factor_centrality: true,
  trend_analysis: true,
  parameter_sensitivity: true,
  rolling_oos: true,
  factor_orthogonalization: false,
  factor_exposure: false,
  long_short_analysis: true,
  feature_quality_diagnostics: true,
  net_ic_analysis: true,
};

/** 無成本預設:cost_enabled=False;禁寫死 5bps。 */
const defaultNetIcConfig: NetICAnalysisRequest = {
  cost_enabled: false,
  cost_bps: null,
};

const defaultConfig: ICAnalysisConfig = {
  features_path: '',
  labels_path: '',
  meta_path: '',
  config_hash: undefined,
  cross_sectional_runs: [],
  mode: 'global',
  cross_sectional_symbols: [],
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

export const useICAnalysisStore = create<ICAnalysisState>((set, get) => ({
  config: defaultConfig,
  taskId: null,
  status: 'idle',
  progress: 0,
  currentStage: null,
  featureCount: null,
  eventScanDisclosure: null,
  error: null,
  report: null,
  selectedFeature: null,
  availableFeatures: [],
  featureFilter: {
    include_pattern: '',
    include_categories: [],
    include_data_sources: [],
    include_families: [],
    max_features: undefined,
  },
  selectedFeatures: [],
  deepAnalysisModules: defaultDeepAnalysisModules,
  netIcConfig: { ...defaultNetIcConfig },
  deepAnalysisStatus: 'idle',
  deepAnalysisProgress: 0,
  deepAnalysisReport: null,
  deepAnalysisModuleStatus: [],
  activeTab: 'basic',
  featureTier: 'intermediate',
  featureToggles: { ...PRESET_TOGGLES.intermediate },
  setConfig: (config) => set({ config }),
  updateConfig: (patch) =>
    set((state) => {
      const modeChanged = patch.mode !== undefined && patch.mode !== state.config.mode;
      return {
        config: {
          ...state.config,
          ...patch,
          ...(modeChanged
            ? {
                cross_sectional_symbols: [],
                cross_sectional_runs: [],
                config_hash: undefined,
                symbol: undefined,
                timeframe: undefined,
              }
            : {}),
          thresholds: {
            ...state.config.thresholds,
            ...(patch.thresholds || {}),
          },
        },
      };
    }),
  setTask: (taskId, status) =>
    set({
      taskId,
      status: status ?? (taskId ? 'pending' : 'idle'),
      progress: taskId ? 0 : 0,
      currentStage: null,
    }),
  setProgress: (progress, currentStage) => set({ progress, currentStage }),
  setFeatureCount: (featureCount) => set({ featureCount }),
  setEventScanDisclosure: (eventScanDisclosure) => set({ eventScanDisclosure }),
  setStatus: (status) => set({ status }),
  setReport: (report) => set({ report }),
  setError: (error) => set({ error }),
  setSelectedFeature: (featureName) => set({ selectedFeature: featureName }),
  setAvailableFeatures: (features) => set({ availableFeatures: features }),
  setFeatureFilter: (filter) =>
    set((state) => ({ featureFilter: { ...state.featureFilter, ...filter } })),
  setSelectedFeatures: (featureNames) => set({ selectedFeatures: featureNames }),
  setDeepAnalysisModules: (modules) => set({ deepAnalysisModules: modules }),
  setNetIcConfig: (netIcConfig) => set({ netIcConfig: { ...netIcConfig } }),
  setDeepAnalysisStatus: (deepAnalysisStatus) => set({ deepAnalysisStatus }),
  setDeepAnalysisProgress: (deepAnalysisProgress) => set({ deepAnalysisProgress }),
  setDeepAnalysisReport: (deepAnalysisReport) => set({ deepAnalysisReport }),
  setDeepAnalysisModuleStatus: (deepAnalysisModuleStatus) => set({ deepAnalysisModuleStatus }),
  setActiveTab: (activeTab) => set({ activeTab }),
  buildDeepAnalysisRequest: (opts) => {
    const state = get();
    return {
      selected_features: opts.selected_features,
      top_n: opts.top_n ?? 30,
      modules: state.deepAnalysisModules,
      config_override: opts.config_override,
      net_ic: {
        cost_enabled: Boolean(state.netIcConfig.cost_enabled),
        cost_bps: state.netIcConfig.cost_enabled
          ? state.netIcConfig.cost_bps ?? null
          : state.netIcConfig.cost_bps ?? null,
      },
    };
  },
  setFeatureTier: (featureTier) =>
    set((state) => {
      if (featureTier === 'custom') {
        return { featureTier };
      }
      const preset = PRESET_TOGGLES[featureTier];
      return {
        featureTier,
        featureToggles: { ...preset },
        deepAnalysisModules: {
          ...state.deepAnalysisModules,
          factor_return: Boolean(preset.factor_return),
          factor_centrality: Boolean(preset.factor_centrality),
          trend_analysis: Boolean(preset.trend_analysis),
          parameter_sensitivity: Boolean(preset.parameter_sensitivity),
          rolling_oos: Boolean(preset.rolling_oos),
          factor_orthogonalization: Boolean(preset.factor_orthogonalization),
          factor_exposure: Boolean(preset.factor_exposure),
          long_short_analysis: Boolean(preset.long_short_analysis),
          feature_quality_diagnostics: Boolean(preset.feature_quality_diagnostics),
          net_ic_analysis: Boolean(preset.net_ic_analysis),
        },
      };
    }),
  toggleFeature: (key) =>
    set((state) => {
      if (LOCKED_TOGGLES.has(key)) {
        return state;
      }

      const nextEnabled = !Boolean(state.featureToggles[key]);
      const nextToggles = { ...state.featureToggles, [key]: nextEnabled };
      const nextDeepModules = {
        ...state.deepAnalysisModules,
      };

      if (key in nextDeepModules) {
        (nextDeepModules as Record<string, boolean>)[key] = nextEnabled;
      }

      return {
        featureTier: 'custom',
        featureToggles: nextToggles,
        deepAnalysisModules: nextDeepModules,
      };
    }),
  getEffectiveConfig: () => {
    const state = get();
    const stageOverrides: Record<string, boolean> = {
      ic_decay: Boolean(state.featureToggles.ic_decay),
      grouped_ic: Boolean(state.featureToggles.grouped_ic),
      turnover_analysis: Boolean(state.featureToggles.turnover_analysis),
      event_filtering: Boolean(state.featureToggles.event_filtering),
      ai_summary: Boolean(state.featureToggles.ai_summary),
      // UI 邊界唯一轉名點 → 後端 significance.fdr.enabled（D-G / Task 4.2）
      fdr_correction: Boolean(state.featureToggles.fdr_correction),
      // GAP-2 Task 5.1：邊際 IC／多因子組合（後端 STAGE_OVERRIDE_PATHS.marginal_ic → marginal_ic.enabled；預設開）
      marginal_ic: Boolean(state.featureToggles.marginal_ic),
    };

    const moduleOverrides: Record<string, boolean> = {
      factor_return: Boolean(state.featureToggles.factor_return),
      factor_centrality: Boolean(state.featureToggles.factor_centrality),
      trend_analysis: Boolean(state.featureToggles.trend_analysis),
      parameter_sensitivity: Boolean(state.featureToggles.parameter_sensitivity),
      rolling_oos: Boolean(state.featureToggles.rolling_oos),
      factor_orthogonalization: Boolean(state.featureToggles.factor_orthogonalization),
      factor_exposure: Boolean(state.featureToggles.factor_exposure),
      long_short_analysis: Boolean(state.featureToggles.long_short_analysis),
      feature_quality_diagnostics: Boolean(state.featureToggles.feature_quality_diagnostics),
      net_ic_analysis: Boolean(state.featureToggles.net_ic_analysis),
    };

    // 具名 preset 也必須送出 fdr_correction，否則 UI preset ON 會在後端靜默丟失
    // （backend 具名 preset 分支會映射 fdr_correction→significance.fdr.enabled）
    if (state.featureTier === 'custom') {
      return {
        feature_tiers: {
          active_preset: 'custom',
          custom_overrides: {
            stage_overrides: stageOverrides,
            module_overrides: moduleOverrides,
          },
        },
      };
    }

    return {
      feature_tiers: {
        active_preset: state.featureTier,
        custom_overrides: {
          stage_overrides: {
            fdr_correction: Boolean(state.featureToggles.fdr_correction),
            // GAP-2 Task 5.1：具名 preset 亦送出 marginal_ic（比照 fdr；後端具名分支消費）
            marginal_ic: Boolean(state.featureToggles.marginal_ic),
          },
        },
      },
    };
  },
  resetReport: () =>
    set({
      report: null,
      selectedFeature: null,
      progress: 0,
      currentStage: null,
      error: null,
      deepAnalysisStatus: 'idle',
      deepAnalysisProgress: 0,
      deepAnalysisReport: null,
      deepAnalysisModuleStatus: [],
      activeTab: 'basic',
      featureTier: 'intermediate',
      featureToggles: { ...PRESET_TOGGLES.intermediate },
    }),
}));

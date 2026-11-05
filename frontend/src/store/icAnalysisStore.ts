import { create } from 'zustand';
import {
  DeepAnalysisConfig,
  FeatureTierLevel,
  FeatureFilterConfig,
  FeatureListItem,
  ICAnalysisConfig,
  ICEventScanDisclosure,
  ICSubProgress,
  ICTaskFallback,
  ICTaskWarning,
  ICReport,
  ICMethodSettings,
  ModuleStatus,
  DeepCandidateSelection,
  NetICAnalysisRequest,
  ICSummaryPage,
  ICFeatureDetail,
  ICReportLight,
  SummaryPageParams,
  FeatureDetailStatus,
} from '@/lib/types';

type ICAnalysisStatus = 'idle' | 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

interface ICAnalysisState {
  config: ICAnalysisConfig;
  taskId: string | null;
  status: ICAnalysisStatus;
  progress: number;
  currentStage: string | null;
  /** GAP-3 UX Task 6.3：這個 run 有幾個特徵；解析不到為 null（**不填假值**）。 */
  featureCount: number | null;
  /** EVTALIGN Task 4.1：階段內進度（done/total＋ETA）；後端沒送 ⇒ null，**不填假 ETA**。 */
  subProgress: ICSubProgress | null;
  /** EVTALIGN Task 4.1：後端 WARN（例：memory_pressure_observed）；只揭露不擋。 */
  taskWarnings: ICTaskWarning[];
  /** 降級重跑（全樣本、無 OOS）之原因——重跑**當下**即揭露；沒有降級 ⇒ null。 */
  taskFallback: ICTaskFallback | null;
  /**
   * `G3-D2` D4.2／D4.3：**後端**回傳之事件分析揭露（兩上界、k 雙值、掃描結果）。
   * 🔴 尚未分析 ⇒ `null`，前端**不猜數字**（上界之公式住 producer，重算即第二份實作）。
   */
  eventScanDisclosure: ICEventScanDisclosure | null;
  error: string | null;
  /** ICRESULT_PAGING：light 視圖（無七段 per-feature 資料；表格／圖表各走投影端點）。 */
  report: ICReport | ICReportLight | null;
  /** ICRESULT_PAGING §C-7：結果世代戳；summary／feature 回應之 revision 不符者一律丟棄。 */
  resultRevision: number | null;
  summaryPage: ICSummaryPage | null;
  summaryParams: SummaryPageParams;
  summaryLoading: boolean;
  summaryError: string | null;
  featureDetail: ICFeatureDetail | null;
  featureDetailStatus: FeatureDetailStatus;
  featureDetailError: string | null;
  selectedFeature: string | null;
  availableFeatures: FeatureListItem[];
  featureFilter: FeatureFilterConfig;
  selectedFeatures: string[];
  /** ICPERF Task 0.4 ㊻：選欄來源——auto＝頁面自動預選（深度分析不送 selected_features，交後端全域規則）；manual＝使用者操作 */
  selectedFeaturesSource: 'auto' | 'manual';
  /** ㊻：未手選時之深度分析候選數 n（預設 30，可選 50／100） */
  deepTopN: number;
  /** ㊻：最近一次深度分析之候選來源與逐欄篩選通過狀態 */
  deepCandidateSelection: DeepCandidateSelection | null;
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
  /** ㊸：本次分析送出時之方法選擇與門檻開關（按下分析當下快照；報告頂端「本次設定」讀此，不讀之後又改過之面板值）。 */
  runSettings: ICMethodSettings | null;
  setRunSettings: (settings: ICMethodSettings | null) => void;
  setConfig: (config: ICAnalysisConfig) => void;
  updateConfig: (patch: Partial<ICAnalysisConfig>) => void;
  setTask: (taskId: string | null, status?: ICAnalysisStatus) => void;
  setProgress: (progress: number, currentStage?: string | null) => void;
  setFeatureCount: (featureCount: number | null) => void;
  setSubProgress: (subProgress: ICSubProgress | null) => void;
  setTaskWarnings: (warnings: ICTaskWarning[]) => void;
  setTaskFallback: (fallback: ICTaskFallback | null) => void;
  setEventScanDisclosure: (d: ICEventScanDisclosure | null) => void;
  setStatus: (status: ICAnalysisStatus) => void;
  setReport: (report: ICReport | ICReportLight | null) => void;
  setResultRevision: (revision: number | null) => void;
  setSummaryPage: (page: ICSummaryPage | null) => void;
  setSummaryParams: (patch: Partial<SummaryPageParams>) => void;
  setSummaryLoading: (loading: boolean) => void;
  setSummaryError: (error: string | null) => void;
  setFeatureDetail: (detail: ICFeatureDetail | null, status: FeatureDetailStatus, error?: string | null) => void;
  setError: (error: string | null) => void;
  setSelectedFeature: (featureName: string | null) => void;
  setAvailableFeatures: (features: FeatureListItem[]) => void;
  setFeatureFilter: (filter: FeatureFilterConfig) => void;
  setSelectedFeatures: (featureNames: string[], source?: 'auto' | 'manual') => void;
  setDeepTopN: (n: number) => void;
  setDeepCandidateSelection: (selection: DeepCandidateSelection | null) => void;
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

/**
 * 票 TIERTOGGLE：送給後端的開關鍵集（單一真相源＝`momentum/Analysis/contracts/ui_stage_toggles.json`）。
 * stage → 後端 `STAGE_OVERRIDE_PATHS`；module → 後端 `MODULE_ENABLED_PATHS`。
 * 新增／刪除鍵時**必須**同步契約檔，否則 `icAnalysisStore.toggles.test.ts` 與 pytest 皆紅。
 */
export const STAGE_TOGGLE_KEYS = [
  'ic_decay',
  'grouped_ic',
  'turnover_analysis',
  'event_filtering',
  'ai_summary',
  'fdr_correction',
  'marginal_ic',
] as const;

export const MODULE_TOGGLE_KEYS = [
  'factor_return',
  'factor_centrality',
  'trend_analysis',
  'parameter_sensitivity',
  'rolling_oos',
  'factor_orthogonalization',
  'factor_exposure',
  'long_short_analysis',
  'feature_quality_diagnostics',
  'net_ic_analysis',
] as const;

const PRESET_TOGGLES: Record<'foundation' | 'intermediate' | 'advanced', Record<string, boolean>> = {
  foundation: {
    ic_calculation: true,
    ai_summary: true,
    ic_decay: false,
    grouped_ic: false,
    event_filtering: false,
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
    factor_centrality: false,
    factor_orthogonalization: false,
    factor_exposure: false,
  },
  intermediate: {
    ic_calculation: true,
    ai_summary: true,
    ic_decay: true,
    grouped_ic: true,
    event_filtering: true,
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
    factor_centrality: true,
    factor_orthogonalization: false,
    factor_exposure: false,
  },
  advanced: {
    ic_calculation: true,
    ai_summary: true,
    ic_decay: true,
    grouped_ic: true,
    event_filtering: true,
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
    factor_centrality: true,
    factor_orthogonalization: true,
    factor_exposure: true,
  },
};

// ICPERF Task 0.4 ㊸：原 ui_only 七鍵（ic_method_selection、winsorization_method、return_type_selection、
// redundancy_method_selection、monotonicity_test、vif_filter、ic_autocorrelation）不再是 tier 之布林開關——
// 前五者改為 `config.ic_settings` 之方法選擇／門檻開關（經 `buildConfigOverride` 送後端），vif_filter 併入去重方法之 vif，
// ic_autocorrelation 只揭露（後端算出但無消費者）；分類見契約 `setting_keys`／`merged_keys`／`disclosed_keys`。
const LOCKED_TOGGLES = new Set(['ic_calculation', 'ai_summary']);

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
  // EVTLABEL Task 3.2：預設 `auto`——有可用的 0/1 就用，否則後端退回報酬版並寫明原因。
  // 送出時 `auto` 會被省略（後端同為預設值），故不影響非事件請求。
  event_label_mode: 'auto',
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
  subProgress: null,
  taskWarnings: [],
  taskFallback: null,
  eventScanDisclosure: null,
  error: null,
  report: null,
  resultRevision: null,
  summaryPage: null,
  summaryParams: { sort_by: 'icir_aligned', sort_order: 'desc', offset: 0, limit: 50, search: '' },
  summaryLoading: false,
  summaryError: null,
  featureDetail: null,
  featureDetailStatus: 'idle',
  featureDetailError: null,
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
  selectedFeaturesSource: 'auto',
  deepTopN: 30,
  deepCandidateSelection: null,
  deepAnalysisModules: defaultDeepAnalysisModules,
  netIcConfig: { ...defaultNetIcConfig },
  deepAnalysisStatus: 'idle',
  deepAnalysisProgress: 0,
  deepAnalysisReport: null,
  deepAnalysisModuleStatus: [],
  activeTab: 'basic',
  featureTier: 'intermediate',
  featureToggles: { ...PRESET_TOGGLES.intermediate },
  runSettings: null,
  setRunSettings: (runSettings) => set({ runSettings }),
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
      subProgress: null,
      taskWarnings: [],
      taskFallback: null,
    }),
  setProgress: (progress, currentStage) => set({ progress, currentStage }),
  setFeatureCount: (featureCount) => set({ featureCount }),
  setSubProgress: (subProgress) => set({ subProgress }),
  setTaskWarnings: (taskWarnings) => set({ taskWarnings }),
  setTaskFallback: (taskFallback) => set({ taskFallback }),
  setEventScanDisclosure: (eventScanDisclosure) => set({ eventScanDisclosure }),
  setStatus: (status) => set({ status }),
  setReport: (report) =>
    set({
      report,
      resultRevision: report && typeof (report as ICReportLight).result_revision === 'number' ? (report as ICReportLight).result_revision : null,
      summaryPage: report && (report as ICReportLight).view === 'light' ? (report as ICReportLight).summary_page : null,
    }),
  setResultRevision: (resultRevision) => set({ resultRevision }),
  setSummaryPage: (summaryPage) => set({ summaryPage }),
  setSummaryParams: (patch) => set((state) => ({ summaryParams: { ...state.summaryParams, ...patch } })),
  setSummaryLoading: (summaryLoading) => set({ summaryLoading }),
  setSummaryError: (summaryError) => set({ summaryError }),
  // 切換特徵時**不清空**舊 detail（SPEC §C-10：保留舊圖＋遮罩）；只有 ready／missing／error 才換內容
  setFeatureDetail: (detail, status, error = null) =>
    set((state) => ({ featureDetail: status === 'loading' ? state.featureDetail : detail, featureDetailStatus: status, featureDetailError: error })),
  setError: (error) => set({ error }),
  setSelectedFeature: (featureName) => set({ selectedFeature: featureName }),
  setAvailableFeatures: (features) => set({ availableFeatures: features }),
  setFeatureFilter: (filter) =>
    set((state) => ({ featureFilter: { ...state.featureFilter, ...filter } })),
  setSelectedFeatures: (featureNames, source = 'manual') =>
    set({ selectedFeatures: featureNames, selectedFeaturesSource: source }),
  setDeepTopN: (deepTopN) => set({ deepTopN }),
  setDeepCandidateSelection: (deepCandidateSelection) => set({ deepCandidateSelection }),
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
    const pick = (keys: readonly string[]): Record<string, boolean> =>
      Object.fromEntries(keys.map((k) => [k, Boolean((state.featureToggles as Record<string, unknown>)[k])]));
    const stageOverrides = pick(STAGE_TOGGLE_KEYS);
    const moduleOverrides = pick(MODULE_TOGGLE_KEYS);

    // 🔴 票 TIERTOGGLE（使用者 2026-09-10）：**具名 preset 也送出全部 stage 開關**。
    //    舊版只送 fdr_correction／marginal_ic 兩鍵 ⇒ 「基礎」preset 的 ic_decay:false／
    //    grouped_ic:false 根本沒離開瀏覽器，後端照 config 預設跑＝幽靈開關。
    //    鍵集之單一真相源＝`momentum/Analysis/contracts/ui_stage_toggles.json`
    //    （icAnalysisStore.toggles.test.ts 機械對證；後端同檔 pytest 對證）。
    //    module 開關具名 preset 不送：後端由 schema presets 之 deep_analysis／disabled_modules 決定
    //    （foundation deep_analysis=false ⇒ 深度模組全關），custom 才走 module_overrides。
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
        custom_overrides: { stage_overrides: stageOverrides },
      },
    };
  },
  resetReport: () =>
    set({
      report: null,
      resultRevision: null,
      summaryPage: null,
      summaryParams: { sort_by: 'icir_aligned', sort_order: 'desc', offset: 0, limit: 50, search: '' },
      summaryLoading: false,
      summaryError: null,
      featureDetail: null,
      featureDetailStatus: 'idle',
      featureDetailError: null,
      selectedFeature: null,
      progress: 0,
      currentStage: null,
      error: null,
      deepAnalysisStatus: 'idle',
      deepAnalysisProgress: 0,
      deepAnalysisReport: null,
      deepAnalysisModuleStatus: [],
      deepCandidateSelection: null,
      activeTab: 'basic',
      featureTier: 'intermediate',
      featureToggles: { ...PRESET_TOGGLES.intermediate },
    }),
}));

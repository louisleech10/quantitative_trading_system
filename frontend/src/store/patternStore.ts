// frontend/src/store/patternStore.ts
// Pattern Discovery 狀態管理

import { create } from 'zustand';
import type { 
  Pattern, 
  XGBoostAnalysisResult, 
  PatternStatistics,
  OOTValidationResult,
  DriftReport,
  RegimeReport,
  PredictionsResponse,
  FeatureImportanceTypesResponse,
  GlobalSHAPResult,
  SingleCaseSHAPResult,
  CalibrationCurveData,
  PRCurveData,
  ProbabilityDensityData,
  EquityCurveData,
  FalsePositiveCase,
  RollingAUCData
} from '@/lib/patternTypes';
import {
  validateOOT,
  getDriftReport,
  getRegimeAnalysis,
  getPredictions,
  getFeatureImportanceAll,
  getSHAPGlobal,
  getCalibrationCurve,
  getPRCurve,
  getProbabilityDensity,
  getStrategyEquity,
  getTopFalsePositives,
  getRollingAUC
} from '@/lib/api/patternApi';

interface PatternState {
  // Pattern 相關
  patterns: Pattern[];
  currentPattern: Pattern | null;
  patternStatistics: PatternStatistics | null;
  
  // XGBoost Analysis 相關
  currentAnalysis: XGBoostAnalysisResult | null;
  analysisLoading: boolean;
  analysisTaskId: string | null;

  // 深度分析狀態
  ootValidation: OOTValidationResult | null;
  driftReport: DriftReport | null;
  regimeAnalysis: RegimeReport | null;
  predictions: PredictionsResponse | null;
  featureImportanceAll: FeatureImportanceTypesResponse | null;
  shapGlobal: GlobalSHAPResult | null;
  shapSingleCase: SingleCaseSHAPResult | null;
  calibrationCurve: CalibrationCurveData | null;
  prCurve: PRCurveData | null;
  probabilityDensity: ProbabilityDensityData | null;
  strategyEquity: EquityCurveData | null;
  topFalsePositives: FalsePositiveCase[] | null;
  rollingAUC: RollingAUCData | null;

  deepAnalysisLoading: {
    oot: boolean;
    drift: boolean;
    regime: boolean;
    shap: boolean;
    predictions: boolean;
    calibration: boolean;
    pr: boolean;
    density: boolean;
    equity: boolean;
    falsePositives: boolean;
    rollingAuc: boolean;
  };
  
  // UI 狀態
  selectedPatternId: string | null;
  filters: {
    status?: string;
    tags: string[];
    case_id?: string;
  };
  
  // Actions - Pattern Management
  setPatterns: (patterns: Pattern[]) => void;
  setCurrentPattern: (pattern: Pattern | null) => void;
  setPatternStatistics: (stats: PatternStatistics | null) => void;
  selectPattern: (patternId: string | null) => void;
  addPattern: (pattern: Pattern) => void;
  updatePattern: (patternId: string, updates: Partial<Pattern>) => void;
  deletePattern: (patternId: string) => void;
  
  // Actions - XGBoost Analysis
  setCurrentAnalysis: (analysis: XGBoostAnalysisResult | null) => void;
  setAnalysisLoading: (loading: boolean) => void;
  setAnalysisTaskId: (taskId: string | null) => void;

  // Actions - Deep Analysis
  setOOTValidation: (data: OOTValidationResult | null) => void;
  setDriftReport: (data: DriftReport | null) => void;
  setRegimeAnalysis: (data: RegimeReport | null) => void;
  setPredictions: (data: PredictionsResponse | null) => void;
  setFeatureImportanceAll: (data: FeatureImportanceTypesResponse | null) => void;
  setSHAPGlobal: (data: GlobalSHAPResult | null) => void;
  setSHAPSingleCase: (data: SingleCaseSHAPResult | null) => void;
  setCalibrationCurve: (data: CalibrationCurveData | null) => void;
  setPRCurve: (data: PRCurveData | null) => void;
  setProbabilityDensity: (data: ProbabilityDensityData | null) => void;
  setStrategyEquity: (data: EquityCurveData | null) => void;
  setTopFalsePositives: (data: FalsePositiveCase[] | null) => void;
  setRollingAUC: (data: RollingAUCData | null) => void;

  loadDeepAnalysis: (taskId: string) => Promise<void>;
  clearDeepAnalysis: () => void;
  
  // Actions - Filters
  setFilterStatus: (status?: string) => void;
  setFilterTags: (tags: string[]) => void;
  setFilterCaseId: (caseId?: string) => void;
  clearFilters: () => void;
  
  // Computed
  getFilteredPatterns: () => Pattern[];
}

export const usePatternStore = create<PatternState>((set, get) => ({
  // Initial State
  patterns: [],
  currentPattern: null,
  patternStatistics: null,
  currentAnalysis: null,
  analysisLoading: false,
  analysisTaskId: null,
  ootValidation: null,
  driftReport: null,
  regimeAnalysis: null,
  predictions: null,
  featureImportanceAll: null,
  shapGlobal: null,
  shapSingleCase: null,
  calibrationCurve: null,
  prCurve: null,
  probabilityDensity: null,
  strategyEquity: null,
  topFalsePositives: null,
  rollingAUC: null,
  deepAnalysisLoading: {
    oot: false,
    drift: false,
    regime: false,
    shap: false,
    predictions: false,
    calibration: false,
    pr: false,
    density: false,
    equity: false,
    falsePositives: false,
    rollingAuc: false
  },
  selectedPatternId: null,
  filters: {
    status: undefined,
    tags: [],
    case_id: undefined
  },
  
  // Pattern Management Actions
  setPatterns: (patterns) => set({ patterns }),
  
  setCurrentPattern: (pattern) => set({ currentPattern: pattern }),
  
  setPatternStatistics: (stats) => set({ patternStatistics: stats }),
  
  selectPattern: (patternId) => {
    set({ selectedPatternId: patternId });
    if (patternId) {
      const pattern = get().patterns.find(p => p.pattern_id === patternId);
      set({ currentPattern: pattern || null });
    } else {
      set({ currentPattern: null });
    }
  },
  
  addPattern: (pattern) => set((state) => ({
    patterns: [pattern, ...state.patterns]
  })),
  
  updatePattern: (patternId, updates) => set((state) => ({
    patterns: state.patterns.map(p => 
      p.pattern_id === patternId ? { ...p, ...updates } : p
    ),
    currentPattern: state.currentPattern?.pattern_id === patternId 
      ? { ...state.currentPattern, ...updates } 
      : state.currentPattern
  })),
  
  deletePattern: (patternId) => set((state) => ({
    patterns: state.patterns.filter(p => p.pattern_id !== patternId),
    currentPattern: state.currentPattern?.pattern_id === patternId 
      ? null 
      : state.currentPattern,
    selectedPatternId: state.selectedPatternId === patternId 
      ? null 
      : state.selectedPatternId
  })),
  
  // XGBoost Analysis Actions
  setCurrentAnalysis: (analysis) => set({ currentAnalysis: analysis }),
  
  setAnalysisLoading: (loading) => set({ analysisLoading: loading }),
  
  setAnalysisTaskId: (taskId) => set({ analysisTaskId: taskId }),

  // Deep Analysis Actions
  setOOTValidation: (data) => set({ ootValidation: data }),
  setDriftReport: (data) => set({ driftReport: data }),
  setRegimeAnalysis: (data) => set({ regimeAnalysis: data }),
  setPredictions: (data) => set({ predictions: data }),
  setFeatureImportanceAll: (data) => set({ featureImportanceAll: data }),
  setSHAPGlobal: (data) => set({ shapGlobal: data }),
  setSHAPSingleCase: (data) => set({ shapSingleCase: data }),
  setCalibrationCurve: (data) => set({ calibrationCurve: data }),
  setPRCurve: (data) => set({ prCurve: data }),
  setProbabilityDensity: (data) => set({ probabilityDensity: data }),
  setStrategyEquity: (data) => set({ strategyEquity: data }),
  setTopFalsePositives: (data) => set({ topFalsePositives: data }),
  setRollingAUC: (data) => set({ rollingAUC: data }),

  loadDeepAnalysis: async (taskId: string) => {
    set({
      deepAnalysisLoading: {
        oot: true,
        drift: true,
        regime: true,
        shap: true,
        predictions: true,
        calibration: true,
        pr: true,
        density: true,
        equity: true,
        falsePositives: true,
        rollingAuc: true
      }
    });

    const results = await Promise.allSettled([
      validateOOT({ task_id: taskId }),
      getDriftReport(taskId),
      getRegimeAnalysis(taskId),
      getSHAPGlobal(taskId),
      getPredictions(taskId, true),
      getFeatureImportanceAll(taskId, ['gain', 'cover', 'weight']),
      getCalibrationCurve(taskId),
      getPRCurve(taskId),
      getProbabilityDensity(taskId),
      getStrategyEquity(taskId),
      getTopFalsePositives(taskId),
      getRollingAUC(taskId)
    ]);

    const [
      oot,
      drift,
      regime,
      shap,
      predictions,
      importanceAll,
      calibration,
      pr,
      density,
      equity,
      falsePositives,
      rollingAuc
    ] = results;

    if (oot.status === 'fulfilled') set({ ootValidation: oot.value.validation_result || null });
    if (drift.status === 'fulfilled') set({ driftReport: drift.value.report || null });
    if (regime.status === 'fulfilled') set({ regimeAnalysis: regime.value.report || null });
    if (shap.status === 'fulfilled') set({ shapGlobal: shap.value.result || null });
    if (predictions.status === 'fulfilled') set({ predictions: predictions.value });
    if (importanceAll.status === 'fulfilled') set({ featureImportanceAll: importanceAll.value });
    if (calibration.status === 'fulfilled') set({ calibrationCurve: calibration.value.data });
    if (pr.status === 'fulfilled') set({ prCurve: pr.value.data });
    if (density.status === 'fulfilled') set({ probabilityDensity: density.value.data });
    if (equity.status === 'fulfilled') set({ strategyEquity: equity.value.data });
    if (falsePositives.status === 'fulfilled') set({ topFalsePositives: falsePositives.value.cases });
    if (rollingAuc.status === 'fulfilled') set({ rollingAUC: rollingAuc.value.data });

    set({
      deepAnalysisLoading: {
        oot: false,
        drift: false,
        regime: false,
        shap: false,
        predictions: false,
        calibration: false,
        pr: false,
        density: false,
        equity: false,
        falsePositives: false,
        rollingAuc: false
      }
    });
  },

  clearDeepAnalysis: () => set({
    ootValidation: null,
    driftReport: null,
    regimeAnalysis: null,
    predictions: null,
    featureImportanceAll: null,
    shapGlobal: null,
    shapSingleCase: null,
    calibrationCurve: null,
    prCurve: null,
    probabilityDensity: null,
    strategyEquity: null,
    topFalsePositives: null,
    rollingAUC: null,
    deepAnalysisLoading: {
      oot: false,
      drift: false,
      regime: false,
      shap: false,
      predictions: false,
      calibration: false,
      pr: false,
      density: false,
      equity: false,
      falsePositives: false,
      rollingAuc: false
    }
  }),
  
  // Filter Actions
  setFilterStatus: (status) => set((state) => ({
    filters: { ...state.filters, status }
  })),
  
  setFilterTags: (tags) => set((state) => ({
    filters: { ...state.filters, tags }
  })),
  
  setFilterCaseId: (caseId) => set((state) => ({
    filters: { ...state.filters, case_id: caseId }
  })),
  
  clearFilters: () => set({ 
    filters: { status: undefined, tags: [], case_id: undefined }
  }),
  
  // Computed
  getFilteredPatterns: () => {
    const { patterns, filters } = get();
    
    let filtered = patterns;
    
    // 依狀態過濾
    if (filters.status) {
      filtered = filtered.filter(p => p.status === filters.status);
    }
    
    // 依標籤過濾
    if (filters.tags.length > 0) {
      filtered = filtered.filter(p => 
        filters.tags.some(tag => p.tags?.includes(tag))
      );
    }
    
    // 依案例 ID 過濾
    if (filters.case_id) {
      filtered = filtered.filter(p => 
        p.case_id.toLowerCase().includes(filters.case_id!.toLowerCase())
      );
    }
    
    return filtered;
  }
}));

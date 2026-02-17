// frontend/src/store/strategyTestStore.ts
// Persistent state management for strategy test results

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface DensityMetrics {
  positive_avg_density?: number;
  negative_avg_density?: number;
  positive_far_avg_density?: number;
  negative_far_avg_density?: number;
  positive_near_far_ratio?: number;
  negative_near_far_ratio?: number;
  near_far_ratio?: number;
  positive_std?: number;
  negative_std?: number;
  positive_far_std?: number;
  negative_far_std?: number;
  positive_ratio_std?: number;
  negative_ratio_std?: number;
  separation?: number;
  ratio_separation?: number;
  p_value?: number;
  cohens_d?: number;
  stability_cv?: number;
  positive_ratio_cv?: number;
  separation_cv?: number;
  positive_sample_size?: number;
  negative_sample_size?: number;
  positive_near_zero_count?: number;
  positive_near_zero_ratio?: number;
  positive_far_zero_count?: number;
  positive_far_zero_ratio?: number;
  negative_near_zero_count?: number;
  negative_near_zero_ratio?: number;
  negative_far_zero_count?: number;
  negative_far_zero_ratio?: number;
  positive_weighted_mean_m?: number;
  negative_weighted_mean_m?: number;
  positive_m_std?: number;
  negative_m_std?: number;
  m_separation?: number;
  positive_m_cv?: number;
  m_separation_cv?: number;
  positive_total_weight?: number;
  negative_total_weight?: number;
  positive_active_cases?: number;
  negative_active_cases?: number;
  optuna_golden_score?: number;
  excluded_months_count?: number;
  included_months_count?: number;
  sample_warnings?: string[];
}

export interface DataQualitySummary {
  total_cases?: number;
  positive_cases?: number;
  negative_cases?: number;
  success_rate?: number;
  error_messages?: string[];
}

export interface StrategyTestResult {
  signal_count: number;
  total_bars: number;
  is_sampled: boolean;
  signal_density?: number;
  strategy_name?: string;
  metadata?: {
    total_klines?: number;
    calculation_time_ms?: number;
    strategy_config?: Record<string, unknown>;
    density_metrics?: DensityMetrics;
    quality?: DataQualitySummary;
  };
}

interface StrategyTestState {
  // Test result data
  testResult: StrategyTestResult | null;
  caseLevelDensities: Record<string, number>;
  positiveCaseIds: string[];
  negativeCaseIds: string[];
  
  // UI state
  apiError: string | null;
  lastRunTimestamp: number | null;
  
  // Hydration state
  _hasHydrated: boolean;
  
  // Actions
  setTestResult: (result: StrategyTestResult | null) => void;
  setCaseLevelDensities: (densities: Record<string, number>) => void;
  setPositiveCaseIds: (ids: string[]) => void;
  setNegativeCaseIds: (ids: string[]) => void;
  setApiError: (error: string | null) => void;
  clearResults: () => void;
  setHasHydrated: (state: boolean) => void;
}

export const useStrategyTestStore = create<StrategyTestState>()(
  persist(
    (set) => ({
      // Initial state
      testResult: null,
      caseLevelDensities: {},
      positiveCaseIds: [],
      negativeCaseIds: [],
      apiError: null,
      lastRunTimestamp: null,
      _hasHydrated: false,

      // Actions
      setTestResult: (result) => set({ 
        testResult: result,
        lastRunTimestamp: result ? Date.now() : null
      }),
      
      setCaseLevelDensities: (densities) => set({ caseLevelDensities: densities }),
      
      setPositiveCaseIds: (ids) => set({ positiveCaseIds: ids }),
      
      setNegativeCaseIds: (ids) => set({ negativeCaseIds: ids }),
      
      setApiError: (error) => set({ apiError: error }),
      
      clearResults: () => set({
        testResult: null,
        caseLevelDensities: {},
        positiveCaseIds: [],
        negativeCaseIds: [],
        apiError: null,
        lastRunTimestamp: null
      }),
      
      setHasHydrated: (state) => set({ _hasHydrated: state }),
    }),
    {
      name: 'strategy-test-storage', // localStorage key
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        // Only persist these fields (exclude _hasHydrated)
        testResult: state.testResult,
        caseLevelDensities: state.caseLevelDensities,
        positiveCaseIds: state.positiveCaseIds,
        negativeCaseIds: state.negativeCaseIds,
        lastRunTimestamp: state.lastRunTimestamp,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);

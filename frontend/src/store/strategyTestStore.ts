// frontend/src/store/strategyTestStore.ts
// Persistent state management for strategy test results

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

// Use generic types to avoid conflicts with page-level definitions
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type TestResultType = any;

interface StrategyTestState {
  // Test result data
  testResult: TestResultType | null;
  caseLevelDensities: Record<string, number>;
  positiveCaseIds: string[];
  negativeCaseIds: string[];
  
  // UI state
  apiError: string | null;
  lastRunTimestamp: number | null;
  
  // Hydration state
  _hasHydrated: boolean;
  
  // Actions
  setTestResult: (result: TestResultType | null) => void;
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

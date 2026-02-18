import { create } from 'zustand'
import type {
  BacktestProgressEvent,
  ExecutionOptimizationConfig,
  HyperparamOptimizationConfig,
  OptimizationResult,
  OverfittingAlertEvent,
  ParetoUpdateEvent,
} from '@/lib/types/optimization'

interface OptimizationState {
  hyperparamConfig: HyperparamOptimizationConfig | null
  executionConfig: ExecutionOptimizationConfig | null
  currentResult: OptimizationResult | null
  backtestProgress: BacktestProgressEvent[]
  paretoFront: Array<{ sharpe: number; max_dd: number }>
  overfittingAlerts: OverfittingAlertEvent[]
  isLoading: boolean
  error: string | null
  setHyperparamConfig: (config: HyperparamOptimizationConfig) => void
  setExecutionConfig: (config: ExecutionOptimizationConfig) => void
  setCurrentResult: (result: OptimizationResult | null) => void
  appendBacktestProgress: (event: BacktestProgressEvent) => void
  setParetoUpdate: (event: ParetoUpdateEvent) => void
  appendOverfittingAlert: (event: OverfittingAlertEvent) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  resetRealtime: () => void
}

export const useOptimizationStore = create<OptimizationState>((set) => ({
  hyperparamConfig: null,
  executionConfig: null,
  currentResult: null,
  backtestProgress: [],
  paretoFront: [],
  overfittingAlerts: [],
  isLoading: false,
  error: null,

  setHyperparamConfig: (config) => set({ hyperparamConfig: config }),
  setExecutionConfig: (config) => set({ executionConfig: config }),
  setCurrentResult: (result) => set({ currentResult: result }),
  appendBacktestProgress: (event) =>
    set((state) => ({
      backtestProgress: [...state.backtestProgress, event].slice(-200),
    })),
  setParetoUpdate: (event) => set({ paretoFront: event.pareto_front }),
  appendOverfittingAlert: (event) =>
    set((state) => ({
      overfittingAlerts: [...state.overfittingAlerts, event].slice(-200),
    })),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  resetRealtime: () => set({ backtestProgress: [], paretoFront: [], overfittingAlerts: [] }),
}))

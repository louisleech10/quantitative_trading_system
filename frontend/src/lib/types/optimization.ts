export type TargetMetric = 'expectancy' | 'sharpe_ratio' | 'sortino_ratio' | 'calmar_ratio' | 'sqn'
export type ModelType = 'lightgbm' | 'xgboost'
export type TaskType = 'execution' | 'hyperparameter'

export interface ExecutionOptimizationConfig {
  model_predictions_path: string
  target_metric: TargetMetric
  n_trials: number
  timeout_seconds: number
  search_space_override?: Record<string, unknown>
  constraints?: {
    max_drawdown?: number
    min_win_rate?: number
    min_trades?: number
  }
  backtest_config?: {
    commission?: number
    slippage?: number
  }
  multi_objective: boolean
}

export interface HyperparamOptimizationConfig {
  model_type: ModelType
  features_path: string
  labels_path: string
  n_trials: number
  timeout_seconds: number
  search_space_override?: Record<string, unknown>
  max_train_val_gap: number
  cv_folds: number
}

export interface OptimizationTaskCreateResponse {
  task_id: string
  status: string
  created_at: string
}

export interface OptimizationResult {
  task_id: string
  task_type: string
  status: string
  best_trial?: {
    trial_number: number | null
    value: number | null
    params: Record<string, unknown> | null
  } | null
  performance_metrics?: Record<string, number | string | boolean | null> | null
  parameter_importance?: Record<string, number> | null
  constraint_satisfaction?: Record<
    string,
    { limit: number; actual: number; satisfied: boolean }
  >
}

export interface OptimizationConfigResponse {
  execution: Record<string, unknown>
  hyperparameter: Record<string, unknown>
}

export interface OptimizationTaskProgress {
  completed_trials: number
  total_trials: number
  completion_percentage: number
  best_value?: number | null
}

export interface OptimizationTaskStatusResponse {
  success?: boolean
  data?: {
    status?: string
    progress?: OptimizationTaskProgress
  }
  status?: string
  progress?: OptimizationTaskProgress
}

export interface BacktestProgressEvent {
  trial_number: number
  sharpe: number
  max_dd: number
  win_rate: number
  expectancy: number
}

export interface ParetoUpdateEvent {
  pareto_front: Array<{ sharpe: number; max_dd: number }>
}

export interface OverfittingAlertEvent {
  trial_number: number
  train_val_gap: number
  threshold: number
}

export interface TrialRow {
  trial_number: number
  value: number
  state?: string
  params?: Record<string, unknown>
}

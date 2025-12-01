/**
 * 優化任務相關TypeScript類型定義
 *
 * Author: Claude (Phase 3.5 Day 5-6)
 * Date: 2025-11-02
 */

// ==================== Enums ====================

export enum OptimizationTaskStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export enum SamplerType {
  TPE = 'TPE',
  CMAES = 'CmaEs',
  RANDOM = 'Random',
  GP = 'GP',
  NSGA_II = 'NSGA-II'
}

// ==================== Progress ====================

export interface OptimizationTaskProgress {
  completed_trials: number
  total_trials: number
  completion_percentage: number
  best_value?: number
  best_params?: Record<string, any>
  elapsed_time: number
  estimated_remaining_time?: number
  trials_per_hour: number
  current_milestone?: number // 25, 50, 75
  error_count: number
}

// ==================== Task Info ====================

export interface OptimizationTaskInfo {
  task_id: string
  study_name: string
  status: OptimizationTaskStatus
  created_at: string
  started_at?: string
  completed_at?: string
  progress: OptimizationTaskProgress
  result?: OptimizationResult
  error_message?: string
  config: OptimizationConfig
  duration_seconds?: number
}

export interface OptimizationConfig {
  positive_cases: string[]
  negative_cases: string[]
  training_window: {
    start_date: string
    end_date: string
    timeframe: string
  }
  sampler_type: SamplerType
  n_trials: number
  n_jobs: number
  use_multi_objective: boolean
}

export interface OptimizationResult {
  best_value: number
  best_params: Record<string, any>
  best_trial_number: number
  n_trials: number
  optimization_time: number
}

// ==================== WebSocket Events ====================

export type WebSocketEventType =
  | 'connected'
  | 'optimization_started'
  | 'progress_update'
  | 'new_best_value'
  | 'milestone_reached'
  | 'optimization_finished'
  | 'ping'
  | 'error'

export interface WebSocketMessage {
  event: WebSocketEventType
  data: any
  timestamp: string
}

export interface ProgressUpdateData {
  task_id: string
  completed_trials: number
  total_trials: number
  completion_percentage: number
  best_value?: number
  elapsed_time: number
  estimated_remaining_time?: number
  trials_per_hour: number
}

export interface NewBestValueData {
  task_id: string
  trial_number: number
  best_value: number
  best_params: Record<string, any>
  completion_percentage: number
}

export interface MilestoneReachedData {
  task_id: string
  milestone_percentage: number
  completed_trials: number
  total_trials: number
  best_value?: number
  estimated_remaining_time?: number
}

// ==================== API Requests ====================

export interface CreateOptimizationTaskRequest {
  study_name: string
  positive_cases: string[]
  negative_cases: string[]
  training_window: {
    start_date: string
    end_date: string
    timeframe: string
  }
  sampler_type: SamplerType
  n_trials: number
  n_jobs: number
  use_multi_objective: boolean
  parameter_ranges?: any
}

export interface CreateOptimizationTaskResponse {
  success: boolean
  task_id: string
  message: string
}

export interface TaskStatusResponse {
  success: boolean
  data: OptimizationTaskInfo
}

export interface TaskListResponse {
  success: boolean
  data: OptimizationTaskInfo[]
  total: number
}

// ==================== Analysis Types ====================

export interface ParameterImportance {
  parameter_name: string
  importance: number
  rank: number // 1 = most important
}

export interface ImportanceAnalysisResponse {
  success: boolean
  task_id: string
  study_name: string
  n_trials: number
  importances: ParameterImportance[]
  evaluator: string // fanova, mean_decrease_impurity
  message?: string
}

export interface OptimizationHistoryPoint {
  trial_number: number
  value: number
  best_value_so_far: number
  datetime: string
  params: Record<string, any>
  state: string // COMPLETE, PRUNED, FAIL
}

export interface OptimizationHistoryResponse {
  success: boolean
  task_id: string
  study_name: string
  history: OptimizationHistoryPoint[]
  total_trials: number
}

export interface ParamSpacePoint {
  trial_number: number
  value: number
  params: Record<string, any>
  state: string
}

export interface ParamSpaceResponse {
  success: boolean
  task_id: string
  study_name: string
  points: ParamSpacePoint[]
  param_names: string[]
  total_trials: number
}

// ==================== Ultra Think Step 3 優化: 新增 Phase 2 API 類型 ====================

// 參數空間熱力圖
export interface HeatmapDataPoint {
  x: number
  y: number
  value: number
  trial_number: number
}

export interface HeatmapData {
  param_x: string
  param_y: string
  data_points: HeatmapDataPoint[]
  value_range: [number, number]
}

export interface HeatmapResponse {
  success: boolean
  task_id: string
  data: HeatmapData
}

// 收斂分析
export interface BestValueHistoryPoint {
  trial: number
  value: number
}

export interface ConvergenceAnalysis {
  converged: boolean
  convergence_trial?: number
  convergence_value?: number
  best_value_history: BestValueHistoryPoint[]
  improvement_rate: number
}

export interface ConvergenceResponse {
  success: boolean
  task_id: string
  data: ConvergenceAnalysis
}

// 穩定性分析
export interface MonthlyStability {
  month: string // YYYY-MM
  mean_value: number
  std_value: number
  n_trials: number
  is_worst_month: boolean
}

export interface StabilityAnalysis {
  overall_cv: number // Coefficient of Variation
  monthly_stats: MonthlyStability[]
  worst_month?: string
  best_month?: string
}

export interface StabilityResponse {
  success: boolean
  task_id: string
  data: StabilityAnalysis
}

// Top Trials
export interface TrialDetail {
  rank: number
  trial_number: number
  value: number
  datetime_start?: string
  datetime_complete?: string
  params: Record<string, any>
  user_attrs?: Record<string, any>
}

export interface TrialsResponse {
  success: boolean
  task_id: string
  trials: TrialDetail[]
  total_count: number
}

// 完整優化結果
export interface OptimizationResultDetail {
  best_value: number
  best_params: Record<string, any>
  best_trial_number: number
  n_trials: number
  optimization_time: number
  study_direction: string
  convergence_info?: any
}

export interface OptimizationResultResponse {
  success: boolean
  task_id: string
  study_name: string
  result: OptimizationResultDetail
}

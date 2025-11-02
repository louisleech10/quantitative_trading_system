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

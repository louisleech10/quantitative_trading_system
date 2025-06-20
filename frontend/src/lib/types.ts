// frontend/src/lib/types.ts
// Type definitions for Case Search frontend

export interface CaseData {
  symbol: string;
  timestamp: string;
  trigger_idx: number;
  open: number;        // 確保這個存在
  high: number;        // 確保這個存在  
  low: number;         // 確保這個存在 
  close: number;
  volume: number;
  price_change: number;
  market_phase: string;
  future1_close_return?: number;
  future2_close_return?: number;
  future4_close_return?: number;
  future6_close_return?: number;
  future_max_return?: number;
  future_max_drawdown?: number;
  future24_close?: number;
  future24_low?: number;
  prior_volatility?: number;
  prior_range?: number;
  prior_abs_change_sum?: number;
  time_range: {
    start: string;
    end: string;
  };
}

export interface CaseSummary {
  total_cases: number;
  positive_cases: number;
  negative_cases: number;
  unique_symbols: number;
  time_range: {
    start: string;
    end: string;
  };
  market_phase_distribution: Record<string, number>;
}

export interface SamplingQuality {
  time_separation_score: number;
  symbol_diversity_score: number;
  market_phase_balance: number;
  overall_quality_score: number;
  warnings: string[];
}

export interface SearchResultData {
  cases: CaseData[];
  summary: CaseSummary;
  sampling_quality: SamplingQuality;
  execution_time: number;
  cache_used: boolean;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  timestamp: string;
}

export interface TaskInfo {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  updated_at: string;
  config_name: string;
  progress?: {
    current: number;
    total: number;
    percentage: number;
    current_symbol?: string;
    estimated_remaining_seconds?: number;
  };
  error_message?: string;
}

export interface SearchTemplate {
  name: string;
  description: string;
  config: any;
  is_default: boolean;
  created_at: string;
}

// Search request types
export interface SearchRequest {
  config: {
    name: string;
    description?: string;
    timeframe: string;
    start_date: string;
    end_date: string;
    lookback_periods: number;
    forward_periods: number;
    sample_limit: number;
    min_volume: number;
    exclude_new_listing_days: number;
    initial_conditions: FilterCondition[];
    advanced_conditions: FilterCondition[];
  };
  symbols?: string[];
  save_results?: boolean;
  export_format?: string;
}

export interface FilterCondition {
  condition_type: string;
  parameter: string;
  operator: string;
  value: number | number[];
  description?: string;
}
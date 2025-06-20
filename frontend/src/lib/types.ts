// frontend/src/lib/types.ts
// Type definitions for Case Search API responses

export interface CaseData {
  symbol: string;
  timestamp: string;
  trigger_idx: number;
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
  prior_volatility?: number;
  prior_range?: number;
  prior_abs_change_sum?: number;
  time_range?: {
    start: string;
    end: string;
  };
}

export interface SearchResult {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress?: number;
  cases?: CaseData[];
  statistics?: {
    total_cases: number;
    symbols_count: number;
    market_phases: Record<string, number>;
    avg_price_change: number;
    avg_future_return: number;
  };
  error?: string;
}

export interface SearchTemplate {
  id: string;
  name: string;
  description: string;
  config: {
    name: string;
    start_time: string;
    end_time: string;
    price_change_min: number;
    volume_threshold: number;
    sample_limit: number;
  };
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  timestamp?: string;
}

// API request types
export interface SearchRequest {
  template_id?: string;
  custom_config?: {
    name: string;
    start_time: string;
    end_time: string;
    price_change_min: number;
    price_change_max: number;
    volume_threshold: number;
    sample_limit: number;
  };
}
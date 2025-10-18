// frontend/src/lib/types.ts - 安全擴充版本
// 在現有內容基礎上添加20個新參數，保持向後兼容

// ===== 保持現有的基礎類型定義 =====

export interface CaseData {
  symbol: string;
  timestamp: string;
  trigger_idx: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  price_change: number;
  market_phase: string;
  
  // 現有的未來表現參數 (保持不變)
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
  
  // ===== 新增：基礎觸發條件參數 (5個新增) =====
  closing_strength?: number;      // 收盤強度
  price_position?: number;        // 價格位置
  volume_multiplier?: number;     // 成交量倍數
  taker_buy_ratio?: number;       // 主動買入比例
  timeframe?: string;             // 時間框架
  
  // ===== 新增：未來收益參數 (1-12根K線) =====
  future_1bar_return?: number;
  future_2bar_return?: number;
  future_3bar_return?: number;
  future_4bar_return?: number;
  future_5bar_return?: number;
  future_6bar_return?: number;
  future_7bar_return?: number;
  future_8bar_return?: number;
  future_9bar_return?: number;
  future_10bar_return?: number;
  future_11bar_return?: number;
  future_12bar_return?: number;
  
  // ===== 新增：未來回撤參數 (1-12根K線) =====
  future_1bar_max_drawdown?: number;
  future_2bar_max_drawdown?: number;
  future_3bar_max_drawdown?: number;
  future_4bar_max_drawdown?: number;
  future_5bar_max_drawdown?: number;
  future_6bar_max_drawdown?: number;
  future_7bar_max_drawdown?: number;
  future_8bar_max_drawdown?: number;
  future_9bar_max_drawdown?: number;
  future_10bar_max_drawdown?: number;
  future_11bar_max_drawdown?: number;
  future_12bar_max_drawdown?: number;
  
  // ===== 新增：時間相關描述參數 =====
  hour_of_day?: number;           // 觸發時的小時 (0-23)
  day_of_week?: number;           // 觸發時的星期 (1-7)

  // ===== 改寫：分類特徵參數 (9個) =====
  // 數值參數（3個）
  past_3day_max_volatility?: number;   // 過去3天最大波動度(%)
  past_3day_direction?: number;        // 過去3天方向性(%)
  past_3day_volume_cv?: number;        // 過去3天量能變異係數

  // 分類參數（6個）
  volatility_class?: string;   // L/M/H/X
  direction_class?: string;    // D/S/U/V
  volume_class?: string;       // A/B/C
  market_class?: string;       // C1-C12
  market_class_name?: string;  // 平靜橫盤等
  difficulty_level?: string;   // 簡單/中等/困難

  // ===== 新增：標準化時間回報 (向後兼容) =====
  future24_close_return?: number;
  future48_close_return?: number;
  future72_close_return?: number;
  future72_max_return?: number;
  future72_max_drawdown?: number;
  
  // ===== 新增：反例專用參數 =====
  positive_negative_ratio?: string;  // 正負比例 (如 "1:2")
  time_separation_days?: number;     // 時間分離天數
  case_type?: 'positive' | 'negative'; // 案例類型
  label?: 0 | 1;                     // 標籤 (1=正例, 0=負例)
  
  // 現有的時間範圍 (保持不變)
  time_range: {
    start: string;
    end: string;
  };
}

// ===== 保持現有的其他類型定義不變 =====

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
  
  // ===== 新增：參數統計和驗證報告 =====
  parameter_statistics?: ParameterStatistics;
  validation_report?: ParameterValidationReport;
  basic_trigger_stats?: Record<string, any>;
  future_performance_stats?: Record<string, any>;
  time_distribution_stats?: Record<string, any>;
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

// ===== 新增：參數相關的類型定義 =====

// 參數統計類型
export interface ParameterStatistics {
  basic_trigger_params: {
    price_change: ParameterStat;
    closing_strength: ParameterStat;
    price_position: ParameterStat;
    volume_multiplier: ParameterStat;
    taker_buy_ratio: ParameterStat;
  };
  
  future_return_params: Record<string, ParameterStat>;
  future_drawdown_params: Record<string, ParameterStat>;
  
  time_distribution: {
    hour_distribution: Record<number, number>;
    day_distribution: Record<number, number>;
    market_phase_distribution: Record<string, number>;
  };
}

export interface ParameterStat {
  min: number;
  max: number;
  avg: number;
  count: number;
  valid_percentage: number;
}

// 參數驗證報告類型
export interface ParameterValidationReport {
  total_rows: number;
  parameters_status: {
    basic_trigger: Record<string, ParameterStatus>;
    future_returns: Record<string, ParameterStatus>;
    future_drawdowns: Record<string, ParameterStatus>;
    descriptive: Record<string, ParameterStatus>;
  };
  data_quality: {
    total_parameters: number;
    existing_parameters: number;
    completion_rate: number;
    has_errors: boolean;
    has_warnings: boolean;
  };
  warnings: string[];
  errors: string[];
  basic_trigger_params_count: number;
  future_return_params_count: number;
  future_drawdown_params_count: number;
  descriptive_params_count: number;
  total_new_params_count: number;
  completion_rate: number;
  quality_score: number;
}

export interface ParameterStatus {
  exists: boolean;
  nan_count?: number;
  nan_percentage?: number;
  data_type?: string;
  sample_values?: any[];
}

// ===== 新增：參數常數定義 =====

// 基礎觸發條件參數列表
export const BASIC_TRIGGER_PARAMETERS = [
  'price_change',
  'closing_strength', 
  'price_position',
  'volume_multiplier',
  'taker_buy_ratio'
] as const;

// 未來收益參數列表 (1-12根K線)
export const FUTURE_RETURN_PARAMETERS = [
  'future_1bar_return', 'future_2bar_return', 'future_3bar_return', 
  'future_4bar_return', 'future_5bar_return', 'future_6bar_return',
  'future_7bar_return', 'future_8bar_return', 'future_9bar_return',
  'future_10bar_return', 'future_11bar_return', 'future_12bar_return'
] as const;

// 未來回撤參數列表 (1-12根K線)
export const FUTURE_DRAWDOWN_PARAMETERS = [
  'future_1bar_max_drawdown', 'future_2bar_max_drawdown', 'future_3bar_max_drawdown',
  'future_4bar_max_drawdown', 'future_5bar_max_drawdown', 'future_6bar_max_drawdown',
  'future_7bar_max_drawdown', 'future_8bar_max_drawdown', 'future_9bar_max_drawdown',
  'future_10bar_max_drawdown', 'future_11bar_max_drawdown', 'future_12bar_max_drawdown'
] as const;

// 時間描述參數列表
export const DESCRIPTIVE_PARAMETERS = [
  'hour_of_day',
  'day_of_week', 
  'market_phase',
  'timeframe'
] as const;

// 反例專用參數列表
export const NEGATIVE_SAMPLING_PARAMETERS = [
  'positive_negative_ratio',
  'enable_time_separation',
  'time_separation_days'
] as const;

// 向後兼容的現有參數列表
export const LEGACY_PARAMETERS = [
  'future1_close_return',
  'future2_close_return', 
  'future4_close_return',
  'future6_close_return',
  'future24_close_return',
  'future48_close_return',
  'future72_close_return',
  'future_max_return',
  'future_max_drawdown',
  'future72_max_return',
  'future72_max_drawdown',
  'future24_close',
  'future24_low'
] as const;

// 所有新參數的聯合類型
export type NewParameterNames = 
  | typeof BASIC_TRIGGER_PARAMETERS[number]
  | typeof FUTURE_RETURN_PARAMETERS[number] 
  | typeof FUTURE_DRAWDOWN_PARAMETERS[number]
  | typeof DESCRIPTIVE_PARAMETERS[number]
  | typeof NEGATIVE_SAMPLING_PARAMETERS[number];

// 參數分組
export interface ParameterGroups {
  basicTrigger: typeof BASIC_TRIGGER_PARAMETERS;
  futureReturn: typeof FUTURE_RETURN_PARAMETERS;
  futureDrawdown: typeof FUTURE_DRAWDOWN_PARAMETERS;
  descriptive: typeof DESCRIPTIVE_PARAMETERS;
  negativeSampling: typeof NEGATIVE_SAMPLING_PARAMETERS;
  legacy: typeof LEGACY_PARAMETERS;
}

// 參數類別常數
export const PARAMETER_CATEGORIES = {
  BASIC_TRIGGER: 'basic_trigger',
  FUTURE_RETURN: 'future_return', 
  FUTURE_DRAWDOWN: 'future_drawdown',
  DESCRIPTIVE: 'descriptive',
  NEGATIVE_SAMPLING: 'negative_sampling',
  LEGACY: 'legacy'
} as const;

// ===== 新增：工具函數類型 =====

// 參數格式化函數類型
export type ParameterFormatter = (value: number | undefined | null) => string;

// 參數驗證函數類型
export type ParameterValidator = (value: number | undefined | null) => boolean;

// 參數範圍類型
export interface ParameterRange {
  min: number;
  max: number;
  step?: number;
  default?: number;
}

// 參數配置界面類型
export interface ParameterUIConfig {
  label: string;
  description: string;
  range: ParameterRange;
  formatter: ParameterFormatter;
  validator: ParameterValidator;
  category: keyof typeof PARAMETER_CATEGORIES;
}
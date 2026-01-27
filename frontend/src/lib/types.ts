// frontend/src/lib/types.ts - 安全擴充版本
// 在現有內容基礎上添加20個新參數，保持向後兼容

// ===== 保持現有的基礎類型定義 =====

/**
 * 價格變動計算方式
 * OPEN_TO_CLOSE: 使用 (Close - Open) / Open，適合日內交易
 * CLOSE_TO_CLOSE: 使用 pct_change()，適合波段交易，包含跳空
 */
export enum PriceChangeMethod {
  OPEN_TO_CLOSE = "OPEN_TO_CLOSE",
  CLOSE_TO_CLOSE = "CLOSE_TO_CLOSE"
}

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
    price_change_method?: PriceChangeMethod; // 可選，預設 CLOSE_TO_CLOSE
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

// ===== Phase 3.2: 信號密度分析類型定義 =====

/**
 * 訓練窗口配置
 * 定義從哪個參考點開始,往前/往後看多少根K線作為訓練窗口
 */
export interface TrainingWindowConfig {
  /** 參考點類型: TO(開單點)/TC(平倉點)/custom(自定義時間戳) */
  reference_point: "TO" | "TC" | "custom";
  /** 從參考點往前看N根K線(1~1000) */
  lookback_bars: number;
  /** 從參考點往後看M根K線(0~100,預設0避免未來函數洩漏) */
  lookforward_bars: number;
  /** 窗口模式: relative(嚴格N根)/full_range(使用全部可用K線) */
  mode: "relative" | "full_range";
  /** 自定義時間戳(僅當reference_point='custom'時使用) */
  custom_timestamp?: number;
}

/**
 * 策略配置
 * 定義策略使用的指標類型、數據源、策略邏輯和參數
 */
export interface StrategyConfig {
  /** 數據源(close/open/high/low/volume/taker_buy_volume/taker_ratio/quote_volume) */
  data_source: string;
  /** 指標類型(ema/sma/rsi等,必須已在IndicatorEngine中註冊) */
  indicator_type: string;
  /** 策略邏輯類型(three_line/crossover/threshold/ma_distance等) */
  strategy_logic: string;
  /** 策略參數字典,包含指標參數(如period)和策略參數(如閾值) */
  params: Record<string, any>;
}

/**
 * 信號密度分析請求
 */
export interface SignalDensityRequest {
  /** 策略配置 */
  strategy_config: StrategyConfig;
  /** 訓練窗口配置 */
  training_window: TrainingWindowConfig;
  /** 正例案例ID列表(建議≥10個) */
  positive_cases: string[];
  /** 反例案例ID列表(建議≥10個) */
  negative_cases: string[];
}

/**
 * 信號密度分析響應
 *
 * 判斷標準:
 * - 優秀策略: separation>0.3 AND p_value<0.05 AND cohens_d>0.5
 * - 中等策略: separation>0.2 AND p_value<0.10
 * - 較弱策略: separation<0.2 OR p_value>0.10
 */
export interface SignalDensityResponse {
  /** 正例平均信號密度(0.0~1.0) */
  positive_avg_density: number;
  /** 反例平均信號密度(0.0~1.0) */
  negative_avg_density: number;
  /** 密度差異(positive - negative),Optuna優化目標,範圍-1.0~1.0 */
  separation: number;
  /** 統計顯著性p-value(獨立t-test),<0.05為顯著,<0.01為高度顯著 */
  p_value: number;
  /** Cohen's d效果量,>0.2小效果,>0.5中效果,>0.8大效果 */
  cohens_d: number;
  /** 穩定性係數(按月分組CV),<0.3穩定,<0.5可接受,>0.5不穩定 */
  stability_cv: number;
  /** 正例信號密度標準差 */
  positive_std: number;
  /** 反例信號密度標準差 */
  negative_std: number;
  /** 正例樣本數量 */
  positive_sample_size: number;
  /** 反例樣本數量 */
  negative_sample_size: number;
  /** 每個案例的信號密度字典(case_id → density) */
  case_level_densities: Record<string, number>;
}

/**
 * 訓練窗口預覽響應(Debug用)
 */
export interface TrainingWindowPreview {
  /** 案例ID */
  case_id: string;
  /** 交易對 */
  symbol: string;
  /** 時間框架 */
  timeframe: string;
  /** 參考點類型 */
  reference_point: string;
  /** 往前看根數 */
  lookback_bars: number;
  /** 往後看根數 */
  lookforward_bars: number;
  /** 實際K線數量 */
  actual_bars: number;
  /** 時間戳範圍 */
  timestamp_range: {
    start: number | null;
    end: number | null;
  };
}

// ===== Phase 3.6: 優化結果展示UI 類型定義 =====

/**
 * 策略參數
 * 定義策略的完整參數組合
 */
export interface StrategyParameters {
  /** 數據源 (close/open/high/low/volume/taker_ratio) */
  data_source: string;
  /** 指標類型 (ema/sma/rsi等) */
  indicator_type: string;
  /** 策略邏輯 (three_line/short_long_cross/mid_long_cross) */
  strategy_logic: string;
  /** EMA短週期參數 */
  ema_short?: number;
  /** EMA中週期參數 */
  ema_mid?: number;
  /** EMA長週期參數 */
  ema_long?: number;
  /** 其他動態參數 */
  [key: string]: any;
}

/**
 * 試驗摘要
 * 單個Optuna試驗的完整信息
 */
export interface TrialSummary {
  /** 試驗編號 */
  trial_number: number;
  /** 參數組合 */
  params: StrategyParameters;
  /** 目標值 (separation) */
  value: number;
  /** 試驗狀態 */
  state: 'COMPLETE' | 'PRUNED' | 'FAIL';
  /** 完成時間 */
  datetime_complete: string;
  /** 中間值（用於剪枝分析） */
  intermediate_values?: number[];
  /** 試驗持續時間（單位：秒） */
  duration?: number;
}

/**
 * 參數重要性
 * Optuna計算的參數影響力分析
 */
export interface ParamImportance {
  /** 參數名稱 */
  parameter_name: string;
  /** 重要性得分 (範圍 0-1, 1=最重要) */
  importance: number;
  /** 排名 (1=最重要) */
  rank: number;
}

/**
 * Trial - 單次優化試驗記錄
 * 對應 OptimizationHistoryPoint
 */
export interface Trial {
  /** 試驗編號 */
  trial_number: number;
  /** 目標值 (separation) */
  value: number;
  /** 截至當前的最佳值 */
  best_value_so_far: number;
  /** 完成時間 */
  datetime: string;
  /** 參數組合 */
  params: Record<string, any>;
  /** 試驗狀態 */
  state: 'COMPLETE' | 'PRUNED' | 'FAIL';
}

/**
 * 月度數據
 * 按月分組的穩定性分析數據
 */
export interface MonthlyData {
  /** 月份 (YYYY-MM) */
  month: string;
  /** 該月的separation值 */
  separation: number;
  /** 該月的正例平均密度 */
  positive_density: number;
  /** 該月的反例平均密度 */
  negative_density: number;
  /** 該月的案例數量 */
  case_count: number;
}

/**
 * 穩定性分析
 * 策略在不同時期的表現穩定性評估
 */
export interface StabilityAnalysis {
  /** 月度separation數據 */
  monthly_separations: MonthlyData[];
  /** 平均separation */
  mean_separation: number;
  /** separation標準差 */
  std_separation: number;
  /** 變異係數 (CV = std / mean) */
  cv: number;
  /** separation > 0的月份占比 */
  positive_ratio: number;
  /** 表現最差的月份 */
  worst_month: MonthlyData;
  /** 表現最好的月份 */
  best_month: MonthlyData;
}

/**
 * Pareto前沿解
 * 多目標優化中的非支配解
 */
export interface ParetoSolution {
  /** 試驗編號 */
  trial_number: number;
  /** 參數組合 */
  params: StrategyParameters;
  /** 目標1: separation */
  separation: number;
  /** 目標2: 穩定性得分 (1 - CV) */
  stability_score: number;
  /** 是否為推薦解 */
  is_recommended: boolean;
}

/**
 * 優化結果
 * 完整的Optuna優化結果數據
 */
export interface OptimizationResult {
  /** 任務ID */
  task_id: string;
  /** 最佳目標值 (最佳separation) */
  best_value: number;
  /** 最佳參數組合 */
  best_params: StrategyParameters;
  /** 最佳試驗編號 */
  best_trial_number: number;
  /** 總試驗次數 */
  total_trials: number;
  /** 優化總耗時（秒） */
  optimization_time: number;
  /** 收斂歷史（每次試驗的當前最佳值） */
  convergence_history: number[];
  /** 所有試驗摘要 */
  trials_summary: TrialSummary[];
  /** 參數重要性分析 */
  param_importances?: ParamImportance[];
  /** 信號密度分析結果 */
  density_analysis: SignalDensityResponse;
  /** 穩定性分析 */
  stability_analysis?: StabilityAnalysis;
  /** Pareto前沿數據（多目標優化） */
  pareto_front?: ParetoSolution[];
  /** 創建時間 */
  created_at: string;
  /** 完成時間 */
  completed_at?: string;
}

/**
 * 參數重要性分析響應
 * 後端API返回的參數重要性數據
 */
export interface ImportanceAnalysisResponse {
  /** 任務ID */
  task_id: string;
  /** 參數重要性列表 */
  importances: ParamImportance[];
  /** 分析方法 (fanova/permutation) */
  method: string;
  /** 計算時間戳 */
  computed_at: string;
}

/**
 * 優化歷史響應
 * 後端API返回的優化歷程數據
 */
export interface OptimizationHistoryResponse {
  /** 任務ID */
  task_id: string;
  /** 收斂歷史（累積最佳值） */
  convergence_history: number[];
  /** 所有試驗的目標值 */
  trial_values: number[];
  /** 試驗編號列表 */
  trial_numbers: number[];
  /** 試驗狀態列表 */
  trial_states: string[];
  /** 總試驗次數 */
  total_trials: number;
  /** 完成試驗次數 */
  completed_trials: number;
  /** 剪枝試驗次數 */
  pruned_trials: number;
  /** 失敗試驗次數 */
  failed_trials: number;
}

/**
 * 參數空間響應
 * 後端API返回的參數空間探索數據
 */
export interface ParamSpaceResponse {
  /** 任務ID */
  task_id: string;
  /** 所有試驗數據 */
  trials: {
    /** 試驗編號 */
    number: number;
    /** 參數字典 */
    params: Record<string, any>;
    /** 目標值 */
    value: number;
    /** 狀態 */
    state: string;
  }[];
  /** 參數名稱列表 */
  param_names: string[];
  /** 參數範圍 */
  param_ranges: Record<string, { min: number; max: number }>;
}

/**
 * 策略對比結果
 * 多個策略的並列對比數據
 */
export interface ComparisonResult {
  /** 對比的策略列表 */
  strategies: {
    /** 任務ID */
    task_id: string;
    /** 策略名稱 */
    name: string;
    /** 核心指標 */
    metrics: {
      separation: number;
      p_value: number;
      cohens_d: number;
      cv: number;
      positive_density: number;
      negative_density: number;
    };
    /** 最佳參數 */
    best_params: StrategyParameters;
  }[];
  /** 對比時間戳 */
  compared_at: string;
}

/**
 * 匯出格式類型
 */
export type ExportFormat = 'csv' | 'png' | 'pdf';

/**
 * 圖表類型
 */
export type ChartType = 
  | 'box_plot'           // 箱型圖
  | 'histogram'          // 直方圖
  | 'violin_plot'        // 小提琴圖
  | 'convergence'        // 收斂曲線
  | 'param_importance'   // 參數重要性
  | 'stability'          // 穩定性時間序列
  | 'param_space_2d'     // 2D參數空間
  | 'param_space_3d'     // 3D參數空間
  | 'pareto_front';      // Pareto前沿

/**
 * 圖表配置
 */
export interface ChartConfig {
  /** 圖表類型 */
  type: ChartType;
  /** 圖表標題 */
  title: string;
  /** 圖表寬度 */
  width?: number;
  /** 圖表高度 */
  height?: number;
  /** 是否顯示圖例 */
  showLegend?: boolean;
  /** 自定義顏色方案 */
  colors?: string[];
}

/**
 * 統計顯著性等級
 */
export type SignificanceLevel = 'highly_significant' | 'significant' | 'not_significant';

/**
 * 效果量等級
 */
export type EffectSizeLevel = 'large' | 'medium' | 'small' | 'negligible';

/**
 * 穩定性等級
 */
export type StabilityLevel = 'stable' | 'moderate' | 'unstable';

/**
 * 策略質量評估
 */
export interface StrategyQualityAssessment {
  /** 整體評級 (excellent/good/weak) */
  overall_rating: 'excellent' | 'good' | 'weak';
  /** 統計顯著性等級 */
  significance: SignificanceLevel;
  /** 效果量等級 */
  effect_size: EffectSizeLevel;
  /** 穩定性等級 */
  stability: StabilityLevel;
  /** 警告信息 */
  warnings: string[];
  /** 建議信息 */
  recommendations: string[];
}

/**
 * 獲取統計顯著性等級
 */
export function getSignificanceLevel(pValue: number): SignificanceLevel {
  if (pValue < 0.01) return 'highly_significant';
  if (pValue < 0.05) return 'significant';
  return 'not_significant';
}

/**
 * 獲取效果量等級
 */
export function getEffectSizeLevel(cohensD: number): EffectSizeLevel {
  const absD = Math.abs(cohensD);
  if (absD >= 0.8) return 'large';
  if (absD >= 0.5) return 'medium';
  if (absD >= 0.2) return 'small';
  return 'negligible';
}

/**
 * 獲取穩定性等級
 */
export function getStabilityLevel(cv: number): StabilityLevel {
  if (cv < 0.3) return 'stable';
  if (cv < 0.5) return 'moderate';
  return 'unstable';
}

/**
 * 評估策略質量
 */
export function assessStrategyQuality(
  result: OptimizationResult
): StrategyQualityAssessment {
  const { separation, p_value, cohens_d, stability_cv } = result.density_analysis;
  
  // NaN 檢查：數據包含無效值時返回弱評級
  if (isNaN(separation) || isNaN(p_value) || isNaN(cohens_d) || isNaN(stability_cv)) {
    return {
      overall_rating: 'weak',
      significance: 'not_significant',
      effect_size: 'negligible',
      stability: 'unstable',
      warnings: ['數據包含無效值 (NaN)，無法進行質量評估'],
      recommendations: ['請檢查輸入數據的完整性']
    };
  }
  
  const significance = getSignificanceLevel(p_value);
  const effectSize = getEffectSizeLevel(cohens_d);
  const stability = getStabilityLevel(stability_cv);
  
  const warnings: string[] = [];
  const recommendations: string[] = [];
  
  // 判斷整體評級
  let overallRating: 'excellent' | 'good' | 'weak' = 'weak';
  
  if (separation > 0.3 && p_value < 0.05 && cohens_d > 0.5 && stability_cv < 0.5) {
    overallRating = 'excellent';
  } else if (separation > 0.2 && p_value < 0.10) {
    overallRating = 'good';
  }
  
  // 生成警告
  if (p_value >= 0.05) {
    warnings.push(`統計顯著性不足 (p-value = ${p_value.toFixed(4)})`);
    recommendations.push('建議增加樣本數量或調整策略參數');
  }
  
  if (cohens_d < 0.2) {
    warnings.push(`效果量較小 (Cohen's d = ${cohens_d.toFixed(2)})`);
    recommendations.push('策略區分能力較弱，可能需要優化參數範圍');
  }
  
  if (stability_cv > 0.5) {
    warnings.push(`穩定性較差 (CV = ${stability_cv.toFixed(2)})`);
    recommendations.push('策略在不同時期表現波動大，需謹慎使用');
  }
  
  return {
    overall_rating: overallRating,
    significance,
    effect_size: effectSize,
    stability,
    warnings,
    recommendations,
  };
}
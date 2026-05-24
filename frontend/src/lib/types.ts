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
    positive_case?: boolean | number;
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
  basic_trigger_stats?: Record<string, unknown>;
  future_performance_stats?: Record<string, unknown>;
  time_distribution_stats?: Record<string, unknown>;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: unknown;
  };
  timestamp: string;
}

// ===== Feature Factory 類型定義 =====

export interface FeatureFactoryConfig {
  global_settings: {
    sequence_length: number;
    max_lag_ratio: number;
    lag_strategy?: string;
    custom_lags?: number[] | null;
  };
  data_sources: {
    enabled_sources: string[];
    synthetic_sources?: string[];
  };
  timeframes: {
    primary: string;
    training: string[];
    alignment?: string;
    alignment_mode?: 'open_minus' | 'close_time';
  };
  atomic_indicators: Record<
    string,
    {
      enabled: boolean;
      indicators?: Array<{ name: string; enabled?: boolean; [key: string]: unknown }>;
      features?: Record<string, { enabled: boolean; [key: string]: unknown }>;
      data_sources?: string[] | null;
    }
  >;
  operators?: {
    enabled?: boolean;
    [key: string]: { enabled: boolean; [key: string]: unknown } | boolean | undefined;
  };
  rolling_aggregation?: {
    enabled?: boolean;
    windows: number[];
    aggregators?: Record<string, { enabled: boolean; [key: string]: unknown }> | string[];
    apply_to?: string | string[];
  };
  lag_features?: {
    enabled?: boolean;
    apply_to?: string | string[];
    exclude_patterns?: string[];
  };
  cross_sectional?: {
    enabled?: boolean;
    reference_symbol?: string;
    features?: Record<string, { enabled: boolean; [key: string]: unknown }> | string[];
  };
  meta_features?: {
    enabled?: boolean;
    consensus?: boolean;
    interaction?: boolean;
    time_features?: boolean;
    trend_consensus?: boolean;
    momentum_divergence?: boolean;
    volume_price_divergence?: boolean;
    volatility_regime?: boolean;
  };
  labels?: {
    binary?: { horizons?: number[]; threshold?: number };
    regression?: { horizons?: number[] };
  };
  custom_indicators?: unknown[];
  preprocessing?: {
    enabled?: boolean;
    mode?: 'append' | 'replace';
    winsorization?: {
      enabled?: boolean;
      method?: 'sigma' | 'quantile';
      sigma_k?: number;
      quantile_range?: [number, number] | number[];
      apply_to?: string | string[];
    };
    adf_differencing?: {
      enabled?: boolean;
      adf_threshold?: number;
      max_diff?: number;
      sample_size?: number;
      apply_to?: string;
    };
    fractional_differencing?: {
      enabled?: boolean;
      d_range?: [number, number] | number[];
      adf_threshold?: number;
      weight_threshold?: number;
      precision?: number;
      apply_to?: string;
      cache_d_star?: boolean;
    };
    rank_transform?: {
      enabled?: boolean;
      window?: number;
      apply_to?: string | string[];
    };
    gaussian_normalize?: {
      enabled?: boolean;
      clip_range?: [number, number] | number[];
      apply_to?: string | string[];
    };
    /** IC-First 兩段式路由：winsor 全特徵 → IC 選特徵 → rank/zscore 只做選出特徵 */
    ic_first_pipeline?: boolean;
    adaptive_zscore?: {
      enabled?: boolean;
      windows?: number[];
      epsilon?: number;
      apply_to?: string | string[];
    };
  };
}

export interface FeatureRegistryEntry {
  symbol: string;
  timeframe: string;
  config_hash: string;
  feature_count: number;
  row_count: number;
  created_at: number;
  hdf5_relative_path: string;
}

export interface FeatureRegistryResponse {
  entries: FeatureRegistryEntry[];
  total: number;
}

export interface FeatureGenerationRequest {
  config?: Record<string, unknown>;
  symbols: string[];
  timeframe: string;
  start_date?: string;
  end_date?: string;
  force_regenerate?: boolean;
}

// ===== Feature Factory Schema Types =====

export interface SchemaIndicator {
  name: string;
  enabled: boolean;
  description: string;
  params?: Record<string, unknown>;
}

export interface SchemaCategory {
  enabled: boolean;
  level: string;
  description: string;
  indicators?: SchemaIndicator[];
  features?: SchemaIndicator[];
  params?: Record<string, unknown>;
}

export interface SchemaOperator {
  enabled: boolean;
  description: string;
  rules?: Array<{
    indicator: string;
    condition: string;
    name_suffix: string;
    enabled: boolean;
  }>;
  operators?: Record<string, { enabled: boolean }>;
}

export interface SchemaAggregator {
  enabled: boolean;
  description: string;
}

export interface SchemaSubEngine {
  enabled: boolean;
  description: string;
}

export interface SchemaMethod {
  enabled: boolean;
  description: string;
  params?: Record<string, unknown>;
}

export interface FeatureSchema {
  layers: {
    layer1: {
      name: string;
      enabled: boolean;
      categories: Record<string, SchemaCategory>;
    };
    layer2: {
      name: string;
      enabled: boolean;
      operators: Record<string, SchemaOperator>;
    };
    layer3: {
      name: string;
      enabled: boolean;
      windows: number[];
      aggregators: Record<string, SchemaAggregator>;
      apply_to: string;
    };
    layer4: {
      name: string;
      enabled: boolean;
      apply_to: string;
      exclude_patterns: string[];
    };
    layer5: {
      name: string;
      enabled: boolean;
      reference_symbol: string;
      features: Record<string, { enabled: boolean; description: string }>;
    };
    layer6: {
      name: string;
      enabled: boolean;
      sub_engines: Record<string, SchemaSubEngine>;
    };
    layer6_5: {
      name: string;
      enabled: boolean;
      mode: string;
      methods: Record<string, SchemaMethod>;
    };
  };
}

export interface BatchToggleItem {
  path: string;
  value: boolean;
}

export interface BatchGenerateRequest {
  symbols: string[];
  timeframe: string;
  config_override?: Record<string, unknown>;
  force_regenerate?: boolean;
  max_workers?: number;
}

export type BatchTaskStatusValue =
  | 'idle'
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'partial'
  | 'paused'
  | 'paused_ram_gate';

export interface BatchOutputPath {
  symbol: string;
  timeframe: string;
  path: string;
  download_url?: string;
}

export interface BatchItemRss {
  symbol: string;
  timeframe: string;
  rssBeforeItemMB?: number;
  rssPeakMB: number;
  rssAfterGcMB: number;
}

export interface BatchItemMetrics {
  current_symbol?: string | null;
  current_timeframe?: string | null;
  rss_before_item_mb?: number;
  rss_peak_item_mb?: number;
  rss_after_gc_mb?: number;
}

export interface BatchTaskStatus {
  task_id: string;
  batch_id?: string;
  status: BatchTaskStatusValue;
  total: number;
  completed: number;
  failed: number;
  progress: number;
  current_symbol?: string | null;
  current_timeframe?: string | null;
  queued?: number;
  concurrent_symbols?: number;
  memory_sanity_failed?: boolean;
  eta_seconds?: number;
  resume_available?: boolean;
  output_paths?: BatchOutputPath[];
  per_item_rss?: BatchItemRss[];
  last_item_metrics?: BatchItemMetrics | null;
  results?: Record<string, string>;
  errors?: Record<string, string>;
}

export interface FeaturePreview {
  total_features: number;
  estimated_time_seconds: number;
  memory_mb: number;
  breakdown: Record<string, number>;
}

export interface FeatureValidationSummary {
  has_nan: boolean;
  has_inf: boolean;
  coverage: number;
  inf_count: number;
  inf_ratio: number;
  groups_with_inf: number;
  warnings?: string[];
}

export interface FeatureTask {
  task_id: string;
  status: string;
  progress: number;
  current_stage: string | null;
  completed_stages: string[];
  error: string | null;
  compute_warnings?: string[];
  validation_summary?: FeatureValidationSummary;
}

export interface FeatureFactoryPreset {
  name: string;
  description?: string;
  level?: 'L1' | 'L2' | 'L3' | 'ML';
  config?: FeatureFactoryConfig;
}

export interface FeatureIndicatorSpec {
  name: string;
  category?: string;
  input_type?: string;
  output_count?: number;
}

export interface FeatureGenerationProgress {
  status?: string;
  stage?: string;
  progress?: number;
  message?: string;
}

export interface FeatureNLResult {
  config_patch: Record<string, unknown>;
  description: string;
  preview?: FeaturePreview;
}

export interface FeatureGenerationResult {
  feature_names?: string[];
  metadata?: {
    compute_warnings?: string[];
    feature_count?: number;
    layer_counts?: Record<string, number>;
    [key: string]: unknown;
  };
}

export type ExplorerTab =
  | 'overview'
  | 'table'
  | 'timeseries'
  | 'correlation'
  | 'distribution'
  | 'nan';

export interface FeatureSummary {
  total_features: number;
  total_rows: number;
  by_category: Record<string, number>;
  by_level: Record<string, number>;
  by_layer: Record<string, number>;
  quality: {
    nan_ratio_mean: number;
    nan_ratio_max: number;
    nan_ratio_distribution: number[];
    constant_features: string[];
    high_corr_pairs_count: number;
    stationary_ratio: number;
    quality_alerts?: Array<{
      severity: 'info' | 'warning' | 'error';
      feature: string;
      message: string;
    }>;
  };
  generation_info: {
    task_id: string;
    symbol?: string;
    timeframe?: string;
    generated_at?: string;
    generation_time?: number;
    config_hash?: string;
  };
}

export interface BrowseFeatureItem {
  name: string;
  category: string;
  level: 'L1' | 'L2' | 'L3';
  layer: string;
  nan_ratio: number;
  mean: number | null;
  std: number | null;
  min: number | null;
  q25: number | null;
  median: number | null;
  q75: number | null;
  max: number | null;
  skewness: number | null;
  kurtosis: number | null;
  is_stationary: boolean | null;
  adf_pvalue: number | null;
}

export interface BrowseFeaturesResponse {
  total: number;
  offset: number;
  limit: number;
  cursor?: string | null;
  next_cursor?: string | null;
  has_more?: boolean;
  filters_applied: {
    category?: string | null;
    level?: string | null;
    search?: string | null;
  };
  features: BrowseFeatureItem[];
}

export interface FeatureDataRow {
  timestamp: string | null;
  [featureName: string]: number | string | null;
}

export interface BrowseFeatureDataResponse {
  total_rows: number;
  offset: number;
  limit: number;
  features: string[];
  rows: FeatureDataRow[];
}

export interface BrowseCorrelationMatrix {
  features: string[];
  method?: 'pearson' | 'spearman' | 'kendall';
  matrix: number[][];
}

export interface VifRow {
  feature_name: string;
  vif: number;
  status: 'stable' | 'warning' | 'severe';
}

export interface BrowseVifResponse {
  items: VifRow[];
}

export interface FeatureStats {
  count: number;
  nan_ratio: number;
  mean: number | null;
  std: number | null;
  min: number | null;
  q25: number | null;
  median: number | null;
  q75: number | null;
  max: number | null;
  skewness: number | null;
  kurtosis: number | null;
  adf_pvalue: number | null;
  is_stationary: boolean;
}

export interface DistributionData {
  feature: string;
  n_bins: number;
  bins: number[];
  edges: number[];
  stats: FeatureStats;
}

export interface NanPatternData {
  features: string[];
  timestamps: string[];
  timestamps_total?: number;  // total time points before subsampling
  matrix: boolean[][];        // [N_features, T_sampled] — one row per feature
  nan_ratios: number[];
}

// ---- Data Quality Diagnostics --------------------------------------------
export interface DataQualityWarmupBucket {
  bucket: string;     // e.g. "0", "1-50", "51-200", "201-1000", ">1000"
  count: number;
  ratio: number;
}

export interface DataQualityCoveragePoint {
  index: number;
  timestamp: string;
  coverage: number;   // [0, 1]
}

export interface DataQualityFeatureHole {
  name: string;
  hole_count: number;
  hole_ratio: number;
}

export interface DataQualityFeatureTrailing {
  name: string;
  trailing_length: number;
}

export interface DataQualityFeatureScattered {
  name: string;
  nan_ratio: number;
}

export interface DataQualityReport {
  total_features: number;
  total_timesteps: number;
  timestamp_start: string;
  timestamp_end: string;
  is_clean: boolean;
  recommended_start_index: number;
  recommended_start_timestamp: string;
  warmup_loss_ratio: number;
  max_warmup: number;
  p95_warmup: number;
  warmup_distribution: DataQualityWarmupBucket[];
  coverage_timeline: DataQualityCoveragePoint[];
  min_coverage: number;
  min_coverage_timestamp: string;
  mid_holes: DataQualityFeatureHole[];
  trailing_nans: DataQualityFeatureTrailing[];
  scattered_nans: DataQualityFeatureScattered[];
  counts: {
    mid_holes: number;
    trailing_nans: number;
    high_nan: number;
  };
}

export interface AutoResearchStatus {
  status: string;
  research_id?: string;
}

export interface AutoResearchLogEntry {
  iteration: number;
  decision: string;
  next_action: string;
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
  config: unknown;
  is_default: boolean;
  created_at: string;
}

export type SearchResult = SearchResultData;

export interface SimpleSearchRequest {
  name: string;
  symbols: string[];
  timeframe: string;
  searchMode?: 'research' | 'realtime';
  startDate?: string | null;
  endDate?: string | null;
  priceChangeMethod?: PriceChangeMethod;
  priceChange?: number | null;
  volumeMultiplier?: number | null;
  closingStrength?: number | null;
  takerBuyRatio?: number | null;
  pricePosition?: number | null;
  saveResults?: boolean;
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
  sample_values?: unknown[];
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
  params: Record<string, unknown>;
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
  [key: string]: unknown;
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
  params: Record<string, unknown>;
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

// ===== Phase 4: Model Enhancement UI 類型定義 =====

export interface CalibrationReliabilityCurve {
  bin_midpoints: number[];
  original_freq: number[];
  calibrated_freq: number[];
}

export interface CalibrationMethodMetric {
  ece: number;
  brier: number;
}

export interface CalibrationResult {
  method: string;
  best_method: string;
  improvement_pct: number;
  calibration_failed: boolean;
  reliability_curve: CalibrationReliabilityCurve;
  comparison: Record<string, CalibrationMethodMetric>;
  sample_size: number;
  cv_folds: number;
  status?: 'skipped';
  skipped?: SkippedResult;
}

export interface WalkForwardPeriod {
  period_index: number;
  train_start_idx: number;
  train_end_idx: number;
  test_start_idx: number;
  test_end_idx: number;
  train_samples: number;
  test_samples: number;
  test_auc: number | null;
  test_precision_at_k: number | null;
  test_brier_score: number | null;
  is_auc: number | null;
  is_oos_gap: number | null;
  top_features: string[];
}

export interface WalkForwardResult {
  mode: 'rolling' | 'expanding';
  n_periods: number;
  period_results: WalkForwardPeriod[];
  mean_oos_auc: number;
  std_oos_auc: number;
  min_oos_auc: number;
  max_oos_auc: number;
  oos_hit_rate: number;
  mean_is_oos_gap: number;
  auc_trend: 'improving' | 'degrading' | 'stable';
  degradation_periods: number[];
  feature_stability: Record<string, number>;
  assessment: 'robust' | 'moderate' | 'unstable';
}

export interface WalkForwardMultiModeResult {
  rolling?: WalkForwardResult;
  expanding?: WalkForwardResult;
}

export interface AdversarialFeatureTest {
  ks_statistic?: number;
  ks_pvalue?: number;
  psi?: number;
  status: 'stable' | 'warning' | 'severe';
  method?: string;
}

export interface AdversarialDistributionTest {
  auc: number;
  std: number;
  status: 'good' | 'warning' | 'severe';
  top_discriminating_features: string[];
}

export interface AdversarialLeakageDetection {
  suspicious_features: string[];
  autocorrelation_flags: Record<string, {
    future_corr: number;
    lag_1_corr: number;
    is_suspicious: boolean;
  }>;
  status: 'ok' | 'skipped';
}

export interface AdversarialResult {
  distribution_test: AdversarialDistributionTest;
  feature_level_tests: Record<string, AdversarialFeatureTest>;
  leakage_detection: AdversarialLeakageDetection;
  overall_status: 'good' | 'warning' | 'severe';
  recommendations: string[];
}

export interface CPCVPathResult {
  path_index: number;
  test_groups: number[];
  auc: number | null;
  n_train: number;
  n_test: number;
}

export interface CPCVResult {
  config: {
    n_groups: number;
    n_test_groups: number;
    purge_gap: number;
    embargo_pct: number;
  };
  n_paths: number;
  summary: {
    mean_auc: number;
    std_auc: number;
    min_auc: number;
    max_auc: number;
    hit_rate: number;
  };
  path_results: CPCVPathResult[];
  path_aucs: number[];
  backtest_paths: number[][];
  feature_stability: Record<string, number>;
  status?: 'skipped';
  skipped?: SkippedResult;
}

export interface LearningCurveDataCurve {
  fractions: number[];
  train_scores: number[];
  cv_scores: number[];
  cv_stds?: number[];
  feature_names?: string[];
}

export interface LearningCurveFeatureCurve {
  feature_counts: number[];
  cv_scores: number[];
  optimal_n_features: number;
  feature_ranking: string[];
}

export interface LearningCurveDiagnosis {
  type: 'high_bias' | 'high_variance' | 'good_fit' | 'no_predictive_power' | 'insufficient_data';
  description: string;
  train_cv_gap: number;
  convergence: boolean;
  recommendation: string;
}

export interface LearningCurveResult {
  data_curve: LearningCurveDataCurve;
  feature_curve: LearningCurveFeatureCurve;
  diagnosis: LearningCurveDiagnosis;
}

export interface ModelEnhancementModuleResponse {
  task_id: string;
  status: 'running' | 'completed' | 'failed' | 'skipped';
  module: 'calibration' | 'walk_forward' | 'sample_weight' | 'adversarial' | 'cpcv' | 'learning_curve';
  result?: Record<string, unknown>;
  skipped_reason?: string | null;
  execution_time_seconds?: number;
  created_at: string;
}

export interface ModelEnhancementResult {
  modules: {
    calibration?: CalibrationResult;
    walk_forward?: WalkForwardResult | WalkForwardMultiModeResult;
    adversarial?: AdversarialResult;
    cpcv?: CPCVResult;
    learning_curve?: LearningCurveResult;
    sample_weight?: Record<string, unknown>;
  };
  module_statuses?: Record<string, ModelEnhancementModuleResponse>;
  task_id?: string;
  status?: 'running' | 'completed' | 'failed' | 'skipped';
  total_execution_time_seconds?: number;
}

// ===== Phase 6: Feature Toggle 類型定義 =====

export interface FeatureToggle {
  feature_id: string;
  name: string;
  description: string;
  difficulty: 'L1' | 'L2' | 'L3';
  is_enabled: boolean;
  is_locked: boolean;
  engine_types: string[];
  dependencies: string[];
  phase: string;
  module?: string | null;
  estimated_time?: string | null;
  tags: string[];
}

export interface FeatureToggleSummaryResponse {
  total: number;
  enabled: number;
  by_difficulty: Record<string, { total: number; enabled: number }>;
  estimated_total_seconds: number;
}

export interface FeatureToggleListResponse {
  toggles: FeatureToggle[];
  summary: FeatureToggleSummaryResponse;
  presets: string[];
}

export interface FeatureToggleUpdateRequest {
  enabled: boolean;
}

export interface FeatureToggleResponse {
  toggle: FeatureToggle;
  cascaded: string[];
  summary: FeatureToggleSummaryResponse;
}

export interface BatchToggleUpdateRequest {
  updates: Record<string, boolean>;
}

export interface BatchToggleResponse {
  updated: Record<string, boolean>;
  cascaded: string[];
  summary: FeatureToggleSummaryResponse;
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
    params: Record<string, unknown>;
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

// ===== Phase 2.4: IC 分析 UI 類型定義 =====

export interface ICAnalysisConfig {
  features_path: string;
  symbol?: string;
  timeframe?: string;
  labels_path?: string;
  meta_path?: string;
  mode: 'global' | 'event' | 'cross_sectional';
  cross_sectional_symbols?: string[];
  event_query?: string;
  event_timestamps?: number[];
  horizons: number[];
  thresholds: {
    ic_mean_min: number;
    icir_min: number;
    p_value_max: number;
    monotonicity_score_min?: number;
    correlation_threshold: number;
  };
  feature_tiers?: FeatureTierConfig;
}

export type FeatureTierLevel = 'foundation' | 'intermediate' | 'advanced' | 'custom';

export interface FeatureTierConfig {
  active_preset: FeatureTierLevel;
  custom_overrides?: {
    stage_overrides?: Record<string, boolean>;
    module_overrides?: Record<string, boolean>;
  };
}

export interface FeatureToggleItem {
  key: string;
  label: string;
  tier: 'L1' | 'L2' | 'L3';
  locked: boolean;
  enabled: boolean;
  tooltip: string;
  category: 'stage' | 'module';
}

export interface ICFeatureInfo {
  rank: number;
  feature_name: string;
  ic_mean: number;
  ic_std?: number;
  icir: number;
  p_value: number;
  ic_hit_rate?: number;
  t_stat?: number;
  monotonicity_score?: number;
  coverage?: number;
  turnover_rate?: number;
}

export interface ICDecayData {
  horizons: number[];
  ic_values: number[];
  half_life?: number;
  peak_horizon?: number;
  decay_rate?: number;
  decay_type?: string;
  fit_r2?: number;
}

export interface TurnoverTimeSeriesData {
  quantile_turnovers: number[];
  rank_change_rates: number[];
  timestamps: Array<number | string>;
}

export interface TurnoverFeatureData {
  quantile_turnover?: number;
  rank_change_rate?: number;
  autocorrelation?: number;
  time_series?: TurnoverTimeSeriesData;
}

export interface QuantileReturnData {
  quantile_mean_returns: Record<string, number>;
  long_short_spread?: number;
  cumulative_returns?: Record<string, number[]>;
}

export interface EquityCurvePoint {
  bar_index: number;
  Q1: number;
  Q5: number;
  ls_spread: number;
  drawdown?: number;
}

export interface CorrelationMatrix {
  features: string[];
  matrix: number[][];
}

export interface CrossSectionalICMatrix {
  symbols: string[];
  features: string[];
  matrix: Record<string, Record<string, number | null>>;
}

export interface CrossSymbolValidationSummary {
  status?: 'completed' | 'skipped' | 'not_run';
  reason?: string | null;
  consistency_score?: number | null;
  best_symbol?: string | null;
  worst_symbol?: string | null;
  symbol_scores?: Record<string, number>;
  feature_summary?: {
    total_features?: number;
    universal_features?: number;
    symbol_specific_features?: number;
    sign_conflict_features?: number;
  };
  samples?: {
    universal_features?: string[];
    symbol_specific_features?: string[];
    sign_conflict_features?: string[];
  };
  suggestions?: string[];
}

export interface FilterLogStage {
  input: number;
  output: number;
  removed_reasons?: Record<string, number>;
}

export interface FilterLogData {
  [stage: string]: FilterLogStage;
}

export type RollingICSeries = Record<string, number[]>;

export type GroupedICData = Record<string, Record<string, number> | Record<string, Record<string, number>>>;

export interface ICReport {
  version?: string;
  metadata?: Record<string, unknown>;
  filter_log?: FilterLogData;
  summary_table?: ICFeatureInfo[];
  ic_decay?: Record<string, ICDecayData>;
  quantile_returns?: Record<string, QuantileReturnData>;
  correlation_matrix?: CorrelationMatrix;
  grouped_ic?: GroupedICData;
  rolling_ic_series?: Record<string, RollingICSeries>;
  turnover_analysis?: Record<string, TurnoverFeatureData>;
  diversification_metrics?: Record<string, number>;
  cross_sectional_symbol_ic?: CrossSectionalICMatrix;
  cross_symbol_validation?: CrossSymbolValidationSummary;
  ai_summary?: string;
  deep_analysis_enabled?: boolean;
  deep_analysis_version?: string;
  deep_analysis_errors?: SkippedResult[];
  module_statuses?: ModuleStatus[];
  deep_analysis_summary?: {
    total: number;
    completed: number;
    skipped: number;
    failed: number;
  };
  factor_returns?: FactorReturnData;
  factor_centrality?: FactorCentralityData;
  trend_analysis?: TrendAnalysisData;
  parameter_sensitivity?: ParameterSensitivityData;
  rolling_oos?: RollingOOSData;
  factor_orthogonalization?: FactorOrthogonalizationData;
  factor_exposure?: FactorExposureData;
  long_short_analysis?: LongShortAnalysisData;
  feature_quality_diagnostics?: FeatureQualityDiagnosticsData;
  net_ic_analysis?: NetICAnalysisData;
}

export interface FeatureListItem {
  feature_name: string;
  category?: string | null;
  data_source?: string | null;
  family?: string | null;
  layer?: number | null;
}

export interface FeatureFilterConfig {
  include_features?: string[];
  exclude_features?: string[];
  include_pattern?: string;
  include_categories?: string[];
  include_data_sources?: string[];
  include_families?: string[];
  max_features?: number;
}

export interface DeepAnalysisModules {
  factor_return: boolean;
  factor_centrality: boolean;
  trend_analysis: boolean;
  parameter_sensitivity: boolean;
  rolling_oos: boolean;
  factor_orthogonalization: boolean;
  factor_exposure: boolean;
  long_short_analysis: boolean;
  feature_quality_diagnostics: boolean;
  net_ic_analysis: boolean;
}

export interface DeepAnalysisConfig {
  selected_features?: string[];
  top_n?: number;
  modules: DeepAnalysisModules;
  config_override?: Record<string, unknown>;
}

export interface ModuleStatus {
  module_name: string;
  status: string;
  reason?: string;
  error_type?: string;
}

export interface DeepAnalysisResponse {
  task_id: string;
  status: string;
  progress: number;
  current_step?: string | null;
  applied_tier?: string | null;
  summary?: {
    total_modules: number;
    completed_count: number;
    skipped_count: number;
    failed_count: number;
    total_execution_time_s: number;
  } | null;
  module_status?: ModuleStatus[] | null;
  results?: Record<string, unknown> | null;
  error?: string | null;
}

export type WatchlistStatus = 'candidate' | 'verified' | 'rejected' | 'watching';

export interface WatchlistEntry {
  feature_name: string;
  task_id: string;
  status: WatchlistStatus;
  note: string;
  ic_snapshot: number | null;
  icir_snapshot: number | null;
  turnover_snapshot?: number | null;
  added_at: string;
  updated_at: string;
}

export interface WatchlistExportPayload {
  version: '1.0';
  exported_at: string;
  entries: WatchlistEntry[];
}

export interface SkippedResult {
  module_name: string;
  reason: string;
  error_type: string;
  retryable?: boolean;
  timestamp?: string;
}

export type FactorReturnData = Record<string, {
  quantile_returns_summary?: Record<string, number>;
  long_short_mean_return?: number;
  risk_metrics?: Record<string, number>;
  cumulative_returns_sampled?: Record<string, number[]>;
  ls_cumulative_sampled?: number[];
  num_quantiles_used?: number;
  skipped?: boolean;
  reason?: string;
}>;

export interface FactorCentralityData {
  pca_summary?: {
    explained_variance_ratio?: number[];
    total_variance_explained?: number;
    effective_rank?: number;
    n_components_used?: number;
    crowded_threshold?: number;
  };
  features?: Record<string, {
    centrality?: number;
    crowded?: boolean;
    risk_level?: string;
    percentile_rank?: number;
    trend?: string;
  }>;
  crowded_features?: string[];
  independent_features?: string[];
}

export interface TrendResult {
  slope?: number;
  p_value?: number;
  r_squared?: number;
  tail_estimate?: number;
  trend?: 'up' | 'down' | 'flat' | 'indeterminate' | string;
  interpretation?: string;
}

export type TrendAnalysisData = Record<string, {
  ic_trend?: TrendResult;
  centrality_trend?: TrendResult;
  factor_return_trend?: TrendResult;
  ls_spread_trend?: TrendResult;
  combined_signal?: {
    recommendation?: string;
    reason?: string;
    action?: string;
  };
}>;

export interface ParameterSensitivityFamily {
  variants?: string[];
  param_axis?: string;
  sensitivity_table?: Array<{
    variant: string;
    param_value: string | number;
    ic_mean: number;
    icir: number;
  }>;
  stability_metrics?: {
    ic_std_across_params?: number;
    icir_std_across_params?: number;
    overfitting_risk?: 'low' | 'medium' | 'high' | string;
    best_param?: string | number;
  };
}

export interface ParameterSensitivityData {
  families?: Record<string, ParameterSensitivityFamily>;
  summary?: {
    total_families?: number;
    high_risk_count?: number;
    robust_count?: number;
  };
  high_risk_families?: string[];
  robust_families?: string[];
}

export interface RollingOOSFeatureResult {
  oos_stability?: {
    mean_oos_ic?: number;
    std_oos_ic?: number;
    oos_hit_rate?: number;
    mean_is_oos_gap?: number;
    oos_icir?: number;
    degradation_ratio?: number;
  };
  assessment?: 'robust' | 'moderate' | 'overfitting' | string;
  splits_sampled?: Array<{
    split_id: number;
    is_ic: number;
    oos_ic: number;
  }>;
  skipped?: boolean;
  reason?: string;
}

export interface RollingOOSData {
  config?: {
    train_window?: number;
    test_window?: number;
    step?: number;
    n_splits?: number;
  };
  features?: Record<string, RollingOOSFeatureResult>;
  summary?: {
    total_validated?: number;
    robust_count?: number;
    moderate_count?: number;
    overfitting_count?: number;
  };
}

export type LongShortFeatureResult = {
  long_analysis?: {
    mean_return?: number;
    ic?: number;
    hit_rate?: number;
    sharpe?: number;
    side?: string;
    samples?: number;
  };
  short_analysis?: {
    mean_return?: number;
    ic?: number;
    hit_rate?: number;
    sharpe?: number;
    side?: string;
    samples?: number;
  };
  asymmetry?: {
    type?: string;
    long_contribution?: number;
    short_contribution?: number;
    ratio?: number;
  };
  recommendation?: string;
  num_quantiles_used?: number;
  skipped?: boolean;
  reason?: string;
};

export type LongShortAnalysisData = Record<string, LongShortFeatureResult>;

export interface FactorOrthogonalizationData {
  orthogonalization_matrix?: number[][];
  feature_names?: string[];
  residual_variance_ratio?: Record<string, number>;
}

export interface FactorExposureData {
  portfolio_exposure?: Record<string, number>;
  neutralized_portfolio_exposure?: Record<string, number>;
  neutralization_mode?: 'none' | 'beta_neutral' | 'vol_neutral' | string;
  neutralization_lookback?: number;
  neutralization_delta_hhi?: number | null;
  factor_attribution?: {
    factor_betas?: Record<string, number>;
    alpha?: number;
    r_squared?: number;
    attribution?: Record<string, number>;
    unexplained?: number;
  };
  concentration?: {
    max_exposure_factor?: string | null;
    max_exposure_value?: number;
    hhi?: number;
    concentrated?: boolean;
    warnings?: string[];
  };
  neutralized_concentration?: {
    max_exposure_factor?: string | null;
    max_exposure_value?: number;
    hhi?: number;
    concentrated?: boolean;
    warnings?: string[];
  };
}

export interface FeatureQualityDiagnosticsData {
  adf_results?: Record<string, {
    adf_statistic?: number;
    p_value?: number;
    is_stationary?: boolean;
    skipped?: boolean;
    reason?: string;
  }>;
  autocorrelation_results?: Record<string, {
    ljungbox_stat?: number;
    p_value?: number;
    significant_autocorrelation?: boolean;
    effective_sample_ratio?: number;
    skipped?: boolean;
    reason?: string;
  }>;
  drift_results?: Record<string, {
    cusum_breakpoint?: string | null;
    psi_score?: number;
    drifted?: boolean;
    skipped?: boolean;
    reason?: string;
  }>;
  coverage_stats?: Record<string, {
    coverage?: number;
    nan_count?: number;
    total?: number;
  }>;
  redundancy_scan?: {
    high_correlation_pairs?: [string, string, number][];
    threshold?: number;
    method?: string;
    skipped?: boolean;
  };
  quality_flags?: {
    non_stationary?: string[];
    high_autocorrelation?: string[];
    low_coverage?: string[];
    drifted?: string[];
  };
  summary?: {
    total_features?: number;
    stationary_rate?: number;
    mean_coverage?: number;
    low_quality_count?: number;
  };
}

export interface NetICAnalysisData {
  skipped?: boolean;
  reason?: string;
  features?: Record<string, {
    gross_ic?: number;
    net_ic?: number;
    turnover?: number;
    cost_bps?: number;
    profitable_after_cost?: boolean;
    breakeven_cost_bps?: number;
    cost_sensitivity?: Array<{ cost_bps: number; net_ic: number }>;
    capacity?: {
      estimated_capacity_usd?: number;
      capacity_tier?: string;
    };
    skipped?: boolean;
    reason?: string;
  }>;
  summary?: {
    total_analyzed?: number;
    profitable_count?: number;
    avg_ic_loss_pct?: number;
    rank_correlation_gross_vs_net?: number;
  };
}

export interface FeatureBrowserCatalogItem {
  name: string;
  category: string;
  source: string;
  layer: string;
  family: string;
  params: Record<string, unknown>;
  coverage: number;
  mean: number | null;
  std: number | null;
  nan_pct: number;
}

export interface FeatureBrowserCatalogSummary {
  total_features: number;
  total_categories: number;
  avg_coverage: number;
  stationary_ratio: number;
  low_quality_count: number;
  redundant_pairs: number;
}

export interface FeatureBrowserCatalogResponse {
  items: FeatureBrowserCatalogItem[];
  summary: FeatureBrowserCatalogSummary;
}

export interface FeatureBrowserHistogramBin {
  left: number;
  right: number;
  count: number;
  density: number;
}

export interface FeatureBrowserDistributionStatistics {
  mean: number | null;
  std: number | null;
  skew: number | null;
  kurtosis: number | null;
  min: number | null;
  max: number | null;
  median: number | null;
  q25: number | null;
  q75: number | null;
  nan_pct: number;
  unique_count: number;
  zero_count: number;
  jb_stat: number | null;
  jb_pvalue: number | null;
}

export interface FeatureBrowserDistributionResponse {
  feature_name: string;
  bins: number;
  histogram: FeatureBrowserHistogramBin[];
  kde_x: number[];
  kde_y: number[];
  statistics: FeatureBrowserDistributionStatistics;
}

export interface FeatureBrowserTimeSeriesPoint {
  timestamp: string | null;
  values: Record<string, number | null>;
}

export interface FeatureBrowserACFItem {
  lag: number;
  value: number;
}

export interface FeatureBrowserFrequencyItem {
  frequency: number;
  amplitude: number;
}

export interface FeatureBrowserTimeSeriesResponse {
  features: string[];
  sample_rate: number;
  points: FeatureBrowserTimeSeriesPoint[];
  acf: Record<string, FeatureBrowserACFItem[]>;
  periodicity: Record<string, FeatureBrowserFrequencyItem[]>;
}

export interface FeatureBrowserCorrelationResponse {
  method: 'pearson' | 'spearman' | 'kendall';
  features: string[];
  matrix: number[][];
  mode: string;
}

export interface FeatureBrowserQualityItem {
  feature: string;
  adf_pvalue: number | null;
  is_stationary: boolean;
  coverage: number;
  nan_pct: number;
}

export interface FeatureBrowserQualityResponse {
  results: FeatureBrowserQualityItem[];
}

export interface FeatureBrowserDataTableResponse {
  total_rows: number;
  page: number;
  page_size: number;
  columns: string[];
  rows: Record<string, unknown>[];
}

export interface FeatureOverviewItem {
  feature_name: string;
  data_type: string;
  mean: number | null;
  std: number | null;
  min: number | null;
  max: number | null;
  nan_pct: number;
}

export interface FeatureOverview {
  total_rows: number;
  total_features: number;
  numeric_features: number;
  mean_nan_pct: number;
  items: FeatureOverviewItem[];
}

export interface ICDashboardEntry {
  feature_name: string;
  ic_mean: number;
  ic_std: number;
  ir: number;
  t_stat: number;
  significance: string;
  sparkline: number[];
}

export interface ICDashboardResult {
  available: boolean;
  message: string | null;
  entries: ICDashboardEntry[];
}

export interface RollingICPoint {
  timestamp: string;
  ic: number;
  ir: number | null;
}

export interface RollingIC {
  feature_name: string;
  window: number;
  points: RollingICPoint[];
}

export interface FeatureQualityScore {
  feature_name: string;
  stationarity_score: number;
  coverage_score: number;
  drift_score: number;
  redundancy_score: number;
  total_score: number;
  grade: string;
}

export interface CorrelationMatrix {
  method?: 'pearson' | 'spearman' | 'kendall';
  features: string[];
  matrix: number[][];
  truncated?: boolean;
  original_feature_count?: number;
}

export interface DriftMonitorEntry {
  feature_name: string;
  psi: number;
  ks_stat: number;
  ks_pvalue: number;
  status: 'stable' | 'warning' | 'severe';
}

export interface SHAPSummary {
  available: boolean;
  message: string | null;
  items: Array<{
    feature_name: string;
    mean_abs_shap: number;
    mean_shap: number;
  }>;
}

export interface ImportanceComparison {
  items: Array<{
    feature_name: string;
    lightgbm_importance: number;
    xgboost_importance: number;
  }>;
}

export interface CoverageMatrixRequestPayload {
  symbols: string[];
  timeframe: string;
  feature_names: string[];
  feature_base_path?: string;
  timeout_seconds?: number;
}

export interface CoverageMatrixResponsePayload {
  matrix: Record<string, Record<string, number | null>>;
  valid_counts: Record<string, Record<string, number>>;
  row_counts: Record<string, number>;
  symbols: string[];
  features: string[];
  summary: {
    avg_coverage: number;
    worst_symbol: string | null;
    worst_feature: string | null;
  };
}

export type FeatureBrowserTab =
  | 'overview'
  | 'ic_dashboard'
  | 'quality'
  | 'correlation'
  | 'drift'
  | 'attribution'
  | 'coverage';
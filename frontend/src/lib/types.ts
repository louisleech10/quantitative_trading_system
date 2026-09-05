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

  // ===== GAP-3 UX Task 1.3：來源 canonical bytes（一律由後端計算；前端不得自算）=====
  /** 本結果集之來源 canonical 文字（後端 §G S-9 exact bytes 之 UTF-8 解碼，無尾端 newline）。 */
  source_file_text?: string;
  /** `sha256(source_file_text)`＝契約 `source_file_digest`；與 `rule_digest` 為兩件事。 */
  source_file_digest?: string;

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

export interface FailOpenGateFlags {
  allow_partial_layers?: boolean;
  allow_partial_timeframes?: boolean;
  allow_partial_ic?: boolean;
  allow_partial_training?: boolean;
  max_inf_ratio?: number;
  max_nan_ratio?: number | null;
}

export interface FeatureFactoryConfig {
  allow_partial_layers?: boolean;
  allow_partial_timeframes?: boolean;
  allow_partial_ic?: boolean;
  allow_partial_training?: boolean;
  max_inf_ratio?: number;
  max_nan_ratio?: number | null;
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
  start_date?: string;
  end_date?: string;
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

/** GET /batch/list 單筆可恢復批次摘要 */
export interface RecoverableBatchSummary {
  batch_id: string;
  symbols: string[];
  timeframe: string;
  completed_count: number;
  updated_at: string;
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
  current_stage?: string | null;
  stage_progress?: number | null;
  process_rss_mb?: number | null;
  worker_rss_mb?: number | null;
  current_rss_mb?: number | null;
  schema_version?: number;
  queued?: number;
  concurrent_symbols?: number;
  memory_sanity_failed?: boolean;
  eta_seconds?: number;
  resume_available?: boolean;
  output_paths?: BatchOutputPath[];
  per_item_rss?: BatchItemRss[];
  last_item_metrics?: BatchItemMetrics | null;
  results?: Record<string, string>;
  browse_task_ids?: Record<string, string>;
  errors?: Record<string, string>;
  retention_pending?: BatchRetentionItem[];
  warmup_insufficient_items?: BatchWarmupInsufficientItem[];
}

export interface BatchRetentionItem {
  symbol: string;
  timeframe: string;
  config_hash: string;
  state: string;
  hdf5_path?: string | null;
  error?: string | null;
}

export interface BatchRetentionDecisionRequest {
  decision: 'retain' | 'discard';
}

export interface BatchRetentionDecisionResponse {
  batch_id: string;
  symbol: string;
  timeframe: string;
  config_hash: string;
  state: string;
  hdf5_path?: string | null;
  error?: string | null;
}

export interface BatchRetentionPendingResponse {
  batch_id: string;
  pending: BatchRetentionItem[];
}

export interface BatchRetentionRunRef {
  symbol: string;
  timeframe: string;
  config_hash: string;
}

export interface BatchRetentionBulkRequest {
  decision: 'retain' | 'discard';
  runs: BatchRetentionRunRef[];
}

export interface BatchRetentionBulkResultItem {
  symbol: string;
  timeframe: string;
  config_hash: string;
  status: 'succeeded' | 'failed' | 'skipped';
  state: string;
  error?: string | null;
  code?: string | null;
}

export interface BatchRetentionBulkResponse {
  results: BatchRetentionBulkResultItem[];
}

export interface WarmupInsufficient {
  needed: number;
  available: number;
  affected_bars: number;
}

export interface BatchWarmupInsufficientItem {
  symbol: string;
  timeframe: string;
  warmup_insufficient: WarmupInsufficient;
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
  process_rss_mb?: number | null;
  worker_rss_mb?: number | null;
  current_rss_mb?: number | null;
  schema_version?: number;
  compute_warnings?: string[];
  validation_summary?: FeatureValidationSummary;
  retention_prompt?: boolean;
  run_identity?: RunIdentity;
  warmup_insufficient?: WarmupInsufficient | null;
  result?: Record<string, unknown>;
}

export interface RunIdentity { symbol: string; timeframe: string; config_hash: string; }

/** completionQueue 項目來源：單 symbol modal vs batch 面板 */
export type CompletionSource = 'single' | 'batch';

export interface CompletionQueueItem extends RunIdentity {
  source: CompletionSource;
}
export interface RunInfo extends RunIdentity {
  alias?: string | null;
  batch_id?: string | null;
  batch_alias?: string | null;
  training_timeframes?: string[] | null;
  created_at?: string | null;
  last_generated_at?: string | null;
  size_bytes?: number | null;
  active: boolean;
  browse_task_id: string;
  browse_ready: boolean;
  browse_path?: string | null;
  feature_count?: number | null;
  row_count?: number | null;
  quality_status?: string | null;
  /**
   * GAP-3 UX Task 7.7 ①：feature run 之時間範圍，形狀與後端 manifest **同形**。
   *
   * 🔴 值為**字串**（實測現存 manifest 皆為 epoch **秒之數字字串**，例 `"1704067200"`），
   *    **不是** epoch 毫秒整數——前端不得自行轉型別或比較大小，
   *    涵蓋判定一律由後端 `check_feature_run_coverage()` 做。
   * 🔴 舊 run 可能是 `{start: null, end: null}` 或整個鍵不存在（實掃 14 份 manifest 有 2 份缺鍵）；
   *    兩者後端都判 `feature_coverage_unknown_legacy_run` 而 fail-closed。
   */
  time_range?: { start: string | null; end: string | null } | null;
}
export interface EnsureBrowseResponse extends RunIdentity {
  browse_task_id: string;
  browse_ready: boolean;
}
export interface DeleteRunResponse extends RunIdentity {
  features_deleted: boolean; cgsa_deleted: boolean; registry_removed: boolean;
  skipped: string[]; errors: string[]; total_bytes: number;
}

/** B4 bulk-delete 單筆目標 */
export type BulkDeleteRunItem = RunIdentity;

/** B4 bulk-delete 單筆結果 */
export interface BulkDeleteRunOutcome extends RunIdentity {
  bytes: number;
  error?: string | null;
}

/** B4 bulk-delete 彙整報告（HTTP 200 + per-run status） */
export interface BulkDeleteResponse {
  deleted: BulkDeleteRunOutcome[];
  failed: BulkDeleteRunOutcome[];
  skipped: BulkDeleteRunOutcome[];
}

/** B4 孤兒掃描條目 */
export interface OrphanEntry {
  kind: string;
  symbol: string;
  timeframe: string;
  config_hash: string;
  leaf_kind?: string | null;
}

/** B4 孤兒掃描報告 */
export interface OrphanScanResponse {
  orphans: OrphanEntry[];
  count: number;
}

/** B4 孤兒清理報告 */
export interface OrphanCleanResponse {
  orphans: OrphanEntry[];
  cleaned_registry: number;
  cleaned_leaves: number;
  errors: string[];
  dry_run: boolean;
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
  process_rss_mb?: number | null;
  worker_rss_mb?: number | null;
  current_rss_mb?: number | null;
  schema_version?: number;
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
    nan_ratio_quantiles?: {
      min: number;
      q1: number;
      median: number;
      q3: number;
      max: number;
    };
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
  stats_warmup?: {
    computed: number;
    total: number;
    pct: number;
    complete: boolean;
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

export interface DataQualityGroupStat {
  layer: string;
  tf: string;
  feature_count: number;
  mean_nan_ratio: number;
  warmup_only: number;
  real_problem: number;
}

export interface DataQualityRealProblemFeature {
  name: string;
  nan_ratio: number;
  hole_count: number;
  kind: 'all_nan' | 'high_nan_hole';
}

export interface NanRatioQuantiles {
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
}

export interface DataQualityReport {
  schema_version?: string;
  nan_ratio_mean?: number;
  nan_ratio_max?: number;
  nan_ratio_quantiles?: NanRatioQuantiles;
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
  real_problem_features?: DataQualityRealProblemFeature[];
  counts: {
    mid_holes: number;
    trailing_nans: number;
    high_nan: number;
    warmup_only_high_nan?: number;
    real_problem?: number;
  };
  group_breakdown?: DataQualityGroupStat[];
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
  config_hash?: string;
  cross_sectional_runs?: { symbol: string; config_hash: string }[];
  labels_path?: string;
  meta_path?: string;
  mode: 'global' | 'event' | 'cross_sectional';
  cross_sectional_symbols?: string[];
  event_query?: string;
  /**
   * legacy 事件路徑之時間戳。
   * 🔴 **選了 `event_import_id` 時不得同時送**（後端定死互斥 ⇒ 422，兩個真相源）。
   * 🔴 Task 7.7 ⑦ 起，選批**不再**寫入本欄——映射由後端依 receipt 之 `decision_at_ms` 產生。
   */
  event_timestamps?: number[];
  /** GAP-3 B5.2：從已匯入事件批（/case/events）選事件。Task 7.0b ③ 起**直接送到後端**。 */
  event_import_id?: string;
  /**
   * GAP-3 UX Task 7.0b ③：分析參數，**只作用於本次分析、不回寫事件批**。
   *
   * 🔴 `horizon_bars` 之缺省為**字面常數 `1`**——**禁**以匯出檔／已落檔批之
   * `label_definition.window.horizon_bars` 種子化：該欄語意為 D-7 深度宣告，
   * 分析層禁止讀成答案窗（既有批之殘值為 `3`，種子化＝靜默給錯預設答案窗）。
   * 其餘三鍵之初始值由**後端**取該批 F-0 種子，前端不猜。
   */
  event_label_spec?: {
    horizon_bars: number;
    entry_price_semantic?: string;
    label_return_mode?: string;
    decision_offset_bars?: number;
  };
  /**
   * `G3-D2` D4.3：k／h 掃描網格之上界（裁定③「填 m 就掃 0～m」，h 自 1 起）。
   *
   * 🔴 **請求頂層 sibling，不在 `event_label_spec` 內**——後者恆四鍵，
   * 多一鍵後端 normalizer 直接 fail-closed。
   * 未掃描 ⇒ 整個鍵**省略**（送空物件在後端仍代表「有掃描」）。
   */
  event_label_scan?: ICEventLabelScan;
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
  /** HAC raw p；舊 report / 不可用時可為 null（CODEX-6） */
  p_value?: number | null;
  /** BH FDR q（p_value_adj）；舊 report 可缺欄 */
  p_value_adj?: number | null;
  ic_hit_rate?: number;
  /** HAC t-stat；禁前端 i.i.d. 推導 */
  t_stat?: number | null;
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
  /** S2/RULING-5: warmup [0, first_valid) 為 null；長度=源 raw n */
  quantile_turnovers: (number | null)[];
  rank_change_rates: (number | null)[];
  timestamps: Array<number | string>;
}

export interface TurnoverFeatureData {
  quantile_turnover?: number;
  rank_change_rate?: number;
  autocorrelation?: number;
  time_series?: TurnoverTimeSeriesData;
}

// ===== ICHC 契約對應段（SoT＝momentum/Analysis/contracts/ic_report_contract.json；Task 5.2 機檢三方一致，勿在此自行增刪值）=====
export type CapabilityStatus =
  | 'ok'
  | 'not_applicable'
  | 'not_computed'
  | 'computation_failed'
  | 'disabled'
  | 'unavailable';

export interface SectionStatusObject {
  status: CapabilityStatus;
  reason?: string;
}

/** ICHC type guard：節是 status 物件（不適用/停用…）而非 feature 資料 map */
export function isSectionStatus(value: unknown): value is SectionStatusObject {
  return (
    typeof value === 'object' &&
    value !== null &&
    'status' in value &&
    typeof (value as { status: unknown }).status === 'string'
  );
}
// ===== ICHC 契約對應段結束 =====

export interface QuantileReturnData {
  quantile_mean_returns: Record<string, number>;
  long_short_spread?: number;
  long_short_tstat?: number;
  monotonicity_score?: number;
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

// ===== GAP-2 邊際 IC／倖存者輸出（SoT＝momentum/Analysis/contracts/ic_survivor_contract.json；此處為前端型別鏡像，欄名以契約為準；ICHC 契約段外）=====
export interface MarginalICPerFeature {
  status: CapabilityStatus;
  reason: string | null;
  conditioning_set: string[];
  marginal_ic: number | null;
  gross_ic: number | null;
  ic_retained_ratio: number | null;
  marginal_ic_train_insample: number | null;
  ci95: [number, number] | null;
  condition_number: number | null;
  r2_train: number | null;
  n_used_train: number;
  n_used_test: number;
}

export interface MarginalICSequentialEntry extends MarginalICPerFeature {
  feature: string;
  step: number;
}

export interface MarginalICComposite {
  status: CapabilityStatus;
  reason: string | null;
  method?: 'equal' | 'ic_weighted';
  weights?: Record<string, number>;
  signs?: Record<string, number>;
  excluded?: Record<string, string>;
  composite_ic?: number | null;
  composite_ic_train_insample?: number | null;
  top_train_single?: string | null;
  top_train_single_test_ic?: number | null;
  best_single_test_ic?: number | null;
  best_single_feature?: string | null;
  delta_vs_top_train_single?: number | null;
  delta_ci95?: [number, number] | null;
  n_used_test?: number;
  n_used_train?: number;
  fit_scope?: 'train' | 'full_sample' | null;
  oos_guarantees?: boolean | null;
}

export interface MarginalICSection {
  status: CapabilityStatus;
  reason: string | null;
  fit_scope: 'train' | 'full_sample' | null;
  oos_guarantees: boolean | null;
  pass_class: 'oos' | 'full_sample_research_only' | null;
  statistic: string;
  projection_space: string;
  /** D3′：恆 false（契約 independent_oos_validation_allowed=[false]） */
  independent_oos_validation: boolean;
  selection_sample: string;
  oos_semantics: string;
  algorithm_version: string;
  views: Record<string, SectionStatusObject>;
  per_feature: Record<string, MarginalICPerFeature>;
  sequential: MarginalICSequentialEntry[];
  removed_candidates: Record<string, MarginalICPerFeature>;
  train_ic: Record<string, number | null>;
  n_train: number | null;
  n_test: number | null;
  n_regressions: number;
  budget: Record<string, number>;
  composite?: MarginalICComposite;
}

/** 報告 metadata.survivor_output 五鍵（契約 survivor_output_status_keys） */
export interface SurvivorOutputMeta {
  status: CapabilityStatus;
  reason: string | null;
  path: string | null;
  sha256: string | null;
  case_id: string;
}

/** type guard：完整邊際 IC 節（含 per_feature）而非純 status 物件 */
export function isMarginalICSection(value: unknown): value is MarginalICSection {
  return (
    isSectionStatus(value) &&
    typeof (value as { per_feature?: unknown }).per_feature === 'object' &&
    (value as { per_feature?: unknown }).per_feature !== null
  );
}
// ===== GAP-2 段結束 =====

export interface ICReport {
  version?: string;
  /** LA-1 B3：ok_oos | degraded_full_sample（optional 相容舊 artifact；禁 |string 塌 union） */
  analysis_status?: 'ok_oos' | 'degraded_full_sample';
  /** LA-1 B3：root 鏡像 OOS 保證（optional 相容舊 artifact） */
  oos_guarantees?: boolean;
  metadata?: Record<string, unknown> & { survivor_output?: SurvivorOutputMeta };
  filter_log?: FilterLogData;
  summary_table?: ICFeatureInfo[];
  /** GAP-2 Task 5.1：邊際 IC／多因子組合節（status object 或完整節；舊報告缺席） */
  marginal_ic?: MarginalICSection | SectionStatusObject;
  /** ICHC Task 3.2：五節 union——SectionStatusObject（xsec 不適用）或 legacy 資料形 */
  ic_decay?: SectionStatusObject | Record<string, ICDecayData>;
  quantile_returns?: SectionStatusObject | Record<string, QuantileReturnData>;
  correlation_matrix?: CorrelationMatrix;
  grouped_ic?: SectionStatusObject | GroupedICData;
  rolling_ic_series?: Record<string, RollingICSeries>;
  turnover_analysis?: SectionStatusObject | Record<string, TurnoverFeatureData>;
  /** coverage 目前無 UI consumer（wiring allowlist 具名孤兒欄）；型別先入契約 */
  coverage_analysis?: SectionStatusObject | Record<string, unknown>;
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

/** Deep analysis 成本參數(與 API NetICAnalysisRequest 同構)。 */
export interface NetICAnalysisRequest {
  cost_enabled: boolean;
  cost_bps?: number | null;
}

export interface DeepAnalysisConfig {
  selected_features?: string[];
  top_n?: number;
  modules: DeepAnalysisModules;
  config_override?: Record<string, unknown>;
  /** request 欄名 net_ic;config/模組鍵 net_ic_analysis — 不得混用。 */
  net_ic?: NetICAnalysisRequest;
}

/** deep module_summary 合法 scalar 狀態（D-4 completed_partial；closed union，禁 `| string` 逃生） */
export type ModuleSummaryStatus =
  | 'completed'
  | 'completed_partial'
  | 'skipped'
  | 'unavailable'
  | 'not_run';

export interface ModuleStatus {
  module_name: string;
  status: ModuleSummaryStatus;
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

/**
 * IC1C-FR-FULL §U: results.factor_returns = discriminated union。
 * ok → value 含 metadata + features(非裸 feature map); unavailable → value=null + reason。
 * legacy 裸 map 僅 runtime 可能殘留,型別不收納為合法形狀。
 */
/** 單特徵 payload(ok union value.features 葉)。 */
export type FactorReturnFeaturePayload = {
  long_short_mean_return?: number;
  ls_cumulative_sampled?: number[];
  risk_metrics?: {
    sharpe_ratio?: number;
    [key: string]: number | undefined;
  };
  active_bar_count?: number;
  turnover?: number | number[];
  quantile_summary?: Record<string, unknown>;
  num_quantiles_used?: number;
  /** legacy 欄位保留型別可讀性;ok 路徑不依賴 */
  quantile_returns_summary?: Record<string, number>;
  cumulative_returns_sampled?: Record<string, number[]>;
  skipped?: boolean;
  reason?: string;
};

/** @deprecated 僅供 runtime legacy 辨識;ok 路徑不用此形狀 */
export type FactorReturnLegacyFeaturePayload = FactorReturnFeaturePayload;

/** @deprecated 裸 feature map(無 status);sanitizer 擋,前端不繪 */
export type FactorReturnLegacyMap = Record<string, FactorReturnFeaturePayload>;

/** §U ok value: metadata 與 features 分層(SPEC §U / F3.1)。literal 鎖死,禁 `| string` 放寬。 */
export type FactorReturnDataOkValue = {
  schema_version: 'fr_full_v1';
  semantics: 'single_asset_factor_timing_ls';
  quantile_fit: 'pit_expanding';
  return_transform: 'identity';
  turnover_semantics?: string;
  warmup_periods?: number;
  features: Record<string, FactorReturnFeaturePayload>;
};

export type FactorReturnDataOk = {
  status: 'ok';
  value: FactorReturnDataOkValue;
  reason: null;
};

export type FactorReturnDataUnavailable = {
  status: 'unavailable';
  value: null;
  reason: string;
};

/** ICReport.factor_returns / API 節 = §U union(非只新增旁路型別)。 */
export type FactorReturnData = FactorReturnDataOk | FactorReturnDataUnavailable;

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

/**
 * B3/B5 幽靈契約：factor_attribution 三態 discriminated union。
 * - unavailable：§U 三鍵（未接真 OLS）
 * - ok：B1+ 新形（必有 status:'ok' + intercept + 非 null 數值）
 * - legacy：真 p0 舊 stub 形（無 status、數值可 null、無 intercept）
 * 反例 `{factor_betas:{x:1}}` 不得被當成 unavailable（須靠 status 判別）。
 */
export type FactorAttributionUnavailable = {
  status: 'unavailable';
  value: null;
  reason: string;
  /** 禁幽靈數值欄與 unavailable 共存 */
  factor_betas?: never;
  alpha?: never;
  r_squared?: never;
  intercept?: never;
  unexplained?: never;
  attribution?: never;
};

/** B1+ 接真 OLS 形：status 必為 'ok'，數值非 null，含 intercept */
export type FactorAttributionOk = {
  status: 'ok';
  alpha: number;
  r_squared: number;
  intercept: number;
  unexplained: number;
  factor_betas: Record<string, number>;
  attribution: Record<string, number>;
  value?: never;
  reason?: never;
};

/**
 * 真實 p0 legacy 舊 stub 形（handoffs/ic1d_baseline/p0_before.json）：
 * 無 status、無 intercept、alpha/r_squared/unexplained 可 null、可有 factor_betas。
 * 使 typed consumer 消費真 p0 legacy 不需 unsafe cast。
 */
export type FactorAttributionLegacy = {
  /** 無 status 欄；禁止寫入 status 以免與 ok/unavailable 混淆 */
  status?: never;
  alpha: number | null;
  r_squared: number | null;
  unexplained: number | null;
  /** intercept 為 B1 才加，legacy 可缺 */
  intercept?: number;
  factor_betas?: Record<string, number>;
  attribution?: Record<string, number>;
  value?: never;
  reason?: never;
};

/** FactorExposureData.factor_attribution = unavailable | ok | legacy */
export type FactorAttributionData =
  | FactorAttributionUnavailable
  | FactorAttributionOk
  | FactorAttributionLegacy;

export interface FactorExposureData {
  portfolio_exposure?: Record<string, number>;
  neutralized_portfolio_exposure?: Record<string, number>;
  neutralization_mode?: 'none' | 'beta_neutral' | 'vol_neutral' | string;
  neutralization_lookback?: number;
  neutralization_delta_hhi?: number | null;
  factor_attribution?: FactorAttributionData;
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

/**
 * §U conditional metric — 真 discriminated union(同構 API)。
 * ok → value 有值 + reason=null; unavailable → value=null + reason 非空。
 * 禁止 status:'ok'+value:null 或 status:'unavailable'+reason:null 等非法形狀。
 */
export type ConditionalMetricOk = {
  status: 'ok';
  value: number | boolean;
  reason: null;
};

export type ConditionalMetricUnavailable = {
  status: 'unavailable';
  value: null;
  reason: string;
};

export type ConditionalMetricUnion =
  | ConditionalMetricOk
  | ConditionalMetricUnavailable;

/** capacity 子鍵集合(SPEC v1.1 精確鍵,多/少=FAIL)。 */
export type NetICCapacity = {
  estimated_capacity_usd: number | null;
  capacity_tier: string;
  /** 恒 "uncalibrated"(未建 canonical capacity 校準前) */
  calibration: 'uncalibrated';
};

/** SCHEMA_SKIPPED 精確鍵={skipped, reason};排除全部非 skipped 鍵。 */
export type NetICFeatureSkipped = {
  skipped: true;
  reason: string;
  gross_ic?: never;
  turnover?: never;
  turnover_semantics?: never;
  capacity?: never;
  net_factor_return?: never;
  cost_bps?: never;
  cost_semantics?: never;
  cost_drag_return?: never;
  cost_sensitivity?: never;
  breakeven_cost_bps?: never;
  profitable_after_cost?: never;
};

/** GROSS_ONLY 共用欄(無 cost / 無 skipped)。 */
type NetICFeatureGrossCore = {
  gross_ic: number;
  turnover: number;
  turnover_semantics: string;
  capacity: NetICCapacity;
  net_factor_return: ConditionalMetricUnion;
};

/** SCHEMA_GROSS_ONLY 精確鍵集合;cost_* / skipped 以 never 排除混合 profile。 */
export type NetICFeatureGrossOnly = NetICFeatureGrossCore & {
  cost_bps?: never;
  cost_semantics?: never;
  cost_drag_return?: never;
  cost_sensitivity?: never;
  breakeven_cost_bps?: never;
  profitable_after_cost?: never;
  skipped?: never;
  reason?: never;
};

/** SCHEMA_COST_ENABLED = GROSS core ∪ 全部 cost 鍵;排除 skipped 鍵。 */
export type NetICFeatureCostEnabled = NetICFeatureGrossCore & {
  cost_bps: number;
  cost_semantics: string;
  cost_drag_return: number;
  cost_sensitivity: Array<{ cost_bps: number; cost_drag_return: number }>;
  breakeven_cost_bps: ConditionalMetricUnion;
  profitable_after_cost: ConditionalMetricUnion;
  skipped?: never;
  reason?: never;
};

/** 三 profile 精確型別 union(非全 optional 單 interface;非 subtype 互滲)。 */
export type NetICFeatureResult =
  | NetICFeatureSkipped
  | NetICFeatureGrossOnly
  | NetICFeatureCostEnabled;

/** 頂層:模組 SKIPPED 或完整 features+summary。 */
export type NetICAnalysisSkipped = {
  skipped: true;
  reason: string;
  features?: never;
  summary?: never;
};

export type NetICAnalysisOk = {
  skipped?: never;
  features: Record<string, NetICFeatureResult>;
  summary: {
    total_analyzed: number;
    evaluable_count: number;
    profitable_count: number;
    /** cost_enabled 時存在;GROSS_ONLY 可省略 */
    avg_cost_drag_return?: number;
  };
};

export type NetICAnalysisData = NetICAnalysisSkipped | NetICAnalysisOk;

export interface CorrelationMatrix {
  method?: 'pearson' | 'spearman' | 'kendall';
  features: string[];
  matrix: number[][];
  truncated?: boolean;
  original_feature_count?: number;
}

export interface GroupCoverageResponsePayload {
  groups: string[];
  symbols: string[];
  matrix: Record<string, Record<string, number | null>>;
  divergence: Record<string, number>;
  summary: {
    avg_coverage: number;
    worst_symbol: string | null;
    worst_group: string | null;
    missing_symbols: string[];
  };
}

export interface GroupFeatureCoverageResponsePayload {
  group_name: string;
  features: string[];
  symbols: string[];
  matrix: Record<string, Record<string, number | null>>;
  divergence: Record<string, number>;
  row_counts: Record<string, number>;
}

// ============================================================
// GAP-3 事件型（B5.2）：匯入批與兩張表（欄位字面以後端契約為準，前端不重算統計）
// ============================================================
export interface EventImportSummary {
  import_id: string;
  source_name: string | null;
  upload_sha256: string;
  imported_at: string;
  n_events: number;
  symbols: string[];
  timeframes: string[];
  direction: string | null;
  scenario: string | null;
}

export interface EventImportListResponse {
  total: number;
  imports: EventImportSummary[];
}

/**
 * GAP-3 UX Task 7.6：事件批 detail 之**批次事實欄**（封閉五鍵，SPEC R11 定死 wire shape）。
 *
 * 🔴 `t0`／`label` 為**逐列陣列**（按 `event_id` UTF-8 升冪），元素鍵集**互不含對方**；
 *    前端**不得**由此另算一份 t0 語意（只做摘要顯示，見 `eventFieldFormatters.ts`）。
 * 🔴 `control_kind` 為 `null` 有兩種意思（批內混值／該批無此欄）
 *    ⇒ 兩者之區分在 `batch_fact_notes.control_kind_values`，不要只看 `null`。
 */
export interface EventBatchFacts {
  scenario: string | null;
  control_kind: string | null;
  direction: string | null;
  /** 這批的答案是怎麼來的（provenance）。批內混值或舊批未宣告 ⇒ `null`（顯示「（未宣告）」）。 */
  label_origin: string | null;
  t0: { event_id: string; t0_ms: number }[];
  label: { event_id: string; label: number }[];
}

/**
 * 批次宣告種子（F-0）；分析參數區之初始值來源，**不計入**批次事實欄之鍵集。
 *
 * 🔴 `G3-D2` **D4.3**：`decision_offset_bars` **已移除**（裁定②）。k 是分析參數，
 * 同一批可以用不同 k 各分析一次 ⇒ 拿匯入檔的 k 當初始值等於讓宣告偷偷決定參數。
 * 批內**記錄**之 k 改由 `batch_fact_notes.decision_offset_bars_record_values` 揭露。
 */
export interface EventDeclarationSeeds {
  entry_price_semantic: string | null;
  label_return_mode: string | null;
}

export interface EventImportDetail {
  summary: EventImportSummary;
  records: Record<string, unknown>[];
  batch_facts: EventBatchFacts;
  declaration_seeds: EventDeclarationSeeds;
  batch_fact_notes: {
    control_kind_values: string[];
    /** `G3-D2` D4.3：批內**記錄**之 k distinct 值（升冪）；空＝該批無此欄（≠ `[0]`）。 */
    decision_offset_bars_record_values: number[];
  };
}

/** `G3-D2` D4.3：k／h 掃描網格之請求上界（請求**頂層 sibling**，不在 `event_label_spec` 內）。 */
export interface ICEventLabelScan {
  decision_offset_bars_max?: number;
  horizon_bars_max?: number;
}

/** 掃描網格單格之結果（行 k、列 h）。 */
export interface ICEventScanCell {
  k: number;
  h: number;
  capability: 'available' | 'unavailable';
  reason?: string | null;
  n_events: number;
  analysis_alignment_receipt_hash: string | null;
  ic_summary?: Record<string, unknown> | null;
}

/**
 * `G3-D2` D4.2／D4.3：**後端**回傳之事件分析揭露。
 *
 * 🔴 兩個上界為**幾何／coverage 上界**（`D-001` D4.2 誠實邊界）：
 *    超過 ⇒ 幾何上必失敗；**未超過不保證**零 failures。UI 文案不得寫成成功保證。
 */
export interface ICEventScanDisclosure {
  decision_offset_bars_capability?: string | null;
  decision_offset_bars_reason?: string | null;
  /** 批內**記錄**之 k distinct 值（事實）。 */
  decision_offset_bars_record_values?: number[] | null;
  /** **本次分析**採用之 k（參數）。與上一欄同名不同義。 */
  decision_offset_bars_analysis?: number | null;
  k_max_feasible_at_h?: number | null;
  h_max_feasible_at_k?: number | null;
  /** `bounded` ｜ `no_feasible_k` ｜ `no_feasible_h` ｜ `h_inert_for_mode`。 */
  k_bound_status?: string | null;
  h_bound_status?: string | null;
  /** 契約 `analysis_params.decision_offset_bars_scan_max`（建議上限；超過只警示不擋）。 */
  decision_offset_bars_scan_max?: number | null;
  /**
   * 🔴 `CODEX-R1-P2-04`：兩上界是**對誰**算的。
   * `bounds_scope_symbol` ＝本次 IC 的 run symbol（`null` ⇒ 未指定、對全批算）；
   * `bounds_scope_excluded_events` ＝因 symbol 不符而未計入上界的事件筆數。
   */
  bounds_scope_symbol?: string | null;
  bounds_scope_excluded_events?: number | null;
  event_label_scan?: {
    scan_total: number;
    scan_done: number;
    scan_results: ICEventScanCell[];
    capability: 'available' | 'unavailable';
    reason?: string | null;
    message?: string | null;
  } | null;
}

export interface EventImportFailure {
  row: number | null;
  event_id: string | number | null;
  field: string | null;
  reason: string;
}

export interface EventImportResponse {
  accepted: boolean;
  import_id: string | null;
  n_rows: number;
  n_valid: number;
  failures: EventImportFailure[];
  warnings: string[];
  upload_sha256: string | null;
  source_digest_verified: boolean;
  contract_version: string | null;
  stored_path: string | null;
  /** GAP-3 UX Task 1.9／1.11／1.12：答案窗宣告 receipt（深度語意住 lookahead_bars_declared） */
  lookahead_declaration?: EventLookaheadDeclarationReceipt | null;
}

/** GAP-3 UX Task 1.9／1.12：落檔之答案窗宣告與 L3 狀態（後端算，前端只顯示）。 */
export interface EventLookaheadDeclarationReceipt {
  requires_declaration: boolean;
  referenced_columns: string[];
  default_window_bars: Record<string, number>;
  declared_window_bars: Record<string, number> | null;
  /** 逐 timeframe 的真實深度；🔴 深度語意看這個，不是 label_definition.window.horizon_bars */
  lookahead_bars_declared: Record<string, number> | null;
  acknowledged_unverifiable: boolean;
  embargo_ms_by_symbol: Record<string, number>;
  /** true ⇒ 該批禁進 train/test 切分與條件 IC，只能產事件研究表 */
  split_blocked: boolean;
}

/**
 * GAP-3 UX Task 1.5／1.6：CSV 欄名對映之送出內容。
 *
 * `columnMapping` ＝ `{契約欄名: CSV 欄名}`；🔴 **無預設對映**（A-4′），每一項都得使用者自己選。
 * `confirmedAt` ＝ 使用者勾選「我聲明這是我標好的正反例」之時間（UTC ISO-8601），
 * 落進 receipt 之 `mapping_provenance`（Task 1.6）。
 */
export interface EventCsvMappingSubmission {
  columnMapping: Record<string, string>;
  batchDefaults?: Record<string, unknown> | null;
  confirmedAt: string;
  validateOnly: boolean;
  /**
   * 由後端在 t0 單位正規化後依契約模板逐列產生 `event_id`（殘留 `R-B2-1`）。
   * 🔴 預設 `false`／不送＝不推斷（A-4′）；上傳位元組不因此改變。
   */
  deriveEventId?: boolean;
}

export interface EventImportRejected {
  kind: 'legacy_schema_detected' | 'new_schema_on_legacy_endpoint' | 'contract_violation' | 'parse_error'
    | 'lookahead_declaration_required' | 'lookahead_declaration_invalid'
    | 'lookahead_declaration_unacknowledged_lowering' | 'lookahead_declaration_unacknowledged_unverifiable' | string;
  message: string;
  failures: EventImportFailure[];
  migration_hint?: Record<string, unknown> | null;
  /** 結構化補充（如 default_window_bars／lowered_timeframes），供 UI 預填與說明 */
  detail?: Record<string, unknown> | null;
}

/** 表格 capability：ok ⇒ 數值；其他 ⇒ 顯示 reason（不得空白） */
export interface EventTableStatus {
  capability_status?: 'ok' | 'unavailable' | 'not_computed' | 'not_applicable' | string;
  reason?: string | null;
  [k: string]: unknown;
}

export interface EventAnalyzeResponse {
  import_id: string;
  summary: Record<string, unknown>;
  align_failures: { event_id: string; reason: string }[];
  tables: {
    event_forward_return_table: EventTableStatus;
    binary_discrimination_table: EventTableStatus;
    all_bars_evaluation?: EventTableStatus;
  };
  /** epoch ms（契約單位） */
  event_timestamps: number[];
  /** bar open 秒（IC 主線單位） */
  event_timestamps_ic_seconds?: number[];
  /** GAP-3 UX Task 1.9：該批落檔之答案窗宣告 receipt（舊批為 null） */
  lookahead_declaration?: EventLookaheadDeclarationReceipt | null;
  /** GAP-3 UX Task 1.12：`split` 為 `unavailable` ⇒ 該批只走事件研究，未執行切分與條件 IC */
  capability?: { split: 'ok' | 'unavailable' | string; reason?: string };
  /**
   * GAP-3 UX Task 1.9：**實際**送進切分的隔離寬度。
   * 🔴 宣告深度是下界：`source === 'lookahead_declaration_lower_bound'` 表示請求值低於宣告深度而被提高
   * ——UI 顯示隔離寬度時必須讀 `applied_ms`，不是使用者送出的請求值。
   */
  embargo?: {
    applied_ms: number | null;
    source: 'lookahead_declaration_lower_bound' | 'request' | 'label_window_max'
      | 'not_applicable_event_study_only' | string;
  };
}

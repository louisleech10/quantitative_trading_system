// frontend/src/lib/patternTypes.ts
// Pattern Discovery System 類型定義

export interface PatternRule {
  feature: string;
  operator: string;
  threshold: number;
  description: string;
}

export type EngineType = 'lightgbm' | 'xgboost';
export type EngineMode = EngineType | 'both';

export interface IndicatorConfig {
  id: string;
  indicator: string;
  data_source: string;
  params: Record<string, unknown>;
}

export interface Pattern {
  pattern_id: string;
  name: string;
  description: string;
  rules: PatternRule[];
  case_id: string;
  xgboost_importance: Record<string, number>;
  performance_metrics: {
    accuracy?: number;
    precision: number;
    recall: number;
    f1_score: number;
    train_auc?: number;
    cv_auc_mean?: number;
    cv_auc_std?: number;
    overfitting_score?: number;
    sample_count?: number;
    profitable_count?: number;
  };
  created_at: string;
  updated_at: string;
  status: 'active' | 'archived' | 'testing';
  tags: string[];
  metadata: {
    data_selection?: {
      symbol?: string;
      symbols?: string[];
      timeframe?: string;
      lookback_bars?: number;
      [key: string]: unknown;
    };
    indicator_config?: Array<{
      indicator?: string;
      data_source?: string;
      params?: Record<string, unknown>;
      [key: string]: unknown;
    }>;
    sequence_config?: {
      sequence_length?: number;
      sequence_feature_mode?: 'aggregate' | 'flatten';
      sequence_stride?: number;
      aggregation_methods?: string[];
      multi_scale_windows?: number[];
      [key: string]: unknown;
    };
    training_config?: {
      time_series_split?: boolean;
      cv_folds?: number;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
}

export interface CreatePatternRequest {
  name: string;
  description: string;
  rules: PatternRule[];
  case_id: string;
  xgboost_importance: Record<string, number>;
  performance_metrics: Record<string, number>;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export interface UpdatePatternRequest {
  name?: string;
  description?: string;
  status?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export interface PatternListResponse {
  success: boolean;
  count: number;
  patterns: Pattern[];
}

export interface PatternSummary {
  pattern_id: string;
  name: string;
  description: string;
  rule_count: number;
  rule_condition: string;
  case_id: string;
  performance_metrics: Record<string, number>;
  status: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface PatternStatistics {
  total_patterns: number;
  by_status: {
    active: number;
    archived: number;
    testing: number;
  };
  average_performance: {
    accuracy: number;
    precision: number;
    recall: number;
    f1_score: number;
  };
  performance_distribution?: Array<{ bucket: string; count: number }>;
  by_tags?: Record<string, number>;
  by_case_id?: Record<string, number>;
  total?: number;
  active?: number;
  archived?: number;
  testing?: number;
  avg_rules_per_pattern?: number;
  top_tags?: [string, number][];
}

export interface FeatureImportance {
  feature: string;
  importance: number;
  rank: number;
  method: string;
}

export interface DecisionRule {
  rule_id: number;
  condition: string;
  support: number;
  confidence: number;
  lift: number;
  feature_conditions: Array<{
    feature: string;
    operator: string;
    threshold: number;
  }>;
}

export interface ModelPerformance {
  engine_type?: EngineType;
  test_accuracy?: number;
  test_precision?: number;
  test_recall?: number;
  test_f1?: number;
  test_auc?: number;
  train_auc: number;
  cv_auc_mean: number;
  cv_auc_std: number;
  precision: number;
  recall: number;
  f1_score: number;
  overfitting_score: number;
  brier_score?: number;
  ece?: number;
  calibration_quality?: string;
  pr_auc?: number;
  positive_rate?: number;
}

export interface PrecisionAtKResult {
  precision_at_k: Record<number, number>;
  threshold_at_k: Record<number, number>;
  sample_count_at_k: Record<number, number>;
  recommended_k?: number | null;
  recommended_threshold?: number | null;
  recommended_precision?: number | null;
}

export interface ExpectancyResult {
  win_rate: number;
  avg_win: number;
  avg_loss: number;
  expectancy: number;
  total_trades: number;
  threshold: number;
  note: string;
  sharpe_proxy?: number | null;
}

export interface BootstrapCIResult {
  metric: string;
  point_estimate: number;
  ci_lower: number;
  ci_upper: number;
  confidence_level: number;
  n_bootstrap: number;
}

export interface PermutationImportanceItem {
  feature: string;
  importance: number;
  std: number;
  rank: number;
  gain_rank?: number | null;
  rank_gap?: number | null;
  overfit_flag?: boolean;
}

export interface PermutationImportanceResult {
  rank_gap_threshold: number;
  items: PermutationImportanceItem[];
}

export interface FoldImportanceStabilityResult {
  stable_features: string[];
  unstable_features: Array<{ feature: string; cv: number; rank_range: number[] }>;
  feature_cv: Record<string, number>;
}

export interface CrossSymbolValidationResult {
  source_symbol: string;
  target_symbol: string;
  source_auc: number;
  target_auc: number;
  generalization_gap: number;
  verdict: string;
}

export interface XGBoostAnalysisResult {
  case_id: string;
  model_performance: ModelPerformance;
  feature_importance: FeatureImportance[];
  decision_rules: DecisionRule[];
  precision_at_k?: PrecisionAtKResult | null;
  expectancy?: ExpectancyResult | null;
  bootstrap_ci?: Record<string, BootstrapCIResult> | null;
  permutation_importance?: PermutationImportanceResult | null;
  fold_importance_stability?: FoldImportanceStabilityResult | null;
  cross_symbol_validation?: CrossSymbolValidationResult[] | null;
  model_saved: boolean;
  model_path?: string;
}

export interface ValidationConfig {
  cv_folds: number;
  purge_gap: number;
  oot_enabled: boolean;
  oot_ratio: number;
  early_stopping_rounds: number;
}

export interface ModelTrainingRequest {
  engine: EngineType;
  features_source: string;
  config?: Record<string, unknown>;
  validation?: ValidationConfig;
  run_comparison: boolean;
}

export interface BatchAnalysisRequest {
  engine?: EngineType;
  symbols: string[];
  timeframe: string;
  indicators: IndicatorConfig[];
  selected_features?: string[];
  lookback_bars: number;
  sequence_length?: number | null;
  sequence_feature_mode?: 'aggregate' | 'flatten';
  sequence_stride?: number;
  aggregation_methods?: string[] | null;
  multi_scale_windows?: number[] | null;
  time_series_split?: boolean;
  model_params?: Record<string, unknown>;
  cv_folds: number;
  run_comparison?: boolean;
}

export interface ModelPerformanceResponse {
  engine_type?: string;
  train_auc: number;
  cv_auc_mean: number;
  cv_auc_std: number;
  precision: number;
  recall: number;
  f1_score: number;
  overfitting_score: number;
  oot_auc?: number | null;
  brier_score?: number | null;
  ece?: number | null;
  calibration_quality?: string | null;
  pr_auc?: number | null;
  positive_rate?: number | null;
  training_time_seconds?: number | null;
}

export interface ComparisonReportResponse {
  engine_performances: Record<string, ModelPerformanceResponse>;
  consensus_rate: number;
  feature_rank_correlation: number;
  recommended_engine: string;
  recommendation_reason: string;
}

export interface TaskStartResponse {
  task_id: string;
  status: string;
  engine: string;
}

export interface LightGBMTrainingRequest {
  features_source: string;
  config?: Record<string, unknown>;
  boosting_type: 'gbdt' | 'dart' | 'goss';
  categorical_features?: string[];
  validation?: ValidationConfig;
}

export interface LightGBMResultsResponse {
  task_id: string;
  performance: ModelPerformanceResponse;
  feature_importance: Array<{ feature: string; importance: number; rank: number }>;
  predictions_summary?: Record<string, unknown>;
}

export interface LightGBMConfig {
  boosting_type: 'gbdt' | 'dart' | 'goss';
  num_leaves: number;
  max_depth: number;
  learning_rate: number;
  n_estimators: number;
  subsample: number;
  colsample_bytree: number;
  min_child_samples: number;
  reg_alpha: number;
  reg_lambda: number;
  min_gain_to_split: number;
  categorical_features?: string[];
}

export interface XGBoostConfig {
  max_depth: number;
  learning_rate: number;
  n_estimators: number;
  subsample: number;
  colsample_bytree: number;
  min_child_weight: number;
  gamma: number;
  reg_alpha: number;
  reg_lambda: number;
}

export interface ModelHyperparamOptimizationRequest {
  task_type: 'model_hyperparam';
  engine: EngineType;
  n_trials: number;
  objective_config: {
    engine: EngineType;
    features_source?: string;
    cv_folds?: number;
    base_model_params?: Record<string, unknown>;
  };
}

export interface AnalysisResult {
  symbol: string;
  symbols?: string[];
  timeframe: string;
  total_cases: number;
  valid_cases: number;
  positive_cases: number;
  negative_cases: number;
  features_generated: number;
  feature_names: string[];
  engine_type?: EngineType;
  model_performance: ModelPerformance;
  feature_importance: FeatureImportance[];
  decision_rules: DecisionRule[];
  precision_at_k?: PrecisionAtKResult | null;
  expectancy?: ExpectancyResult | null;
  bootstrap_ci?: Record<string, BootstrapCIResult> | null;
  permutation_importance?: PermutationImportanceResult | null;
  fold_importance_stability?: FoldImportanceStabilityResult | null;
  cross_symbol_validation?: CrossSymbolValidationResult[] | null;
  model_saved: boolean;
  model_path?: string;
  metadata?: {
    data_selection?: {
      symbol?: string;
      symbols?: string[];
      timeframe: string;
      lookback_bars: number;
    };
    indicator_config?: Array<{
      indicator: string;
      data_source: string;
      params: Record<string, unknown>;
    }>;
    sequence_config?: {
      sequence_length: number;
      sequence_feature_mode: 'aggregate' | 'flatten';
      sequence_stride: number;
      aggregation_methods: string[];
      multi_scale_windows: number[];
    };
    training_config?: {
      time_series_split: boolean;
      cv_folds: number;
    };
  };
}

export interface XGBoostAnalysisRequest {
  case_id: string;
  max_depth?: number;
  learning_rate?: number;
  n_estimators?: number;
  top_n_features?: number;
  min_rule_support?: number;
  xgboost_params?: Record<string, unknown>;
  cv_folds?: number;
  top_n_rules?: number;
  min_support?: number;
}

// ==================== 深度分析類型 ====================

export interface OOTValidationRequest {
  task_id: string;
  oot_start_date?: string;
  oot_ratio?: number;
  validation_ratio?: number;
  timestamp_column?: string;
}

export interface OOTValidationResult {
  oot_auc: number;
  oot_precision: number;
  oot_recall: number;
  oot_f1: number;
  oot_samples: number;
  oot_positive_count: number;
  oot_positive_rate: number;
  cv_auc_mean: number;
  cv_oot_gap: number;
  gap_status: 'good' | 'acceptable' | 'warning' | 'unknown';
  is_generalization_good: boolean;
  oot_period_start: string;
  oot_period_end: string;
}

export interface TimePeriodInfo {
  start: string;
  end: string;
  samples: number;
  positive_count?: number;
  positive_rate?: number;
}

export interface TimeSplitReport {
  split_method: string;
  timestamp_column: string;
  random_seed?: number | null;
  train_period: TimePeriodInfo;
  validation_period?: TimePeriodInfo | null;
  oot_period: TimePeriodInfo;
  total_samples: number;
}

export interface PSIResult {
  feature: string;
  psi: number;
  status: 'stable' | 'drift_warning' | 'drift_severe';
  distribution_comparison: {
    bins: number[];
    train_pct: number[];
    test_pct: number[];
  };
}

export interface DriftReport {
  total_features: number;
  drifted_features: string[];
  severe_features: string[];
  results: PSIResult[];
}

export interface PhaseMetrics {
  phase: string;
  support: number;
  auc: number | null;
  precision_at_10: number | null;
  avg_pred_proba?: number | null;
  recommendation: string;
  note?: string | null;
}

export interface RegimeClusterStat {
  regime: string;
  count: number;
  pct: number;
  volatility_mean?: number;
  volatility_std?: number;
  trend_strength_mean?: number;
  trend_strength_std?: number;
  volume_ratio_mean?: number;
  volume_ratio_std?: number;
}

export interface RegimeReport {
  overall_auc?: number | null;
  phase_metrics: PhaseMetrics[];
  trading_rules: Record<string, { threshold: number | null; position_size: string | null }>;
  regime_method?: string | null;  // "rule" | "kmeans"
  cluster_stats?: RegimeClusterStat[] | null;  // K-Means 聚類統計
}

export interface SHAPSummaryPoint {
  feature: string;
  value: number;
  shap_value: number;
}

export interface SHAPFeatureImportance {
  feature: string;
  mean_abs_shap: number;
  mean_shap: number;
  rank: number;
}

export interface GlobalSHAPResult {
  expected_value: number;
  feature_importance_shap: SHAPFeatureImportance[];
  top_positive_features: string[];
  top_negative_features: string[];
  sample_size?: number;
  summary_points?: SHAPSummaryPoint[];
}

export interface SingleCaseContribution {
  feature: string;
  value: number;
  shap_value: number;
  contribution_pct: number;
}

export interface SingleCaseSHAPResult {
  predicted_proba: number;
  expected_value: number;
  contributions: SingleCaseContribution[];
}

export interface CalibrationCurveData {
  bin_midpoints: number[];
  actual_positive_rate: number[];
  predicted_mean: number[];
  sample_count: number[];
  perfect_calibration?: number[];
}

export interface PRCurveData {
  precision: number[];
  recall: number[];
  thresholds: number[];
  pr_auc?: number | null;
  baseline?: number | null;
}

export interface OOTValidationResponse {
  task_id: string;
  status: string;
  message: string;
  validation_result?: OOTValidationResult | null;
  time_split_report?: TimeSplitReport | null;
  drift_report?: DriftReport | null;
  error?: string | null;
}

export interface DriftReportResponse {
  task_id: string;
  status: string;
  message: string;
  report?: DriftReport | null;
  error?: string | null;
}

export interface RegimeAnalysisResponse {
  task_id: string;
  status: string;
  message: string;
  report?: RegimeReport | null;
  error?: string | null;
}

export interface PredictionsResponse {
  task_id: string;
  total_cases: number;
  summary: {
    mean: number;
    std: number;
    bins: Record<string, number>;
    min: number;
    max: number;
  };
  predictions?: Array<{
    case_id: string;
    y_true?: number | null;
    predicted_proba: number;
  }> | null;
}

export interface FeatureImportanceTypesResponse {
  task_id: string;
  types: {
    gain?: Array<{ feature: string; importance: number; rank: number; method: string }>;
    cover?: Array<{ feature: string; importance: number; rank: number; method: string }>;
    weight?: Array<{ feature: string; importance: number; rank: number; method: string }>;
  };
}

export interface SHAPGlobalResponse {
  task_id: string;
  status: string;
  message: string;
  result?: GlobalSHAPResult | null;
  error?: string | null;
}

export interface SHAPSingleCaseResponse {
  task_id: string;
  case_id: string;
  status: string;
  message: string;
  result?: SingleCaseSHAPResult | null;
  error?: string | null;
}

export interface CalibrationCurveResponse {
  task_id: string;
  data: CalibrationCurveData;
}

export interface PRCurveResponse {
  task_id: string;
  data: PRCurveData;
}

export interface ProbabilityDensityData {
  positive_density: { bins: number[]; density: number[] };
  negative_density: { bins: number[]; density: number[] };
  overlap_score: number;
}

export interface ProbabilityDensityResponse {
  task_id: string;
  data: ProbabilityDensityData;
}

export interface EquityCurveData {
  timestamps: number[];
  strategy_returns: number[];
  benchmark_returns: number[];
  threshold: number;
  final_return_pct: { strategy: number; benchmark: number };
}

export interface EquityCurveResponse {
  task_id: string;
  data: EquityCurveData;
}

export interface FalsePositiveCase {
  case_id: string;
  timestamp: string;
  symbol: string;
  predicted_proba: number;
  actual_return: number;
}

export interface TopFalsePositivesResponse {
  task_id: string;
  cases: FalsePositiveCase[];
  total_false_positives: number;
}

export interface RollingAUCData {
  timestamps: number[];
  auc_values: Array<number | null>;
  window_size: number;
  warning_zones: Array<{ start: string; end: string }>;
}

export interface RollingAUCResponse {
  task_id: string;
  data: RollingAUCData;
}

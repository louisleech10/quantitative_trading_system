// frontend/src/lib/patternTypes.ts
// Pattern Discovery System 類型定義

export interface PatternRule {
  feature: string;
  operator: string;
  threshold: number;
  description: string;
}

export interface Pattern {
  pattern_id: string;
  name: string;
  description: string;
  rules: PatternRule[];
  case_id: string;
  xgboost_importance: Record<string, number>;
  performance_metrics: {
    precision: number;
    recall: number;
    f1_score: number;
    train_auc?: number;
    cv_auc_mean?: number;
    cv_auc_std?: number;
  };
  created_at: string;
  updated_at: string;
  status: 'active' | 'archived' | 'testing';
  tags: string[];
  metadata: Record<string, any>;
}

export interface CreatePatternRequest {
  name: string;
  description: string;
  rules: PatternRule[];
  case_id: string;
  xgboost_importance: Record<string, number>;
  performance_metrics: Record<string, number>;
  tags?: string[];
  metadata?: Record<string, any>;
}

export interface UpdatePatternRequest {
  name?: string;
  description?: string;
  status?: string;
  tags?: string[];
  metadata?: Record<string, any>;
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
  total: number;
  active: number;
  archived: number;
  testing: number;
  avg_rules_per_pattern: number;
  top_tags: [string, number][];
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

export interface XGBoostAnalysisRequest {
  case_id: string;
  xgboost_params?: Record<string, any>;
  cv_folds?: number;
  top_n_rules?: number;
  min_support?: number;
}

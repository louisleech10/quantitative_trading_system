// frontend/src/lib/api/patternApi.ts
// Pattern Discovery API 客戶端

import type {
  Pattern,
  CreatePatternRequest,
  UpdatePatternRequest,
  PatternListResponse,
  PatternSummary,
  PatternStatistics,
  BatchAnalysisRequest,
  ModelTrainingRequest,
  TaskStartResponse,
  ModelPerformanceResponse,
  ComparisonReportResponse,
  ModelHyperparamOptimizationRequest,
  XGBoostAnalysisRequest,
  XGBoostAnalysisResult,
  OOTValidationRequest,
  OOTValidationResponse,
  DriftReportResponse,
  RegimeAnalysisResponse,
  PredictionsResponse,
  FeatureImportanceTypesResponse,
  SHAPGlobalResponse,
  SHAPSingleCaseResponse,
  CalibrationCurveResponse,
  PRCurveResponse,
  ProbabilityDensityResponse,
  EquityCurveResponse,
  TopFalsePositivesResponse,
  RollingAUCResponse
} from '@/lib/patternTypes';
import { httpErrorMessage } from '../httpError';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1';

// 通用 fetch 封裝
export class APIError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'APIError';
  }
}

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers
    }
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const message = httpErrorMessage(error, 'API request failed');
    throw new APIError(response.status, message);
  }

  return response.json();
}

// ===== Pattern Management API =====

export async function createPattern(request: CreatePatternRequest): Promise<{ success: boolean; pattern_id?: string; pattern?: Pattern; error?: string }> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/patterns/define`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });
  
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error);
  }
  
  return response.json();
}

export async function getPattern(patternId: string): Promise<{ success: boolean; pattern?: Pattern; error?: string }> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/patterns/${patternId}`);
  
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error);
  }
  
  return response.json();
}

export async function listPatterns(
  status?: string,
  tags?: string[],
  caseId?: string
): Promise<PatternListResponse> {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (tags && tags.length > 0) params.append('tags', tags.join(','));
  if (caseId) params.append('case_id', caseId);
  
  const response = await fetch(
    `${API_BASE_URL}${API_PREFIX}/patterns/list?${params.toString()}`
  );
  
  if (!response.ok) {
    throw new Error('Failed to fetch patterns');
  }
  
  return response.json();
}

export async function updatePattern(
  patternId: string,
  request: UpdatePatternRequest
): Promise<{ success: boolean; message?: string; error?: string }> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/patterns/${patternId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });
  
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error);
  }
  
  return response.json();
}

export async function deletePattern(patternId: string): Promise<{ success: boolean; message?: string; error?: string }> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/patterns/${patternId}`, {
    method: 'DELETE'
  });
  
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error);
  }
  
  return response.json();
}
export async function deleteAllPatterns(): Promise<{ success: boolean; message?: string; deleted_count?: number; error?: string }> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/patterns/batch/delete-all`, {
    method: 'DELETE'
  });
  
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error);
  }
  
  return response.json();
}
export async function getPatternSummary(patternId: string): Promise<{ success: boolean; summary?: PatternSummary; error?: string }> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/patterns/${patternId}/summary`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch pattern summary');
  }
  
  return response.json();
}

export async function getPatternStatistics(): Promise<{ success: boolean; statistics?: PatternStatistics; error?: string }> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/patterns/statistics`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch pattern statistics');
  }
  
  return response.json();
}

// ===== XGBoost Analysis API =====

export async function startXGBoostAnalysis(request: XGBoostAnalysisRequest): Promise<{ task_id: string; message: string; status: string }> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/pattern-analysis/xgboost/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });
  
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error);
  }
  
  return response.json();
}

export async function getXGBoostTaskStatus(taskId: string): Promise<{
  status: string;
  progress: number;
  message: string;
  result?: XGBoostAnalysisResult;
  error?: string;
}> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/pattern-analysis/xgboost/task/${taskId}`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch task status');
  }
  
  return response.json();
}

export async function getModelInfo(caseId: string): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/pattern-analysis/model/info/${caseId}`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch model info');
  }
  
  return response.json();
}

export async function listModels(): Promise<unknown[]> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/pattern-analysis/model/list`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch models');
  }
  
  return response.json();
}

export async function getCaseSummary(symbol?: string, timeframe?: string): Promise<{
  total_cases: number;
  positive_cases: number;
  negative_cases: number;
  symbols: string[];
  timeframes: string[];
}> {
  const params = new URLSearchParams();
  if (symbol) params.append('symbol', symbol);
  if (timeframe) params.append('timeframe', timeframe);
  const query = params.toString();
  return fetchAPI(`/pattern-analysis/cases/summary${query ? `?${query}` : ''}`);
}

export async function startBatchAnalysis(config: BatchAnalysisRequest): Promise<{ task_id: string }> {
  const endpoint = config.engine === 'lightgbm' || config.run_comparison
    ? '/pattern-analysis/batch/start'
    : '/pattern-analysis/xgboost/batch/start';

  return fetchAPI(endpoint, {
    method: 'POST',
    body: JSON.stringify(config)
  });
}

export async function getBatchTaskStatus(taskId: string): Promise<{
  status: 'running' | 'completed' | 'failed';
  progress: number;
  current_step: string;
  message: string;
  total_cases: number;
  processed_cases: number;
  result?: unknown;
  error?: string;
}> {
  return fetchAPI(`/pattern-analysis/xgboost/batch/task/${taskId}`);
}

export async function startModelTraining(request: ModelTrainingRequest): Promise<TaskStartResponse> {
  return fetchAPI('/pattern-analysis/model/train', {
    method: 'POST',
    body: JSON.stringify(request)
  });
}

export async function getModelPerformance(taskId: string): Promise<ModelPerformanceResponse> {
  return fetchAPI(`/pattern-analysis/model/${taskId}/performance`);
}

export async function getModelComparison(taskId: string): Promise<ComparisonReportResponse> {
  return fetchAPI(`/pattern-analysis/model/${taskId}/comparison`);
}

export async function startModelHyperparamOptimization(
  request: ModelHyperparamOptimizationRequest
): Promise<{ task_id: string }> {
  return fetchAPI('/optimization/start', {
    method: 'POST',
    body: JSON.stringify(request)
  });
}

// ===== 深度分析 API =====

export async function validateOOT(request: OOTValidationRequest): Promise<OOTValidationResponse> {
  return fetchAPI<OOTValidationResponse>('/pattern-analysis/xgboost/validate-oot', {
    method: 'POST',
    body: JSON.stringify(request)
  });
}

export async function getDriftReport(taskId: string): Promise<DriftReportResponse> {
  return fetchAPI<DriftReportResponse>(`/pattern-analysis/xgboost/${taskId}/drift-report`);
}

export async function getRegimeAnalysis(taskId: string): Promise<RegimeAnalysisResponse> {
  return fetchAPI<RegimeAnalysisResponse>(`/pattern-analysis/xgboost/${taskId}/regime-analysis`);
}

export async function getPredictions(taskId: string, includeDetails = false): Promise<PredictionsResponse> {
  const params = includeDetails ? '?include_details=true' : '';
  return fetchAPI<PredictionsResponse>(`/pattern-analysis/xgboost/${taskId}/predictions${params}`);
}

export async function getFeatureImportanceAll(taskId: string, types?: string[]): Promise<FeatureImportanceTypesResponse> {
  const params = types && types.length > 0 ? `?types=${types.join(',')}` : '';
  return fetchAPI<FeatureImportanceTypesResponse>(`/pattern-analysis/xgboost/${taskId}/feature-importance${params}`);
}

export async function getSHAPGlobal(taskId: string, sampleSize?: number, includeSummaryPoints = true): Promise<SHAPGlobalResponse> {
  return fetchAPI<SHAPGlobalResponse>(`/pattern-analysis/xgboost/${taskId}/shap`, {
    method: 'POST',
    body: JSON.stringify({ sample_size: sampleSize, include_summary_points: includeSummaryPoints })
  });
}

export async function getSHAPSingleCase(taskId: string, caseId: string): Promise<SHAPSingleCaseResponse> {
  return fetchAPI<SHAPSingleCaseResponse>(`/pattern-analysis/xgboost/${taskId}/shap/case/${caseId}`);
}

export async function getCalibrationCurve(taskId: string): Promise<CalibrationCurveResponse> {
  return fetchAPI<CalibrationCurveResponse>(`/pattern-analysis/xgboost/${taskId}/calibration-curve`);
}

export async function getPRCurve(taskId: string): Promise<PRCurveResponse> {
  return fetchAPI<PRCurveResponse>(`/pattern-analysis/xgboost/${taskId}/pr-curve`);
}

export async function getProbabilityDensity(taskId: string, nBins = 50): Promise<ProbabilityDensityResponse> {
  return fetchAPI<ProbabilityDensityResponse>(`/pattern-analysis/xgboost/${taskId}/probability-density?n_bins=${nBins}`);
}

export async function getStrategyEquity(taskId: string, threshold = 0.75): Promise<EquityCurveResponse> {
  return fetchAPI<EquityCurveResponse>(`/pattern-analysis/xgboost/${taskId}/strategy-equity?threshold=${threshold}`);
}

export async function getTopFalsePositives(taskId: string, topN = 5): Promise<TopFalsePositivesResponse> {
  return fetchAPI<TopFalsePositivesResponse>(`/pattern-analysis/xgboost/${taskId}/top-false-positives?top_n=${topN}`);
}

export async function getRollingAUC(taskId: string, window = 500): Promise<RollingAUCResponse> {
  return fetchAPI<RollingAUCResponse>(`/pattern-analysis/xgboost/${taskId}/rolling-auc?window=${window}`);
}

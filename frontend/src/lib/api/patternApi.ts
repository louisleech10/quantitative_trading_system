// frontend/src/lib/api/patternApi.ts
// Pattern Discovery API 客戶端

import type {
  Pattern,
  CreatePatternRequest,
  UpdatePatternRequest,
  PatternListResponse,
  PatternSummary,
  PatternStatistics,
  XGBoostAnalysisRequest,
  XGBoostAnalysisResult
} from '@/lib/patternTypes';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1';

// ===== Pattern Management API =====

export async function createPattern(request: CreatePatternRequest): Promise<{ success: boolean; pattern_id?: string; error?: string }> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/pattern-management/patterns/define`, {
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
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/pattern-management/patterns/${patternId}`);
  
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
    `${API_BASE_URL}${API_PREFIX}/pattern-management/patterns/list?${params.toString()}`
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
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/pattern-management/patterns/${patternId}`, {
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
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/pattern-management/patterns/${patternId}`, {
    method: 'DELETE'
  });
  
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error);
  }
  
  return response.json();
}

export async function getPatternSummary(patternId: string): Promise<{ success: boolean; summary?: PatternSummary; error?: string }> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/pattern-management/patterns/${patternId}/summary`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch pattern summary');
  }
  
  return response.json();
}

export async function getPatternStatistics(): Promise<{ success: boolean; statistics?: PatternStatistics; error?: string }> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/pattern-management/patterns/statistics`);
  
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

export async function getModelInfo(caseId: string): Promise<any> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/pattern-analysis/model/info/${caseId}`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch model info');
  }
  
  return response.json();
}

export async function listModels(): Promise<any[]> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/pattern-analysis/model/list`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch models');
  }
  
  return response.json();
}

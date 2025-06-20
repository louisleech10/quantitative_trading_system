// frontend/src/lib/api.ts
// API client for connecting to FastAPI backend

import { ApiResponse, SearchResultData, SearchTemplate, SearchRequest, TaskInfo } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1';

class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = `${API_BASE_URL}${API_PREFIX}`;
  }

  // Generic fetch wrapper with error handling
  private async fetchApi<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error?.message || `HTTP ${response.status}: Request failed`);
      }

      return data;
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  // Search operations
  async executeSearch(request: SearchRequest): Promise<ApiResponse<TaskInfo>> {
    return this.fetchApi('/search/execute', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getTaskStatus(taskId: string): Promise<ApiResponse<TaskInfo>> {
    return this.fetchApi(`/search/task/${taskId}`);
  }

  async getTaskResult(taskId: string): Promise<ApiResponse<SearchResultData>> {
    return this.fetchApi(`/search/task/${taskId}/result`);
  }

  // Configuration operations
  async getSearchTemplates(): Promise<ApiResponse<{ templates: SearchTemplate[]; total: number }>> {
    return this.fetchApi('/config/templates');
  }

  async getSystemConfig(): Promise<ApiResponse<any>> {
    return this.fetchApi('/config/system');
  }

  // Health check
  async healthCheck(): Promise<ApiResponse<{ status: string }>> {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      return await response.json();
    } catch (error) {
      return {
        success: false,
        error: { 
          code: 'CONNECTION_ERROR', 
          message: 'Cannot connect to API server' 
        },
        timestamp: new Date().toISOString()
      };
    }
  }

  // Preview search
  async previewSearch(config: any, symbolsLimit: number = 10): Promise<ApiResponse<any>> {
    return this.fetchApi('/search/preview', {
      method: 'POST',
      body: JSON.stringify({
        config,
        symbols_limit: symbolsLimit
      }),
    });
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Utility functions
export const formatTimestamp = (timestamp: string): string => {
  return new Date(timestamp).toLocaleString('zh-TW');
};

export const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

export const formatPercentage = (value: number): string => {
  return `${(value * 100).toFixed(2)}%`;
};

export const formatNumber = (value: number, decimals: number = 2): string => {
  return value.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};
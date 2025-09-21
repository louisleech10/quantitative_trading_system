// frontend/src/lib/api.ts 
// API client for connecting to FastAPI backend - 兩階段搜索版本

import { ApiResponse, SearchResultData, SearchTemplate, SearchRequest, TaskInfo } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1';

// 後端搜索配置請求格式
interface SearchConfigRequest {
  name: string;
  timeframe: string;
  initial_conditions: FilterConditionRequest[];
  symbols?: string[];
  save_results?: boolean;
}

interface FilterConditionRequest {
  condition_type: string;
  parameter: string;
  operator: string;
  value: number | string;
  description?: string;
}

// 反例搜索請求格式
interface NegativeCaseRequest {
  search_config: SearchConfigRequest;
  negative_ratio: number;
  time_separation_days: number;
  sampling_strategy: string;
  negative_conditions?: any[];
}

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

  // 轉換前端搜索請求為後端格式
  private convertToSearchConfig(request: SearchRequest): SearchConfigRequest {
    const conditions: FilterConditionRequest[] = [];

    // 轉換價格變化條件
    if (request.priceChange !== undefined) {
      conditions.push({
        condition_type: "price_change",
        parameter: "price_change_percentage",
        operator: ">=",
        value: request.priceChange,
        description: `價格變化 >= ${request.priceChange}%`
      });
    }

    // 轉換成交量條件
    if (request.volumeMultiplier !== undefined) {
      conditions.push({
        condition_type: "volume",
        parameter: "volume_multiplier",
        operator: ">=",
        value: request.volumeMultiplier,
        description: `成交量倍數 >= ${request.volumeMultiplier}`
      });
    }

    // 轉換收盤強度條件
    if (request.closingStrength !== undefined) {
      conditions.push({
        condition_type: "price_position",
        parameter: "closing_strength",
        operator: ">=",
        value: request.closingStrength,
        description: `收盤強度 >= ${request.closingStrength}`
      });
    }

    // 轉換主動買入比例條件
    if (request.takerBuyRatio !== undefined) {
      conditions.push({
        condition_type: "market_sentiment",
        parameter: "taker_buy_ratio",
        operator: ">=",
        value: request.takerBuyRatio,
        description: `主動買入比例 >= ${request.takerBuyRatio}`
      });
    }

    return {
      name: request.name || `搜索_${new Date().toISOString().slice(0, 19)}`,
      timeframe: request.timeframe || "12h",
      initial_conditions: conditions,
      symbols: request.symbols,
      save_results: request.saveResults || false
    };
  }

  // 原有的單一搜索方法（向後兼容）
  async executeSearch(request: SearchRequest): Promise<ApiResponse<TaskInfo>> {
    const searchConfig = this.convertToSearchConfig(request);
    return this.fetchApi('/search/execute', {
      method: 'POST',
      body: JSON.stringify(searchConfig),
    });
  }

  // 兩階段搜索 - 步驟1：執行正例搜索
  async executePositiveSearch(request: SearchRequest): Promise<ApiResponse<TaskInfo>> {
    const searchConfig = this.convertToSearchConfig(request);
    
    console.log('執行正例搜索，配置:', searchConfig);
    
    return this.fetchApi('/two-stage/positive', {
      method: 'POST',
      body: JSON.stringify(searchConfig),
    });
  }

  // 兩階段搜索 - 步驟2：執行反例搜索
  async executeNegativeSearch(
    positiveTaskId: string, 
    negativeRatio: number = 2.0,
    timeSeparationDays: number = 7,
    customConditions: any[] = []
  ): Promise<ApiResponse<TaskInfo>> {
    
    console.log('執行反例搜索，正例任務ID:', positiveTaskId);
    
    const negativeRequest: NegativeCaseRequest = {
      search_config: {
        name: `negative_search_${positiveTaskId}`,
        timeframe: "12h",
        initial_conditions: []
      },
      negative_ratio: negativeRatio,
      time_separation_days: timeSeparationDays,
      sampling_strategy: "time_separated",
      negative_conditions: customConditions
    };

    return this.fetchApi(`/two-stage/negative/${positiveTaskId}`, {
      method: 'POST',
      body: JSON.stringify(negativeRequest),
    });
  }

  // 兩階段搜索 - 步驟3：獲取合併結果
  async getCombinedResults(
    positiveTaskId: string, 
    negativeTaskId: string
  ): Promise<ApiResponse<SearchResultData>> {
    
    console.log('獲取合併結果:', { positiveTaskId, negativeTaskId });
    
    return this.fetchApi(`/two-stage/combined/${positiveTaskId}/${negativeTaskId}`);
  }

  // 獲取任務狀態
  async getTaskStatus(taskId: string): Promise<ApiResponse<TaskInfo>> {
    return this.fetchApi(`/search/task/${taskId}`);
  }

  // 獲取任務結果（單一任務）
  async getTaskResult(taskId: string): Promise<ApiResponse<SearchResultData>> {
    return this.fetchApi(`/search/task/${taskId}/result`);
  }

  // 取消任務
  async cancelTask(taskId: string): Promise<ApiResponse<{ success: boolean }>> {
    return this.fetchApi(`/search/task/${taskId}/cancel`, {
      method: 'POST',
    });
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

  // 新增：等待任務完成的輔助方法
  async waitForTaskCompletion(
    taskId: string, 
    maxWaitTime: number = 300000, // 5分鐘
    pollInterval: number = 2000 // 2秒
  ): Promise<TaskInfo> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < maxWaitTime) {
      try {
        const statusResponse = await this.getTaskStatus(taskId);
        
        if (!statusResponse.success || !statusResponse.data) {
          throw new Error('無法獲取任務狀態');
        }

        const status = statusResponse.data.status;
        
        if (status === 'completed') {
          console.log('任務完成:', taskId);
          return statusResponse.data;
        } else if (status === 'failed') {
          throw new Error('任務執行失敗');
        } else if (status === 'cancelled') {
          throw new Error('任務已取消');
        }
        
        // 等待下次輪詢
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        
      } catch (error) {
        console.error('輪詢任務狀態時出錯:', error);
        throw error;
      }
    }
    
    throw new Error('任務執行超時');
  }

  // 新增：完整的兩階段搜索流程
  async executeTwoStageSearch(
    request: SearchRequest,
    negativeRatio: number = 2.0,
    timeSeparationDays: number = 7,
    onProgress?: (stage: string, taskId?: string) => void
  ): Promise<SearchResultData> {
    
    try {
      // 階段1：執行正例搜索
      onProgress?.('正例搜索中...');
      const positiveResponse = await this.executePositiveSearch(request);
      
      if (!positiveResponse.success || !positiveResponse.data) {
        throw new Error('正例搜索啟動失敗');
      }
      
      const positiveTaskId = positiveResponse.data.task_id;
      onProgress?.('正例搜索中...', positiveTaskId);
      
      // 等待正例搜索完成
      await this.waitForTaskCompletion(positiveTaskId);
      
      // 階段2：執行反例搜索
      onProgress?.('反例搜索中...');
      const negativeResponse = await this.executeNegativeSearch(
        positiveTaskId, 
        negativeRatio, 
        timeSeparationDays
      );
      
      if (!negativeResponse.success || !negativeResponse.data) {
        throw new Error('反例搜索啟動失敗');
      }
      
      const negativeTaskId = negativeResponse.data.task_id;
      onProgress?.('反例搜索中...', negativeTaskId);
      
      // 等待反例搜索完成
      await this.waitForTaskCompletion(negativeTaskId);
      
      // 階段3：獲取合併結果
      onProgress?.('合併結果中...');
      const combinedResponse = await this.getCombinedResults(positiveTaskId, negativeTaskId);
      
      if (!combinedResponse.success || !combinedResponse.data) {
        throw new Error('獲取合併結果失敗');
      }
      
      onProgress?.('搜索完成');
      return combinedResponse.data;
      
    } catch (error) {
      console.error('兩階段搜索失敗:', error);
      throw error;
    }
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
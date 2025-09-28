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
  negative_conditions: any[];
  negative_ratio: number;
  time_separation_days: number;
  sampling_strategy: string;
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
  private convertToSearchConfig(
    request: SearchRequest,
    operators: { 
      priceChange: string;
      volumeMultiplier: string;
      closingStrength: string;
      takerBuyRatio: string;
      pricePosition: string;
    },
    rangeValues: { 
      priceChange: { min: number | null, max: number | null };
      volumeMultiplier: { min: number | null, max: number | null };
      closingStrength: { min: number | null, max: number | null };
      takerBuyRatio: { min: number | null, max: number | null };
      pricePosition: { min: number | null, max: number | null };
    }
  ): SearchConfigRequest {
    const conditions: FilterConditionRequest[] = [];

    // 1. 價格變化條件 (已修復)
    if (operators.priceChange === 'BETWEEN' && 
        rangeValues.priceChange.min !== null && 
        rangeValues.priceChange.max !== null) {
      conditions.push({
        condition_type: "price",
        parameter: "price_change",
        operator: "between",
        value: [rangeValues.priceChange.min / 100, rangeValues.priceChange.max / 100],
        description: `價格變化介於 ${rangeValues.priceChange.min}% 到 ${rangeValues.priceChange.max}%`
      });
    } else if (request.priceChange !== null && request.priceChange !== undefined) {
      conditions.push({
        condition_type: "price",
        parameter: "price_change",
        operator: operators.priceChange,  // 動態運算符
        value: request.priceChange / 100,
        description: `價格變化 ${operators.priceChange} ${request.priceChange}%`
      });
    }

    // 2. 成交量倍數條件 (新修復)
    if (operators.volumeMultiplier === 'BETWEEN' && 
        rangeValues.volumeMultiplier.min !== null && 
        rangeValues.volumeMultiplier.max !== null) {
      conditions.push({
        condition_type: "volume",
        parameter: "volume_multiplier",
        operator: "between",
        value: [rangeValues.volumeMultiplier.min, rangeValues.volumeMultiplier.max],
        description: `成交量倍數介於 ${rangeValues.volumeMultiplier.min} 到 ${rangeValues.volumeMultiplier.max}`
      });
    } else if (request.volumeMultiplier !== null && request.volumeMultiplier !== undefined) {
      conditions.push({
        condition_type: "volume",
        parameter: "volume_multiplier",
        operator: operators.volumeMultiplier,  // 修復：使用動態運算符
        value: request.volumeMultiplier,
        description: `成交量倍數 ${operators.volumeMultiplier} ${request.volumeMultiplier}`
      });
    }

    // 3. 收盤強度條件 (新修復)
    if (operators.closingStrength === 'BETWEEN' && 
        rangeValues.closingStrength.min !== null && 
        rangeValues.closingStrength.max !== null) {
      conditions.push({
        condition_type: "price",
        parameter: "closing_strength",
        operator: "between",
        value: [rangeValues.closingStrength.min, rangeValues.closingStrength.max],
        description: `收盤強度介於 ${rangeValues.closingStrength.min} 到 ${rangeValues.closingStrength.max}`
      });
    } else if (request.closingStrength !== null && request.closingStrength !== undefined) {
      conditions.push({
        condition_type: "price",
        parameter: "closing_strength",
        operator: operators.closingStrength,  // 修復：使用動態運算符
        value: request.closingStrength,
        description: `收盤強度 ${operators.closingStrength} ${request.closingStrength}`
      });
    }

    // 4. 主動買入比例條件 (新修復)
    if (operators.takerBuyRatio === 'BETWEEN' && 
        rangeValues.takerBuyRatio.min !== null && 
        rangeValues.takerBuyRatio.max !== null) {
      conditions.push({
        condition_type: "volume",
        parameter: "taker_buy_ratio",
        operator: "between",
        value: [rangeValues.takerBuyRatio.min, rangeValues.takerBuyRatio.max],
        description: `主動買入比例介於 ${rangeValues.takerBuyRatio.min} 到 ${rangeValues.takerBuyRatio.max}`
      });
    } else if (request.takerBuyRatio !== null && request.takerBuyRatio !== undefined) {
      conditions.push({
        condition_type: "volume",
        parameter: "taker_buy_ratio",
        operator: operators.takerBuyRatio,  // 修復：使用動態運算符
        value: request.takerBuyRatio,
        description: `主動買入比例 ${operators.takerBuyRatio} ${request.takerBuyRatio}`
      });
    }

    // 5. 價格位置條件 (新修復)
    if (operators.pricePosition === 'BETWEEN' && 
        rangeValues.pricePosition.min !== null && 
        rangeValues.pricePosition.max !== null) {
      conditions.push({
        condition_type: "price",
        parameter: "price_position",
        operator: "between",
        value: [rangeValues.pricePosition.min, rangeValues.pricePosition.max],
        description: `價格位置介於 ${rangeValues.pricePosition.min} 到 ${rangeValues.pricePosition.max}`
      });
    } else if (request.pricePosition !== null && request.pricePosition !== undefined) {
      conditions.push({
        condition_type: "price",
        parameter: "price_position",
        operator: operators.pricePosition,  // 修復：使用動態運算符
        value: request.pricePosition,
        description: `價格位置 ${operators.pricePosition} ${request.pricePosition}`
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
  async executePositiveSearch(
    request: SearchRequest,
    operators: any,
    rangeValues: any
  ): Promise<ApiResponse<TaskInfo>> {
    const searchConfig = this.convertToSearchConfig(request, operators, rangeValues);

    console.log('執行正例搜索，配置:', searchConfig);
    
    // 包裝成後端期望的格式
    const apiRequest = {
      request: searchConfig,
      symbols: request.symbols
    };
    
    console.log('API請求格式:', apiRequest);
    
    return this.fetchApi('/two-stage/positive', {
      method: 'POST',
      body: JSON.stringify(apiRequest),
    });
  }

  // 兩階段搜索 - 步驟2：執行反例搜索
  async executeNegativeSearch(
    positiveTaskId: string, 
    negativeRatio: number = 2.0,
    timeSeparationDays: number = 7,
    negativeRequest: SimpleSearchRequest,     // 新增：改為接收 SimpleSearchRequest
    negativeOperators: any,             // 新增：反例運算符
    negativeRangeValues: any            // 新增：反例範圍值
  ): Promise<ApiResponse<TaskInfo>> {
    
    console.log('執行反例搜索，正例任務ID:', positiveTaskId);
    //console.log('傳入的反例條件:', customConditions); // 新增日誌
  
    const negativeConditions = this.convertToSearchConfig(
      negativeRequest, 
      negativeOperators, 
      negativeRangeValues
    ).initial_conditions;

    console.log('使用統一轉換函數生成的反例條件:', negativeConditions);

    const negativeApiRequest: NegativeCaseRequest = {
      negative_conditions: negativeConditions,  // 使用轉換後的條件
      negative_ratio: negativeRatio,
      time_separation_days: timeSeparationDays,
      sampling_strategy: "time_separated"
    };

    console.log('發送到後端的反例請求:', negativeApiRequest);


    return this.fetchApi(`/two-stage/negative/${positiveTaskId}`, {
      method: 'POST',
      body: JSON.stringify(negativeApiRequest),
    });
  }

  // 兩階段搜索 - 步驟3：獲取合併結果
  async getCombinedResults(
    positiveTaskId: string, 
    negativeTaskId: string
  ): Promise<ApiResponse<SearchResultData>> {
    
    console.log('獲取合併結果:', { positiveTaskId, negativeTaskId });

    try {
      const result = await this.fetchApi(`/two-stage/combined/${positiveTaskId}/${negativeTaskId}`);
      console.log('合併結果API響應:', result);
      return result;
    } catch (error) {
      console.error('獲取合併結果失敗:', error);
      throw error;
    }
    
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
    request: SimpleSearchRequest,
    negativeRatio: number = 2.0,
    timeSeparationDays: number = 7,
    onProgress?: (stage: string, taskId?: string) => void,
    negativeRequest: SimpleSearchRequest,     // 新增：反例搜索請求
    negativeOperators: any,             // 新增：反例運算符
    negativeRangeValues: any,           // 新增：反例範圍值
    operators: any,                     // 正例運算符
    rangeValues: any                    // 正例範圍值
  ): Promise<SearchResultData> {
    
    try {
      // 階段1：執行正例搜索
      onProgress?.('正例搜索中...');
      const positiveResponse = await this.executePositiveSearch(request, operators, rangeValues);
      
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
        timeSeparationDays,
        negativeRequest,      // 傳遞反例搜索請求
        negativeOperators,    // 傳遞反例運算符
        negativeRangeValues   // 傳遞反例範圍值
      );
      
      if (!negativeResponse.success || !negativeResponse.data) {
        throw new Error('反例搜索啟動失敗');
      }
      
      const negativeTaskId = negativeResponse.data.task_id;
      onProgress?.('反例搜索中...', negativeTaskId);
      
      // 等待反例搜索完成
      // 暫時跳過反例狀態輪詢，使用延遲等待
      console.log('反例搜索已啟動，等待完成中...');
      onProgress?.('等待反例搜索完成...');
      await new Promise(resolve => setTimeout(resolve, 15000)); // 等待15秒

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
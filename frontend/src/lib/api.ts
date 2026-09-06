// frontend/src/lib/api.ts 
// API client for connecting to FastAPI backend - 兩階段搜索版本

import { ApiResponse, SearchResultData, SearchTemplate, SimpleSearchRequest, TaskInfo } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1';

// 後端搜索配置請求格式
interface SearchConfigRequest {
  name: string;
  timeframe: string;
  initial_conditions: FilterConditionRequest[];
  symbols?: string[];
  save_results?: boolean;
  searchMode?: string;
  // ✅ 修復：添加時間範圍字段
  startDate?: string | null;
  endDate?: string | null;
  // ✅ 新增：價格計算方式
  price_change_method?: string;
}

interface FilterConditionRequest {
  condition_type: string;
  parameter: string;
  operator: string;
  value: number | string | number[];
  description?: string;
}

// 反例搜索請求格式
interface NegativeCaseRequest {
  negative_conditions: unknown[];
  negative_ratio: number;
  enable_time_separation: boolean;
  time_separation_days: number;
  sampling_strategy: string;
  enable_random_sampling?: boolean;
}

interface SearchOperators {
  priceChange: string;
  volumeMultiplier: string;
  closingStrength: string;
  takerBuyRatio: string;
  pricePosition: string;
}

interface SearchRangeValues {
  priceChange: { min: number | null; max: number | null };
  volumeMultiplier: { min: number | null; max: number | null };
  closingStrength: { min: number | null; max: number | null };
  takerBuyRatio: { min: number | null; max: number | null };
  pricePosition: { min: number | null; max: number | null };
}

class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = `${API_BASE_URL}${API_PREFIX}`;
  }

  // Generic fetch wrapper with error handling
  private async fetchApi<T>(
    endpoint: string, 
    options: RequestInit = {},
    timeout: number = 30000  // 30秒超時
  ): Promise<ApiResponse<T>> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      clearTimeout(timeoutId);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error?.message || `HTTP ${response.status}: Request failed`);
      }

      return data;
    } catch (error: unknown) {
      clearTimeout(timeoutId);
      
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('請求超時，請檢查網路連接');
      }
      
      console.error('API Error:', error);
      throw error;
    }
  }

  // 轉換前端搜索請求為後端格式
  private convertToSearchConfig(
    request: SimpleSearchRequest,
    operators: SearchOperators,
    rangeValues: SearchRangeValues
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

    // 添加debug log來確認時間數據
    console.log('convertToSearchConfig 接收到的request:', request);
    console.log('  - startDate:', request.startDate);
    console.log('  - endDate:', request.endDate);
    console.log('  - priceChangeMethod:', request.priceChangeMethod);
    console.log('  - searchMode:', request.searchMode);

    return {
      name: request.name || `搜索_${new Date().toISOString().slice(0, 19)}`,
      timeframe: request.timeframe || "12h",
      initial_conditions: conditions,
      symbols: request.symbols,
      save_results: request.saveResults || false,
      searchMode: request.searchMode || 'research',
      // ✅ 修復：添加時間範圍字段
      startDate: request.startDate || null,
      endDate: request.endDate || null,
      // ✅ 新增：傳遞價格計算方式
      price_change_method: request.priceChangeMethod || "CLOSE_TO_CLOSE"
    };
  }

  // 原有的單一搜索方法（向後兼容）
  async executeSearch(
    request: SimpleSearchRequest,
    operators: SearchOperators,
    rangeValues: SearchRangeValues
  ): Promise<ApiResponse<TaskInfo>> {
    // 使用統一的轉換函數
    const searchConfig = this.convertToSearchConfig(request, operators, rangeValues);
    
    console.log('單一搜索配置:', searchConfig);

    // 後端 /two-stage/positive 直接接收 SearchConfigRequest
    const apiRequest = searchConfig;

    console.log('單一搜索API請求格式:', apiRequest);

    return this.fetchApi('/two-stage/positive', {
      method: 'POST',
      body: JSON.stringify(apiRequest),
    });
  }

  // 兩階段搜索 - 步驟1：執行正例搜索
  async executePositiveSearch(
    request: SimpleSearchRequest,
    operators: SearchOperators,
    rangeValues: SearchRangeValues
  ): Promise<ApiResponse<TaskInfo>> {
    const searchConfig = this.convertToSearchConfig(request, operators, rangeValues);

    console.log('執行正例搜索，配置:', searchConfig);
    
    // 後端 /two-stage/positive 直接接收 SearchConfigRequest
    const apiRequest = searchConfig;
    
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
    enableTimeSeparation: boolean = true,
    timeSeparationDays: number = 3,
    negativeRequest: SimpleSearchRequest,
    negativeOperators: SearchOperators,
    negativeRangeValues: SearchRangeValues,
    enableRandomSampling: boolean = true  // ===== 新增：隨機取樣開關 =====
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
      enable_time_separation: enableTimeSeparation,
      time_separation_days: timeSeparationDays,
      sampling_strategy: "time_separated",
      enable_random_sampling: enableRandomSampling  // ===== 新增：隨機取樣開關 =====
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
      const result = await this.fetchApi<SearchResultData>(
        `/two-stage/combined/${positiveTaskId}/${negativeTaskId}`
      );
      console.log('合併結果API響應:', result);
      return result;
    } catch (error) {
      console.error('獲取合併結果失敗:', error);
      throw error;
    }
    
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

  async getSystemConfig(): Promise<ApiResponse<unknown>> {
    return this.fetchApi('/config/system');
  }

  // Health check
  async healthCheck(): Promise<ApiResponse<{ status: string }>> {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      return await response.json();
    } catch (error) {
    void error;
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
  async previewSearch(config: unknown, symbolsLimit: number = 10): Promise<ApiResponse<unknown>> {
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
    enableTimeSeparation: boolean = true,
    timeSeparationDays: number = 3,
    onProgress?: (stage: string, taskId?: string) => void,
    negativeRequest: SimpleSearchRequest = request,
    negativeOperators: SearchOperators = {
      priceChange: '<=',
      volumeMultiplier: '<=',
      closingStrength: '<=',
      takerBuyRatio: '<=',
      pricePosition: '<=',
    },
    negativeRangeValues: SearchRangeValues = {
      priceChange: { min: null, max: null },
      volumeMultiplier: { min: null, max: null },
      closingStrength: { min: null, max: null },
      takerBuyRatio: { min: null, max: null },
      pricePosition: { min: null, max: null },
    },
    operators: SearchOperators = {
      priceChange: '>=',
      volumeMultiplier: '>=',
      closingStrength: '>=',
      takerBuyRatio: '>=',
      pricePosition: '>=',
    },
    rangeValues: SearchRangeValues = {
      priceChange: { min: null, max: null },
      volumeMultiplier: { min: null, max: null },
      closingStrength: { min: null, max: null },
      takerBuyRatio: { min: null, max: null },
      pricePosition: { min: null, max: null },
    },
    enableRandomSampling: boolean = true  // ===== 新增：隨機取樣開關 =====
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
        enableTimeSeparation,
        timeSeparationDays,
        negativeRequest,      // 傳遞反例搜索請求
        negativeOperators,    // 傳遞反例運算符
        negativeRangeValues,  // 傳遞反例範圍值
        enableRandomSampling  // ===== 新增：傳遞隨機取樣開關 =====
      );
      
      if (!negativeResponse.success || !negativeResponse.data) {
        throw new Error('反例搜索啟動失敗');
      }
      
      const negativeTaskId = negativeResponse.data.task_id;
      onProgress?.('反例搜索中...', negativeTaskId);

      // 等待反例搜索完成
      console.log('反例搜索已啟動，等待完成中...');
      onProgress?.('等待反例搜索完成...');
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

// ===== Phase 3.2: 信號密度分析 API =====

import type {
  SignalDensityRequest,
  SignalDensityResponse,
  TrainingWindowConfig,
  TrainingWindowPreview
} from './types';

/**
 * 計算信號密度分析
 *
 * @param request 信號密度分析請求
 * @returns 信號密度分析響應
 * @throws Error 當API調用失敗時
 *
 * @example
 * ```typescript
 * const result = await calculateSignalDensity({
 *   strategy_config: {
 *     data_source: "close",
 *     indicator_type: "ema",
 *     strategy_logic: "three_line",
 *     params: { ema_short: 5, ema_mid: 10, ema_long: 20 }
 *   },
 *   training_window: {
 *     reference_point: "TO",
 *     lookback_bars: 24,
 *     lookforward_bars: 0,
 *     mode: "relative"
 *   },
 *   positive_cases: ["case1", "case2"],
 *   negative_cases: ["case3", "case4"]
 * });
 *
 * console.log(`Separation: ${result.separation.toFixed(4)}`);
 * console.log(`P-value: ${result.p_value.toFixed(6)}`);
 * ```
 */
export async function calculateSignalDensity(
  request: SignalDensityRequest
): Promise<SignalDensityResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/signal-analysis/density`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(httpErrorMessage(error, `HTTP ${response.status}: 信號密度計算失敗`));
    }

    const data: SignalDensityResponse = await response.json();
    return data;

  } catch (error) {
    console.error('計算信號密度失敗:', error);
    throw error;
  }
}

/**
 * 預覽訓練窗口 (Debug用)
 *
 * 返回指定案例的訓練窗口K線數據範圍和數量,不執行實際分析。
 * 用於驗證訓練窗口配置是否正確。
 *
 * @param caseId 案例ID
 * @param windowConfig 訓練窗口配置
 * @returns 訓練窗口預覽信息
 * @throws Error 當API調用失敗時
 *
 * @example
 * ```typescript
 * const preview = await previewTrainingWindow("BTCUSDT_1736942400_1", {
 *   reference_point: "TO",
 *   lookback_bars: 24,
 *   lookforward_bars: 0,
 *   mode: "relative"
 * });
 *
 * console.log(`Actual bars: ${preview.actual_bars}`);
 * console.log(`Time range: ${preview.timestamp_range.start} - ${preview.timestamp_range.end}`);
 * ```
 */
export async function previewTrainingWindow(
  caseId: string,
  windowConfig: TrainingWindowConfig
): Promise<TrainingWindowPreview> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/signal-analysis/preview-window`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        case_id: caseId,
        window_config: windowConfig,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(httpErrorMessage(error, `HTTP ${response.status}: 預覽訓練窗口失敗`));
    }

    const data: TrainingWindowPreview = await response.json();
    return data;

  } catch (error) {
    console.error('預覽訓練窗口失敗:', error);
    throw error;
  }
}

/**
 * 評估策略質量
 *
 * 根據separation, p_value, cohens_d判斷策略質量
 *
 * @param result 信號密度分析結果
 * @returns 策略質量評級 "excellent" | "good" | "weak"
 */
export function evaluateStrategyQuality(
  result: SignalDensityResponse
): "excellent" | "good" | "weak" {
  const { separation, p_value, cohens_d } = result;

  // 優秀策略
  if (separation > 0.3 && p_value < 0.05 && cohens_d > 0.5) {
    return "excellent";
  }

  // 中等策略
  if (separation > 0.2 && p_value < 0.10) {
    return "good";
  }

  // 較弱策略
  return "weak";
}

/**
 * 格式化信號密度分析結果為可讀字串
 *
 * @param result 信號密度分析結果
 * @returns 格式化的結果字串
 */
export function formatSignalDensityResult(
  result: SignalDensityResponse
): string {
  const quality = evaluateStrategyQuality(result);
  const qualityEmoji = quality === "excellent" ? "✅" : quality === "good" ? "⚠️" : "❌";

  return `
${qualityEmoji} 策略質量: ${quality === "excellent" ? "優秀" : quality === "good" ? "中等" : "較弱"}

核心指標:
  • Separation: ${result.separation.toFixed(4)} (${result.separation > 0 ? "正例較高" : "反例較高"})
  • P-value: ${result.p_value.toFixed(6)} (${result.p_value < 0.05 ? "統計顯著" : "不顯著"})
  • Cohen's d: ${result.cohens_d.toFixed(2)} (${result.cohens_d > 0.5 ? "中/大效果" : "小效果"})
  • 穩定性 CV: ${result.stability_cv.toFixed(3)} (${result.stability_cv < 0.3 ? "穩定" : "不穩定"})

信號密度:
  • 正例: ${(result.positive_avg_density * 100).toFixed(2)}% ± ${(result.positive_std * 100).toFixed(2)}% (n=${result.positive_sample_size})
  • 反例: ${(result.negative_avg_density * 100).toFixed(2)}% ± ${(result.negative_std * 100).toFixed(2)}% (n=${result.negative_sample_size})
  `.trim();
}
// ===== Phase 3.6: 優化結果展示UI API =====

import type {
  OptimizationResult,
  ImportanceAnalysisResponse,
  OptimizationHistoryResponse,
  ParamSpaceResponse,
  StabilityAnalysis,
  ComparisonResult
} from './types';

/**
 * 獲取優化任務結果
 */
export async function fetchOptimizationResult(
  taskId: string
): Promise<OptimizationResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/optimization/tasks/${taskId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(httpErrorMessage(error, `HTTP ${response.status}: 獲取優化結果失敗`));
    }

    const data: OptimizationResult = await response.json();
    return data;

  } catch (error) {
    console.error('獲取優化結果失敗:', error);
    throw error;
  }
}

/**
 * 獲取參數重要性分析
 */
export async function fetchParameterImportance(
  taskId: string
): Promise<ImportanceAnalysisResponse> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/analysis/importance`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(httpErrorMessage(error, `HTTP ${response.status}: 獲取參數重要性失敗`));
    }

    const data: ImportanceAnalysisResponse = await response.json();
    return data;

  } catch (error) {
    console.error('獲取參數重要性失敗:', error);
    throw error;
  }
}

/**
 * 獲取優化歷史數據
 */
export async function fetchOptimizationHistory(
  taskId: string
): Promise<OptimizationHistoryResponse> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/analysis/history`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(httpErrorMessage(error, `HTTP ${response.status}: 獲取優化歷史失敗`));
    }

    const data: OptimizationHistoryResponse = await response.json();
    return data;

  } catch (error) {
    console.error('獲取優化歷史失敗:', error);
    throw error;
  }
}

/**
 * 獲取參數空間探索數據
 */
export async function fetchParamSpace(
  taskId: string
): Promise<ParamSpaceResponse> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/analysis/param-space`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(httpErrorMessage(error, `HTTP ${response.status}: 獲取參數空間失敗`));
    }

    const data: ParamSpaceResponse = await response.json();
    return data;

  } catch (error) {
    console.error('獲取參數空間失敗:', error);
    throw error;
  }
}

/**
 * 獲取穩定性分析
 */
export async function fetchStabilityAnalysis(
  taskId: string
): Promise<StabilityAnalysis> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/analysis/stability`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(httpErrorMessage(error, `HTTP ${response.status}: 獲取穩定性分析失敗`));
    }

    const data: StabilityAnalysis = await response.json();
    return data;

  } catch (error) {
    console.error('獲取穩定性分析失敗:', error);
    throw error;
  }
}

/**
 * 對比多個優化結果
 */
export async function compareOptimizationResults(
  taskIds: string[]
): Promise<ComparisonResult> {
  // 數量驗證
  if (taskIds.length < 2 || taskIds.length > 5) {
    throw new Error('對比任務數量必須在2-5之間');
  }
  
  // ID 有效性驗證
  if (taskIds.some(id => !id || id.trim() === '')) {
    throw new Error('任務ID不能為空');
  }
  
  // 重複驗證
  if (new Set(taskIds).size !== taskIds.length) {
    throw new Error('任務ID不能重複');
  }

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/optimization/compare`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ task_ids: taskIds }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(httpErrorMessage(error, `HTTP ${response.status}: 對比優化結果失敗`));
    }

    const data: ComparisonResult = await response.json();
    return data;

  } catch (error) {
    console.error('對比優化結果失敗:', error);
    throw error;
  }
}

/**
 * 匯出試驗歷史CSV
 */
export async function exportTrialsCSV(taskId: string): Promise<Blob> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/export/csv`,
      {
        method: 'GET',
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: 匯出CSV失敗`);
    }

    const blob = await response.blob();
    return blob;

  } catch (error) {
    console.error('匯出CSV失敗:', error);
    throw error;
  }
}

/**
 * 匯出PDF報告（暫緩實作）
 */
export async function exportPdfReport(taskId: string): Promise<Blob> {
  void taskId;
  throw new Error('PDF報告匯出功能已暫緩至Phase 4實作');
}

// ============================================================
// GAP-3 事件型（B5.2）：匯入批 / 兩張表（後端 /api/v1/case/events*）
// ============================================================
import type {
  EventAnalyzeResponse, EventCsvMappingSubmission, EventImportDetail, EventImportListResponse,
  EventImportRejected, EventImportResponse,
  RandomControlCompareRequest, RandomControlCompareResult, RandomControlGenerateRequest,
} from './types';
import type { LookaheadDeclarationPayload, LookaheadDeclarationPreview } from './lookaheadDeclaration';
import { httpErrorMessage } from './httpError';

export class EventImportRejectedError extends Error {
  payload: EventImportRejected;
  status: number;
  constructor(status: number, payload: EventImportRejected) {
    super(payload.message);
    this.payload = payload;
    this.status = status;
  }
}

async function parseRejected(response: Response): Promise<never> {
  let payload: EventImportRejected = { kind: 'http_error', message: `HTTP ${response.status}`, failures: [] };
  try {
    const data = await response.json();
    const detail = data?.detail ?? data?.error?.message ?? data;
    if (detail && typeof detail === 'object' && 'message' in detail) payload = detail as EventImportRejected;
    else if (typeof detail === 'string') payload = { kind: 'http_error', message: detail, failures: [] };
  } catch {
    /* keep default */
  }
  throw new EventImportRejectedError(response.status, payload);
}

export async function listEventImports(): Promise<EventImportListResponse> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/case/events`);
  if (!response.ok) await parseRejected(response);
  return response.json();
}

/**
 * GAP-3 UX Task 3.1：刪除一整批事件（含其全部落檔產物）。
 *
 * 成功為 204 No Content ⇒ **不解析 body**。不存在之批 ⇒ 後端回 404，於此拋出。
 * 🔴 一次只收一個 `importId`——契約上不存在「刪除全部」之呼叫形狀。
 */
export async function deleteEventImport(importId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}${API_PREFIX}/case/events/${encodeURIComponent(importId)}`,
    { method: 'DELETE' },
  );
  if (!response.ok) await parseRejected(response);
}

export async function uploadEventImport(
  file: File,
  validateOnly: boolean,
  lookaheadDeclaration?: LookaheadDeclarationPayload | null,
): Promise<EventImportResponse> {
  const formData = new FormData();
  formData.append('file', file);
  // GAP-3 UX Task 1.9／1.11：答案窗宣告（逐 tf）；未宣告時不送此欄，由後端決定拒收或封鎖切分
  if (lookaheadDeclaration) formData.append('lookahead_declaration', JSON.stringify(lookaheadDeclaration));
  const response = await fetch(
    `${API_BASE_URL}${API_PREFIX}/case/import-events?validate_only=${validateOnly ? 'true' : 'false'}`,
    { method: 'POST', body: formData },
  );
  if (!response.ok) await parseRejected(response);
  return response.json();
}

/**
 * GAP-3 UX Task 1.5／1.6：CSV ＋ 欄名對映匯入（`POST /case/import-events/csv`）。
 *
 * 🔴 `column_mapping` 無預設（A-4′）；`mapping_confirmed_at` 即使用者勾選確認之時間，
 *    後端寫入 receipt 之 `mapping_provenance`（Task 1.6）。
 */
export async function uploadEventCsvMapping(
  file: File,
  submission: EventCsvMappingSubmission,
  lookaheadDeclaration?: LookaheadDeclarationPayload | null,
): Promise<EventImportResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('column_mapping', JSON.stringify(submission.columnMapping));
  if (submission.batchDefaults) formData.append('batch_defaults', JSON.stringify(submission.batchDefaults));
  if (lookaheadDeclaration) formData.append('lookahead_declaration', JSON.stringify(lookaheadDeclaration));
  formData.append('mapping_confirmed_at', submission.confirmedAt);
  if (submission.deriveEventId) formData.append('derive_event_id', 'true');
  const response = await fetch(
    `${API_BASE_URL}${API_PREFIX}/case/import-events/csv?validate_only=${submission.validateOnly ? 'true' : 'false'}`,
    { method: 'POST', body: formData },
  );
  if (!response.ok) await parseRejected(response);
  return response.json();
}

/**
 * GAP-3 UX Task 1.9′（R 重開 D-8）：`/search` 匯出端答案窗宣告框之**預填**資料。
 *
 * 🔴 預設值只是候選（registry 之揭露用途），**不是**深度導出——深度＝使用者宣告；
 *    唯一實作在後端 `preview_from_columns`（與匯入端 preview 同一函式），前端**禁**在 TS 重寫換算表。
 *    Phase 2 之 `/case/lookahead-depth`（由篩選條件導出下界）已退役。
 */
export async function fetchLookaheadDeclarationPreviewColumns(payload: {
  columns: string[];
  timeframes: string[];
}): Promise<LookaheadDeclarationPreview> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/case/lookahead-declaration/preview-columns`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) await parseRejected(response);
  return response.json();
}

/**
 * GAP-3 UX Task 1.9 ①：宣告 UI 之預填（逐 tf 預設值＝檔內最大可用 horizon）。
 *
 * 對映路徑須一併送 `column_mapping`／`batch_defaults`，否則後端看不到 `label_definition`
 * （含 `filters`），引用欄會整批看不見、預設值算錯。
 */
export async function fetchLookaheadDeclarationPreview(
  file: File,
  mappingContext?: { columnMapping?: Record<string, string> | null; batchDefaults?: Record<string, unknown> | null },
): Promise<LookaheadDeclarationPreview> {
  const formData = new FormData();
  formData.append('file', file);
  if (mappingContext?.columnMapping && Object.keys(mappingContext.columnMapping).length > 0) {
    formData.append('column_mapping', JSON.stringify(mappingContext.columnMapping));
  }
  if (mappingContext?.batchDefaults) formData.append('batch_defaults', JSON.stringify(mappingContext.batchDefaults));
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/case/import-events/lookahead-declaration`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) await parseRejected(response);
  return response.json();
}

export async function analyzeEventImport(
  importId: string,
  body: { horizons?: number[]; n_boot?: number; test_fraction?: number } = {},
): Promise<EventAnalyzeResponse> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/case/events/${encodeURIComponent(importId)}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) await parseRejected(response);
  return response.json();
}

/**
 * 事件批 detail。🔴 Task 7.6 起另含 `batch_facts`／`declaration_seeds`／`batch_fact_notes`
 * ——型別由 `EventImportDetail` 承載，不再就地寫 inline 形狀（inline 形狀不會有人同步）。
 */
export async function getEventImport(importId: string): Promise<EventImportDetail> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/case/events/${encodeURIComponent(importId)}`);
  if (!response.ok) await parseRejected(response);
  return response.json();
}

/**
 * `G3-D2` D5.3：觸發批 vs 隨機對照批之 prevalence 並排（規則身分閘四段）。
 *
 * 🔴 這支的存在本身是 R1 三家獨立命中之閉合：閘原本只有 service 方法、沒有取用路徑。
 */
export async function compareRandomControl(
  body: RandomControlCompareRequest,
): Promise<RandomControlCompareResult> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/case/events/compare-random-control`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) await parseRejected(response);
  return response.json();
}

/**
 * `G3-D2` D5.3：依既有觸發批產一批**隨機對照組**並落檔。
 *
 * 🔴 `random_control_spec` 只送**輸入**鍵（universe／strata／allocation／exclusion／
 *    label_rule／seed／n_requested／replacement）；收據鍵（n_drawn／per_stratum／
 *    sample_ids_digest…）由後端產生器填回——前端送這些鍵是把產出當輸入，
 *    後端會以 typed schema 收下並**覆寫**，不會有人發現值被無視。
 */
export async function createRandomControlBatch(
  body: RandomControlGenerateRequest,
): Promise<EventImportResponse> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/case/import-events/random-control`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) await parseRejected(response);
  return response.json();
}

// 🔴 **GAP-3 UX Task 7.7 ⑦：`eventT0MsToIcTimestamps` 已移除，不得復活。**
//
// 它把**原始 `t0` ÷1000** 當成 IC 主線的 `event_timestamps`。但 §D-3a 已裁定
// 每列 feature sample key 須為 receipt 之 `decision_at_ms`／`last_bar_open_ms`，
// **不是原始 t0** ⇒ `decision_offset_bars = k > 0` 時，這個映射會把特徵取樣點推到
// **決策時點之後**，與 `ic_feed.py` 的 `feature_cutoff_rule = max_close_ms_le_decision_at`
// 直接互斥——也就是說它會讓「決策當下看不到的資料」進到特徵裡。
//
// 現行做法：前端只送 `event_import_id` ＋ `event_label_spec`，映射由**後端**於分析時
// 依 receipt 產生（`ic_analysis_service._run_event_label_stages`）。
// 前端**不得**持有或傳送 `label_value`，也不得自算時間戳。

import type {
  ICScanCubeCharts,
  ICScanCubeManifest,
  ICScanCubeRowsPage,
} from './types';

// ══════════════════════════════════════════════════════════════════════════
// `SCANCUBE` — 掃描結果立方體
//
// 🔴 三個端點的錯誤碼語意各不相同，呼叫端**必須**分開處理，不得一律當成「沒資料」：
//    · 404 ＝ 找不到這個 task 的立方體
//    · 409 ＝ 該層 fail-closed 沒保存（detail 帶 reason 與 fits_hint）
//    · 200 + 空 rows ＝ 篩選後真的沒有
// ══════════════════════════════════════════════════════════════════════════

/** 該層未保存時由 409 轉成的例外；`info` 帶 reason／fits_hint 供畫面明講。 */
export class ScanCubeTierNotStored extends Error {
  constructor(public readonly info: Record<string, unknown>) {
    super(`scan cube tier not stored: ${String(info?.reason ?? 'unknown')}`);
    this.name = 'ScanCubeTierNotStored';
  }
}

async function _cubeFetch(path: string): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/ic/scan-cube/${path}`);
  if (response.status === 409) {
    const body = await response.json().catch(() => ({}));
    throw new ScanCubeTierNotStored((body?.detail ?? {}) as Record<string, unknown>);
  }
  if (!response.ok) await parseRejected(response);
  return response.json();
}

export async function getScanCubeManifest(taskId: string): Promise<ICScanCubeManifest> {
  return _cubeFetch(`${encodeURIComponent(taskId)}/manifest`) as Promise<ICScanCubeManifest>;
}

export async function getScanCubeRows(
  taskId: string,
  params: {
    k?: number[]; h?: number[]; feature?: string; metric?: string[];
    sort?: string; offset?: number; limit?: number;
  } = {},
): Promise<ICScanCubeRowsPage> {
  const qs = new URLSearchParams();
  // 🔴 陣列參數逐值 append（FastAPI 之 `Query(None)` list 形狀），不是 join(',')
  (params.k ?? []).forEach((v) => qs.append('k', String(v)));
  (params.h ?? []).forEach((v) => qs.append('h', String(v)));
  (params.metric ?? []).forEach((v) => qs.append('metric', v));
  if (params.feature) qs.append('feature', params.feature);
  if (params.sort) qs.append('sort', params.sort);
  qs.append('offset', String(params.offset ?? 0));
  qs.append('limit', String(params.limit ?? 100));
  return _cubeFetch(
    `${encodeURIComponent(taskId)}/rows?${qs.toString()}`,
  ) as Promise<ICScanCubeRowsPage>;
}

export async function getScanCubeCharts(
  taskId: string, k: number, h: number, feature: string,
): Promise<ICScanCubeCharts> {
  const qs = new URLSearchParams({ k: String(k), h: String(h), feature });
  return _cubeFetch(
    `${encodeURIComponent(taskId)}/charts?${qs.toString()}`,
  ) as Promise<ICScanCubeCharts>;
}

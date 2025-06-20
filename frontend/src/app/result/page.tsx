'use client';


import React, { useState } from 'react';
import { Search, Download, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';

// 定義類型接口 - 基於完整的 CSV 數據結構
interface CaseData {
  symbol: string;
  timestamp: string;
  trigger_idx: number;
  
  // 完整的 OHLCV 數據
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  price_change: number;
  
  // 市場和時間數據
  market_phase: string;
  timeframe: string;
  
  // 未來表現指標
  future1_close_return?: number;
  future2_close_return?: number;
  future4_close_return?: number;
  future6_close_return?: number;
  future24_close_return?: number;
  future48_close_return?: number;
  future_max_return?: number;
  future72_max_return?: number;
  future_max_drawdown?: number;
  future72_max_drawdown?: number;
  
  // 未來價格數據
  future24_close?: number;
  future24_low?: number;
  
  // 前期技術指標
  prior_volatility?: number;
  prior_range?: number;
  prior_abs_change_sum?: number;
  
  // 信號相關
  signal_type?: string;
  base_std?: number;
  
  // 時間範圍
  time_range: {
    start: string;
    end: string;
  };
}

interface SearchResultData {
  cases: CaseData[];
  summary: {
    total_cases: number;
    positive_cases: number;
    negative_cases: number;
    unique_symbols: number;
    time_range: {
      start: string;
      end: string;
    };
    market_phase_distribution: Record<string, number>;
  };
  sampling_quality: {
    time_separation_score: number;
    symbol_diversity_score: number;
    market_phase_balance: number;
    overall_quality_score: number;
    warnings: string[];
  };
  execution_time: number;
  cache_used: boolean;
}

interface TaskInfo {
  task_id: string;
  status: string;
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

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  timestamp: string;
}

export default function ResultsPage() {
  const [searchResults, setSearchResults] = useState<SearchResultData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  // 執行測試搜索
  const executeTestSearch = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // 創建測試搜索請求 - 使用更大的時間範圍
      const testRequest = {
        config: {
          name: "Frontend_Test_Search",
          description: "測試前端展示的搜索",
          timeframe: "4h",
          start_date: "2023-02-01",  // 擴大到整年
          end_date: "2023-12-31",    // 擴大到整年
          lookback_periods: 20,
          forward_periods: 10,
          sample_limit: 10,
          min_volume: 1000,
          exclude_new_listing_days: 7,
          initial_conditions: [{
            condition_type: "price",
            parameter: "price_change",
            operator: ">=",
            value: 0.03,  // 降低到 3% 增加找到案例的機會
            description: "價格漲幅大於3%"
          }],
          advanced_conditions: []
        },
        symbols: ["BTCUSDT"],
        save_results: false
      };

      console.log('Sending search request:', testRequest);

      // 執行搜索
      const executeResponse = await fetch('http://localhost:8000/api/v1/search/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(testRequest)
      });

      if (!executeResponse.ok) {
        const errorText = await executeResponse.text();
        throw new Error(`Search execution failed: ${executeResponse.status} - ${errorText}`);
      }

      const executeData: ApiResponse<TaskInfo> = await executeResponse.json();
      
      if (!executeData.success || !executeData.data) {
        throw new Error(`Failed to start search task: ${executeData.error?.message || 'Unknown error'}`);
      }

      const taskId = executeData.data.task_id;
      setSelectedTaskId(taskId);
      
      console.log('Search task started with ID:', taskId);
      
      // 等待搜索完成
      await waitForSearchCompletion(taskId);
      
    } catch (err) {
      console.error('Search execution error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  // 等待搜索完成
  const waitForSearchCompletion = async (taskId: string) => {
    const maxAttempts = 30; // 最多等待30次（約1分鐘）
    let attempts = 0;

    while (attempts < maxAttempts) {
      try {
        console.log(`Checking task status (attempt ${attempts + 1}/${maxAttempts})`);
        
        // 檢查任務狀態
        const statusResponse = await fetch(`http://localhost:8000/api/v1/search/task/${taskId}`);
        
        if (!statusResponse.ok) {
          throw new Error(`Failed to check task status: ${statusResponse.status}`);
        }

        const statusData: ApiResponse<TaskInfo> = await statusResponse.json();
        
        if (!statusData.success || !statusData.data) {
          throw new Error('Failed to get task status');
        }

        const task = statusData.data;
        console.log('Task status:', task.status);

        if (task.status === 'completed') {
          // 獲取結果
          await fetchSearchResults(taskId);
          return;
        } else if (task.status === 'failed') {
          throw new Error(task.error_message || 'Search failed');
        }

        // 等待2秒後重試
        await new Promise(resolve => setTimeout(resolve, 2000));
        attempts++;
        
      } catch (err) {
        console.error('Status check error:', err);
        throw err;
      }
    }
    
    throw new Error('Search timeout: Task did not complete within expected time');
  };

  // 獲取搜索結果
  const fetchSearchResults = async (taskId: string) => {
    try {
      console.log('Fetching search results for task:', taskId);
      
      const resultResponse = await fetch(`http://localhost:8000/api/v1/search/task/${taskId}/result`);
      
      if (!resultResponse.ok) {
        throw new Error(`Failed to fetch results: ${resultResponse.status}`);
      }

      const resultData: ApiResponse<SearchResultData> = await resultResponse.json();
      
      if (!resultData.success || !resultData.data) {
        throw new Error('Failed to get search results');
      }

      console.log('Search results received:', resultData.data);
      setSearchResults(resultData.data);
      
    } catch (err) {
      console.error('Results fetch error:', err);
      throw err;
    }
  };

  // 格式化數值顯示
  const formatNumber = (value: number | undefined | null, decimals: number = 4): string => {
    if (value === null || value === undefined) return 'N/A';
    return value.toFixed(decimals);
  };

  // 格式化百分比
  const formatPercentage = (value: number | undefined | null): string => {
    if (value === null || value === undefined) return 'N/A';
    return `${(value * 100).toFixed(2)}%`;
  };

  // 導出 CSV - 包含所有欄位
  const exportToCSV = () => {
    if (!searchResults || !searchResults.cases.length) return;

    const headers = [
      'Symbol', 'Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 
      'Price Change (%)', 'Market Phase', 'Timeframe', 'Signal Type',
      'Future 24h Return (%)', 'Future 48h Return (%)', 'Future 72h Max Return (%)', 
      'Future 72h Max Drawdown (%)', 'Future 24h Close', 'Future 24h Low',
      'Prior Volatility', 'Prior Range', 'Prior Abs Change Sum', 'Base Std'
    ];

    const csvContent = [
      headers.join(','),
      ...searchResults.cases.map(case_ => [
        case_.symbol,
        case_.timestamp,
        case_.open,
        case_.high,
        case_.low,
        case_.close,
        case_.volume,
        formatPercentage(case_.price_change),
        case_.market_phase,
        case_.timeframe || '4h',
        case_.signal_type || 'MOMENTUM',
        formatPercentage(case_.future24_close_return),
        formatPercentage(case_.future48_close_return),
        formatPercentage(case_.future72_max_return || case_.future_max_return),
        formatPercentage(case_.future72_max_drawdown || case_.future_max_drawdown),
        case_.future24_close,
        case_.future24_low,
        formatNumber(case_.prior_volatility),
        formatNumber(case_.prior_range),
        formatNumber(case_.prior_abs_change_sum),
        formatNumber(case_.base_std)
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `complete_search_results_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 頁面標題 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">搜索結果展示</h1>
          <p className="text-gray-600">查看和分析案例搜索的結果數據</p>
        </div>

        {/* 操作區域 */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">操作面板</h2>
            {searchResults && (
              <button
                onClick={exportToCSV}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                <Download className="w-4 h-4" />
                導出 CSV
              </button>
            )}
          </div>
          
          <button
            onClick={executeTestSearch}
            disabled={isLoading}
            className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <RefreshCw className="w-5 h-5 animate-spin" />
            ) : (
              <Search className="w-5 h-5" />
            )}
            {isLoading ? '搜索中...' : '執行測試搜索'}
          </button>

          {selectedTaskId && (
            <p className="mt-2 text-sm text-gray-600">
              任務 ID: {selectedTaskId}
            </p>
          )}
        </div>

        {/* 錯誤顯示 */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <h3 className="text-red-800 font-medium">錯誤</h3>
            </div>
            <p className="text-red-700 mt-1">{error}</p>
          </div>
        )}

        {/* 結果摘要 */}
        {searchResults && (
          <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <h2 className="text-xl font-semibold text-gray-900">搜索摘要</h2>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">{searchResults.summary.total_cases}</div>
                <div className="text-sm text-gray-600">總案例數</div>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">{searchResults.summary.unique_symbols}</div>
                <div className="text-sm text-gray-600">交易對數量</div>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">{searchResults.execution_time.toFixed(1)}s</div>
                <div className="text-sm text-gray-600">執行時間</div>
              </div>
              <div className="text-center p-4 bg-yellow-50 rounded-lg">
                <div className="text-2xl font-bold text-yellow-600">{(searchResults.sampling_quality.overall_quality_score * 100).toFixed(0)}%</div>
                <div className="text-sm text-gray-600">採樣品質</div>
              </div>
            </div>
          </div>
        )}

        {/* 數據表格 */}
        {searchResults && searchResults.cases.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">案例數據</h2>
              <p className="text-gray-600 text-sm">找到 {searchResults.cases.length} 個符合條件的案例</p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">交易對</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">時間</th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">開盤價</th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">最高價</th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">最低價</th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">收盤價</th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">成交量</th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">價格變化</th>
                    <th className="px-4 py-3 text-center text-sm font-medium text-gray-900">市場階段</th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">24h回報</th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">48h回報</th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">最大回報</th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">最大回撤</th>
                    <th className="px-4 py-3 text-center text-sm font-medium text-gray-900">信號類型</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {searchResults.cases.map((case_, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{case_.symbol}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{case_.timestamp}</td>
                      <td className="px-4 py-3 text-sm text-right text-gray-900">
                        ${typeof case_.open === 'number' ? case_.open.toLocaleString() : 'N/A'}
                      </td>
                      <td className="px-4 py-3 text-sm text-right text-gray-900">
                        ${typeof case_.high === 'number' ? case_.high.toLocaleString() : 'N/A'}
                      </td>
                      <td className="px-4 py-3 text-sm text-right text-gray-900">
                        ${typeof case_.low === 'number' ? case_.low.toLocaleString() : 'N/A'}
                      </td>
                      <td className="px-4 py-3 text-sm text-right text-gray-900">${case_.close.toLocaleString()}</td>
                      <td className="px-4 py-3 text-sm text-right text-gray-600">{case_.volume.toFixed(2)}</td>
                      <td className={`px-4 py-3 text-sm text-right font-medium ${case_.price_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatPercentage(case_.price_change)}
                      </td>
                      <td className="px-4 py-3 text-sm text-center">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          case_.market_phase === 'GREED' ? 'bg-red-100 text-red-800' :
                          case_.market_phase === 'FEAR' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {case_.market_phase}
                        </span>
                      </td>
                      <td className={`px-4 py-3 text-sm text-right font-medium ${
                        (case_.future24_close_return || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {formatPercentage(case_.future24_close_return)}
                      </td>
                      <td className={`px-4 py-3 text-sm text-right font-medium ${
                        (case_.future48_close_return || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {formatPercentage(case_.future48_close_return)}
                      </td>
                      <td className="px-4 py-3 text-sm text-right text-green-600 font-medium">
                        {formatPercentage(case_.future72_max_return || case_.future_max_return)}
                      </td>
                      <td className="px-4 py-3 text-sm text-right text-red-600 font-medium">
                        {formatPercentage(case_.future72_max_drawdown || case_.future_max_drawdown)}
                      </td>
                      <td className="px-4 py-3 text-sm text-center">
                        <span className="px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                          {case_.signal_type || 'MOMENTUM'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 無數據狀態 */}
        {!searchResults && !isLoading && !error && (
          <div className="bg-white rounded-lg shadow-sm border p-12 text-center">
            <Search className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">尚無搜索結果</h3>
            <p className="text-gray-600 mb-6">點擊上方的「執行測試搜索」按鈕開始搜索案例</p>
          </div>
        )}
      </div>
    </div>
  );
}
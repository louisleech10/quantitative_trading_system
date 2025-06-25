// frontend/src/app/result/page.tsx - 完整版本，解決語法錯誤

'use client';

import React, { useState } from 'react';
import { Search, Download, RefreshCw, AlertCircle, CheckCircle, ChevronDown, ChevronRight } from 'lucide-react';

// ===== 擴充現有的類型定義 =====
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
  
  // ===== 現有的未來表現指標 (保持不變) =====
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
  future24_close?: number;
  future24_low?: number;
  
  // ===== 新增：基礎觸發條件參數 =====
  closing_strength?: number;
  price_position?: number;
  volume_multiplier?: number;
  taker_buy_ratio?: number;
  
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
  
  // ===== 新增：時間描述參數 =====
  hour_of_day?: number;
  day_of_week?: number;
  
  // 時間範圍
  time_range: {
    start: string;
    end: string;
  };
}

// ===== 保持現有的其他類型定義不變 =====
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
  
  // ===== 新增：參數驗證報告 =====
  validation_report?: {
    total_rows: number;
    basic_trigger_params_count: number;
    future_return_params_count: number;
    future_drawdown_params_count: number;
    completion_rate: number;
    warnings: string[];
    errors: string[];
  };
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

// ===== 參數常數定義 =====
const BASIC_TRIGGER_PARAMETERS = [
  'price_change', 'closing_strength', 'price_position', 'volume_multiplier', 'taker_buy_ratio'
];

const FUTURE_RETURN_PARAMETERS = [
  'future_1bar_return', 'future_2bar_return', 'future_3bar_return', 'future_4bar_return',
  'future_5bar_return', 'future_6bar_return', 'future_7bar_return', 'future_8bar_return',
  'future_9bar_return', 'future_10bar_return', 'future_11bar_return', 'future_12bar_return'
];

const FUTURE_DRAWDOWN_PARAMETERS = [
  'future_1bar_max_drawdown', 'future_2bar_max_drawdown', 'future_3bar_max_drawdown', 'future_4bar_max_drawdown',
  'future_5bar_max_drawdown', 'future_6bar_max_drawdown', 'future_7bar_max_drawdown', 'future_8bar_max_drawdown',
  'future_9bar_max_drawdown', 'future_10bar_max_drawdown', 'future_11bar_max_drawdown', 'future_12bar_max_drawdown'
];

export default function ResultsPage() {
  const [searchResults, setSearchResults] = useState<SearchResultData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  
  // ===== 新增：表格展開狀態管理 =====
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    overview: true,      // 現有的總覽表格
    basicTrigger: false, // 新增的基礎觸發參數
    futureReturns: false, // 新增的未來收益參數
    futureDrawdowns: false, // 新增的未來回撤參數
    timeParams: false    // 新增的時間參數
  });

  // ===== 保持所有現有的搜索邏輯不變 =====
  const executeTestSearch = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // 創建測試搜索請求 - 保持原有邏輯
      const testRequest = {
        config: {
          name: "Frontend_Test_Search",
          description: "測試前端展示的搜索",
          timeframe: "12h",
          start_date: "2024-02-01",
          end_date: "2025-05-31",
          lookback_periods: 20,
          forward_periods: 10,
          sample_limit: 100,
          min_volume: 1000,
          exclude_new_listing_days: 7,
          initial_conditions: [{
            condition_type: "price",
            parameter: "price_change",
            operator: ">=",
            value: 0.03,
            description: "價格漲幅大於3%"
          }],
          advanced_conditions: []
        },
        symbols: ["BTCUSDT"],
        save_results: false
      };

      console.log('Sending search request:', testRequest);

      // 執行搜索 - 保持原有邏輯
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
      
      // 等待搜索完成 - 保持原有邏輯
      await waitForSearchCompletion(taskId);
      
    } catch (err) {
      console.error('Search execution error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
      setIsLoading(false);
    }
  };

  // ===== 保持所有現有的輔助函數不變 =====
  const waitForSearchCompletion = async (taskId: string): Promise<void> => {
    const maxAttempts = 60; // 最多等待5分鐘
    let attempts = 0;
    
    const pollStatus = async (): Promise<void> => {
      try {
        const statusResponse = await fetch(`http://localhost:8000/api/v1/search/status/${taskId}`);
        
        if (!statusResponse.ok) {
          throw new Error(`Failed to get task status: ${statusResponse.status}`);
        }
        
        const statusData: ApiResponse<TaskInfo> = await statusResponse.json();
        
        if (!statusData.success || !statusData.data) {
          throw new Error('Failed to get task status data');
        }
        
        const taskInfo = statusData.data;
        console.log('Task status:', taskInfo.status, 'Progress:', taskInfo.progress);
        
        if (taskInfo.status === 'completed') {
          await fetchResults(taskId);
          return;
        } else if (taskInfo.status === 'failed') {
          throw new Error(taskInfo.error_message || 'Search task failed');
        } else if (attempts >= maxAttempts) {
          throw new Error('Search timeout - task did not complete within expected time');
        }
        
        attempts++;
        setTimeout(pollStatus, 5000); // 等待5秒後再次檢查
        
      } catch (err) {
        console.error('Status polling error:', err);
        throw err;
      }
    };
    
    await pollStatus();
  };

  const fetchResults = async (taskId: string): Promise<void> => {
    try {
      const resultResponse = await fetch(`http://localhost:8000/api/v1/search/result/${taskId}`);
      
      if (!resultResponse.ok) {
        throw new Error(`Failed to fetch results: ${resultResponse.status}`);
      }

      const resultData: ApiResponse<SearchResultData> = await resultResponse.json();
      
      if (!resultData.success || !resultData.data) {
        throw new Error('Failed to get search results');
      }

      console.log('Search results received:', resultData.data);
      setSearchResults(resultData.data);
      setIsLoading(false);
      
    } catch (err) {
      console.error('Results fetch error:', err);
      throw err;
    }
  };

  // ===== 保持現有的格式化函數，新增一些擴充 =====
  const formatNumber = (value: number | undefined | null, decimals: number = 4): string => {
    if (value === null || value === undefined || isNaN(value)) return 'N/A';
    return value.toFixed(decimals);
  };

  const formatPercentage = (value: number | undefined | null): string => {
    if (value === null || value === undefined || isNaN(value)) return 'N/A';
    return `${(value * 100).toFixed(2)}%`;
  };

  const formatInteger = (value: number | undefined | null): string => {
    if (value === undefined || value === null || isNaN(value)) return 'N/A';
    return Math.round(value).toString();
  };

  // ===== 擴充的CSV導出功能 =====
  const exportToCSV = () => {
    if (!searchResults || !searchResults.cases.length) return;

    // 擴充的CSV標題 - 包含所有20個新參數
    const headers = [
      // 基本資訊
      'Symbol', 'Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Price Change (%)', 'Market Phase', 'Timeframe',
      // 基礎觸發條件參數 (5個)
      'Closing Strength', 'Price Position', 'Volume Multiplier', 'Taker Buy Ratio',
      // 未來收益參數 (12個)
      'Future 1Bar Return (%)', 'Future 2Bar Return (%)', 'Future 3Bar Return (%)', 'Future 4Bar Return (%)',
      'Future 5Bar Return (%)', 'Future 6Bar Return (%)', 'Future 7Bar Return (%)', 'Future 8Bar Return (%)',
      'Future 9Bar Return (%)', 'Future 10Bar Return (%)', 'Future 11Bar Return (%)', 'Future 12Bar Return (%)',
      // 未來回撤參數 (12個)  
      'Future 1Bar Drawdown (%)', 'Future 2Bar Drawdown (%)', 'Future 3Bar Drawdown (%)', 'Future 4Bar Drawdown (%)',
      'Future 5Bar Drawdown (%)', 'Future 6Bar Drawdown (%)', 'Future 7Bar Drawdown (%)', 'Future 8Bar Drawdown (%)',
      'Future 9Bar Drawdown (%)', 'Future 10Bar Drawdown (%)', 'Future 11Bar Drawdown (%)', 'Future 12Bar Drawdown (%)',
      // 時間描述參數
      'Hour Of Day', 'Day Of Week',
      // 向後兼容參數
      'Future 24h Return (%)', 'Future 48h Return (%)', 'Future 72h Max Return (%)', 
      'Future 72h Max Drawdown (%)', 'Future 24h Close', 'Future 24h Low'
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
        case_.timeframe || 'N/A',
        // 基礎觸發條件參數
        formatNumber(case_.closing_strength),
        formatNumber(case_.price_position),
        formatNumber(case_.volume_multiplier),
        formatNumber(case_.taker_buy_ratio),
        // 未來收益參數
        formatPercentage(case_.future_1bar_return),
        formatPercentage(case_.future_2bar_return),
        formatPercentage(case_.future_3bar_return),
        formatPercentage(case_.future_4bar_return),
        formatPercentage(case_.future_5bar_return),
        formatPercentage(case_.future_6bar_return),
        formatPercentage(case_.future_7bar_return),
        formatPercentage(case_.future_8bar_return),
        formatPercentage(case_.future_9bar_return),
        formatPercentage(case_.future_10bar_return),
        formatPercentage(case_.future_11bar_return),
        formatPercentage(case_.future_12bar_return),
        // 未來回撤參數
        formatPercentage(case_.future_1bar_max_drawdown),
        formatPercentage(case_.future_2bar_max_drawdown),
        formatPercentage(case_.future_3bar_max_drawdown),
        formatPercentage(case_.future_4bar_max_drawdown),
        formatPercentage(case_.future_5bar_max_drawdown),
        formatPercentage(case_.future_6bar_max_drawdown),
        formatPercentage(case_.future_7bar_max_drawdown),
        formatPercentage(case_.future_8bar_max_drawdown),
        formatPercentage(case_.future_9bar_max_drawdown),
        formatPercentage(case_.future_10bar_max_drawdown),
        formatPercentage(case_.future_11bar_max_drawdown),
        formatPercentage(case_.future_12bar_max_drawdown),
        // 時間描述參數
        formatInteger(case_.hour_of_day),
        formatInteger(case_.day_of_week),
        // 向後兼容參數
        formatPercentage(case_.future24_close_return),
        formatPercentage(case_.future48_close_return),
        formatPercentage(case_.future72_max_return || case_.future_max_return),
        formatPercentage(case_.future72_max_drawdown || case_.future_max_drawdown),
        case_.future24_close || 'N/A',
        case_.future24_low || 'N/A'
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `enhanced_search_results_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  // ===== 新增：切換展開/收起功能 =====
  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-[100rem] mx-auto">
        {/* 頁面標題 - 更新為擴充版本 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">搜索結果展示</h1>
          <p className="text-gray-600">查看和分析案例搜索的結果數據（支援20個新參數）</p>
        </div>

        {/* ===== 保持現有的操作區域，更新導出功能 ===== */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">操作面板</h2>
            {searchResults && (
              <button
                onClick={exportToCSV}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                <Download className="w-4 h-4" />
                導出擴充CSV (含20個新參數)
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
            {isLoading ? '搜索中...' : '執行測試搜索 (BTCUSDT)'}
          </button>
        </div>

        {/* ===== 保持現有的錯誤顯示 ===== */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2 text-red-700">
              <AlertCircle className="w-5 h-5" />
              <span className="font-medium">錯誤：{error}</span>
            </div>
          </div>
        )}

        {/* ===== 新增：參數驗證報告 ===== */}
        {searchResults?.validation_report && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
            <h3 className="text-lg font-semibold text-blue-900 mb-4">參數計算狀態報告</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{searchResults.validation_report.basic_trigger_params_count}</div>
                <div className="text-sm text-blue-700">基礎觸發參數</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{searchResults.validation_report.future_return_params_count}</div>
                <div className="text-sm text-blue-700">未來收益參數</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{searchResults.validation_report.future_drawdown_params_count}</div>
                <div className="text-sm text-blue-700">未來回撤參數</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{searchResults.validation_report.completion_rate.toFixed(1)}%</div>
                <div className="text-sm text-blue-700">參數完整度</div>
              </div>
            </div>
            
            {searchResults.validation_report.warnings.length > 0 && (
              <div className="mt-4">
                <h4 className="font-medium text-blue-900 mb-2">警告信息：</h4>
                <ul className="text-sm text-blue-800 space-y-1">
                  {searchResults.validation_report.warnings.map((warning, idx) => (
                    <li key={idx}>• {warning}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* ===== 保持現有的搜索結果摘要 ===== */}
        {searchResults && (
          <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">搜索結果摘要</h3>
            <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">{searchResults.summary.total_cases}</div>
                <div className="text-sm text-gray-600">總案例數</div>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">{searchResults.summary.positive_cases}</div>
                <div className="text-sm text-gray-600">正例案例</div>
              </div>
              <div className="text-center p-4 bg-red-50 rounded-lg">
                <div className="text-2xl font-bold text-red-600">{searchResults.summary.negative_cases}</div>
                <div className="text-sm text-gray-600">負例案例</div>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">{searchResults.summary.unique_symbols}</div>
                <div className="text-sm text-gray-600">交易對數</div>
              </div>
              <div className="text-center p-4 bg-orange-50 rounded-lg">
                <div className="text-2xl font-bold text-orange-600">{searchResults.execution_time.toFixed(1)}s</div>
                <div className="text-sm text-gray-600">執行時間</div>
              </div>
              <div className="text-center p-4 bg-yellow-50 rounded-lg">
                <div className="text-2xl font-bold text-yellow-600">{(searchResults.sampling_quality.overall_quality_score * 100).toFixed(0)}%</div>
                <div className="text-sm text-gray-600">採樣品質</div>
              </div>
            </div>
          </div>
        )}

        {/* ===== 新增：可展開的參數分類表格 ===== */}
        {searchResults && searchResults.cases.length > 0 && (
          <div className="space-y-6">
            
            {/* 現有的總覽表格 - 保持原有設計 */}
            <div className="bg-white rounded-lg shadow-sm border">
              <div 
                className="p-4 border-b cursor-pointer hover:bg-gray-50 flex items-center justify-between"
                onClick={() => toggleSection('overview')}
              >
                <h3 className="text-lg font-semibold text-gray-900">總覽數據 (原有格式)</h3>
                {expandedSections.overview ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
              </div>
              
              {expandedSections.overview && (
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
                          <td className={`px-4 py-3 text-sm text-right font-medium ${case_.price_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {formatPercentage(case_.price_change)}
                          </td>
                          <td className="px-4 py-3 text-sm text-center">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              case_.market_phase === 'GREED' ? 'bg-red-100 text-red-800' :
                              case_.market_phase === 'FEAR' ? 'bg-blue-100 text-blue-800' :
                              case_.market_phase === 'EXTREME' ? 'bg-purple-100 text-purple-800' :
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
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* 基礎觸發條件參數表格 */}
            <div className="bg-white rounded-lg shadow-sm border">
              <div 
                className="p-4 border-b cursor-pointer hover:bg-gray-50 flex items-center justify-between"
                onClick={() => toggleSection('basicTrigger')}
              >
                <h3 className="text-lg font-semibold text-gray-900">基礎觸發條件參數 (5個)</h3>
                {expandedSections.basicTrigger ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
              </div>
              
              {expandedSections.basicTrigger && (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Symbol</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Timestamp</th>
                        <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">價格變化</th>
                        <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">收盤強度</th>
                        <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">價格位置</th>
                        <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">成交量倍數</th>
                        <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">主動買入比例</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {searchResults.cases.map((case_, index) => (
                        <tr key={index} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">{case_.symbol}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{case_.timestamp}</td>
                          <td className={`px-4 py-3 text-sm text-right font-medium ${case_.price_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {formatPercentage(case_.price_change)}
                          </td>
                          <td className="px-4 py-3 text-sm text-right text-gray-900">{formatNumber(case_.closing_strength)}</td>
                          <td className="px-4 py-3 text-sm text-right text-gray-900">{formatNumber(case_.price_position)}</td>
                          <td className="px-4 py-3 text-sm text-right text-gray-900">{formatNumber(case_.volume_multiplier)}</td>
                          <td className="px-4 py-3 text-sm text-right text-gray-900">{formatNumber(case_.taker_buy_ratio)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* 未來收益參數表格 (1-12根K線) */}
            <div className="bg-white rounded-lg shadow-sm border">
              <div 
                className="p-4 border-b cursor-pointer hover:bg-gray-50 flex items-center justify-between"
                onClick={() => toggleSection('futureReturns')}
              >
                <h3 className="text-lg font-semibold text-gray-900">未來收益參數 (1-12根K線)</h3>
                {expandedSections.futureReturns ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
              </div>
              
              {expandedSections.futureReturns && (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Symbol</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Timestamp</th>
                        {FUTURE_RETURN_PARAMETERS.map(param => (
                          <th key={param} className="px-4 py-3 text-right text-sm font-medium text-gray-900">
                            {param.replace('future_', '').replace('bar_return', 'Bar')}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {searchResults.cases.map((case_, index) => (
                        <tr key={index} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">{case_.symbol}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{case_.timestamp}</td>
                          {FUTURE_RETURN_PARAMETERS.map((param, paramIndex) => {
                            const value = case_[param as keyof CaseData] as number | undefined;
                            return (
                              <td key={paramIndex} className={`px-4 py-3 text-sm text-right font-medium ${
                                (value || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                              }`}>
                                {formatPercentage(value)}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* 未來回撤參數表格 (1-12根K線) */}
            <div className="bg-white rounded-lg shadow-sm border">
              <div 
                className="p-4 border-b cursor-pointer hover:bg-gray-50 flex items-center justify-between"
                onClick={() => toggleSection('futureDrawdowns')}
              >
                <h3 className="text-lg font-semibold text-gray-900">未來回撤參數 (1-12根K線)</h3>
                {expandedSections.futureDrawdowns ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
              </div>
              
              {expandedSections.futureDrawdowns && (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Symbol</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Timestamp</th>
                        {FUTURE_DRAWDOWN_PARAMETERS.map(param => (
                          <th key={param} className="px-4 py-3 text-right text-sm font-medium text-gray-900">
                            {param.replace('future_', '').replace('bar_max_drawdown', 'Bar')}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {searchResults.cases.map((case_, index) => (
                        <tr key={index} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">{case_.symbol}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{case_.timestamp}</td>
                          {FUTURE_DRAWDOWN_PARAMETERS.map((param, paramIndex) => {
                            const value = case_[param as keyof CaseData] as number | undefined;
                            return (
                              <td key={paramIndex} className="px-4 py-3 text-sm text-right text-red-600 font-medium">
                                {formatPercentage(value)}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* 時間和市場描述參數表格 */}
            <div className="bg-white rounded-lg shadow-sm border">
              <div 
                className="p-4 border-b cursor-pointer hover:bg-gray-50 flex items-center justify-between"
                onClick={() => toggleSection('timeParams')}
              >
                <h3 className="text-lg font-semibold text-gray-900">時間和市場描述參數</h3>
                {expandedSections.timeParams ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
              </div>
              
              {expandedSections.timeParams && (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Symbol</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Timestamp</th>
                        <th className="px-4 py-3 text-center text-sm font-medium text-gray-900">時間框架</th>
                        <th className="px-4 py-3 text-center text-sm font-medium text-gray-900">小時 (0-23)</th>
                        <th className="px-4 py-3 text-center text-sm font-medium text-gray-900">星期 (1-7)</th>
                        <th className="px-4 py-3 text-center text-sm font-medium text-gray-900">市場階段</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {searchResults.cases.map((case_, index) => (
                        <tr key={index} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">{case_.symbol}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{case_.timestamp}</td>
                          <td className="px-4 py-3 text-sm text-center text-gray-900">{case_.timeframe || 'N/A'}</td>
                          <td className="px-4 py-3 text-sm text-center text-gray-900">{formatInteger(case_.hour_of_day)}</td>
                          <td className="px-4 py-3 text-sm text-center text-gray-900">{formatInteger(case_.day_of_week)}</td>
                          <td className="px-4 py-3 text-sm text-center">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              case_.market_phase === 'GREED' ? 'bg-red-100 text-red-800' :
                              case_.market_phase === 'FEAR' ? 'bg-blue-100 text-blue-800' :
                              case_.market_phase === 'EXTREME' ? 'bg-purple-100 text-purple-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {case_.market_phase || 'N/A'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

          </div>
        )}

        {/* ===== 保持現有的無數據狀態 ===== */}
        {!searchResults && !isLoading && !error && (
          <div className="bg-white rounded-lg shadow-sm border p-12 text-center">
            <Search className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">尚無搜索結果</h3>
            <p className="text-gray-600 mb-6">點擊上方的「執行測試搜索」按鈕開始搜索案例</p>
            <div className="text-sm text-gray-500">
              <p>新版本支援完整的20個參數：</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2 text-xs">
                <div>• 5個基礎觸發參數</div>
                <div>• 12個未來收益參數</div>
                <div>• 12個未來回撤參數</div>
                <div>• 時間和市場描述參數</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
'use client';

import { useState, useEffect } from 'react';
import { TestChart } from '@/components/charts/TestChart';

/**
 * 案例數據結構
 */
interface CaseRecord {
  case_id: string;
  symbol: string;
  timeframe: string;
  timestamp: number;
  positive_case: boolean;
  details?: {
    close?: number;
    volume?: number;
    timestamp_str?: string;
  };
}

/**
 * 案例列表API響應
 * 注意：後端直接返回數據，沒有 success/data/error 包裹層
 */
interface CaseListResponse {
  total: number;
  cases: CaseRecord[];
  positive_count: number;
  negative_count: number;
  symbols: string[];
  timeframes: string[];
}

/**
 * 案例類型選項
 */
type CaseTypeFilter = 'all' | 'positive' | 'negative';

/**
 * 生產環境圖表頁面
 *
 * 功能：
 * 1. 從案例列表加載可用數據
 * 2. Symbol選擇器
 * 3. 時間戳選擇器（根據選擇的symbol和案例類型過濾）
 * 4. 案例類型過濾器（全部/正例/反例）
 * 5. 圖表渲染
 */
export default function ChartPage() {
  // 狀態管理
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 案例數據
  const [caseList, setCaseList] = useState<CaseRecord[]>([]);
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);
  const [availableTimeframes, setAvailableTimeframes] = useState<string[]>([]);

  // 用戶選擇
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');
  const [selectedTimestamp, setSelectedTimestamp] = useState<number | null>(null);
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>('1h');
  const [caseTypeFilter, setCaseTypeFilter] = useState<CaseTypeFilter>('all');

  // 當前選擇案例的詳細信息
  const [currentCase, setCurrentCase] = useState<CaseRecord | null>(null);

  /**
   * 加載案例列表數據
   */
  useEffect(() => {
    const fetchCaseList = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch('http://localhost:8000/api/v1/case/list');

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result: CaseListResponse = await response.json();

        // 後端直接返回數據，無需檢查 success 字段
        // 設置案例數據
        setCaseList(result.cases);
        setAvailableSymbols(result.symbols);
        setAvailableTimeframes(result.timeframes);

        // 自動選擇第一個symbol
        if (result.symbols.length > 0) {
          setSelectedSymbol(result.symbols[0]);
        }

        // 自動選擇第一個timeframe（如果有）
        if (result.timeframes.length > 0) {
          setSelectedTimeframe(result.timeframes[0]);
        }

      } catch (err) {
        console.error('Failed to fetch case list:', err);
        setError(err instanceof Error ? err.message : '加載案例列表時發生錯誤');
      } finally {
        setLoading(false);
      }
    };

    fetchCaseList();
  }, []);

  /**
   * 根據當前選擇過濾可用的案例
   */
  const filteredCases = caseList.filter(c => {
    // 過濾symbol
    if (selectedSymbol && c.symbol !== selectedSymbol) {
      return false;
    }

    // 過濾案例類型
    if (caseTypeFilter === 'positive' && !c.positive_case) {
      return false;
    }
    if (caseTypeFilter === 'negative' && c.positive_case) {
      return false;
    }

    return true;
  });

  /**
   * 當symbol或案例類型改變時，重置timestamp選擇
   */
  useEffect(() => {
    if (filteredCases.length > 0) {
      // 自動選擇第一個可用的timestamp
      const firstCase = filteredCases[0];
      setSelectedTimestamp(firstCase.timestamp);
      setCurrentCase(firstCase);
    } else {
      setSelectedTimestamp(null);
      setCurrentCase(null);
    }
  }, [selectedSymbol, caseTypeFilter]);

  /**
   * 當timestamp選擇改變時，更新當前案例
   */
  useEffect(() => {
    if (selectedTimestamp !== null) {
      const foundCase = filteredCases.find(c => c.timestamp === selectedTimestamp);
      setCurrentCase(foundCase || null);
    }
  }, [selectedTimestamp, filteredCases]);

  /**
   * 格式化時間戳為可讀格式
   */
  const formatTimestamp = (timestamp: number): string => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('zh-TW', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  };

  /**
   * 渲染加載狀態
   */
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">加載案例數據中...</p>
        </div>
      </div>
    );
  }

  /**
   * 渲染錯誤狀態
   */
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <h2 className="text-red-800 text-lg font-semibold mb-2">加載失敗</h2>
          <p className="text-red-600">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            重新加載
          </button>
        </div>
      </div>
    );
  }

  /**
   * 渲染無數據狀態
   */
  if (caseList.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 max-w-md">
          <h2 className="text-yellow-800 text-lg font-semibold mb-2">暫無數據</h2>
          <p className="text-yellow-700">
            尚未導入任何案例數據。請先使用 Phase 1 功能導入案例CSV並下載K線數據。
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6">
      {/* 頁面標題 */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">圖表查看</h1>
        <p className="text-gray-600">選擇案例查看K線圖表</p>
      </div>

      {/* 控制面板 */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">

          {/* Symbol選擇器 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              交易對
            </label>
            <select
              value={selectedSymbol}
              onChange={(e) => setSelectedSymbol(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {availableSymbols.map(symbol => (
                <option key={symbol} value={symbol}>{symbol}</option>
              ))}
            </select>
          </div>

          {/* 案例類型過濾器 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              案例類型
            </label>
            <select
              value={caseTypeFilter}
              onChange={(e) => setCaseTypeFilter(e.target.value as CaseTypeFilter)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">全部</option>
              <option value="positive">正例</option>
              <option value="negative">反例</option>
            </select>
          </div>

          {/* 時間框架選擇器 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              時間框架
            </label>
            <select
              value={selectedTimeframe}
              onChange={(e) => setSelectedTimeframe(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {availableTimeframes.map(tf => (
                <option key={tf} value={tf}>{tf}</option>
              ))}
            </select>
          </div>

          {/* 時間戳選擇器 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              案例時間點 ({filteredCases.length} 個可用)
            </label>
            <select
              value={selectedTimestamp || ''}
              onChange={(e) => setSelectedTimestamp(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={filteredCases.length === 0}
            >
              {filteredCases.map(c => (
                <option key={c.case_id} value={c.timestamp}>
                  {formatTimestamp(c.timestamp)} {c.positive_case ? '✓' : '✗'}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* 當前案例信息 */}
        {currentCase && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-600">案例ID：</span>
                <span className="font-mono text-gray-800">{currentCase.case_id}</span>
              </div>
              <div>
                <span className="text-gray-600">類型：</span>
                <span className={`font-semibold ${currentCase.positive_case ? 'text-green-600' : 'text-red-600'}`}>
                  {currentCase.positive_case ? '正例 ✓' : '反例 ✗'}
                </span>
              </div>
              {currentCase.details?.close && (
                <div>
                  <span className="text-gray-600">收盤價：</span>
                  <span className="font-mono text-gray-800">{currentCase.details.close}</span>
                </div>
              )}
              {currentCase.details?.volume && (
                <div>
                  <span className="text-gray-600">成交量：</span>
                  <span className="font-mono text-gray-800">{currentCase.details.volume.toLocaleString()}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 圖表區域 */}
      {selectedTimestamp !== null ? (
        <div className="bg-white rounded-lg shadow-md p-6">
          <TestChart
            symbol={selectedSymbol}
            caseTimestamp={selectedTimestamp}
            timeframe={selectedTimeframe}
            maxBars={200}
          />
        </div>
      ) : (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-12 text-center">
          <p className="text-gray-600 text-lg">請選擇案例以查看圖表</p>
        </div>
      )}
    </div>
  );
}

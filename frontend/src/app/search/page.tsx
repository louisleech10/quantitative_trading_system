'use client';

import React, { useState } from 'react';
import { Search, RefreshCw, AlertCircle, HelpCircle, ChevronDown, ChevronRight } from 'lucide-react';

// 搜索請求接口 (符合您的 api.ts 設計)
interface SearchRequest {
  name: string;
  symbols: string[];
  timeframe: string;
  priceChange?: number | null;
  volumeMultiplier?: number | null;
  closingStrength?: number | null;
  takerBuyRatio?: number | null;
  pricePosition?: number | null;
  saveResults?: boolean;
}

// 運算符選項
const OPERATORS = [
  { value: '>=', label: '大於等於 (≥)' },
  { value: '<=', label: '小於等於 (≤)' },
  { value: '=', label: '等於 (=)' },
  { value: '>', label: '大於 (>)' },
  { value: '<', label: '小於 (<)' },
  { value: 'BETWEEN', label: '介於範圍' }
];

// 欄位說明
const FIELD_DESCRIPTIONS = {
  priceChange: '價格變化：當前收盤價相對於前一K線收盤價的變化百分比',
  volumeMultiplier: '成交量倍數：當前K線成交量相對於平均成交量的倍數',
  closingStrength: '收盤強度：收盤價在當根K線高低價範圍中的位置，1表示收在最高價',
  takerBuyRatio: '主動買入比例：主動買入成交量佔總成交量的比例',
  pricePosition: '價格位置：當前價格在近期價格範圍中的相對位置'
};

export default function SearchPage() {
  // 基礎狀態
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentStage, setCurrentStage] = useState<string>('');
  const [searchResults, setSearchResults] = useState<any>(null);
  
  // 搜索參數狀態
  const [searchParams, setSearchParams] = useState<SearchRequest>({
    name: '兩階段搜索測試',
    symbols: [],
    timeframe: '12h',
    priceChange: null,
    volumeMultiplier: null,
    closingStrength: null,
    takerBuyRatio: null,
    pricePosition: null,
    saveResults: false
  });

  // 運算符狀態
  const [operators, setOperators] = useState({
    priceChange: '>=',
    volumeMultiplier: '>=',
    closingStrength: '>=',
    takerBuyRatio: '>=',
    pricePosition: '>='
  });

  // 範圍值狀態 (用於 BETWEEN 運算符)
  const [rangeValues, setRangeValues] = useState({
    priceChange: { min: null as number | null, max: null as number | null },
    volumeMultiplier: { min: null as number | null, max: null as number | null },
    closingStrength: { min: null as number | null, max: null as number | null },
    takerBuyRatio: { min: null as number | null, max: null as number | null },
    pricePosition: { min: null as number | null, max: null as number | null }
  });

  // 時間日期和交易量限制狀態
  const [timeParams, setTimeParams] = useState({
    startDate: '',
    endDate: '',
    volumeMin: null as number | null,
    volumeMax: null as number | null
  });

  // 反例搜索參數
  const [negativeParams, setNegativeParams] = useState({
    enabled: true,
    ratio: 2.0,
    timeSeparationDays: 7,
    priceChange: null as number | null,
    volumeMultiplier: null as number | null,
    closingStrength: null as number | null,
    takerBuyRatio: null as number | null,
    pricePosition: null as number | null,
    customConditions: [] as any[]
  });

  // 反例運算符狀態
  const [negativeOperators, setNegativeOperators] = useState({
    priceChange: '<=',
    volumeMultiplier: '<=',
    closingStrength: '<=',
    takerBuyRatio: '<=',
    pricePosition: '<='
  });

  // UI 狀態
  const [expandedSections, setExpandedSections] = useState({
    positive: true,
    negative: false,
    results: false
  });

  // 切換展開狀態
  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // 執行兩階段搜索 - 修正為真實API調用
  const executeTwoStageSearch = async () => {
    try {
      setIsLoading(true);
      setError(null);
      setSearchResults(null);
      
      console.log('開始執行搜索...');
      console.log('搜索參數:', searchParams);
      console.log('時間參數:', timeParams);
      console.log('反例參數:', negativeParams);
      
      // 準備API請求格式
      const apiRequest = {
        config: {
          name: searchParams.name,
          timeframe: searchParams.timeframe,
          start_date: timeParams.startDate || null,
          end_date: timeParams.endDate || null,
          price_change_min: searchParams.priceChange || null,
          volume_multiplier_min: searchParams.volumeMultiplier || null,
          closing_strength_min: searchParams.closingStrength || null,
          taker_buy_ratio_min: searchParams.takerBuyRatio || null,
          price_position_min: searchParams.pricePosition || null,
          volume_min: timeParams.volumeMin || null,
          volume_max: timeParams.volumeMax || null,
          symbols: searchParams.symbols,
          save_results: searchParams.saveResults || false
        }
      };

      console.log('發送API請求:', apiRequest);
      
      // 調用真實後端API
      setCurrentStage('正例搜索中...');
      const response = await fetch('http://localhost:8000/api/v1/search/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(apiRequest)
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`搜索執行失敗: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      
      if (!data.success || !data.data) {
        throw new Error(`搜索任務啟動失敗: ${data.error?.message || '未知錯誤'}`);
      }

      const taskId = data.data.task_id;
      console.log('搜索任務啟動成功，任務ID:', taskId);
      
      // 等待搜索完成
      setCurrentStage('等待搜索完成...');
      await waitForTaskCompletion(taskId);
      
    } catch (err) {
      console.error('階段搜索失敗:', err);
      setError(err instanceof Error ? err.message : '搜索執行失敗');
    } finally {
      setIsLoading(false);
    }
  };

  // 等待任務完成
  const waitForTaskCompletion = async (taskId: string) => {
    const maxAttempts = 30;
    
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        console.log(`檢查任務狀態 (${attempt}/${maxAttempts}): ${taskId}`);
        
        const statusResponse = await fetch(`http://localhost:8000/api/v1/search/task/${taskId}`);
        
        if (!statusResponse.ok) {
          throw new Error(`狀態查詢失敗: ${statusResponse.status}`);
        }
        
        const statusData = await statusResponse.json();
        
        if (!statusData.success || !statusData.data) {
          throw new Error(`狀態查詢失敗: ${statusData.error?.message || '未知錯誤'}`);
        }
        
        const status = statusData.data.status.toUpperCase();
        console.log(`任務狀態: ${statusData.data.status} (標準化: ${status})`);
        
        if (status === 'COMPLETED') {
          setCurrentStage('獲取搜索結果...');
          const resultResponse = await fetch(`http://localhost:8000/api/v1/search/task/${taskId}/result`);
          
          if (!resultResponse.ok) {
            throw new Error(`結果獲取失敗: ${resultResponse.status}`);
          }
          
          const resultData = await resultResponse.json();
          
          if (!resultData.success || !resultData.data) {
            throw new Error(`結果獲取失敗: ${resultData.error?.message || '未知錯誤'}`);
          }
          
          setSearchResults(resultData.data);
          setCurrentStage(`搜索完成！找到 ${resultData.data.summary.total_cases} 個案例`);
          return;
          
        } else if (status === 'FAILED' || status === 'ERROR') {
          throw new Error(`搜索任務失敗: ${statusData.data.message}`);
        }
        
        await new Promise(resolve => setTimeout(resolve, 1000));
        
      } catch (err) {
        console.error(`任務狀態檢查錯誤 (嘗試 ${attempt}):`, err);
        
        if (attempt === maxAttempts) {
          throw new Error(`任務狀態檢查超時: ${err instanceof Error ? err.message : '未知錯誤'}`);
        }
      }
    }
  };

  // 渲染正例欄位輸入框
  const renderFieldInput = (fieldKey: keyof SearchRequest, label: string, placeholder: string) => {
    const operator = operators[fieldKey as keyof typeof operators];
    const fieldValue = searchParams[fieldKey] as number | null;
    const range = rangeValues[fieldKey as keyof typeof rangeValues];

    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <label className="block text-sm font-medium text-gray-900">
            {label}
          </label>
          <div className="group relative">
            <HelpCircle className="w-4 h-4 text-gray-500 cursor-help" />
            <div className="absolute left-0 top-6 hidden group-hover:block bg-gray-800 text-white text-xs rounded px-3 py-2 z-10 w-72 shadow-lg">
              {FIELD_DESCRIPTIONS[fieldKey as keyof typeof FIELD_DESCRIPTIONS]}
            </div>
          </div>
        </div>
        
        <div className="grid grid-cols-3 gap-2">
          {/* 運算符選擇 */}
          <select
            value={operator}
            onChange={(e) => setOperators(prev => ({
              ...prev,
              [fieldKey]: e.target.value
            }))}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm text-gray-900"
          >
            {OPERATORS.map(op => (
              <option key={op.value} value={op.value}>{op.label}</option>
            ))}
          </select>
          
          {/* 數值輸入 */}
          {operator === 'BETWEEN' ? (
            <>
              <input
                type="number"
                value={range.min || ''}
                onChange={(e) => setRangeValues(prev => ({
                  ...prev,
                  [fieldKey]: { ...prev[fieldKey as keyof typeof rangeValues], min: e.target.value ? parseFloat(e.target.value) : null }
                }))}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                placeholder="最小值"
              />
              <input
                type="number"
                value={range.max || ''}
                onChange={(e) => setRangeValues(prev => ({
                  ...prev,
                  [fieldKey]: { ...prev[fieldKey as keyof typeof rangeValues], max: e.target.value ? parseFloat(e.target.value) : null }
                }))}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                placeholder="最大值"
              />
            </>
          ) : (
            <input
              type="number"
              value={fieldValue || ''}
              onChange={(e) => setSearchParams(prev => ({
                ...prev,
                [fieldKey]: e.target.value ? parseFloat(e.target.value) : null
              }))}
              className="col-span-2 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
              placeholder={placeholder}
            />
          )}
        </div>
      </div>
    );
  };

  // 渲染反例欄位輸入框
  const renderNegativeFieldInput = (fieldKey: keyof typeof negativeParams, label: string, placeholder: string) => {
    const operator = negativeOperators[fieldKey as keyof typeof negativeOperators];
    const fieldValue = negativeParams[fieldKey] as number | null;

    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <label className="block text-sm font-medium text-gray-900">
            {label} (反例條件)
          </label>
          <div className="group relative">
            <HelpCircle className="w-4 h-4 text-gray-500 cursor-help" />
            <div className="absolute left-0 top-6 hidden group-hover:block bg-gray-800 text-white text-xs rounded px-3 py-2 z-10 w-72 shadow-lg">
              反例條件：用於篩選不符合預期表現的案例。通常與正例條件相反。
            </div>
          </div>
        </div>
        
        <div className="grid grid-cols-3 gap-2">
          {/* 運算符選擇 */}
          <select
            value={operator}
            onChange={(e) => setNegativeOperators(prev => ({
              ...prev,
              [fieldKey]: e.target.value
            }))}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 text-sm text-gray-900"
          >
            {OPERATORS.map(op => (
              <option key={op.value} value={op.value}>{op.label}</option>
            ))}
          </select>
          
          {/* 數值輸入 */}
          <input
            type="number"
            value={fieldValue || ''}
            onChange={(e) => setNegativeParams(prev => ({
              ...prev,
              [fieldKey]: e.target.value ? parseFloat(e.target.value) : null
            }))}
            className="col-span-2 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 text-gray-900"
            placeholder={placeholder}
          />
        </div>
      </div>
    );
  };

  return (
    <div className="h-full overflow-auto">
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* 頁面標題 */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">階段案例搜索</h1>
          <p className="text-gray-700">
            設定正例搜索條件，系統將自動生成對應的反例數據集
          </p>
        </div>

        {/* 基本設定 */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">基本設定</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* 搜索名稱 */}
            <div>
              <label className="block text-sm font-medium text-gray-900 mb-2">
                搜索名稱
              </label>
              <input
                type="text"
                value={searchParams.name}
                onChange={(e) => setSearchParams(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                placeholder="例如: USDT突破策略搜索"
              />
            </div>
            
            {/* 交易對輸入 */}
            <div>
              <label className="block text-sm font-medium text-gray-900 mb-2">
                交易對 (支援多個，用逗號分隔)
              </label>
              <input
                type="text"
                value={searchParams.symbols.join(', ')}
                onChange={(e) => setSearchParams(prev => ({ 
                  ...prev, 
                  symbols: e.target.value.split(',').map(s => s.trim()).filter(s => s)
                }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                placeholder="例如: BTCUSDT, ETHUSDT 或 ALL_USDT (全部USDT) 或 ALL_STOCKS (全部股票)"
              />
              <p className="text-sm text-gray-600 mt-1">
                支援：加密貨幣 (USDT對), 股票代碼, 期貨合約, RWA 標的等
              </p>
            </div>
            
            {/* 時間框架 */}
            <div>
              <label className="block text-sm font-medium text-gray-900 mb-2">
                時間框架
              </label>
              <select
                value={searchParams.timeframe}
                onChange={(e) => setSearchParams(prev => ({ ...prev, timeframe: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
              >
                <option value="4h">4小時</option>
                <option value="12h">12小時</option>
                <option value="1d">1天</option>
              </select>
            </div>
          </div>
          
          {/* 時間日期區間 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
            <div>
              <label className="block text-sm font-medium text-gray-900 mb-2">
                開始日期
              </label>
              <input
                type="date"
                value={timeParams.startDate}
                onChange={(e) => setTimeParams(prev => ({ ...prev, startDate: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-900 mb-2">
                結束日期
              </label>
              <input
                type="date"
                value={timeParams.endDate}
                onChange={(e) => setTimeParams(prev => ({ ...prev, endDate: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
              />
            </div>
          </div>
          
          {/* 交易量限制 */}
          <div className="mt-6">
            <label className="block text-sm font-medium text-gray-900 mb-2">
              交易量限制 (USDT)
            </label>
            <div className="grid grid-cols-2 gap-4">
              <input
                type="number"
                value={timeParams.volumeMin || ''}
                onChange={(e) => setTimeParams(prev => ({ 
                  ...prev, 
                  volumeMin: e.target.value ? parseFloat(e.target.value) : null 
                }))}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                placeholder="最小交易量"
              />
              <input
                type="number"
                value={timeParams.volumeMax || ''}
                onChange={(e) => setTimeParams(prev => ({ 
                  ...prev, 
                  volumeMax: e.target.value ? parseFloat(e.target.value) : null 
                }))}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                placeholder="最大交易量"
              />
            </div>
          </div>
        </div>

        {/* 正例搜索條件 */}
        <div className="bg-white rounded-lg shadow-sm border">
          <div 
            className="p-4 border-b cursor-pointer hover:bg-gray-50 flex items-center justify-between"
            onClick={() => toggleSection('positive')}
          >
            <h3 className="text-lg font-semibold text-gray-900">正例搜索條件</h3>
            {expandedSections.positive ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          </div>
          
          {expandedSections.positive && (
            <div className="p-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {renderFieldInput('priceChange', '價格變化 (%)', '例如: 5.0')}
                {renderFieldInput('volumeMultiplier', '成交量倍數', '例如: 2.0')}
                {renderFieldInput('closingStrength', '收盤強度', '例如: 0.8')}
                {renderFieldInput('takerBuyRatio', '主動買入比例', '例如: 0.6')}
                {renderFieldInput('pricePosition', '價格位置', '例如: 0.7')}
              </div>
            </div>
          )}
        </div>

        {/* 反例搜索設定 */}
        <div className="bg-white rounded-lg shadow-sm border">
          <div 
            className="p-4 border-b cursor-pointer hover:bg-gray-50 flex items-center justify-between"
            onClick={() => toggleSection('negative')}
          >
            <h3 className="text-lg font-semibold text-gray-900">反例搜索設定</h3>
            {expandedSections.negative ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          </div>
          
          {expandedSections.negative && (
            <div className="p-6 space-y-6">
              {/* 基本反例設定 */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    反例比例
                  </label>
                  <input
                    type="number"
                    value={negativeParams.ratio}
                    onChange={(e) => setNegativeParams(prev => ({ 
                      ...prev, 
                      ratio: parseFloat(e.target.value) || 2.0 
                    }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 text-gray-900"
                    placeholder="2.0"
                    step="0.1"
                  />
                  <p className="text-sm text-gray-600 mt-1">反例數量 = 正例數量 × 比例</p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    時間分離天數
                  </label>
                  <input
                    type="number"
                    value={negativeParams.timeSeparationDays}
                    onChange={(e) => setNegativeParams(prev => ({ 
                      ...prev, 
                      timeSeparationDays: parseInt(e.target.value) || 7 
                    }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                    placeholder="7"
                  />
                  <p className="text-sm text-gray-600 mt-1">與正例時間的最小間隔</p>
                </div>
                
                <div className="flex items-center space-y-2">
                  <div>
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={negativeParams.enabled}
                        onChange={(e) => setNegativeParams(prev => ({ 
                          ...prev, 
                          enabled: e.target.checked 
                        }))}
                        className="mr-2 w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                      />
                      <span className="text-sm text-gray-900 font-medium">
                        啟用反例搜索
                      </span>
                    </label>
                    <p className="text-sm text-gray-600 mt-1">關閉則只搜索正例</p>
                  </div>
                </div>
              </div>
              
              {/* 反例篩選條件 */}
              {negativeParams.enabled && (
                <div>
                  <h4 className="text-md font-semibold text-gray-900 mb-4 border-b border-gray-200 pb-2">
                    反例篩選條件 (可選)
                  </h4>
                  <p className="text-sm text-gray-600 mb-4">
                    設定反例的具體條件，通常與正例條件相反。留空則由系統自動生成。
                  </p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {renderNegativeFieldInput('priceChange', '價格變化 (%)', '例如: -2.0')}
                    {renderNegativeFieldInput('volumeMultiplier', '成交量倍數', '例如: 0.5')}
                    {renderNegativeFieldInput('closingStrength', '收盤強度', '例如: 0.3')}
                    {renderNegativeFieldInput('takerBuyRatio', '主動買入比例', '例如: 0.4')}
                    {renderNegativeFieldInput('pricePosition', '價格位置', '例如: 0.2')}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* 執行按鈕 */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">執行搜索</h3>
              {currentStage && (
                <p className="text-sm text-blue-600 mt-1 font-medium">{currentStage}</p>
              )}
            </div>
            <button
              onClick={executeTwoStageSearch}
              disabled={isLoading}
              className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <RefreshCw className="w-5 h-5 animate-spin mr-2" />
              ) : (
                <Search className="w-5 h-5 mr-2" />
              )}
              {isLoading ? '搜索中...' : '開始階段搜索'}
            </button>
          </div>
        </div>

        {/* 錯誤顯示 */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center gap-2 text-red-700">
              <AlertCircle className="w-5 h-5" />
              <span className="font-medium">錯誤：{error}</span>
            </div>
          </div>
        )}

        {/* 搜索結果 */}
        {searchResults && (
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">搜索結果</h3>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
                <div className="text-sm text-gray-600">反例案例</div>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">{searchResults.summary.unique_symbols}</div>
                <div className="text-sm text-gray-600">交易對數</div>
              </div>
            </div>
            
            <div className="mt-4 text-sm text-gray-600">
              執行時間: {searchResults.execution_time} 秒
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
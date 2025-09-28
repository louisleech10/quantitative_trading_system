'use client';

import React, { useState } from 'react';
import { Search, RefreshCw, AlertCircle, HelpCircle, ChevronDown, ChevronRight, Download } from 'lucide-react';
import { apiClient } from '@/lib/api';



// 搜索請求接口 (符合您的 api.ts 設計)
interface SimpleSearchRequest {
  name: string;
  symbols: string[];
  timeframe: string;
  startDate?: string | null;     // 新增：開始日期
  endDate?: string | null;       // 新增：結束日期
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
  const [searchParams, setSearchParams] = useState<SimpleSearchRequest>({
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

  const [symbolsInput, setSymbolsInput] = useState('');

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

  // 反例範圍值狀態 (用於反例 BETWEEN 運算符)
  const [negativeRangeValues, setNegativeRangeValues] = useState({
    priceChange: { min: null as number | null, max: null as number | null }
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
      // 準備API條件數組
      const buildConditions = () => {
        const conditions = [];

        // 價格變化條件
        if (operators.priceChange === 'BETWEEN' && rangeValues.priceChange.min !== null && rangeValues.priceChange.max !== null) {
          conditions.push({
            condition_type: "price",
            parameter: "price_change",
            operator: "between",
            value: [rangeValues.priceChange.min / 100, rangeValues.priceChange.max / 100], // 轉換為小數
            description: `價格變化介於 ${rangeValues.priceChange.min}% 到 ${rangeValues.priceChange.max}%`
          });
        } else if (searchParams.priceChange !== null) {
          conditions.push({
            condition_type: "price",
            parameter: "price_change",
            operator: operators.priceChange,
            value: searchParams.priceChange / 100, // 轉換為小數
            description: `價格變化 ${operators.priceChange} ${searchParams.priceChange}%`
          });
        }

        // 成交量倍數條件
        if (operators.volumeMultiplier === 'BETWEEN' && rangeValues.volumeMultiplier.min !== null && rangeValues.volumeMultiplier.max !== null) {
          conditions.push({
            condition_type: "volume",
            parameter: "volume_multiplier",
            operator: "between",
            value: [rangeValues.volumeMultiplier.min, rangeValues.volumeMultiplier.max],
            description: `成交量倍數介於 ${rangeValues.volumeMultiplier.min} 到 ${rangeValues.volumeMultiplier.max}`
          });
        } else if (searchParams.volumeMultiplier !== null) {
          conditions.push({
            condition_type: "volume",
            parameter: "volume_multiplier",
            operator: operators.volumeMultiplier,
            value: searchParams.volumeMultiplier,
            description: `成交量倍數 ${operators.volumeMultiplier} ${searchParams.volumeMultiplier}`
          });
        }

        // 收盤強度條件
        if (operators.closingStrength === 'BETWEEN' && rangeValues.closingStrength.min !== null && rangeValues.closingStrength.max !== null) {
          conditions.push({
            condition_type: "price",
            parameter: "closing_strength",
            operator: "between",
            value: [rangeValues.closingStrength.min, rangeValues.closingStrength.max],
            description: `收盤強度介於 ${rangeValues.closingStrength.min} 到 ${rangeValues.closingStrength.max}`
          });
        } else if (searchParams.closingStrength !== null) {
          conditions.push({
            condition_type: "price",
            parameter: "closing_strength",
            operator: operators.closingStrength,
            value: searchParams.closingStrength,
            description: `收盤強度 ${operators.closingStrength} ${searchParams.closingStrength}`
          });
        }

        // 主動買入比例條件
        if (operators.takerBuyRatio === 'BETWEEN' && rangeValues.takerBuyRatio.min !== null && rangeValues.takerBuyRatio.max !== null) {
          conditions.push({
            condition_type: "volume", 
            parameter: "taker_buy_ratio",
            operator: "between",
            value: [rangeValues.takerBuyRatio.min, rangeValues.takerBuyRatio.max],
            description: `主動買入比例介於 ${rangeValues.takerBuyRatio.min} 到 ${rangeValues.takerBuyRatio.max}`
          });
        } else if (searchParams.takerBuyRatio !== null) {
          conditions.push({
            condition_type: "volume",
            parameter: "taker_buy_ratio", 
            operator: operators.takerBuyRatio,
            value: searchParams.takerBuyRatio,
            description: `主動買入比例 ${operators.takerBuyRatio} ${searchParams.takerBuyRatio}`
          });
        }

        // 價格位置條件
        if (operators.pricePosition === 'BETWEEN' && rangeValues.pricePosition.min !== null && rangeValues.pricePosition.max !== null) {
          conditions.push({
            condition_type: "price",
            parameter: "price_position",
            operator: "between", 
            value: [rangeValues.pricePosition.min, rangeValues.pricePosition.max],
            description: `價格位置介於 ${rangeValues.pricePosition.min} 到 ${rangeValues.pricePosition.max}`
          });
        } else if (searchParams.pricePosition !== null) {
          conditions.push({
            condition_type: "price",
            parameter: "price_position",
            operator: operators.pricePosition,
            value: searchParams.pricePosition,
            description: `價格位置 ${operators.pricePosition} ${searchParams.pricePosition}`
          });
        }

        return conditions;
      };

      // 檢查是否有設定搜索條件
      const hasConditions = buildConditions().length > 0;

      // 如果有條件，必須提供必要參數
      if (hasConditions) {
        if (searchParams.symbols.length === 0) {
          setError('設定搜索條件時必須選擇至少一個交易對');
          return;
        }
        
        if (!timeParams.startDate || !timeParams.endDate) {
          setError('設定搜索條件時必須提供開始和結束日期');
          return;
        }
      }

      const apiRequest = {
        config: {
          name: searchParams.name,
          timeframe: searchParams.timeframe,
          start_date: timeParams.startDate || null,
          end_date: timeParams.endDate || null,
          initial_conditions: buildConditions(),
          min_volume: timeParams.volumeMin || 100000
        },
        symbols: searchParams.symbols,
        save_results: searchParams.saveResults || false
      };

      console.log('發送API請求:', apiRequest);
      
      if (negativeParams.enabled) {
        // 執行完整的兩階段搜索
        console.log('啟用反例搜索，執行兩階段搜索');
        
        // ✅ 新增：使用統一架構 - 構建反例搜索請求對象
        const negativeSearchRequest: SimpleSearchRequest = {
          name: '反例搜索',
          symbols: searchParams.symbols,  // 使用相同的交易對
          timeframe: searchParams.timeframe,  // 使用相同的時間框架
          priceChange: negativeParams.priceChange,
          volumeMultiplier: negativeParams.volumeMultiplier,
          closingStrength: negativeParams.closingStrength,
          takerBuyRatio: negativeParams.takerBuyRatio,
          pricePosition: negativeParams.pricePosition,
          saveResults: false
        };
        
        console.log('反例搜索請求對象:', negativeSearchRequest);
        console.log('反例運算符:', negativeOperators);
        console.log('反例範圍值:', negativeRangeValues);

        // ✅ 修改：API調用 - 注意參數順序已改變
        const result = await apiClient.executeTwoStageSearch(
          // 參數1：正例 SearchRequest 對象
          {
            name: apiRequest.config.name,
            timeframe: apiRequest.config.timeframe,
            startDate: apiRequest.config.start_date,
            endDate: apiRequest.config.end_date,
            priceChange: searchParams.priceChange,
            volumeMultiplier: searchParams.volumeMultiplier,
            takerBuyRatio: searchParams.takerBuyRatio,
            closingStrength: searchParams.closingStrength,
            symbols: apiRequest.symbols,
            saveResults: apiRequest.save_results
          },
          // 參數2：negativeRatio (number)
          negativeParams.ratio,
          // 參數3：timeSeparationDays (number)
          negativeParams.timeSeparationDays,
          // 參數4：onProgress (function)
          (stage: string, taskId?: string) => {
            setCurrentStage(`${stage}${taskId ? `, 任務ID: ${taskId}` : ''}`);
            console.log(`搜索階段: ${stage}${taskId ? `, 任務ID: ${taskId}` : ''}`);
          },
          // 參數5：negativeRequest (SearchRequest) - 🔥 新的統一架構
          negativeSearchRequest,
          // 參數6：negativeOperators (object) - 🔥 新的統一架構  
          negativeOperators,
          // 參數7：negativeRangeValues (object) - 🔥 新的統一架構
          negativeRangeValues,
          // 參數8：operators (object) - 正例運算符
          operators,
          // 參數9：rangeValues (object) - 正例範圍值
          rangeValues
        );

        // 直接設定搜索結果
        setSearchResults(result);
        console.log('兩階段搜索完成，結果:', result);
        return; // 提前返回，不執行下面的單一搜索邏輯
      
      } else {
        // 執行單一正例搜索（原有邏輯）
        console.log('未啟用反例搜索，執行單一正例搜索');
        setCurrentStage('正例搜索中...');
        
        const response = await apiClient.executeSearch(
          // 參數1：搜索請求對象（使用簡化的格式）
          {
            name: apiRequest.config.name,
            timeframe: apiRequest.config.timeframe,
            startDate: apiRequest.config.start_date,
            endDate: apiRequest.config.end_date,
            priceChange: searchParams.priceChange,
            volumeMultiplier: searchParams.volumeMultiplier,
            takerBuyRatio: searchParams.takerBuyRatio,
            closingStrength: searchParams.closingStrength,
            pricePosition: searchParams.pricePosition,  // 新增：確保包含所有欄位
            symbols: apiRequest.symbols,
            saveResults: apiRequest.save_results
          },
          // 參數2：operators - 正例運算符
          operators,
          // 參數3：rangeValues - 正例範圍值
          rangeValues
        );
        
        if (!response.success || !response.data) {
          throw new Error(`搜索任務啟動失敗: ${response.error?.message || '未知錯誤'}`);
        }
        
        const taskId = response.data.task_id;
        console.log('單一搜索任務啟動成功，任務ID:', taskId);
        
        // 等待搜索完成
        setCurrentStage('等待搜索完成...');
        await waitForTaskCompletion(taskId);
      }
      
      
    } catch (err) {
      console.error('階段搜索失敗:', err);
      
      // 分析錯誤類型並提供友善訊息
      let userFriendlyMessage = '';
      
      if (err.message.includes('未知錯誤') || err.message.includes('undefined')) {
        userFriendlyMessage = '在指定條件和時間範圍內未找到符合的案例。建議：放寬搜索條件或擴大時間範圍';
      } else if (err.message.includes('timeout')) {
        userFriendlyMessage = '搜索超時，可能是數據量過大或條件複雜。建議：縮小時間範圍或簡化搜索條件';
      } else if (err.message.includes('No cases found') || err.message.includes('沒有找到')) {
        userFriendlyMessage = '未找到符合條件的案例。建議：調整價格變化閾值，或擴大時間範圍';
      } else if (err.message.includes('422') || err.message.includes('參數驗證')) {
        userFriendlyMessage = '搜索參數有誤。請檢查：交易對格式、日期範圍是否正確';
      } else {
        userFriendlyMessage = `搜索失敗：${err.message}`;
      }
      
      setError(userFriendlyMessage);
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
          console.log('完整錯誤回應:', statusData);
          const errorMsg = statusData.data.message || statusData.data.error_message || statusData.message || '未知錯誤';
          throw new Error(`搜索任務失敗: ${errorMsg}`);
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

  // CSV導出函數
  const exportSearchResultsToCSV = () => {
    if (!searchResults || !searchResults.cases || searchResults.cases.length === 0) {
      alert('沒有搜索結果可以導出');
      return;
    }

    try {
      // CSV標題行 - 包含所有20個參數
      const headers = [
        // 基本資訊
        'Symbol', 'Timestamp', 'Trigger_Index', 'Open', 'High', 'Low', 'Close', 'Volume', 
        'Price_Change_%', 'Market_Phase', 'Timeframe',
        // 基礎觸發條件參數
        'Closing_Strength', 'Price_Position', 'Volume_Multiplier', 'Taker_Buy_Ratio',
        // 未來收益參數 (12個)
        'Future_1Bar_Return_%', 'Future_2Bar_Return_%', 'Future_3Bar_Return_%', 'Future_4Bar_Return_%',
        'Future_5Bar_Return_%', 'Future_6Bar_Return_%', 'Future_7Bar_Return_%', 'Future_8Bar_Return_%',
        'Future_9Bar_Return_%', 'Future_10Bar_Return_%', 'Future_11Bar_Return_%', 'Future_12Bar_Return_%',
        // 未來回撤參數 (12個)  
        'Future_1Bar_Drawdown_%', 'Future_2Bar_Drawdown_%', 'Future_3Bar_Drawdown_%', 'Future_4Bar_Drawdown_%',
        'Future_5Bar_Drawdown_%', 'Future_6Bar_Drawdown_%', 'Future_7Bar_Drawdown_%', 'Future_8Bar_Drawdown_%',
        'Future_9Bar_Drawdown_%', 'Future_10Bar_Drawdown_%', 'Future_11Bar_Drawdown_%', 'Future_12Bar_Drawdown_%',
        // 時間描述參數
        'Hour_Of_Day', 'Day_Of_Week',
        // 正反例標記
        'Positive_Case'
      ].join(',');

      // 格式化函數
      const formatNumber = (value: any, decimals: number = 4): string => {
        if (value === null || value === undefined || isNaN(value)) return '';
        return Number(value).toFixed(decimals);
      };

      const formatPercentage = (value: any): string => {
        if (value === null || value === undefined || isNaN(value)) return '';
        return (Number(value) * 100).toFixed(2);
      };

      // 生成CSV內容
      const csvRows = searchResults.cases.map(case_ => [
        // 基本資訊
        case_.symbol || '',
        case_.timestamp || '',
        case_.trigger_idx || '',
        formatNumber(case_.open),
        formatNumber(case_.high), 
        formatNumber(case_.low),
        formatNumber(case_.close),
        formatNumber(case_.volume),
        formatPercentage(case_.price_change),
        case_.market_phase || '',
        case_.timeframe || '',
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
        case_.hour_of_day || '',
        case_.day_of_week || '',
        // 正反例標記
        case_.positive_case !== undefined ? (case_.positive_case ? '1' : '0') : ''
      ].join(','));

      // 組合完整CSV內容
      const csvContent = [headers, ...csvRows].join('\n');

      // 創建並下載文件
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `case_search_results_${new Date().toISOString().slice(0, 10)}.csv`;
      link.click();
      window.URL.revokeObjectURL(url);

      console.log(`CSV導出成功：${searchResults.cases.length} 個案例`);
    } catch (error) {
      console.error('CSV導出失敗:', error);
      alert('CSV導出失敗，請查看控制台錯誤信息');
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
          {operator === 'BETWEEN' ? (
            <>
              <input
                type="number"
                value={negativeRangeValues[fieldKey]?.min || ''}
                onChange={(e) => setNegativeRangeValues(prev => ({
                  ...prev,
                  [fieldKey]: { 
                    ...prev[fieldKey], 
                    min: e.target.value ? parseFloat(e.target.value) : null 
                  }
                }))}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 text-gray-900"
                placeholder="最小值"
              />
              <input
                type="number"
                value={negativeRangeValues[fieldKey]?.max || ''}
                onChange={(e) => setNegativeRangeValues(prev => ({
                  ...prev,
                  [fieldKey]: { 
                    ...prev[fieldKey], 
                    max: e.target.value ? parseFloat(e.target.value) : null 
                  }
                }))}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 text-gray-900"
                placeholder="最大值"
              />
            </>
          ) : (
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
          )}
        </div>
      </div>
    );
  };

  React.useEffect(() => {
    setSymbolsInput(searchParams.symbols.join(', '));
  }, []);

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
              value={symbolsInput}
              onChange={(e) => {
                setSymbolsInput(e.target.value);
                const symbols = e.target.value.split(/[,，]/).map(s => s.trim()).filter(s => s);
                setSearchParams(prev => ({ ...prev, symbols }));
              }}
              onBlur={() => {
                setSymbolsInput(searchParams.symbols.join(', '));
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
              placeholder="例如: BTCUSDT, ETHUSDT 或 ETHUSDT，BNBUSDT"
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
          
          {/* 最小交易量 */}
          <div className="mt-6">
            <label className="block text-sm font-medium text-gray-900 mb-2">
              最小交易量 (USDT)
            </label>
            <input
              type="number"
              value={timeParams.volumeMin || ''}
              onChange={(e) => setTimeParams(prev => ({ 
                ...prev, 
                volumeMin: e.target.value ? parseFloat(e.target.value) : null 
              }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
              placeholder="留空 = 不限制，例如: 100000"
            />
            <p className="text-sm text-gray-600 mt-1">
              留空表示不對交易量設限制，輸入數值則過濾小於該值的案例
            </p>
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
            <div className="p-6">
              <div className="max-w-md">
                {renderFieldInput('priceChange', '價格變化 (%)', '例如: 5.0')}
              </div>
              
              <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-800">
                  <strong>說明：</strong>正例搜索只需設定價格變化條件，其他30個參數會自動計算並輸出到CSV中供您後續分析使用。
                </p>
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
                    step="1"
                    min="1"
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 text-gray-900"
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
                  
                  <div className="max-w-md">
                    {renderNegativeFieldInput('priceChange', '價格變化 (%)', '例如: -2.0')}
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

            {/* CSV 導出按鈕 */}
            <div className="mt-6 flex justify-center">
              <button
                onClick={exportSearchResultsToCSV}
                className="flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors"
              >
                <Download className="w-5 h-5" />
                導出完整CSV檔案 (含20個參數)
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
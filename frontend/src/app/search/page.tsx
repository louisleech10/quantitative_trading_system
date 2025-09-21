'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { Download, Trash2 } from 'lucide-react';

// 搜索參數介面定義
interface SearchParams {
  // 基礎設定
  timeframe: string;
  symbols: string[];
  startDate: string;
  endDate: string;
  
  // 價格條件
  priceChange: number | null;
  priceOperator: string;
  closingStrength: number | null;
  pricePosition: number | null;
  
  // 成交量條件
  volumeMultiplier: number | null;
  takerBuyRatio: number | null;
  
  // 正反例設定
  showPositiveCase: boolean;
  showNegativeCase: boolean;
  timeSeparationDays: number;
  positiveNegativeRatio: string;
  
  // 配置管理
  configName: string;
}

export default function SearchPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<any>(null);
  
  // 所有搜索參數的狀態管理
  const [searchParams, setSearchParams] = useState<SearchParams>({
    // 基礎設定 - 使用真實預設值
    timeframe: '12h',
    symbols: ['BTCUSDT'], // 真實預設：幣安BTCUSDT交易對
    startDate: '2024-06-01', // 真實預設：6個月前開始
    endDate: new Date().toISOString().split('T')[0], // 真實預設：今天結束
    
    // 價格條件 - 使用真實預設值
    priceChange: 1, // 真實預設：1%價格變化
    priceOperator: '>=',
    closingStrength: null, // 用戶未設定時為null
    pricePosition: null,
    
    // 成交量條件 - 使用真實預設值
    volumeMultiplier: 1.2, // 真實預設：1.2倍平均成交量
    takerBuyRatio: null,
    
    // 正反例設定 - 使用真實預設值
    showPositiveCase: true,
    showNegativeCase: false,
    timeSeparationDays: 7, // 真實預設：7天時間分離
    positiveNegativeRatio: '1:2', // 真實預設：1:2比例
    
    // 配置管理
    configName: ''
  });

  // 更新單個參數的輔助函數
  const updateParam = <K extends keyof SearchParams>(
    key: K, 
    value: SearchParams[K]
  ) => {
    setSearchParams(prev => ({
      ...prev,
      [key]: value
    }));
  };

  // 搜索執行函數 - 讀取真實UI數據
  const handleSearch = async () => {
    setIsLoading(true);
    try {
      const { apiClient } = await import('@/lib/api');
      
      // 構建真實的搜索請求 - 從UI狀態讀取
      const searchRequest = {
        name: searchParams.configName || 'UI_Search_Request',
        timeframe: searchParams.timeframe,
        priceChange: searchParams.priceChange, // 從UI讀取真實值
        volumeMultiplier: searchParams.volumeMultiplier, // 從UI讀取真實值
        closingStrength: searchParams.closingStrength, // 從UI讀取真實值
        takerBuyRatio: searchParams.takerBuyRatio, // 從UI讀取真實值
        symbols: searchParams.symbols,
        saveResults: false
      };
      
      console.log('UI搜索參數:', searchParams);
      console.log('發送搜索請求:', searchRequest);
      
      const result = await apiClient.executePositiveSearch(searchRequest);
      console.log('搜索結果:', result);
      
      setSearchResults(result);
    } catch (error) {
      console.error('搜索錯誤:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // 清除參數函數 - 重置為真實預設值
  const handleClearParams = () => {
    setSearchParams({
      timeframe: '12h',
      symbols: ['BTCUSDT'],
      startDate: '2024-06-01',
      endDate: new Date().toISOString().split('T')[0],
      priceChange: 1,
      priceOperator: '>=',
      closingStrength: null,
      pricePosition: null,
      volumeMultiplier: 1.2,
      takerBuyRatio: null,
      showPositiveCase: true,
      showNegativeCase: false,
      timeSeparationDays: 7,
      positiveNegativeRatio: '1:2',
      configName: ''
    });
    console.log('參數已重置為預設值');
  };

  const handleExportResults = () => {
    console.log('導出結果:', searchResults);
    // 真實導出邏輯將在後續實現
  };

  return (
    <div className="h-full overflow-auto">
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* 頁面標題 */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">案例搜索</h1>
          <p className="text-gray-600">
            設定搜索條件，找出符合特定模式的交易案例
          </p>
        </div>

        {/* 搜索條件區域 */}
        <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
          
          {/* 左側主要參數設定 */}
          <div className="xl:col-span-3 space-y-4">
            
            {/* 基礎設定 */}
            <Card title="基礎設定">
              <div className="space-y-3">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-800 mb-1">時間框架</label>
                    <select 
                      value={searchParams.timeframe}
                      onChange={(e) => updateParam('timeframe', e.target.value)}
                      className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                    >
                      <option value="1h">1小時</option>
                      <option value="4h">4小時</option>
                      <option value="12h">12小時</option>
                      <option value="1d">1天</option>
                    </select>
                  </div>
                  <div>
                    <div className="flex items-center space-x-1 mb-1">
                      <label className="text-xs font-medium text-gray-800">交易對</label>
                      <div className="group relative">
                        <div className="w-3 h-3 bg-gray-400 rounded-full text-white text-xs flex items-center justify-center cursor-help">?</div>
                        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 p-2 bg-gray-800 text-white text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity z-10">
                          <strong>交易對設定：</strong><br/>
                          • 單一交易對：BTCUSDT<br/>
                          • 多個交易對：BTCUSDT,ETHUSDT,BNBUSDT<br/>
                          • 全部USDT交易對：*USDT<br/>
                          • 前N大市值：TOP100, TOP50
                        </div>
                      </div>
                    </div>
                    <input 
                      type="text" 
                      value={searchParams.symbols[0] || ''}
                      onChange={(e) => {
                        const input = e.target.value.trim();
                        if (input === '*USDT' || input === 'TOP100' || input === 'TOP50') {
                          updateParam('symbols', [input]);
                        } else if (input.includes(',')) {
                          updateParam('symbols', input.split(',').map(s => s.trim()).filter(s => s));
                        } else {
                          updateParam('symbols', [input]);
                        }
                      }}
                      placeholder="BTCUSDT 或 *USDT 或 BTCUSDT,ETHUSDT" 
                      className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-800 mb-1">開始日期</label>
                    <input 
                      type="date" 
                      value={searchParams.startDate}
                      onChange={(e) => updateParam('startDate', e.target.value)}
                      className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-800 mb-1">結束日期</label>
                    <input 
                      type="date" 
                      value={searchParams.endDate}
                      onChange={(e) => updateParam('endDate', e.target.value)}
                      className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                    />
                  </div>
                </div>
              </div>
            </Card>

            {/* 價格條件 */}
            <Card title="價格條件">
              <div className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <div className="flex items-center space-x-1 mb-1">
                      <label className="text-xs font-medium text-gray-800">價格變化 (%)</label>
                      <div className="group relative">
                        <div className="w-3 h-3 bg-gray-400 rounded-full text-white text-xs flex items-center justify-center cursor-help">?</div>
                        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-48 p-2 bg-gray-800 text-white text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity z-10">
                          <strong>價格變化：</strong><br/>
                          當根K線的收盤價相對開盤價的變化百分比。正值表示上漲，負值表示下跌。
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <select 
                        value={searchParams.priceOperator}
                        onChange={(e) => updateParam('priceOperator', e.target.value)}
                        className="w-16 px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                      >
                        <option value=">=">&gt;=</option>
                        <option value="<=">&lt;=</option>
                        <option value="=">=</option>
                      </select>
                      <input 
                        type="number" 
                        value={searchParams.priceChange || ''}
                        onChange={(e) => updateParam('priceChange', e.target.value ? parseFloat(e.target.value) : null)}
                        step="0.1"
                        min="-50"
                        max="50"
                        placeholder="1.0"
                        className="flex-1 px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-500"
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center space-x-1 mb-1">
                      <label className="text-xs font-medium text-gray-800">收盤強度</label>
                      <div className="group relative">
                        <div className="w-3 h-3 bg-gray-400 rounded-full text-white text-xs flex items-center justify-center cursor-help">?</div>
                        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-48 p-2 bg-gray-800 text-white text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity z-10">
                          <strong>收盤強度：</strong><br/>
                          收盤價在當根K線高低點間的位置 (0-1)。1表示收在最高點，0表示收在最低點，0.5表示收在中間。
                        </div>
                      </div>
                    </div>
                    <input 
                      type="number" 
                      value={searchParams.closingStrength || ''}
                      onChange={(e) => updateParam('closingStrength', e.target.value ? parseFloat(e.target.value) : null)}
                      step="0.01"
                      min="0"
                      max="1"
                      placeholder="0.8"
                      className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-500"
                    />
                  </div>
                  <div>
                    <div className="flex items-center space-x-1 mb-1">
                      <label className="text-xs font-medium text-gray-800">價格位置</label>
                      <div className="group relative">
                        <div className="w-3 h-3 bg-gray-400 rounded-full text-white text-xs flex items-center justify-center cursor-help">?</div>
                        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-48 p-2 bg-gray-800 text-white text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity z-10">
                          <strong>價格位置：</strong><br/>
                          當前價格在近期價格區間中的相對位置 (0-1)。1表示接近近期高點，0表示接近近期低點。
                        </div>
                      </div>
                    </div>
                    <input 
                      type="number" 
                      value={searchParams.pricePosition || ''}
                      onChange={(e) => updateParam('pricePosition', e.target.value ? parseFloat(e.target.value) : null)}
                      step="0.01"
                      min="0"
                      max="1"
                      placeholder="0.9"
                      className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-500"
                    />
                  </div>
                </div>
              </div>
            </Card>

            {/* 成交量條件 */}
            <Card title="成交量條件">
              <div className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <div className="flex items-center space-x-1 mb-1">
                      <label className="text-xs font-medium text-gray-800">成交量倍數</label>
                      <div className="group relative">
                        <div className="w-3 h-3 bg-gray-400 rounded-full text-white text-xs flex items-center justify-center cursor-help">?</div>
                        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-48 p-2 bg-gray-800 text-white text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity z-10">
                          <strong>成交量倍數：</strong><br/>
                          當根K線成交量相對於近期平均成交量的倍數。1.0表示平均水平，2.0表示放量一倍，0.5表示縮量一半。
                        </div>
                      </div>
                    </div>
                    <input 
                      type="number" 
                      value={searchParams.volumeMultiplier || ''}
                      onChange={(e) => updateParam('volumeMultiplier', e.target.value ? parseFloat(e.target.value) : null)}
                      step="0.1"
                      min="0.1"
                      placeholder="1.2"
                      className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-500"
                    />
                  </div>
                  <div>
                    <div className="flex items-center space-x-1 mb-1">
                      <label className="text-xs font-medium text-gray-800">主動買入比例</label>
                      <div className="group relative">
                        <div className="w-3 h-3 bg-gray-400 rounded-full text-white text-xs flex items-center justify-center cursor-help">?</div>
                        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-48 p-2 bg-gray-800 text-white text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity z-10">
                          <strong>主動買入比例：</strong><br/>
                          主動買入成交量佔總成交量的比例 (0-1)。>0.5表示買方主導市場，<0.5表示賣方主導，0.5表示均衡。
                        </div>
                      </div>
                    </div>
                    <input 
                      type="number" 
                      value={searchParams.takerBuyRatio || ''}
                      onChange={(e) => updateParam('takerBuyRatio', e.target.value ? parseFloat(e.target.value) : null)}
                      step="0.01"
                      min="0"
                      max="1"
                      placeholder="0.6"
                      className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-500"
                    />
                  </div>
                </div>
              </div>
            </Card>

            {/* 正反例設定 */}
            <Card title="正反例設定">
              <div className="space-y-3">
                <div className="flex items-center space-x-4 mb-3">
                  <label className="flex items-center">
                    <input 
                      type="checkbox" 
                      checked={searchParams.showPositiveCase}
                      onChange={(e) => updateParam('showPositiveCase', e.target.checked)}
                      className="mr-2 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-800">包含正例</span>
                  </label>
                  <label className="flex items-center">
                    <input 
                      type="checkbox" 
                      checked={searchParams.showNegativeCase}
                      onChange={(e) => updateParam('showNegativeCase', e.target.checked)}
                      className="mr-2 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-800">包含反例</span>
                  </label>
                </div>
                
                {searchParams.showNegativeCase && (
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-800 mb-1">時間分離間隔</label>
                      <div className="flex items-center space-x-2">
                        <input 
                          type="number" 
                          value={searchParams.timeSeparationDays}
                          onChange={(e) => updateParam('timeSeparationDays', parseInt(e.target.value) || 7)}
                          min="1"
                          max="30"
                          className="w-16 px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                        />
                        <span className="text-xs text-gray-600">天</span>
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-800 mb-1">正反比例</label>
                      <select 
                        value={searchParams.positiveNegativeRatio}
                        onChange={(e) => updateParam('positiveNegativeRatio', e.target.value)}
                        className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                      >
                        <option value="1:1">1:1</option>
                        <option value="1:2">1:2</option>
                        <option value="1:3">1:3</option>
                        <option value="1:4">1:4</option>
                      </select>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          </div>

          {/* 右側控制面板 */}
          <div className="space-y-4">
            
            {/* 搜索控制 */}
            <Card title="搜索控制">
              <div className="space-y-3">
                <button 
                  className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:bg-gray-400"
                  disabled={isLoading}
                  onClick={handleSearch}
                >
                  {isLoading ? (
                    <div className="flex items-center justify-center space-x-2">
                      <LoadingSpinner size="small" />
                      <span>搜索中...</span>
                    </div>
                  ) : (
                    '開始搜索'
                  )}
                </button>

                <button 
                  className="w-full bg-gray-100 text-gray-700 py-2 px-4 rounded-lg font-medium hover:bg-gray-200 transition-colors"
                  onClick={handleClearParams}
                >
                  <div className="flex items-center justify-center space-x-2">
                    <Trash2 className="w-4 h-4" />
                    <span>清除參數</span>
                  </div>
                </button>

                {searchResults && (
                  <button 
                    className="w-full bg-green-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-green-700 transition-colors"
                    onClick={handleExportResults}
                  >
                    <div className="flex items-center justify-center space-x-2">
                      <Download className="w-4 h-4" />
                      <span>導出結果</span>
                    </div>
                  </button>
                )}

                {/* 配置管理 */}
                <hr className="my-3" />
                <div className="space-y-2">
                  <input 
                    type="text" 
                    value={searchParams.configName}
                    onChange={(e) => updateParam('configName', e.target.value)}
                    placeholder="配置名稱" 
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-500"
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <button className="bg-green-600 text-white py-1.5 px-3 text-sm rounded-lg font-medium hover:bg-green-700 transition-colors">
                      保存配置
                    </button>
                    <button className="bg-orange-600 text-white py-1.5 px-3 text-sm rounded-lg font-medium hover:bg-orange-700 transition-colors">
                      載入配置
                    </button>
                  </div>
                </div>
              </div>
            </Card>

            {/* 參數預覽 */}
            <Card title="當前參數">
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-600">時間框架:</span>
                  <span className="font-medium">{searchParams.timeframe}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">交易對:</span>
                  <span className="font-medium">
                    {searchParams.symbols.length > 1 
                      ? `${searchParams.symbols.length}個交易對` 
                      : (searchParams.symbols[0] || 'BTCUSDT')
                    }
                  </span>
                </div>
                {searchParams.priceChange && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">價格變化:</span>
                    <span className="font-medium">{searchParams.priceOperator} {searchParams.priceChange}%</span>
                  </div>
                )}
                {searchParams.volumeMultiplier && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">成交量:</span>
                    <span className="font-medium">{searchParams.volumeMultiplier}x</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-gray-600">正反例:</span>
                  <span className="font-medium">
                    {searchParams.showPositiveCase ? '正例' : ''}
                    {searchParams.showPositiveCase && searchParams.showNegativeCase ? '+' : ''}
                    {searchParams.showNegativeCase ? '反例' : ''}
                  </span>
                </div>
              </div>
            </Card>
          </div>
        </div>

        {/* 搜索結果預覽 */}
        {searchResults && (
          <Card title="搜索結果">
            <div className="text-sm text-gray-600">
              <pre className="bg-gray-50 p-4 rounded-lg overflow-auto max-h-40">
                {JSON.stringify(searchResults, null, 2)}
              </pre>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
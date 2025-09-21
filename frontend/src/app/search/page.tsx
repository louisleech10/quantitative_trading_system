// frontend/src/app/search/page.tsx
'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { Download, Trash2 } from 'lucide-react';

export default function SearchPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<any>(null);
  const [showPositiveCase, setShowPositiveCase] = useState(true);
  const [showNegativeCase, setShowNegativeCase] = useState(false);
  const [priceOperator, setPriceOperator] = useState('>=');

  const handleSearch = async () => {
    setIsLoading(true);
    try {
      // 調用真實的API
      const { apiClient } = await import('@/lib/api');
      
      const searchRequest = {
        name: 'Frontend_Test_Search',
        timeframe: '12h',
        priceChange: 5,  // 5%價格變化
        volumeMultiplier: 2,  // 2倍成交量
        symbols: ['BTCUSDT'],
        saveResults: false
      };
      
      console.log('開始執行搜索:', searchRequest);
      const result = await apiClient.executePositiveSearch(searchRequest);
      console.log('搜索結果:', result);
      
      setSearchResults(result);
    } catch (error) {
      console.error('搜索錯誤:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearParams = () => {
    // 清除所有參數
    console.log('清除參數');
  };

  const handleExportResults = () => {
    console.log('導出結果');
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
            
            {/* 共同設定 - 緊湊設計 */}
            <Card title="共同設定">
              <div className="space-y-3">
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-800 mb-1">時間框架 *</label>
                    <select className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 bg-white">
                      <option value="1h">1小時</option>
                      <option value="4h">4小時</option>
                      <option value="12h" defaultValue>12小時</option>
                      <option value="1d">1天</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-800 mb-1">開始日期</label>
                    <input type="date" defaultValue="2024-01-01" className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-800 mb-1">結束日期</label>
                    <input type="date" defaultValue="2024-12-31" className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-800 mb-1">交易對</label>
                    <input type="text" placeholder="BTCUSDT" defaultValue="BTCUSDT" className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-500" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-800 mb-1">選擇模式</label>
                    <select className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 bg-white">
                      <option value="single">單一交易對</option>
                      <option value="multiple">全市場掃描</option>
                    </select>
                  </div>
                </div>
                <div className="flex flex-wrap gap-3 text-sm">
                  <label className="flex items-center space-x-1">
                    <input type="checkbox" defaultChecked className="rounded border-gray-300" />
                    <span className="text-gray-800">排除新上市（7天內）</span>
                  </label>
                  <label className="flex items-center space-x-1">
                    <input type="checkbox" className="rounded border-gray-300" />
                    <span className="text-gray-800">排除穩定幣</span>
                  </label>
                </div>
              </div>
            </Card>

            {/* 搜索模式與條件整合 */}
            <Card title="搜索條件設定">
              {/* 模式選擇 - 上方一排 */}
              <div className="mb-4 pb-3 border-b border-gray-200">
                <div className="flex space-x-6">
                  <label className="flex items-center space-x-2">
                    <input 
                      type="checkbox" 
                      checked={showPositiveCase}
                      onChange={(e) => setShowPositiveCase(e.target.checked)}
                      className="rounded border-gray-300" 
                    />
                    <span className="text-sm font-medium text-gray-800">正向案例</span>
                  </label>
                  <label className="flex items-center space-x-2">
                    <input 
                      type="checkbox" 
                      checked={showNegativeCase}
                      onChange={(e) => setShowNegativeCase(e.target.checked)}
                      className="rounded border-gray-300" 
                    />
                    <span className="text-sm font-medium text-gray-800">反向案例</span>
                  </label>
                </div>
              </div>

              {/* 條件設定 - 左右分欄 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {/* 左下 - 正向案例條件 */}
                {showPositiveCase && (
                  <div className="space-y-3">
                    <h4 className="font-medium text-gray-900 text-sm">正向案例條件</h4>
                    <div className="space-y-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-800 mb-1">價格變化</label>
                        <div className="space-y-2">
                          <select 
                            value={priceOperator}
                            onChange={(e) => setPriceOperator(e.target.value)}
                            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                          >
                            <option value=">=">&gt;=</option>
                            <option value="<=">&lt;=</option>
                            <option value="=">=</option>
                            <option value="between">介於</option>
                          </select>
                          <div>
                            {priceOperator === 'between' ? (
                              <div className="flex items-center space-x-2">
                                <input type="number" placeholder="最小值" step="0.1" className="w-20 px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900" />
                                <span className="text-xs text-gray-600">到</span>
                                <input type="number" placeholder="最大值" step="0.1" className="w-20 px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900" />
                                <span className="text-xs text-gray-600">%</span>
                              </div>
                            ) : (
                              <div className="flex items-center space-x-2">
                                <input type="number" defaultValue="7" step="0.1" className="flex-1 px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900" />
                                <span className="text-xs text-gray-600">%</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-800 mb-1">最小成交量</label>
                        <div className="flex items-center space-x-2">
                          <input type="number" defaultValue="1000000" className="flex-1 px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900" />
                          <span className="text-xs text-gray-600">USDT</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* 右下 - 反向案例條件 */}
                {showNegativeCase && (
                  <div className="space-y-3">
                    <h4 className="font-medium text-gray-900 text-sm">反向案例條件</h4>
                    <div className="space-y-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-800 mb-1">觀察期間</label>
                        <div className="flex items-center space-x-2">
                          <input type="number" defaultValue="7" className="w-16 px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900" />
                          <span className="text-xs text-gray-600">根K線</span>
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-800 mb-1">價格變化範圍</label>
                        <div className="flex items-center space-x-2">
                          <input type="number" defaultValue="-5" step="0.1" className="w-16 px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900" />
                          <span className="text-xs text-gray-600">到</span>
                          <input type="number" defaultValue="3" step="0.1" className="w-16 px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900" />
                          <span className="text-xs text-gray-600">%</span>
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-800 mb-1">時間分離間隔</label>
                        <div className="flex items-center space-x-2">
                          <input type="number" defaultValue="7" className="w-16 px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900" />
                          <span className="text-xs text-gray-600">根K線</span>
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-800 mb-1">正反比例</label>
                        <select className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900">
                          <option value="1:1">1:1</option>
                          <option value="1:2" defaultValue>1:2</option>
                          <option value="1:3">1:3</option>
                          <option value="1:4">1:4</option>
                        </select>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          </div>

          {/* 右側控制面板 */}
          <div className="space-y-4">
            
            {/* 搜索控制 + 參數管理整合 */}
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

                {/* 參數管理 - 整合到控制面板 */}
                <hr className="my-3" />
                <div className="space-y-2">
                  <input 
                    type="text" 
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

            {/* 搜索進度 */}
            {isLoading && (
              <Card title="搜索進度">
                <div className="space-y-3">
                  <div className="flex justify-between items-center text-sm">
                    <span>總體進度</span>
                    <span>45%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-blue-600 h-2 rounded-full" style={{ width: '45%' }}></div>
                  </div>
                  
                  <div className="text-xs text-gray-500 space-y-1">
                    <div>正在處理: BTCUSDT</div>
                    <div>已完成: 450 / 1000 條記錄</div>
                    <div>預計剩餘: 2分30秒</div>
                  </div>
                </div>
              </Card>
            )}
          </div>
        </div>

        {/* 搜索結果統計區域 */}
        {searchResults && (
          <div className="space-y-6">
            
            {/* 基本統計 - 移除假數據 */}
            <Card title="搜索結果統計">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{searchResults.totalCases || 0}</div>
                  <div className="text-sm text-gray-600">總案例數</div>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">{searchResults.positiveCases || 0}</div>
                  <div className="text-sm text-gray-600">正例案例</div>
                </div>
                <div className="text-center p-4 bg-red-50 rounded-lg">
                  <div className="text-2xl font-bold text-red-600">{searchResults.negativeCases || 0}</div>
                  <div className="text-sm text-gray-600">反例案例</div>
                </div>
                <div className="text-center p-4 bg-purple-50 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">{searchResults.uniqueSymbols || 0}</div>
                  <div className="text-sm text-gray-600">交易對數</div>
                </div>
                <div className="text-center p-4 bg-orange-50 rounded-lg">
                  <div className="text-2xl font-bold text-orange-600">{searchResults.executionTime || 0}s</div>
                  <div className="text-sm text-gray-600">執行時間</div>
                </div>
              </div>
            </Card>

            {/* 分布統計圖表 - 改為視覺化圖表 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              
              {/* 星期分布圖表 */}
              <Card title="星期分布">
                <div className="h-64 flex items-center justify-center border-2 border-dashed border-gray-300 rounded-lg bg-gray-50">
                  <div className="text-center text-gray-500">
                    <div className="text-sm mb-2 font-medium">雙軸圖表區域</div>
                    <div className="text-xs space-y-1">
                      <div>X軸: 週一~週日</div>
                      <div>左Y軸: 百分比（直條圖）</div>
                      <div>右Y軸: 數量（折線圖）</div>
                    </div>
                  </div>
                </div>
              </Card>

              {/* 小時分布圖表 - 全24小時 */}
              <Card title="小時分布（24小時全覽）">
                <div className="h-64 flex items-center justify-center border-2 border-dashed border-gray-300 rounded-lg bg-gray-50">
                  <div className="text-center text-gray-500">
                    <div className="text-sm mb-2 font-medium">雙軸圖表區域</div>
                    <div className="text-xs space-y-1">
                      <div>X軸: 00:00~23:00</div>
                      <div>左Y軸: 百分比（直條圖）</div>
                      <div>右Y軸: 數量（折線圖）</div>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Market Phase 分布圖表 */}
              <Card title="Market Phase 分布">
                <div className="h-64 flex items-center justify-center border-2 border-dashed border-gray-300 rounded-lg bg-gray-50">
                  <div className="text-center text-gray-500">
                    <div className="text-sm mb-2 font-medium">雙軸圖表區域</div>
                    <div className="text-xs space-y-1">
                      <div>X軸: FEAR/NEUTRAL/GREED</div>
                      <div>左Y軸: 百分比（直條圖）</div>
                      <div>右Y軸: 數量（折線圖）</div>
                    </div>
                  </div>
                </div>
              </Card>

              {/* 月份分布圖表 */}
              <Card title="月份分布">
                <div className="h-64 flex items-center justify-center border-2 border-dashed border-gray-300 rounded-lg bg-gray-50">
                  <div className="text-center text-gray-500">
                    <div className="text-sm mb-2 font-medium">雙軸圖表區域</div>
                    <div className="text-xs space-y-1">
                      <div>X軸: 1月~12月</div>
                      <div>左Y軸: 百分比（直條圖）</div>
                      <div>右Y軸: 數量（折線圖）</div>
                    </div>
                  </div>
                </div>
              </Card>

              {/* 日期分布圖表 - 全31天 */}
              <Card title="每月日期分布（全31天）">
                <div className="h-64 flex items-center justify-center border-2 border-dashed border-gray-300 rounded-lg bg-gray-50">
                  <div className="text-center text-gray-500">
                    <div className="text-sm mb-2 font-medium">雙軸圖表區域</div>
                    <div className="text-xs space-y-1">
                      <div>X軸: 1日~31日</div>
                      <div>左Y軸: 百分比（直條圖）</div>
                      <div>右Y軸: 數量（折線圖）</div>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
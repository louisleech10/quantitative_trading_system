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

  // 統計圖表數據模擬
  const [statisticsData] = useState({
    totalCases: 0,
    positiveCases: 0,
    negativeCases: 0,
    timeframeDistribution: {},
    weekdayDistribution: {},
    hourDistribution: {},
  });

  const handleSearch = () => {
    setIsLoading(true);
    // 模擬搜索過程
    setTimeout(() => {
      setSearchResults({
        totalCases: 158,
        positiveCases: 158,
        negativeCases: 0,
        executionTime: 2.3
      });
      setIsLoading(false);
    }, 3000);
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
          <div className="xl:col-span-3 space-y-6">
            
            {/* 共同設定 */}
            <Card title="共同設定">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-800 mb-2">
                    時間框架 *
                  </label>
                  <select className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 bg-white">
                    <option value="1h">1小時</option>
                    <option value="4h">4小時</option>
                    <option value="12h" defaultValue>12小時</option>
                    <option value="1d">1天</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-800 mb-2">
                    開始日期
                  </label>
                  <input 
                    type="date" 
                    defaultValue="2024-01-01"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-800 mb-2">
                    結束日期
                  </label>
                  <input 
                    type="date" 
                    defaultValue="2024-12-31"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                  />
                </div>
              </div>
              
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-800 mb-2">
                  交易對選擇
                </label>
                <div className="space-y-2">
                  <label className="flex items-center space-x-2">
                    <input type="radio" name="symbol_selection" defaultChecked className="text-blue-600" />
                    <span className="text-sm text-gray-800">單一交易對</span>
                  </label>
                  <input 
                    type="text" 
                    placeholder="例：BTCUSDT" 
                    defaultValue="BTCUSDT"
                    className="ml-6 w-full md:w-1/2 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-500"
                  />
                  <label className="flex items-center space-x-2">
                    <input type="radio" name="symbol_selection" className="text-blue-600" />
                    <span className="text-sm text-gray-800">全市場掃描</span>
                  </label>
                </div>
                
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-800 mb-2">
                    排除條件
                  </label>
                  <div className="space-y-2">
                    <label className="flex items-center space-x-2">
                      <input type="checkbox" defaultChecked className="rounded border-gray-300" />
                      <span className="text-sm text-gray-800">排除新上市幣種（7天內）</span>
                    </label>
                    <label className="flex items-center space-x-2">
                      <input type="checkbox" className="rounded border-gray-300" />
                      <span className="text-sm text-gray-800">排除穩定幣</span>
                    </label>
                  </div>
                </div>
              </div>
            </Card>

            {/* 正反案例模式選擇 */}
            <Card title="搜索模式">
              <div className="space-y-4">
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
            </Card>

            {/* 正向案例條件 */}
            {showPositiveCase && (
              <Card title="正向案例條件">
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-800 mb-2">
                        價格變化
                      </label>
                      <div className="flex items-center space-x-2">
                        <select className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900">
                          <option value=">=">&gt;=</option>
                          <option value="<=">&lt;=</option>
                          <option value="=">=</option>
                          <option value="between">介於</option>
                        </select>
                        <input 
                          type="number" 
                          defaultValue="7" 
                          step="0.1"
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                        />
                        <span className="text-sm text-gray-600">%</span>
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-800 mb-2">
                        最小成交量
                      </label>
                      <div className="flex items-center space-x-2">
                        <input 
                          type="number" 
                          defaultValue="1000000" 
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                        />
                        <span className="text-sm text-gray-600">USDT</span>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            )}

            {/* 反向案例條件 */}
            {showNegativeCase && (
              <Card title="反向案例條件">
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-800 mb-2">
                        觀察期間
                      </label>
                      <div className="flex items-center space-x-2">
                        <input 
                          type="number" 
                          defaultValue="7" 
                          className="w-20 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                        />
                        <span className="text-sm text-gray-600">根K線</span>
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-800 mb-2">
                        價格變化範圍
                      </label>
                      <div className="flex items-center space-x-2">
                        <input 
                          type="number" 
                          defaultValue="-5" 
                          step="0.1"
                          className="w-20 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                        />
                        <span className="text-sm text-gray-600">到</span>
                        <input 
                          type="number" 
                          defaultValue="3" 
                          step="0.1"
                          className="w-20 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                        />
                        <span className="text-sm text-gray-600">%</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-800 mb-2">
                        時間分離間隔
                      </label>
                      <div className="flex items-center space-x-2">
                        <input 
                          type="number" 
                          defaultValue="7" 
                          className="w-20 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                        />
                        <span className="text-sm text-gray-600">根K線</span>
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-800 mb-2">
                        正反比例
                      </label>
                      <select className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900">
                        <option value="1:1">1:1</option>
                        <option value="1:2" defaultValue>1:2</option>
                        <option value="1:3">1:3</option>
                        <option value="1:4">1:4</option>
                      </select>
                    </div>
                  </div>
                </div>
              </Card>
            )}

            {/* 參數管理 */}
            <Card title="參數管理">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-gray-900">保存當前配置</h4>
                  <p className="text-sm text-gray-600">將當前參數設定保存為模板，便於下次使用</p>
                </div>
                <div className="flex space-x-3">
                  <input 
                    type="text" 
                    placeholder="配置名稱" 
                    className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-500"
                  />
                  <button className="bg-green-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-green-700 transition-colors">
                    保存配置
                  </button>
                </div>
              </div>
            </Card>
          </div>

          {/* 右側控制面板 */}
          <div className="space-y-6">
            
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
            
            {/* 基本統計 */}
            <Card title="搜索結果統計">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{searchResults.totalCases}</div>
                  <div className="text-sm text-gray-600">總案例數</div>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">{searchResults.positiveCases}</div>
                  <div className="text-sm text-gray-600">正例案例</div>
                </div>
                <div className="text-center p-4 bg-red-50 rounded-lg">
                  <div className="text-2xl font-bold text-red-600">{searchResults.negativeCases}</div>
                  <div className="text-sm text-gray-600">反例案例</div>
                </div>
                <div className="text-center p-4 bg-purple-50 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">1</div>
                  <div className="text-sm text-gray-600">交易對數</div>
                </div>
                <div className="text-center p-4 bg-orange-50 rounded-lg">
                  <div className="text-2xl font-bold text-orange-600">{searchResults.executionTime}s</div>
                  <div className="text-sm text-gray-600">執行時間</div>
                </div>
              </div>
            </Card>

            {/* 分布統計圖表 */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* 時間框架分布 */}
              <Card title="時間框架分布">
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">12小時</span>
                    <span className="text-sm font-medium">158 (100%)</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-blue-600 h-2 rounded-full" style={{ width: '100%' }}></div>
                  </div>
                </div>
              </Card>

              {/* 星期分布 */}
              <Card title="星期分布">
                <div className="space-y-2">
                  {['週一', '週二', '週三', '週四', '週五', '週六', '週日'].map((day, index) => (
                    <div key={day} className="flex justify-between items-center text-sm">
                      <span className="text-gray-600">{day}</span>
                      <span className="font-medium">{Math.floor(Math.random() * 30) + 10}</span>
                    </div>
                  ))}
                </div>
              </Card>

              {/* 小時分布 */}
              <Card title="小時分布（前5名）">
                <div className="space-y-2">
                  {['08:00', '14:00', '20:00', '02:00', '16:00'].map((hour, index) => (
                    <div key={hour} className="flex justify-between items-center text-sm">
                      <span className="text-gray-600">{hour}</span>
                      <span className="font-medium">{30 - index * 4}</span>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
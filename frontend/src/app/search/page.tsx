// frontend/src/app/search/page.tsx
'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

export default function SearchPage() {
  const [isLoading, setIsLoading] = useState(false);

  return (
    <div className="h-full overflow-auto">
      <div className="p-6 max-w-7xl mx-auto">
        {/* 頁面標題 */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">案例搜索</h1>
          <p className="text-gray-600">
            設定搜索條件，找出符合特定模式的交易案例
          </p>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* 左側參數設定區域 */}
          <div className="xl:col-span-2 space-y-6">
            
            {/* 基本觸發條件 */}
            <Card title="基本觸發條件">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    時間框架
                  </label>
                  <select className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                    <option value="1h">1小時</option>
                    <option value="4h">4小時</option>
                    <option value="12h" defaultValue>12小時</option>
                    <option value="1d">1天</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    價格變化 (%)
                  </label>
                  <div className="flex items-center space-x-4">
                    <input 
                      type="range" 
                      min="1" 
                      max="20" 
                      defaultValue="7"
                      className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <input 
                      type="number" 
                      defaultValue="7" 
                      className="w-20 px-3 py-1 border border-gray-300 rounded text-center"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    成交量倍數
                  </label>
                  <div className="flex items-center space-x-4">
                    <input 
                      type="range" 
                      min="1" 
                      max="10" 
                      step="0.5"
                      defaultValue="2"
                      className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <input 
                      type="number" 
                      step="0.5"
                      defaultValue="2" 
                      className="w-20 px-3 py-1 border border-gray-300 rounded text-center"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    主動買入比例 (%)
                  </label>
                  <div className="flex items-center space-x-4">
                    <input 
                      type="range" 
                      min="50" 
                      max="80" 
                      defaultValue="65"
                      className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <input 
                      type="number" 
                      min="50"
                      max="80"
                      defaultValue="65" 
                      className="w-20 px-3 py-1 border border-gray-300 rounded text-center"
                    />
                  </div>
                </div>
              </div>
            </Card>

            {/* 未來表現要求 */}
            <Card title="未來表現要求">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    24小時後收益率要求 (%)
                  </label>
                  <div className="flex items-center space-x-4">
                    <input 
                      type="range" 
                      min="2" 
                      max="15" 
                      defaultValue="5"
                      className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <input 
                      type="number" 
                      defaultValue="5" 
                      className="w-20 px-3 py-1 border border-gray-300 rounded text-center"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    最大回撤容忍度 (%)
                  </label>
                  <div className="flex items-center space-x-4">
                    <input 
                      type="range" 
                      min="5" 
                      max="20" 
                      defaultValue="10"
                      className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <input 
                      type="number" 
                      defaultValue="10" 
                      className="w-20 px-3 py-1 border border-gray-300 rounded text-center"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    觀察時間段
                  </label>
                  <div className="grid grid-cols-3 gap-4">
                    <label className="flex items-center space-x-2">
                      <input type="checkbox" defaultChecked className="rounded border-gray-300" />
                      <span className="text-sm">24小時</span>
                    </label>
                    <label className="flex items-center space-x-2">
                      <input type="checkbox" defaultChecked className="rounded border-gray-300" />
                      <span className="text-sm">48小時</span>
                    </label>
                    <label className="flex items-center space-x-2">
                      <input type="checkbox" className="rounded border-gray-300" />
                      <span className="text-sm">72小時</span>
                    </label>
                  </div>
                </div>
              </div>
            </Card>

            {/* 篩選條件 */}
            <Card title="篩選條件">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    時間範圍
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">開始日期</label>
                      <input 
                        type="date" 
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">結束日期</label>
                      <input 
                        type="date" 
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    交易對選擇
                  </label>
                  <div className="space-y-2">
                    <label className="flex items-center space-x-2">
                      <input type="radio" name="symbol_selection" defaultChecked className="text-blue-600" />
                      <span className="text-sm">單一交易對</span>
                    </label>
                    <div className="ml-6">
                      <input 
                        type="text" 
                        placeholder="例：BTCUSDT" 
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                    <label className="flex items-center space-x-2">
                      <input type="radio" name="symbol_selection" className="text-blue-600" />
                      <span className="text-sm">多個交易對</span>
                    </label>
                    <label className="flex items-center space-x-2">
                      <input type="radio" name="symbol_selection" className="text-blue-600" />
                      <span className="text-sm">全市場掃描</span>
                    </label>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    排除條件
                  </label>
                  <div className="space-y-2">
                    <label className="flex items-center space-x-2">
                      <input type="checkbox" defaultChecked className="rounded border-gray-300" />
                      <span className="text-sm">排除新上市幣種 (7天內)</span>
                    </label>
                    <label className="flex items-center space-x-2">
                      <input type="checkbox" className="rounded border-gray-300" />
                      <span className="text-sm">排除穩定幣</span>
                    </label>
                    <label className="flex items-center space-x-2">
                      <input type="checkbox" className="rounded border-gray-300" />
                      <span className="text-sm">排除槓桿代幣</span>
                    </label>
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* 右側控制面板 */}
          <div className="space-y-6">
            
            {/* 搜索控制 */}
            <Card title="搜索控制">
              <div className="space-y-4">
                <button 
                  className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:bg-gray-400"
                  disabled={isLoading}
                  onClick={() => {
                    setIsLoading(true);
                    // 模擬搜索過程
                    setTimeout(() => setIsLoading(false), 3000);
                  }}
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

                <button className="w-full bg-gray-100 text-gray-700 py-2 px-4 rounded-lg font-medium hover:bg-gray-200 transition-colors">
                  預覽結果數量
                </button>

                <button className="w-full bg-gray-100 text-gray-700 py-2 px-4 rounded-lg font-medium hover:bg-gray-200 transition-colors">
                  重置參數
                </button>
              </div>
            </Card>

            {/* 參數預設 */}
            <Card title="參數預設">
              <div className="space-y-3">
                <button className="w-full text-left px-3 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm transition-colors">
                  動能突破模式
                </button>
                <button className="w-full text-left px-3 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm transition-colors">
                  成交量放大模式
                </button>
                <button className="w-full text-left px-3 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm transition-colors">
                  技術指標組合
                </button>
                <button className="w-full text-left px-3 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm transition-colors">
                  自定義配置
                </button>
              </div>
            </Card>

            {/* 預期結果 */}
            <Card title="預期結果">
              <div className="space-y-3">
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <span className="text-sm text-gray-600">預估案例數</span>
                  <span className="text-sm font-medium">約 150-300</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <span className="text-sm text-gray-600">時間範圍</span>
                  <span className="text-sm font-medium">6個月</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <span className="text-sm text-gray-600">預估用時</span>
                  <span className="text-sm font-medium">2-5分鐘</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-sm text-gray-600">結果品質</span>
                  <span className="text-sm font-medium text-green-600">高</span>
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

        {/* 參數保存 */}
        <div className="mt-8">
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
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <button className="bg-green-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-green-700 transition-colors">
                  保存配置
                </button>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
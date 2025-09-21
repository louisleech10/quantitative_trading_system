'use client';

import { useState } from 'react';

interface SearchParams {
  timeframe: string;
  symbols: string[];
  priceChange: number | null;
}

export default function SearchPage() {
  const [searchParams, setSearchParams] = useState<SearchParams>({
    timeframe: '12h',
    symbols: ['BTCUSDT'],
    priceChange: 1
  });

  const updateParam = <K extends keyof SearchParams>(key: K, value: SearchParams[K]) => {
    setSearchParams(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="h-full overflow-auto">
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">案例搜索</h1>
          <p className="text-gray-600">設定搜索條件，找出符合特定模式的交易案例</p>
        </div>
        
        <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">基礎設定</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">時間框架</label>
              <select 
                value={searchParams.timeframe}
                onChange={(e) => updateParam('timeframe', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="12h">12小時</option>
                <option value="1d">1天</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">交易對</label>
              <input 
                type="text" 
                value={searchParams.symbols[0] || ''}
                onChange={(e) => updateParam('symbols', [e.target.value])}
                placeholder="BTCUSDT"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>
          </div>
          
          <button 
            className="mt-4 w-full bg-blue-600 text-white py-2 px-4 rounded-lg"
            onClick={() => console.log('搜索參數:', searchParams)}
          >
            開始搜索
          </button>
        </div>
      </div>
    </div>
  );
}
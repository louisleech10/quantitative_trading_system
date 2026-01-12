// frontend/src/app/patterns/page.tsx
/**
 * 樣式發現系統主頁面
 * 
 * 整合所有 Pattern Discovery 組件
 */

'use client';

import React, { useEffect, useState } from 'react';
import { usePatternStore } from '@/store/patternStore';
import { listPatterns } from '@/lib/api/patternApi';
import PatternList from '@/components/pattern/PatternList';
import PatternFilters from '@/components/pattern/PatternFilters';
import PatternStatistics from '@/components/pattern/PatternStatistics';
import PatternComparison from '@/components/pattern/PatternComparison';
import Link from 'next/link';

type TabType = 'list' | 'statistics' | 'comparison';

export default function PatternsPage() {
  const { patterns, setPatterns } = usePatternStore();
  const [activeTab, setActiveTab] = useState<TabType>('list');
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadPatterns();
  }, []);
  
  const loadPatterns = async () => {
    try {
      setLoading(true);
      const data = await listPatterns();
      setPatterns(data.patterns);
    } catch (error) {
      console.error('載入樣式失敗:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="min-h-screen bg-white">
      {/* 頁面標題 */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">樣式發現系統</h1>
              <p className="text-gray-600">Pattern Discovery & Management</p>
            </div>
            <div className="flex gap-3">
              <Link
                href="/patterns/xgboost-analysis"
                className="px-6 py-3 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700"
              >
                🧠 XGBoost 分析
              </Link>
              <Link
                href="/patterns/create"
                className="px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700"
              >
                + 建立新樣式
              </Link>
            </div>
          </div>
        </div>
      </div>
      
      {/* 分頁導航 */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-1">
            <button
              onClick={() => setActiveTab('list')}
              className={`px-6 py-3 font-semibold border-b-2 transition-colors ${
                activeTab === 'list'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              樣式列表
            </button>
            <button
              onClick={() => setActiveTab('statistics')}
              className={`px-6 py-3 font-semibold border-b-2 transition-colors ${
                activeTab === 'statistics'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              統計分析
            </button>
            <button
              onClick={() => setActiveTab('comparison')}
              className={`px-6 py-3 font-semibold border-b-2 transition-colors ${
                activeTab === 'comparison'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              樣式比較
            </button>
          </div>
        </div>
      </div>
      
      {/* 主要內容 */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        {loading ? (
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">載入中...</p>
          </div>
        ) : (
          <>
            {activeTab === 'list' && (
              <div className="grid grid-cols-4 gap-6">
                {/* 左側篩選器 */}
                <div className="col-span-1">
                  <PatternFilters />
                </div>
                
                {/* 右側樣式列表 */}
                <div className="col-span-3">
                  <PatternList />
                </div>
              </div>
            )}
            
            {activeTab === 'statistics' && <PatternStatistics />}
            
            {activeTab === 'comparison' && <PatternComparison />}
          </>
        )}
      </div>
    </div>
  );
}

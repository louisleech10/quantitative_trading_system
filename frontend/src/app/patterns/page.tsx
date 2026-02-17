// frontend/src/app/patterns/page.tsx
/**
 * 樣式發現系統主頁面
 * 
 * 整合所有 Pattern Discovery 組件
 */

'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { usePatternStore } from '@/store/patternStore';
import { listPatterns, deleteAllPatterns } from '@/lib/api/patternApi';
import PatternList from '@/components/pattern/PatternList';
import PatternFilters from '@/components/pattern/PatternFilters';
import PatternStatistics from '@/components/pattern/PatternStatistics';
import PatternComparison from '@/components/pattern/PatternComparison';
import Link from 'next/link';
import { Trash2 } from 'lucide-react';

type TabType = 'list' | 'statistics' | 'comparison';

export default function PatternsPage() {
  const router = useRouter();
  void router;
  const { patterns, setPatterns } = usePatternStore();
  const [activeTab, setActiveTab] = useState<TabType>('list');
  const [loading, setLoading] = useState(true);
  
  const loadPatterns = useCallback(async () => {
    try {
      setLoading(true);
      const data = await listPatterns();
      setPatterns(data.patterns);
    } catch (error) {
      console.error('載入樣式失敗:', error);
    } finally {
      setLoading(false);
    }
  }, [setPatterns]);

  // 初始載入
  useEffect(() => {
    loadPatterns();
  }, [loadPatterns]);

  // 監聽頁面可見性變化，重新載入資料
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        loadPatterns();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [loadPatterns]);

  const handleDeleteAll = async () => {
    if (!confirm('確定要刪除所有模式？此操作無法復原！')) return;
    
    try {
      const result = await deleteAllPatterns();
      if (result.success) {
        alert(`✅ ${result.message}`);
        loadPatterns(); // 重新載入
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '未知錯誤';
      alert('❌ 刪除失敗: ' + message);
    }
  };
  
  return (
    <div className="min-h-screen bg-slate-950/40">
      {/* 頁面標題 */}
      <div className="bg-slate-950/80 border-b border-slate-800/80">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-semibold text-slate-100 mb-2">樣式發現系統</h1>
              <p className="text-slate-400">Pattern Discovery & Management</p>
            </div>
            <div className="flex gap-3">
              <Link
                href="/patterns/xgboost-analysis"
                className="px-6 py-3 bg-emerald-500/20 text-emerald-100 rounded-lg font-semibold border border-emerald-400/40 hover:bg-emerald-500/30"
              >
                🧠 XGBoost 分析
              </Link>
              {patterns.length > 0 && (
                <button
                  onClick={handleDeleteAll}
                  className="px-6 py-3 bg-rose-500/20 text-rose-100 rounded-lg font-semibold border border-rose-400/40 hover:bg-rose-500/30 flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  全部刪除
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* 分頁導航 */}
      <div className="bg-slate-950/80 border-b border-slate-800/80">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-1">
            <button
              onClick={() => setActiveTab('list')}
              className={`px-6 py-3 font-semibold border-b-2 transition-colors ${
                activeTab === 'list'
                  ? 'border-emerald-400 text-emerald-300'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              樣式列表
            </button>
            <button
              onClick={() => setActiveTab('statistics')}
              className={`px-6 py-3 font-semibold border-b-2 transition-colors ${
                activeTab === 'statistics'
                  ? 'border-emerald-400 text-emerald-300'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              統計分析
            </button>
            <button
              onClick={() => setActiveTab('comparison')}
              className={`px-6 py-3 font-semibold border-b-2 transition-colors ${
                activeTab === 'comparison'
                  ? 'border-emerald-400 text-emerald-300'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
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
            <p className="text-slate-400 text-lg">載入中...</p>
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

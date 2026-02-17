// frontend/src/components/pattern/PatternStatistics.tsx
/**
 * PatternStatistics.tsx
 * 
 * 樣式統計儀表板
 * 
 * Features:
 * - 總體統計（總數、啟用數、平均效能）
 * - 效能分布圖表（準確度、F1 分數）
 * - 狀態分布圓餅圖
 * - 頂級樣式列表
 */

'use client';

import React, { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { getPatternStatistics } from '@/lib/api/patternApi';
import type { PatternStatistics as Stats } from '@/lib/patternTypes';

export default function PatternStatistics() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadStatistics();
  }, []);
  
  const loadStatistics = async () => {
    try {
      setLoading(true);
      const data = await getPatternStatistics();
      setStats(data.success ? (data.statistics ?? null) : null);
    } catch (error) {
      console.error('載入統計資料失敗:', error);
    } finally {
      setLoading(false);
    }
  };
  
  if (loading) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-400">載入統計資料中...</p>
      </div>
    );
  }
  
  if (!stats) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-400">無法載入統計資料</p>
      </div>
    );
  }
  
  // 狀態分布資料
  const statusData = [
    { name: '啟用中', value: stats.by_status.active || 0, color: '#34d399' },
    { name: '測試中', value: stats.by_status.testing || 0, color: '#fbbf24' },
    { name: '已封存', value: stats.by_status.archived || 0, color: '#64748b' }
  ].filter(d => d.value > 0);
  
  // 效能分布資料（假設有 performance_distribution）
  const performanceData = stats.performance_distribution || [];
  void performanceData;
  
  return (
    <div className="space-y-6">
      {/* 總體統計卡片 */}
      <div className="grid grid-cols-4 gap-4">
        <div className="glass-panel rounded-xl border border-white/10 p-6 text-center">
          <p className="text-sm text-slate-400 mb-1">總樣式數</p>
          <p className="text-3xl font-semibold text-blue-300">{stats.total_patterns}</p>
        </div>
        <div className="glass-panel rounded-xl border border-white/10 p-6 text-center">
          <p className="text-sm text-slate-400 mb-1">啟用中</p>
          <p className="text-3xl font-semibold text-emerald-300">{stats.by_status.active || 0}</p>
        </div>
        <div className="glass-panel rounded-xl border border-white/10 p-6 text-center">
          <p className="text-sm text-slate-400 mb-1">平均準確度</p>
          <p className="text-3xl font-semibold text-purple-400">
            {(stats.average_performance.accuracy * 100).toFixed(1)}%
          </p>
        </div>
        <div className="glass-panel rounded-xl border border-white/10 p-6 text-center">
          <p className="text-sm text-slate-400 mb-1">平均 F1 分數</p>
          <p className="text-3xl font-semibold text-blue-300">
            {stats.average_performance.f1_score.toFixed(3)}
          </p>
        </div>
      </div>
      
      {/* 圖表區域 */}
      <div className="grid grid-cols-2 gap-6">
        {/* 狀態分布圓餅圖 */}
        <div className="glass-panel rounded-xl border border-white/10 p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">狀態分布</h3>
          {statusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={statusData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={(entry) => `${entry.name}: ${entry.value}`}
                >
                  {statusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#1a233a', border: '1px solid rgba(255,255,255,0.1)' }}
                  itemStyle={{ color: '#e2e8f0' }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center text-slate-400 py-12">暫無資料</p>
          )}
        </div>
        
        {/* 效能指標分布 */}
        <div className="glass-panel rounded-xl border border-white/10 p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">平均效能指標</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={[
              { metric: '準確度', value: stats.average_performance.accuracy },
              { metric: '精確度', value: stats.average_performance.precision },
              { metric: '召回率', value: stats.average_performance.recall },
              { metric: 'F1', value: stats.average_performance.f1_score }
            ]}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="metric" />
              <YAxis domain={[0, 1]} />
              <Tooltip
                formatter={(value: number | string) => `${(Number(value) * 100).toFixed(1)}%`}
                contentStyle={{ backgroundColor: '#1a233a', border: '1px solid rgba(255,255,255,0.1)' }}
                itemStyle={{ color: '#e2e8f0' }}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Bar dataKey="value" fill="#60a5fa" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      
      {/* 標籤統計 */}
      {stats.by_tags && Object.keys(stats.by_tags).length > 0 && (
        <div className="glass-panel rounded-xl border border-white/10 p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">熱門標籤</h3>
          <div className="flex flex-wrap gap-3">
            {Object.entries(stats.by_tags)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 10)
              .map(([tag, count]) => (
                <div key={tag} className="px-4 py-2 bg-blue-400/10 border border-blue-400/20 rounded-full">
                  <span className="font-semibold text-blue-200">{tag}</span>
                  <span className="ml-2 text-sm text-blue-300">×{count}</span>
                </div>
              ))}
          </div>
        </div>
      )}
      
      {/* 案例統計 */}
      {stats.by_case_id && Object.keys(stats.by_case_id).length > 0 && (
        <div className="glass-panel rounded-xl border border-white/10 p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">案例分布 (Top 10)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart 
              data={Object.entries(stats.by_case_id)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 10)
                .map(([case_id, count]) => ({ case_id, count }))}
              layout="vertical"
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis type="number" />
              <YAxis dataKey="case_id" type="category" width={120} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1a233a', border: '1px solid rgba(255,255,255,0.1)' }}
                itemStyle={{ color: '#e2e8f0' }}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Bar dataKey="count" fill="#34d399" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

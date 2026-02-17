// frontend/src/components/pattern/PatternComparison.tsx
/**
 * PatternComparison.tsx
 * 
 * 樣式比較組件
 * 
 * Features:
 * - 多樣式選擇（最多 4 個）
 * - 效能指標並排比較
 * - 規則差異對比
 * - 雷達圖視覺化
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Legend, ResponsiveContainer } from 'recharts';
import { usePatternStore } from '@/store/patternStore';
import { getPattern } from '@/lib/api/patternApi';
import type { Pattern } from '@/lib/patternTypes';

const MAX_PATTERNS = 4;
const COLORS = ['#60a5fa', '#34d399', '#fbbf24', '#fb7185'];

export default function PatternComparison() {
  const { patterns } = usePatternStore();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [selectedPatterns, setSelectedPatterns] = useState<Pattern[]>([]);
  const [loading, setLoading] = useState(false);
  void loading;
  
  const loadSelectedPatterns = useCallback(async () => {
    try {
      setLoading(true);
      const promises = selectedIds.map(id => getPattern(id));
      const loadedResponses = await Promise.all(promises);
      const loaded = loadedResponses
        .filter((response) => response.success && response.pattern)
        .map((response) => response.pattern as Pattern);
      setSelectedPatterns(loaded);
    } catch (error) {
      console.error('載入樣式失敗:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedIds]);

  // 載入選中的樣式
  useEffect(() => {
    if (selectedIds.length === 0) {
      setSelectedPatterns([]);
      return;
    }

    loadSelectedPatterns();
  }, [loadSelectedPatterns, selectedIds.length]);
  
  // 新增樣式
  const handleAddPattern = (patternId: string) => {
    if (selectedIds.includes(patternId)) return;
    if (selectedIds.length >= MAX_PATTERNS) {
      alert(`最多只能比較 ${MAX_PATTERNS} 個樣式`);
      return;
    }
    setSelectedIds([...selectedIds, patternId]);
  };
  
  // 移除樣式
  const handleRemovePattern = (patternId: string) => {
    setSelectedIds(selectedIds.filter(id => id !== patternId));
  };
  
  // 準備雷達圖資料
  const radarData = [
    { metric: '準確度', ...Object.fromEntries(selectedPatterns.map((p, i) => [`pattern${i}`, p.performance_metrics.accuracy])) },
    { metric: '精確度', ...Object.fromEntries(selectedPatterns.map((p, i) => [`pattern${i}`, p.performance_metrics.precision])) },
    { metric: '召回率', ...Object.fromEntries(selectedPatterns.map((p, i) => [`pattern${i}`, p.performance_metrics.recall])) },
    { metric: 'F1 分數', ...Object.fromEntries(selectedPatterns.map((p, i) => [`pattern${i}`, p.performance_metrics.f1_score])) }
  ];
  
  return (
    <div className="space-y-6">
      {/* 樣式選擇器 */}
      <div className="glass-panel rounded-xl border border-white/10 p-6">
        <h2 className="text-lg font-semibold text-slate-100 mb-4">選擇要比較的樣式 (最多 {MAX_PATTERNS} 個)</h2>
        <select
          onChange={(e) => handleAddPattern(e.target.value)}
          value=""
          className="w-full px-3 py-2 border border-white/10 rounded bg-slate-900/60 text-slate-200"
          disabled={selectedIds.length >= MAX_PATTERNS}
        >
          <option value="">-- 選擇樣式 --</option>
          {patterns
            .filter(p => !selectedIds.includes(p.pattern_id))
            .map(pattern => (
              <option key={pattern.pattern_id} value={pattern.pattern_id}>
                {pattern.name} ({pattern.case_id})
              </option>
            ))}
        </select>
        
        {/* 已選樣式列表 */}
        {selectedIds.length > 0 && (
          <div className="mt-4 space-y-2">
            {selectedPatterns.map((pattern, index) => (
              <div key={pattern.pattern_id} className="flex items-center justify-between p-3 bg-white/5 border border-white/10 rounded">
                <div className="flex items-center gap-3">
                  <div 
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: COLORS[index] }}
                  />
                  <div>
                    <p className="font-semibold text-slate-100">{pattern.name}</p>
                    <p className="text-sm text-slate-400">{pattern.case_id}</p>
                  </div>
                </div>
                <button
                  onClick={() => handleRemovePattern(pattern.pattern_id)}
                  className="text-rose-300 hover:text-rose-200"
                >
                  移除
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
      
      {/* 比較結果 */}
      {selectedPatterns.length >= 2 && (
        <div className="space-y-6">
          {/* 雷達圖 */}
          <div className="glass-panel rounded-xl border border-white/10 p-6">
            <h3 className="text-lg font-semibold text-slate-100 mb-4">效能雷達圖</h3>
            <ResponsiveContainer width="100%" height={400}>
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="metric" />
                <PolarRadiusAxis angle={90} domain={[0, 1]} />
                {selectedPatterns.map((pattern, index) => (
                  <Radar
                    key={pattern.pattern_id}
                    name={pattern.name}
                    dataKey={`pattern${index}`}
                    stroke={COLORS[index]}
                    fill={COLORS[index]}
                    fillOpacity={0.3}
                  />
                ))}
                <Legend />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          
          {/* 指標對比表 */}
          <div className="glass-panel rounded-xl border border-white/10 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-white/5 text-slate-200">
                <tr>
                  <th className="px-4 py-3 text-left">指標</th>
                  {selectedPatterns.map((pattern, index) => (
                    <th key={pattern.pattern_id} className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <div 
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: COLORS[index] }}
                        />
                        {pattern.name}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr className="border-b">
                  <td className="px-4 py-3 font-semibold text-slate-100">準確度</td>
                  {selectedPatterns.map(p => (
                    <td key={p.pattern_id} className="px-4 py-3 text-center text-slate-200">
                      {((p.performance_metrics.accuracy ?? 0) * 100).toFixed(1)}%
                    </td>
                  ))}
                </tr>
                <tr className="border-b">
                  <td className="px-4 py-3 font-semibold text-slate-100">精確度</td>
                  {selectedPatterns.map(p => (
                    <td key={p.pattern_id} className="px-4 py-3 text-center text-slate-200">
                      {(p.performance_metrics.precision * 100).toFixed(1)}%
                    </td>
                  ))}
                </tr>
                <tr className="border-b">
                  <td className="px-4 py-3 font-semibold text-slate-100">召回率</td>
                  {selectedPatterns.map(p => (
                    <td key={p.pattern_id} className="px-4 py-3 text-center text-slate-200">
                      {(p.performance_metrics.recall * 100).toFixed(1)}%
                    </td>
                  ))}
                </tr>
                <tr className="border-b">
                  <td className="px-4 py-3 font-semibold text-slate-100">F1 分數</td>
                  {selectedPatterns.map(p => (
                    <td key={p.pattern_id} className="px-4 py-3 text-center text-slate-200">
                      {p.performance_metrics.f1_score.toFixed(3)}
                    </td>
                  ))}
                </tr>
                <tr className="border-b">
                  <td className="px-4 py-3 font-semibold text-slate-100">規則數量</td>
                  {selectedPatterns.map(p => (
                    <td key={p.pattern_id} className="px-4 py-3 text-center text-slate-200">
                      {p.rules.length}
                    </td>
                  ))}
                </tr>
                <tr className="border-b">
                  <td className="px-4 py-3 font-semibold text-slate-100">樣本數</td>
                  {selectedPatterns.map(p => (
                    <td key={p.pattern_id} className="px-4 py-3 text-center text-slate-200">
                      {p.performance_metrics.sample_count}
                    </td>
                  ))}
                </tr>
                <tr className="border-b">
                  <td className="px-4 py-3 font-semibold text-slate-100">狀態</td>
                  {selectedPatterns.map(p => (
                    <td key={p.pattern_id} className="px-4 py-3 text-center">
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        p.status === 'active' ? 'bg-emerald-500/20 text-emerald-200' :
                        p.status === 'testing' ? 'bg-amber-500/20 text-amber-200' :
                        'bg-slate-500/20 text-slate-200'
                      }`}>
                        {p.status === 'active' ? '啟用' :
                         p.status === 'testing' ? '測試' : '封存'}
                      </span>
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
          
          {/* 規則對比 */}
          <div className="glass-panel rounded-xl border border-white/10 p-6">
            <h3 className="text-lg font-semibold text-slate-100 mb-4">規則對比</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {selectedPatterns.map((pattern, index) => (
                <div key={pattern.pattern_id} className="border border-white/10 rounded p-4 bg-white/5">
                  <div className="flex items-center gap-2 mb-3">
                    <div 
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: COLORS[index] }}
                    />
                    <h4 className="font-semibold text-slate-100">{pattern.name}</h4>
                  </div>
                  <div className="space-y-2">
                    {pattern.rules.map((rule, rIndex) => (
                      <div key={rIndex} className="text-sm bg-slate-900/60 border border-white/10 p-2 rounded font-mono text-slate-200">
                        {rule.feature} {rule.operator} {rule.threshold}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      
      {/* 空狀態 */}
      {selectedPatterns.length < 2 && (
        <div className="glass-panel rounded-xl border-2 border-dashed border-white/10 p-12 text-center">
          <p className="text-slate-400 text-lg">請選擇至少 2 個樣式進行比較</p>
        </div>
      )}
    </div>
  );
}

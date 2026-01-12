// frontend/src/components/pattern/DecisionRuleTable.tsx
/**
 * DecisionRuleTable.tsx
 * 
 * 顯示 XGBoost 提取的決策規則表格
 * 
 * Features:
 * - 表格顯示規則條件、支持度、信心度、提升
 * - 依信心度或提升排序
 * - 高亮顯示高信心度規則
 * - CSV 匯出功能
 */

'use client';

import React, { useState, useMemo } from 'react';
import type { DecisionRule } from '@/lib/patternTypes';

interface Props {
  rules: DecisionRule[];
}

export default function DecisionRuleTable({ rules }: Props) {
  const [sortBy, setSortBy] = useState<'confidence' | 'lift' | 'support'>('confidence');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  
  // 排序後的規則
  const sortedRules = useMemo(() => {
    const sorted = [...rules].sort((a, b) => {
      let aVal = 0, bVal = 0;
      
      if (sortBy === 'confidence') {
        aVal = a.confidence;
        bVal = b.confidence;
      } else if (sortBy === 'lift') {
        aVal = a.lift;
        bVal = b.lift;
      } else {
        aVal = a.support;
        bVal = b.support;
      }
      
      return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
    });
    
    return sorted;
  }, [rules, sortBy, sortOrder]);
  
  const handleSort = (column: 'confidence' | 'lift' | 'support') => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };
  
  const handleExportCSV = () => {
    const headers = ['規則ID', '條件', '支持度', '信心度', '提升'];
    const rows = sortedRules.map(rule => [
      rule.rule_id,
      rule.condition,
      rule.support,
      rule.confidence.toFixed(4),
      rule.lift.toFixed(4)
    ]);
    
    const csv = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');
    
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `decision_rules_${Date.now()}.csv`;
    link.click();
  };
  
  if (rules.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        沒有決策規則資料
      </div>
    );
  }
  
  return (
    <div className="bg-white rounded-lg border">
      {/* 標題與控制 */}
      <div className="flex justify-between items-center p-4 border-b">
        <h3 className="text-lg font-bold">決策規則 (共 {rules.length} 條)</h3>
        <button
          onClick={handleExportCSV}
          className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
        >
          匯出 CSV
        </button>
      </div>
      
      {/* 表格 */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left">#</th>
              <th className="px-4 py-2 text-left">條件</th>
              <th 
                className="px-4 py-2 text-right cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('support')}
              >
                支持度 {sortBy === 'support' && (sortOrder === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="px-4 py-2 text-right cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('confidence')}
              >
                信心度 {sortBy === 'confidence' && (sortOrder === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="px-4 py-2 text-right cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('lift')}
              >
                提升 {sortBy === 'lift' && (sortOrder === 'asc' ? '↑' : '↓')}
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedRules.map((rule, index) => {
              // 根據信心度決定背景顏色
              const bgColor = 
                rule.confidence >= 0.7 ? 'bg-green-50' :
                rule.confidence >= 0.6 ? 'bg-yellow-50' :
                '';
              
              return (
                <tr key={rule.rule_id} className={`border-b hover:bg-gray-50 ${bgColor}`}>
                  <td className="px-4 py-2">{index + 1}</td>
                  <td className="px-4 py-2 font-mono text-xs">{rule.condition}</td>
                  <td className="px-4 py-2 text-right">{rule.support}</td>
                  <td className="px-4 py-2 text-right">
                    <span className={getConfidenceColor(rule.confidence)}>
                      {(rule.confidence * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <span className={getLiftColor(rule.lift)}>
                      {rule.lift.toFixed(2)}x
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      
      {/* 說明 */}
      <div className="p-4 text-xs text-gray-500 border-t">
        <p>💡 信心度: 符合此規則的樣本中盈利的比例</p>
        <p>💡 提升: 相對於基準盈利概率的提升倍數</p>
        <p>💡 支持度: 符合此規則的樣本數量</p>
      </div>
    </div>
  );
}

// 信心度顏色
function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.7) return 'text-green-600 font-semibold';
  if (confidence >= 0.6) return 'text-yellow-600 font-semibold';
  return 'text-gray-600';
}

// 提升顏色
function getLiftColor(lift: number): string {
  if (lift >= 1.5) return 'text-green-600 font-semibold';
  if (lift >= 1.2) return 'text-yellow-600 font-semibold';
  return 'text-gray-600';
}

// frontend/src/components/pattern/PatternList.tsx
/**
 * PatternList.tsx
 * 
 * 顯示所有模式的列表，支援過濾和排序
 * 
 * Features:
 * - 顯示模式卡片（名稱、描述、規則數、效能指標）
 * - 依狀態過濾（active/archived/testing）
 * - 依標籤過濾
 * - 點擊卡片查看詳情
 * - 刪除模式功能
 */

'use client';

import React, { useEffect, useState } from 'react';
import { usePatternStore } from '@/store/patternStore';
import { listPatterns, deletePattern } from '@/lib/api/patternApi';
import type { Pattern } from '@/lib/patternTypes';

export default function PatternList() {
  const {
    patterns,
    setPatterns,
    selectPattern,
    filters,
    getFilteredPatterns
  } = usePatternStore();
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 載入模式列表
  useEffect(() => {
    loadPatterns();
  }, [filters.status, filters.tags]);
  
  const loadPatterns = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await listPatterns(
        filters.status || undefined,
        filters.tags.length > 0 ? filters.tags : undefined
      );
      
      if (response.success) {
        setPatterns(response.patterns);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load patterns');
    } finally {
      setLoading(false);
    }
  };
  
  const handleDelete = async (patternId: string) => {
    if (!confirm('確定要刪除此模式嗎？')) return;
    
    try {
      const response = await deletePattern(patternId);
      if (response.success) {
        loadPatterns(); // 重新載入
      }
    } catch (err) {
      alert('刪除失敗: ' + (err instanceof Error ? err.message : 'Unknown error'));
    }
  };
  
  const filteredPatterns = getFilteredPatterns();
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">載入中...</div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">錯誤: {error}</p>
        <button 
          onClick={loadPatterns}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          重試
        </button>
      </div>
    );
  }
  
  if (filteredPatterns.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 mb-4">沒有符合條件的模式</p>
        <button 
          onClick={loadPatterns}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          重新整理
        </button>
      </div>
    );
  }
  
  return (
    <div className="space-y-4">
      {/* 標題與統計 */}
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">模式列表</h2>
        <span className="text-sm text-gray-600">共 {filteredPatterns.length} 個模式</span>
      </div>
      
      {/* 模式卡片網格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredPatterns.map((pattern) => (
          <PatternCard
            key={pattern.pattern_id}
            pattern={pattern}
            onSelect={() => selectPattern(pattern.pattern_id)}
            onDelete={() => handleDelete(pattern.pattern_id)}
          />
        ))}
      </div>
    </div>
  );
}

// 模式卡片組件
function PatternCard({ 
  pattern, 
  onSelect, 
  onDelete 
}: { 
  pattern: Pattern; 
  onSelect: () => void; 
  onDelete: () => void;
}) {
  const statusColors = {
    active: 'bg-green-100 text-green-800',
    archived: 'bg-gray-100 text-gray-800',
    testing: 'bg-yellow-100 text-yellow-800'
  };
  
  return (
    <div 
      className="border rounded-lg p-4 hover:shadow-lg transition-shadow cursor-pointer bg-white"
      onClick={onSelect}
    >
      {/* 標題與狀態 */}
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-bold text-lg truncate flex-1 text-gray-900">{pattern.name}</h3>
        <span className={`text-xs px-2 py-1 rounded font-semibold ${statusColors[pattern.status]}`}>
          {pattern.status}
        </span>
      </div>
      
      {/* 描述 */}
      <p className="text-sm text-gray-800 mb-3 line-clamp-2 leading-relaxed">
        {pattern.description}
      </p>
      
      {/* 規則數量 */}
      <div className="text-sm text-gray-800 mb-3">
        規則數: <span className="font-bold text-gray-900">{pattern.rules.length}</span>
      </div>
      
      {/* 效能指標 */}
      <div className="grid grid-cols-3 gap-2 mb-3 text-xs">
        <div className="text-center">
          <div className="text-gray-700 font-semibold">Precision</div>
          <div className="font-bold text-gray-900">{(pattern.performance_metrics.precision * 100).toFixed(1)}%</div>
        </div>
        <div className="text-center">
          <div className="text-gray-700 font-semibold">Recall</div>
          <div className="font-bold text-gray-900">{(pattern.performance_metrics.recall * 100).toFixed(1)}%</div>
        </div>
        <div className="text-center">
          <div className="text-gray-700 font-semibold">F1</div>
          <div className="font-bold text-gray-900">{(pattern.performance_metrics.f1_score * 100).toFixed(1)}%</div>
        </div>
      </div>
      
      {/* 標籤 */}
      {pattern.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {pattern.tags.slice(0, 3).map(tag => (
            <span key={tag} className="text-xs bg-blue-100 text-blue-900 px-2 py-1 rounded font-semibold">
              {tag}
            </span>
          ))}
          {pattern.tags.length > 3 && (
            <span className="text-xs text-gray-800 font-semibold">+{pattern.tags.length - 3}</span>
          )}
        </div>
      )}
      
      {/* 操作按鈕 */}
      <div className="flex gap-2 pt-3 border-t">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onSelect();
          }}
          className="flex-1 px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          查看詳情
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
        >
          刪除
        </button>
      </div>
    </div>
  );
}

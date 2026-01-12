// frontend/src/components/pattern/PatternFilters.tsx
/**
 * PatternFilters.tsx
 * 
 * 樣式篩選器組件
 * 
 * Features:
 * - 狀態篩選（active/testing/archived）
 * - 標籤篩選
 * - 案例 ID 搜尋
 * - 清除篩選
 */

'use client';

import React, { useState } from 'react';
import { usePatternStore } from '@/store/patternStore';

export default function PatternFilters() {
  const { filters, setFilterStatus, setFilterTags, setFilterCaseId } = usePatternStore();
  const [caseIdInput, setCaseIdInput] = useState(filters.case_id || '');
  const [tagInput, setTagInput] = useState('');
  
  // 清除所有篩選
  const handleClearAll = () => {
    setFilterStatus(undefined);
    setFilterTags([]);
    setFilterCaseId(undefined);
    setCaseIdInput('');
    setTagInput('');
  };
  
  // 新增標籤篩選
  const handleAddTag = () => {
    if (tagInput.trim() && !filters.tags.includes(tagInput.trim())) {
      setFilterTags([...filters.tags, tagInput.trim()]);
      setTagInput('');
    }
  };
  
  // 移除標籤篩選
  const handleRemoveTag = (tag: string) => {
    setFilterTags(filters.tags.filter(t => t !== tag));
  };
  
  // 應用案例 ID 篩選
  const handleApplyCaseId = () => {
    setFilterCaseId(caseIdInput.trim() || undefined);
  };
  
  return (
    <div className="bg-white rounded-lg border p-4 space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-bold">篩選器</h3>
        <button
          onClick={handleClearAll}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          清除全部
        </button>
      </div>
      
      {/* 狀態篩選 */}
      <div>
        <label className="block text-sm font-semibold mb-2">狀態</label>
        <div className="flex gap-2">
          <button
            onClick={() => setFilterStatus(undefined)}
            className={`px-3 py-1 rounded text-sm ${
              filters.status === undefined
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            全部
          </button>
          <button
            onClick={() => setFilterStatus('active')}
            className={`px-3 py-1 rounded text-sm ${
              filters.status === 'active'
                ? 'bg-green-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            啟用中
          </button>
          <button
            onClick={() => setFilterStatus('testing')}
            className={`px-3 py-1 rounded text-sm ${
              filters.status === 'testing'
                ? 'bg-yellow-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            測試中
          </button>
          <button
            onClick={() => setFilterStatus('archived')}
            className={`px-3 py-1 rounded text-sm ${
              filters.status === 'archived'
                ? 'bg-gray-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            已封存
          </button>
        </div>
      </div>
      
      {/* 案例 ID 搜尋 */}
      <div>
        <label className="block text-sm font-semibold mb-2">案例 ID</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={caseIdInput}
            onChange={(e) => setCaseIdInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleApplyCaseId()}
            placeholder="輸入案例 ID 搜尋"
            className="flex-1 px-3 py-2 border rounded text-sm"
          />
          <button
            onClick={handleApplyCaseId}
            className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
          >
            搜尋
          </button>
        </div>
        {filters.case_id && (
          <p className="text-xs text-gray-500 mt-1">
            目前搜尋: <span className="font-semibold">{filters.case_id}</span>
          </p>
        )}
      </div>
      
      {/* 標籤篩選 */}
      <div>
        <label className="block text-sm font-semibold mb-2">標籤</label>
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
            placeholder="輸入標籤篩選"
            className="flex-1 px-3 py-2 border rounded text-sm"
          />
          <button
            onClick={handleAddTag}
            className="px-4 py-2 bg-gray-200 rounded text-sm hover:bg-gray-300"
          >
            新增
          </button>
        </div>
        
        {/* 已選標籤 */}
        {filters.tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {filters.tags.map(tag => (
              <span key={tag} className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm flex items-center gap-2">
                {tag}
                <button
                  onClick={() => handleRemoveTag(tag)}
                  className="text-blue-600 hover:text-blue-800"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
      </div>
      
      {/* 篩選結果統計 */}
      <div className="pt-3 border-t text-sm text-gray-500">
        {filters.status !== undefined && <p>✓ 狀態篩選已啟用</p>}
        {filters.case_id && <p>✓ 案例 ID 搜尋已啟用</p>}
        {filters.tags.length > 0 && <p>✓ 標籤篩選已啟用 ({filters.tags.length} 個)</p>}
        {filters.status === undefined && !filters.case_id && filters.tags.length === 0 && (
          <p>未啟用任何篩選</p>
        )}
      </div>
    </div>
  );
}

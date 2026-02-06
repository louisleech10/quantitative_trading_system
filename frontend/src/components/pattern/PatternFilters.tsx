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
    <div className="glass-panel rounded-xl border border-white/10 p-4 space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-medium text-slate-100 text-base">篩選器</h3>
        <button
          onClick={handleClearAll}
          className="text-sm text-blue-300 hover:text-blue-200 font-medium"
        >
          清除全部
        </button>
      </div>
      
      {/* 狀態篩選 */}
      <div>
        <label className="block text-sm font-medium mb-2 text-slate-200">狀態</label>
        <div className="flex gap-2">
          <button
            onClick={() => setFilterStatus(undefined)}
            className={`px-3 py-1 rounded text-sm font-semibold ${
              filters.status === undefined
                ? 'bg-blue-500/20 text-blue-200 border border-blue-400/40'
                : 'bg-white/10 text-slate-100 hover:bg-white/15'
            }`}
          >
            全部
          </button>
          <button
            onClick={() => setFilterStatus('active')}
            className={`px-3 py-1 rounded text-sm font-semibold ${
              filters.status === 'active'
                ? 'bg-emerald-500/20 text-emerald-200 border border-emerald-400/40'
                : 'bg-white/10 text-slate-100 hover:bg-white/15'
            }`}
          >
            啟用中
          </button>
          <button
            onClick={() => setFilterStatus('testing')}
            className={`px-3 py-1 rounded text-sm font-semibold ${
              filters.status === 'testing'
                ? 'bg-amber-500/20 text-amber-200 border border-amber-400/40'
                : 'bg-white/10 text-slate-100 hover:bg-white/15'
            }`}
          >
            測試中
          </button>
          <button
            onClick={() => setFilterStatus('archived')}
            className={`px-3 py-1 rounded text-sm font-semibold ${
              filters.status === 'archived'
                ? 'bg-slate-700/60 text-slate-200 border border-slate-600'
                : 'bg-white/10 text-slate-100 hover:bg-white/15'
            }`}
          >
            已封存
          </button>
        </div>
      </div>
      
      {/* 案例 ID 搜尋 */}
      <div>
        <label className="block text-sm font-medium mb-2 text-slate-200">案例 ID</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={caseIdInput}
            onChange={(e) => setCaseIdInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleApplyCaseId()}
            placeholder="輸入案例 ID 搜尋"
            className="flex-1 px-3 py-2 border border-white/10 rounded text-sm text-slate-100 placeholder:text-slate-500 bg-white/5"
          />
          <button
            onClick={handleApplyCaseId}
            className="px-4 py-2 bg-blue-500/20 text-blue-200 border border-blue-400/40 rounded text-sm hover:bg-blue-500/30 font-semibold"
          >
            搜尋
          </button>
        </div>
        {filters.case_id && (
          <p className="text-xs text-slate-400 mt-1">
            目前搜尋: <span className="font-semibold text-slate-100">{filters.case_id}</span>
          </p>
        )}
      </div>
      
      {/* 標籤篩選 */}
      <div>
        <label className="block text-sm font-medium mb-2 text-slate-200">標籤</label>
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
            placeholder="輸入標籤篩選"
            className="flex-1 px-3 py-2 border border-white/10 rounded text-sm text-slate-100 placeholder:text-slate-500 bg-white/5"
          />
          <button
            onClick={handleAddTag}
            className="px-4 py-2 bg-white/10 rounded text-sm hover:bg-white/15 font-semibold text-slate-100"
          >
            新增
          </button>
        </div>
        
        {/* 已選標籤 */}
        {filters.tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {filters.tags.map(tag => (
              <span key={tag} className="px-3 py-1 bg-blue-500/15 text-blue-200 rounded-full text-sm font-semibold flex items-center gap-2">
                {tag}
                <button
                  onClick={() => handleRemoveTag(tag)}
                  className="text-blue-200 hover:text-blue-100 font-semibold text-base"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
      </div>
      
      {/* 篩選結果統計 */}
      <div className="pt-3 border-t border-white/10 text-sm text-slate-400 font-medium">
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

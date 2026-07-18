// frontend/src/components/pattern/CreatePatternForm.tsx
/**
 * CreatePatternForm.tsx
 * 
 * 建立新樣式定義表單
 * 
 * Features:
 * - 從 XGBoost 分析結果預填充
 * - 動態新增/刪除規則
 * - 規則驗證（語法、特徵名稱、操作符）
 * - 標籤管理
 */

'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { usePatternStore } from '@/store/patternStore';
import { createPattern } from '@/lib/api/patternApi';
import type { CreatePatternRequest } from '@/lib/patternTypes';

interface Props {
  prefillData?: {
    task_id?: string;
    case_id?: string;
    performance_metrics?: unknown;
  };
}

export default function CreatePatternForm({ prefillData }: Props) {
  const router = useRouter();
  const { addPattern } = usePatternStore();
  
  // 表單狀態（LA-2 B3：server 權威 — 需 task_id；rules 由 server 重建）
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [taskId, setTaskId] = useState(prefillData?.task_id || '');
  const [tags, setTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState('');
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  // 新增標籤
  const handleAddTag = () => {
    if (newTag.trim() && !tags.includes(newTag.trim())) {
      setTags([...tags, newTag.trim()]);
      setNewTag('');
    }
  };
  
  // 刪除標籤
  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter(t => t !== tag));
  };
  
  // 驗證表單
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (!name.trim()) newErrors.name = '樣式名稱必填';
    if (!taskId.trim()) newErrors.task_id = 'task_id 必填（server 從 oot_receipt 重建 rules）';
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  // 提交表單
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    try {
      setIsSubmitting(true);
      
      const request: CreatePatternRequest = {
        name,
        description,
        task_id: taskId,
        tags: tags.length > 0 ? tags : undefined,
      };
      
      const created = await createPattern(request);
      if (!created.success || !created.pattern) {
        throw new Error(created.error || '建立樣式失敗');
      }

      addPattern(created.pattern);
      router.push(`/patterns/${created.pattern.pattern_id}`);
    } catch (error) {
      console.error('建立樣式失敗:', error);
      setErrors({ submit: error instanceof Error ? error.message : '未知錯誤' });
    } finally {
      setIsSubmitting(false);
    }
  };
  
  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* 基本資訊 */}
      <div className="glass-panel rounded-xl border border-white/10 p-6">
        <h2 className="text-lg font-semibold text-slate-100 mb-4">基本資訊</h2>
        
        <div className="space-y-4">
          {/* 樣式名稱 */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">樣式名稱 *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如：強勢突破樣式"
              className="w-full px-3 py-2 border border-white/10 rounded text-slate-100 placeholder-slate-500 bg-white/5 focus:border-blue-400/40 focus:ring-1 focus:ring-blue-400/40"
            />
            {errors.name && <p className="text-rose-300 text-sm mt-1">{errors.name}</p>}
          </div>
          
          {/* 描述 */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">描述</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="描述此樣式的特徵與適用場景"
              rows={3}
              className="w-full px-3 py-2 border border-white/10 rounded text-slate-100 placeholder-slate-500 bg-white/5 focus:border-blue-400/40 focus:ring-1 focus:ring-blue-400/40"
            />
          </div>
          
          {/* task_id（server 從 oot_receipt 重建 rules/status） */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Task ID *</label>
            <input
              type="text"
              value={taskId}
              onChange={(e) => setTaskId(e.target.value)}
              placeholder="XGBoost / batch 分析 task_id"
              className="w-full px-3 py-2 border border-white/10 rounded text-slate-100 placeholder-slate-500 bg-white/5 focus:border-blue-400/40 focus:ring-1 focus:ring-blue-400/40"
            />
            {errors.task_id && <p className="text-rose-300 text-sm mt-1">{errors.task_id}</p>}
            <p className="text-xs text-slate-500 mt-1">
              rules / performance / status 由 server 依 OOT receipt 推導（禁 client 偽造）
            </p>
          </div>
        </div>
      </div>
      
      {/* 標籤 */}
      <div className="glass-panel rounded-xl border border-white/10 p-6">
        <h2 className="text-lg font-semibold text-slate-100 mb-4">標籤</h2>
        
        {/* 標籤輸入 */}
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            value={newTag}
            onChange={(e) => setNewTag(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
            placeholder="輸入標籤後按 Enter"
            className="flex-1 px-3 py-2 border border-white/10 rounded text-slate-100 placeholder-slate-500 bg-white/5 focus:border-blue-400/40 focus:ring-1 focus:ring-blue-400/40"
          />
          <button
            type="button"
            onClick={handleAddTag}
            className="px-4 py-2 bg-white/10 text-slate-100 rounded hover:bg-white/15"
          >
            新增
          </button>
        </div>
        
        {/* 標籤列表 */}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {tags.map(tag => (
              <span key={tag} className="px-3 py-1 bg-blue-400/15 text-blue-200 rounded-full text-sm flex items-center gap-2">
                {tag}
                <button
                  type="button"
                  onClick={() => handleRemoveTag(tag)}
                  className="text-blue-200 hover:text-blue-100"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
      </div>
      
      {/* 提交按鈕 */}
      <div className="flex justify-end gap-3">
        <button
          type="button"
          onClick={() => router.back()}
          className="px-6 py-2 border border-white/10 rounded text-slate-200 hover:bg-white/5"
        >
          取消
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-6 py-2 bg-blue-500/20 text-blue-100 rounded border border-blue-400/40 hover:bg-blue-500/30 disabled:bg-slate-700/60 disabled:text-slate-400"
        >
          {isSubmitting ? '建立中...' : '建立樣式'}
        </button>
      </div>
      
      {/* 錯誤訊息 */}
      {errors.submit && (
        <div className="p-3 bg-rose-500/10 border border-rose-400/30 rounded text-rose-200 text-sm">
          ❌ {errors.submit}
        </div>
      )}
    </form>
  );
}

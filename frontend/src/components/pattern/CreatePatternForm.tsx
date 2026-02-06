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
import type { CreatePatternRequest, PatternRule } from '@/lib/patternTypes';

interface Props {
  prefillData?: {
    case_id: string;
    rules?: PatternRule[];
    performance_metrics?: any;
  };
}

export default function CreatePatternForm({ prefillData }: Props) {
  const router = useRouter();
  const { addPattern } = usePatternStore();
  
  // 表單狀態
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [caseId, setCaseId] = useState(prefillData?.case_id || '');
  const [rules, setRules] = useState<PatternRule[]>(prefillData?.rules || [
    { feature: '', operator: '>', threshold: 0, description: '' }
  ]);
  const [tags, setTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState('');
  const [status, setStatus] = useState<string>('testing');
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  // 新增規則
  const handleAddRule = () => {
    setRules([...rules, { feature: '', operator: '>', threshold: 0, description: '' }]);
  };
  
  // 刪除規則
  const handleRemoveRule = (index: number) => {
    setRules(rules.filter((_, i) => i !== index));
  };
  
  // 更新規則
  const handleRuleChange = (index: number, field: keyof PatternRule, value: any) => {
    const updated = [...rules];
    updated[index] = { ...updated[index], [field]: value };
    setRules(updated);
  };
  
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
    if (!caseId.trim()) newErrors.case_id = '案例 ID 必填';
    if (rules.length === 0) newErrors.rules = '至少需要一條規則';
    
    // 驗證每條規則
    rules.forEach((rule, index) => {
      if (!rule.feature.trim()) {
        newErrors[`rule_${index}_feature`] = `規則 ${index + 1} 的特徵必填`;
      }
      if (rule.threshold === null || rule.threshold === undefined) {
        newErrors[`rule_${index}_threshold`] = `規則 ${index + 1} 的閾值必填`;
      }
    });
    
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
        case_id: caseId,
        rules: rules.map(r => ({
          feature: r.feature,
          operator: r.operator,
          threshold: r.threshold,
          description: r.description
        })),
        tags: tags.length > 0 ? tags : undefined,
        status,
        performance_metrics: prefillData?.performance_metrics
      };
      
      const created = await createPattern(request);
      addPattern(created);
      router.push(`/patterns/${created.pattern_id}`);
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
          
          {/* 案例 ID */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">案例 ID *</label>
            <input
              type="text"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
              placeholder="例如：ETHUSDT_12h"
              className="w-full px-3 py-2 border border-white/10 rounded text-slate-100 placeholder-slate-500 bg-white/5 focus:border-blue-400/40 focus:ring-1 focus:ring-blue-400/40"
            />
            {errors.case_id && <p className="text-rose-300 text-sm mt-1">{errors.case_id}</p>}
          </div>
          
          {/* 狀態 */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">狀態</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full px-3 py-2 border border-white/10 rounded text-slate-100 bg-slate-900/60 focus:border-blue-400/40 focus:ring-1 focus:ring-blue-400/40"
            >
              <option value="testing">測試中</option>
              <option value="active">啟用</option>
              <option value="archived">封存</option>
            </select>
          </div>
        </div>
      </div>
      
      {/* 規則列表 */}
      <div className="glass-panel rounded-xl border border-white/10 p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-slate-100">樣式規則</h2>
          <button
            type="button"
            onClick={handleAddRule}
            className="px-3 py-1 bg-blue-500/20 text-blue-200 border border-blue-400/40 rounded text-sm hover:bg-blue-500/30"
          >
            + 新增規則
          </button>
        </div>
        
        {errors.rules && <p className="text-rose-300 text-sm mb-3">{errors.rules}</p>}
        
        <div className="space-y-4">
          {rules.map((rule, index) => (
            <div key={index} className="p-4 border border-white/10 rounded bg-white/5">
              <div className="flex justify-between items-start mb-3">
                <h3 className="font-semibold text-slate-100">規則 {index + 1}</h3>
                {rules.length > 1 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveRule(index)}
                    className="text-rose-300 text-sm hover:text-rose-200"
                  >
                    刪除
                  </button>
                )}
              </div>
              
              <div className="grid grid-cols-4 gap-3">
                {/* 特徵 */}
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">特徵 *</label>
                  <input
                    type="text"
                    value={rule.feature}
                    onChange={(e) => handleRuleChange(index, 'feature', e.target.value)}
                    placeholder="例如：ema_20"
                    className="w-full px-2 py-1 border border-white/10 rounded text-sm text-slate-100 placeholder-slate-500 bg-white/5 focus:border-blue-400/40 focus:ring-1 focus:ring-blue-400/40"
                  />
                  {errors[`rule_${index}_feature`] && (
                    <p className="text-rose-300 text-xs mt-1">{errors[`rule_${index}_feature`]}</p>
                  )}
                </div>
                
                {/* 操作符 */}
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">操作符 *</label>
                  <select
                    value={rule.operator}
                    onChange={(e) => handleRuleChange(index, 'operator', e.target.value)}
                    className="w-full px-2 py-1 border border-white/10 rounded text-sm text-slate-100 bg-slate-900/60 focus:border-blue-400/40 focus:ring-1 focus:ring-blue-400/40"
                  >
                    <option value=">">{'>'}</option>
                    <option value="<">{'<'}</option>
                    <option value=">=">{'>='}</option>
                    <option value="<=">{'<='}</option>
                    <option value="==">{'=='}</option>
                    <option value="!=">{'!='}</option>
                  </select>
                </div>
                
                {/* 閾值 */}
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">閾值 *</label>
                  <input
                    type="number"
                    step="any"
                    value={rule.threshold}
                    onChange={(e) => handleRuleChange(index, 'threshold', parseFloat(e.target.value))}
                    className="w-full px-2 py-1 border border-white/10 rounded text-sm text-slate-100 bg-white/5 focus:border-blue-400/40 focus:ring-1 focus:ring-blue-400/40"
                  />
                  {errors[`rule_${index}_threshold`] && (
                    <p className="text-rose-300 text-xs mt-1">{errors[`rule_${index}_threshold`]}</p>
                  )}
                </div>
                
                {/* 說明 */}
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">說明</label>
                  <input
                    type="text"
                    value={rule.description || ''}
                    onChange={(e) => handleRuleChange(index, 'description', e.target.value)}
                    placeholder="選填"
                    className="w-full px-2 py-1 border border-white/10 rounded text-sm text-slate-100 placeholder-slate-500 bg-white/5 focus:border-blue-400/40 focus:ring-1 focus:ring-blue-400/40"
                  />
                </div>
              </div>
            </div>
          ))}
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

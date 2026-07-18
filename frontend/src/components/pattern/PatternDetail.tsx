// frontend/src/components/pattern/PatternDetail.tsx
/**
 * PatternDetail.tsx
 * 
 * 樣式詳細資訊頁面
 * 
 * Features:
 * - 顯示完整樣式資訊（規則、效能、標籤）
 * - 編輯/刪除操作
 * - 狀態切換（active/testing/archived）
 * - 規則表格顯示
 */

'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { usePatternStore } from '@/store/patternStore';
import { deletePattern } from '@/lib/api/patternApi';
import type { Pattern } from '@/lib/patternTypes';

interface IndicatorConfigItem {
  indicator?: string;
  data_source?: string;
  params?: Record<string, unknown>;
}

interface Props {
  pattern: Pattern;
  onUpdate?: () => void;
}

export default function PatternDetail({ pattern }: Props) {
  // B3-F3：onUpdate 保留在 Props 供 caller 相容，本元件未使用（eslint no-unused-vars）
  const router = useRouter();
  const { deletePattern: deletePatternInStore } = usePatternStore();
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  
  // 刪除樣式
  const handleDelete = async () => {
    try {
      setIsDeleting(true);
      await deletePattern(pattern.pattern_id);
      deletePatternInStore(pattern.pattern_id);
      router.push('/patterns');
    } catch (error) {
      console.error('刪除樣式失敗:', error);
      alert('刪除失敗: ' + (error instanceof Error ? error.message : '未知錯誤'));
    } finally {
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };
  
  // LA-2 B3：status 由 server oot_receipt 推導，禁 client 直改
  
  return (
    <div className="space-y-6">
      {/* 標題區域 */}
      <div className="glass-panel rounded-xl border border-white/10 p-6">
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <h1 className="text-2xl font-semibold mb-2 text-slate-100">{pattern.name}</h1>
            <p className="text-slate-300">{pattern.description}</p>
            
            {/* 狀態標籤 */}
            <div className="flex gap-2 mt-3">
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                pattern.status === 'active' ? 'bg-emerald-400/15 text-emerald-300' :
                pattern.status === 'testing' ? 'bg-amber-400/15 text-amber-200' :
                'bg-white/10 text-slate-300'
              }`}>
                {pattern.status === 'active' ? '啟用中' :
                 pattern.status === 'testing' ? '測試中' : '已封存'}
              </span>
              
              {/* 標籤 */}
              {pattern.tags && pattern.tags.length > 0 && pattern.tags.map(tag => (
                <span key={tag} className="px-3 py-1 bg-blue-400/10 text-blue-300 rounded-full text-sm">
                  {tag}
                </span>
              ))}
            </div>
          </div>
          
          {/* 操作按鈕（status 唯讀 — server OOT receipt 權威） */}
          <div className="flex gap-2">
            <span className="px-3 py-2 border border-white/10 rounded bg-white/5 text-slate-300 text-sm">
              status: {pattern.status}（server 推導）
            </span>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="px-4 py-2 bg-rose-500/20 text-rose-100 rounded border border-rose-400/40 hover:bg-rose-500/30"
            >
              刪除
            </button>
          </div>
        </div>
        
        {/* 基本資訊 */}
        <div className="grid grid-cols-3 gap-4 mt-6 pt-4 border-t border-white/10">
          <div>
            <p className="text-sm text-slate-400 font-medium">案例 ID</p>
            <p className="font-semibold text-slate-100">{pattern.case_id}</p>
          </div>
          <div>
            <p className="text-sm text-slate-400 font-medium">建立時間</p>
            <p className="font-semibold text-slate-100">{new Date(pattern.created_at).toLocaleDateString()}</p>
          </div>
          <div>
            <p className="text-sm text-slate-400 font-medium">最後更新</p>
            <p className="font-semibold text-slate-100">{new Date(pattern.updated_at).toLocaleDateString()}</p>
          </div>
        </div>
      </div>
      
      {/* 效能指標 */}
      <div className="glass-panel rounded-xl border border-white/10 p-6">
        <h2 className="text-lg font-semibold mb-4 text-slate-100">效能指標</h2>
        
        {!pattern.performance_metrics || Object.keys(pattern.performance_metrics).length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            <p>無效能指標資料</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {/* 精確度 Precision */}
              {pattern.performance_metrics.precision !== undefined && (
                <div className="text-center p-4 bg-white/5 border border-white/10 rounded">
                  <p className="text-sm text-slate-400 font-medium mb-1">精確度</p>
                  <p className="text-2xl font-semibold text-emerald-300">
                    {(pattern.performance_metrics.precision * 100).toFixed(1)}%
                  </p>
                </div>
              )}
              
              {/* 召回率 Recall */}
              {pattern.performance_metrics.recall !== undefined && (
                <div className="text-center p-4 bg-white/5 border border-white/10 rounded">
                  <p className="text-sm text-slate-400 font-medium mb-1">召回率</p>
                  <p className="text-2xl font-semibold text-amber-300">
                    {(pattern.performance_metrics.recall * 100).toFixed(1)}%
                  </p>
                </div>
              )}
              
              {/* F1 分數 */}
              {pattern.performance_metrics.f1_score !== undefined && (
                <div className="text-center p-4 bg-white/5 border border-white/10 rounded">
                  <p className="text-sm text-slate-400 font-medium mb-1">F1 分數</p>
                  <p className="text-2xl font-semibold text-purple-400">
                    {(pattern.performance_metrics.f1_score * 100).toFixed(1)}%
                  </p>
                </div>
              )}
              
              {/* 準確度 Accuracy (舊版相容) */}
              {pattern.performance_metrics.accuracy !== undefined && (
                <div className="text-center p-4 bg-white/5 border border-white/10 rounded">
                  <p className="text-sm text-slate-400 font-medium mb-1">準確度</p>
                  <p className="text-2xl font-semibold text-blue-300">
                    {(pattern.performance_metrics.accuracy * 100).toFixed(1)}%
                  </p>
                </div>
              )}
              
              {/* In-sample Train AUC (XGBoost; LA-2 B2 rename) */}
              {pattern.performance_metrics.in_sample_train_auc !== undefined && (
                <div className="text-center p-4 bg-white/5 border border-white/10 rounded">
                  <p className="text-sm text-slate-400 font-medium mb-1">In-sample Train AUC</p>
                  <p className="text-2xl font-semibold text-blue-300">
                    {(pattern.performance_metrics.in_sample_train_auc * 100).toFixed(1)}%
                  </p>
                </div>
              )}
              
              {/* CV AUC (XGBoost) */}
              {pattern.performance_metrics.cv_auc_mean !== undefined && (
                <div className="text-center p-4 bg-white/5 border border-white/10 rounded">
                  <p className="text-sm text-slate-400 font-medium mb-1">CV AUC</p>
                  <p className="text-2xl font-semibold text-emerald-300">
                    {(pattern.performance_metrics.cv_auc_mean * 100).toFixed(1)}%
                  </p>
                  {pattern.performance_metrics.cv_auc_std !== undefined && (
                    <p className="text-xs text-slate-400 mt-1">
                      ±{(pattern.performance_metrics.cv_auc_std * 100).toFixed(1)}%
                    </p>
                  )}
                </div>
              )}
              
              {/* 過擬合分數 (XGBoost) */}
              {pattern.performance_metrics.overfitting_score !== undefined && (
                <div className="text-center p-4 bg-white/5 border border-white/10 rounded">
                  <p className="text-sm text-slate-400 font-medium mb-1">過擬合分數</p>
                  <p className={`text-2xl font-bold ${
                    pattern.performance_metrics.overfitting_score <= 0.05 ? 'text-emerald-300' :
                    pattern.performance_metrics.overfitting_score <= 0.1 ? 'text-amber-300' :
                    'text-rose-300'
                  }`}>
                    {(pattern.performance_metrics.overfitting_score * 100).toFixed(1)}%
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    {pattern.performance_metrics.overfitting_score <= 0.05 ? '✅ 良好' :
                     pattern.performance_metrics.overfitting_score <= 0.1 ? '⚠️ 中等' :
                     '❌ 過高'}
                  </p>
                </div>
              )}
            </div>
            
            {/* 樣本數 */}
            {(pattern.performance_metrics.sample_count !== undefined || 
              pattern.performance_metrics.profitable_count !== undefined) && (
              <div className="grid grid-cols-2 gap-4 mt-4">
                {pattern.performance_metrics.sample_count !== undefined && (
                  <div className="text-center p-3 bg-blue-400/10 border border-blue-400/20 rounded">
                    <p className="text-sm text-slate-400 font-medium">訓練樣本</p>
                    <p className="text-xl font-semibold text-slate-100">{pattern.performance_metrics.sample_count}</p>
                  </div>
                )}
                {pattern.performance_metrics.profitable_count !== undefined && (
                  <div className="text-center p-3 bg-emerald-400/10 border border-emerald-400/20 rounded">
                    <p className="text-sm text-slate-400 font-medium">盈利樣本</p>
                    <p className="text-xl font-semibold text-slate-100">{pattern.performance_metrics.profitable_count}</p>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
      
      {/* 配置資訊 (XGBoost Analysis) */}
      {pattern.metadata && (
        pattern.metadata.data_selection || 
        pattern.metadata.indicator_config || 
        pattern.metadata.sequence_config || 
        pattern.metadata.training_config
      ) && (
        <div className="glass-panel rounded-xl border border-white/10 p-6">
          <h2 className="text-lg font-semibold mb-4 text-slate-100">分析配置</h2>
          
          <div className="space-y-4">
            {/* 數據選擇配置 */}
            {pattern.metadata.data_selection && (
              <div className="border border-white/10 rounded-lg p-4 bg-white/5">
                <h3 className="font-semibold text-slate-100 mb-3 flex items-center gap-2">
                  <span className="text-blue-300">📊</span> 數據選擇配置
                </h3>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-slate-400 font-medium">交易對</p>
                    <p className="text-slate-100 font-semibold mt-1">
                      {pattern.metadata.data_selection.symbol || '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-400 font-medium">時間週期</p>
                    <p className="text-slate-100 font-semibold mt-1">
                      {pattern.metadata.data_selection.timeframe || '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-400 font-medium">回溯 K 線數</p>
                    <p className="text-slate-100 font-semibold mt-1">
                      {pattern.metadata.data_selection.lookback_bars || '-'}
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {/* 指標配置 */}
            {pattern.metadata.indicator_config && pattern.metadata.indicator_config.length > 0 && (
              <div className="border border-white/10 rounded-lg p-4 bg-white/5">
                <h3 className="font-semibold text-slate-100 mb-3 flex items-center gap-2">
                  <span className="text-emerald-300">📈</span> 指標配置
                </h3>
                <div className="space-y-2">
                  {pattern.metadata.indicator_config.map((rawIndicator, idx: number) => {
                    const indicator: IndicatorConfigItem =
                      typeof rawIndicator === 'object' && rawIndicator !== null
                        ? (rawIndicator as IndicatorConfigItem)
                        : {}

                    return (
                    <div key={idx} className="bg-slate-900/40 border border-white/10 rounded p-3 text-sm">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="px-2 py-1 bg-blue-400/15 text-blue-200 rounded text-xs font-semibold">
                          {indicator.indicator || 'Unknown'}
                        </span>
                        <span className="text-slate-400">
                          資料來源: <span className="font-semibold text-slate-100">{indicator.data_source || 'close'}</span>
                        </span>
                      </div>
                      {indicator.params && Object.keys(indicator.params).length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(indicator.params).map(([key, value]) => (
                            <span key={key} className="text-xs text-slate-400">
                              <span className="font-medium">{key}:</span> <span className="text-slate-100">{String(value)}</span>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )})}
                </div>
              </div>
            )}
            
            {/* 序列特徵配置 */}
            {pattern.metadata.sequence_config && (
              <div className="border border-white/10 rounded-lg p-4 bg-white/5">
                <h3 className="font-semibold text-slate-100 mb-3 flex items-center gap-2">
                  <span className="text-purple-400">🔄</span> 序列特徵配置
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-slate-400 font-medium">序列窗口長度</p>
                    <p className="text-slate-100 font-semibold mt-1">
                      {pattern.metadata.sequence_config.sequence_length || '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-400 font-medium">特徵模式</p>
                    <p className="text-slate-100 font-semibold mt-1">
                      {pattern.metadata.sequence_config.sequence_feature_mode || '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-400 font-medium">序列步長</p>
                    <p className="text-slate-100 font-semibold mt-1">
                      {pattern.metadata.sequence_config.sequence_stride || '-'}
                    </p>
                  </div>
                </div>
                
                {/* 彙總方法 */}
                {pattern.metadata.sequence_config.aggregation_methods && 
                 pattern.metadata.sequence_config.aggregation_methods.length > 0 && (
                  <div className="mt-3">
                    <p className="text-slate-400 font-medium text-sm mb-2">彙總方法</p>
                    <div className="flex flex-wrap gap-2">
                      {pattern.metadata.sequence_config.aggregation_methods.map((method: string) => (
                        <span key={method} className="px-2 py-1 bg-purple-400/15 text-purple-400 rounded text-xs font-semibold">
                          {method}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* 多時間尺度窗口 */}
                {pattern.metadata.sequence_config.multi_scale_windows && 
                 pattern.metadata.sequence_config.multi_scale_windows.length > 0 && (
                  <div className="mt-3">
                    <p className="text-slate-400 font-medium text-sm mb-2">多時間尺度窗口</p>
                    <div className="flex flex-wrap gap-2">
                      {pattern.metadata.sequence_config.multi_scale_windows.map((window: number) => (
                        <span key={window} className="px-2 py-1 bg-amber-400/15 text-amber-200 rounded text-xs font-semibold">
                          {window}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {/* 訓練配置 */}
            {pattern.metadata.training_config && (
              <div className="border border-white/10 rounded-lg p-4 bg-white/5">
                <h3 className="font-semibold text-slate-100 mb-3 flex items-center gap-2">
                  <span className="text-amber-300">⚙️</span> 訓練配置
                </h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-slate-400 font-medium">時間序列切分</p>
                    <p className="text-slate-100 font-semibold mt-1">
                      {pattern.metadata.training_config.time_series_split ? '✅ 是' : '❌ 否'}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-400 font-medium">交叉驗證折數</p>
                    <p className="text-slate-100 font-semibold mt-1">
                      {pattern.metadata.training_config.cv_folds || '-'}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* 規則列表 */}
      <div className="glass-panel rounded-xl border border-white/10">
        <div className="p-4 border-b border-white/10">
          <h2 className="text-lg font-semibold text-slate-100">
            樣式規則 {pattern.rules && pattern.rules.length > 0 ? `(共 ${pattern.rules.length} 條)` : ''}
          </h2>
        </div>
        
        {!pattern.rules || pattern.rules.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            <p>無規則資料</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-white/5">
                <tr>
                  <th className="px-4 py-2 text-left text-slate-100 font-semibold">#</th>
                  <th className="px-4 py-2 text-left text-slate-100 font-semibold">特徵</th>
                  <th className="px-4 py-2 text-left text-slate-100 font-semibold">條件</th>
                  <th className="px-4 py-2 text-left text-slate-100 font-semibold">閾值</th>
                  <th className="px-4 py-2 text-left text-slate-100 font-semibold">說明</th>
                </tr>
              </thead>
              <tbody>
                {pattern.rules.map((rule, index) => (
                  <tr key={index} className="border-b border-white/10 hover:bg-white/5">
                    <td className="px-4 py-2 text-slate-100">{index + 1}</td>
                    <td className="px-4 py-2 font-mono text-xs text-slate-100">{rule.feature}</td>
                    <td className="px-4 py-2">
                      <span className="px-2 py-1 bg-blue-400/15 text-blue-200 rounded font-semibold">
                        {rule.operator}
                      </span>
                    </td>
                    <td className="px-4 py-2 font-semibold text-slate-100">{rule.threshold}</td>
                    <td className="px-4 py-2 text-slate-100">{rule.description || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      
      {/* 刪除確認對話框 */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-slate-950/70 flex items-center justify-center z-50">
          <div className="glass-panel rounded-xl border border-white/10 p-6 max-w-md">
            <h3 className="text-lg font-semibold mb-2 text-slate-100">確認刪除</h3>
            <p className="text-slate-300 mb-4">
              確定要刪除樣式「{pattern.name}」嗎？此操作無法復原。
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 border border-white/10 rounded text-slate-200 hover:bg-white/5"
              >
                取消
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="px-4 py-2 bg-rose-500/20 text-rose-100 rounded border border-rose-400/40 hover:bg-rose-500/30 disabled:bg-slate-700/60"
              >
                {isDeleting ? '刪除中...' : '確認刪除'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

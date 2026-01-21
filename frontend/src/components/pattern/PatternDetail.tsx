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
import { deletePattern, updatePattern } from '@/lib/api/patternApi';
import type { Pattern, UpdatePatternRequest } from '@/lib/patternTypes';

interface Props {
  pattern: Pattern;
  onUpdate?: () => void;
}

export default function PatternDetail({ pattern, onUpdate }: Props) {
  const router = useRouter();
  const { deletePattern: deletePatternInStore, updatePattern: updatePatternInStore } = usePatternStore();
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
  
  // 切換狀態
  const handleStatusChange = async (newStatus: string) => {
    try {
      const request: UpdatePatternRequest = {
        status: newStatus
      };
      const updated = await updatePattern(pattern.pattern_id, request);
      updatePatternInStore(updated);
      if (onUpdate) onUpdate();
    } catch (error) {
      console.error('更新狀態失敗:', error);
      alert('更新失敗: ' + (error instanceof Error ? error.message : '未知錯誤'));
    }
  };
  
  return (
    <div className="space-y-6">
      {/* 標題區域 */}
      <div className="bg-white rounded-lg border p-6">
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <h1 className="text-2xl font-bold mb-2 text-gray-900">{pattern.name}</h1>
            <p className="text-gray-900">{pattern.description}</p>
            
            {/* 狀態標籤 */}
            <div className="flex gap-2 mt-3">
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                pattern.status === 'active' ? 'bg-green-100 text-green-700' :
                pattern.status === 'testing' ? 'bg-yellow-100 text-yellow-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                {pattern.status === 'active' ? '啟用中' :
                 pattern.status === 'testing' ? '測試中' : '已封存'}
              </span>
              
              {/* 標籤 */}
              {pattern.tags && pattern.tags.length > 0 && pattern.tags.map(tag => (
                <span key={tag} className="px-3 py-1 bg-blue-50 text-blue-600 rounded-full text-sm">
                  {tag}
                </span>
              ))}
            </div>
          </div>
          
          {/* 操作按鈕 */}
          <div className="flex gap-2">
            {/* 狀態切換 */}
            <select
              value={pattern.status}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="px-3 py-2 border rounded"
            >
              <option value="active">啟用</option>
              <option value="testing">測試</option>
              <option value="archived">封存</option>
            </select>
            
            {/* 刪除按鈕 */}
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              刪除
            </button>
          </div>
        </div>
        
        {/* 基本資訊 */}
        <div className="grid grid-cols-3 gap-4 mt-6 pt-4 border-t">
          <div>
            <p className="text-sm text-gray-700 font-medium">案例 ID</p>
            <p className="font-semibold text-gray-900">{pattern.case_id}</p>
          </div>
          <div>
            <p className="text-sm text-gray-700 font-medium">建立時間</p>
            <p className="font-semibold text-gray-900">{new Date(pattern.created_at).toLocaleDateString()}</p>
          </div>
          <div>
            <p className="text-sm text-gray-700 font-medium">最後更新</p>
            <p className="font-semibold text-gray-900">{new Date(pattern.updated_at).toLocaleDateString()}</p>
          </div>
        </div>
      </div>
      
      {/* 效能指標 */}
      <div className="bg-white rounded-lg border p-6">
        <h2 className="text-lg font-bold mb-4 text-gray-900">效能指標</h2>
        
        {!pattern.performance_metrics || Object.keys(pattern.performance_metrics).length === 0 ? (
          <div className="text-center py-8 text-gray-700">
            <p>無效能指標資料</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {/* 精確度 Precision */}
              {pattern.performance_metrics.precision !== undefined && (
                <div className="text-center p-4 bg-gray-50 rounded">
                  <p className="text-sm text-gray-700 font-medium mb-1">精確度</p>
                  <p className="text-2xl font-bold text-green-600">
                    {(pattern.performance_metrics.precision * 100).toFixed(1)}%
                  </p>
                </div>
              )}
              
              {/* 召回率 Recall */}
              {pattern.performance_metrics.recall !== undefined && (
                <div className="text-center p-4 bg-gray-50 rounded">
                  <p className="text-sm text-gray-700 font-medium mb-1">召回率</p>
                  <p className="text-2xl font-bold text-yellow-600">
                    {(pattern.performance_metrics.recall * 100).toFixed(1)}%
                  </p>
                </div>
              )}
              
              {/* F1 分數 */}
              {pattern.performance_metrics.f1_score !== undefined && (
                <div className="text-center p-4 bg-gray-50 rounded">
                  <p className="text-sm text-gray-700 font-medium mb-1">F1 分數</p>
                  <p className="text-2xl font-bold text-purple-600">
                    {(pattern.performance_metrics.f1_score * 100).toFixed(1)}%
                  </p>
                </div>
              )}
              
              {/* 準確度 Accuracy (舊版相容) */}
              {pattern.performance_metrics.accuracy !== undefined && (
                <div className="text-center p-4 bg-gray-50 rounded">
                  <p className="text-sm text-gray-700 font-medium mb-1">準確度</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {(pattern.performance_metrics.accuracy * 100).toFixed(1)}%
                  </p>
                </div>
              )}
              
              {/* Train AUC (XGBoost) */}
              {pattern.performance_metrics.train_auc !== undefined && (
                <div className="text-center p-4 bg-gray-50 rounded">
                  <p className="text-sm text-gray-700 font-medium mb-1">Train AUC</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {(pattern.performance_metrics.train_auc * 100).toFixed(1)}%
                  </p>
                </div>
              )}
              
              {/* CV AUC (XGBoost) */}
              {pattern.performance_metrics.cv_auc_mean !== undefined && (
                <div className="text-center p-4 bg-gray-50 rounded">
                  <p className="text-sm text-gray-700 font-medium mb-1">CV AUC</p>
                  <p className="text-2xl font-bold text-green-600">
                    {(pattern.performance_metrics.cv_auc_mean * 100).toFixed(1)}%
                  </p>
                  {pattern.performance_metrics.cv_auc_std !== undefined && (
                    <p className="text-xs text-gray-700 mt-1">
                      ±{(pattern.performance_metrics.cv_auc_std * 100).toFixed(1)}%
                    </p>
                  )}
                </div>
              )}
              
              {/* 過擬合分數 (XGBoost) */}
              {pattern.performance_metrics.overfitting_score !== undefined && (
                <div className="text-center p-4 bg-gray-50 rounded">
                  <p className="text-sm text-gray-700 font-medium mb-1">過擬合分數</p>
                  <p className={`text-2xl font-bold ${
                    pattern.performance_metrics.overfitting_score <= 0.05 ? 'text-green-600' :
                    pattern.performance_metrics.overfitting_score <= 0.1 ? 'text-yellow-600' :
                    'text-red-600'
                  }`}>
                    {(pattern.performance_metrics.overfitting_score * 100).toFixed(1)}%
                  </p>
                  <p className="text-xs text-gray-700 mt-1">
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
                  <div className="text-center p-3 bg-blue-50 rounded">
                    <p className="text-sm text-gray-700 font-medium">訓練樣本</p>
                    <p className="text-xl font-semibold text-gray-900">{pattern.performance_metrics.sample_count}</p>
                  </div>
                )}
                {pattern.performance_metrics.profitable_count !== undefined && (
                  <div className="text-center p-3 bg-green-50 rounded">
                    <p className="text-sm text-gray-700 font-medium">盈利樣本</p>
                    <p className="text-xl font-semibold text-gray-900">{pattern.performance_metrics.profitable_count}</p>
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
        <div className="bg-white rounded-lg border p-6">
          <h2 className="text-lg font-bold mb-4 text-gray-900">分析配置</h2>
          
          <div className="space-y-4">
            {/* 數據選擇配置 */}
            {pattern.metadata.data_selection && (
              <div className="border rounded-lg p-4 bg-gray-50">
                <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <span className="text-blue-600">📊</span> 數據選擇配置
                </h3>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-gray-700 font-medium">交易對</p>
                    <p className="text-gray-900 font-semibold mt-1">
                      {pattern.metadata.data_selection.symbol || '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-700 font-medium">時間週期</p>
                    <p className="text-gray-900 font-semibold mt-1">
                      {pattern.metadata.data_selection.timeframe || '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-700 font-medium">回溯 K 線數</p>
                    <p className="text-gray-900 font-semibold mt-1">
                      {pattern.metadata.data_selection.lookback_bars || '-'}
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {/* 指標配置 */}
            {pattern.metadata.indicator_config && pattern.metadata.indicator_config.length > 0 && (
              <div className="border rounded-lg p-4 bg-gray-50">
                <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <span className="text-green-600">📈</span> 指標配置
                </h3>
                <div className="space-y-2">
                  {pattern.metadata.indicator_config.map((indicator: any, idx: number) => (
                    <div key={idx} className="bg-white border rounded p-3 text-sm">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-semibold">
                          {indicator.indicator || 'Unknown'}
                        </span>
                        <span className="text-gray-700">
                          資料來源: <span className="font-semibold text-gray-900">{indicator.data_source || 'close'}</span>
                        </span>
                      </div>
                      {indicator.params && Object.keys(indicator.params).length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(indicator.params).map(([key, value]) => (
                            <span key={key} className="text-xs text-gray-700">
                              <span className="font-medium">{key}:</span> <span className="text-gray-900">{String(value)}</span>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* 序列特徵配置 */}
            {pattern.metadata.sequence_config && (
              <div className="border rounded-lg p-4 bg-gray-50">
                <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <span className="text-purple-600">🔄</span> 序列特徵配置
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-gray-700 font-medium">序列窗口長度</p>
                    <p className="text-gray-900 font-semibold mt-1">
                      {pattern.metadata.sequence_config.sequence_length || '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-700 font-medium">特徵模式</p>
                    <p className="text-gray-900 font-semibold mt-1">
                      {pattern.metadata.sequence_config.sequence_feature_mode || '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-700 font-medium">序列步長</p>
                    <p className="text-gray-900 font-semibold mt-1">
                      {pattern.metadata.sequence_config.sequence_stride || '-'}
                    </p>
                  </div>
                </div>
                
                {/* 彙總方法 */}
                {pattern.metadata.sequence_config.aggregation_methods && 
                 pattern.metadata.sequence_config.aggregation_methods.length > 0 && (
                  <div className="mt-3">
                    <p className="text-gray-700 font-medium text-sm mb-2">彙總方法</p>
                    <div className="flex flex-wrap gap-2">
                      {pattern.metadata.sequence_config.aggregation_methods.map((method: string) => (
                        <span key={method} className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-semibold">
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
                    <p className="text-gray-700 font-medium text-sm mb-2">多時間尺度窗口</p>
                    <div className="flex flex-wrap gap-2">
                      {pattern.metadata.sequence_config.multi_scale_windows.map((window: number) => (
                        <span key={window} className="px-2 py-1 bg-orange-100 text-orange-700 rounded text-xs font-semibold">
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
              <div className="border rounded-lg p-4 bg-gray-50">
                <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <span className="text-yellow-600">⚙️</span> 訓練配置
                </h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-700 font-medium">時間序列切分</p>
                    <p className="text-gray-900 font-semibold mt-1">
                      {pattern.metadata.training_config.time_series_split ? '✅ 是' : '❌ 否'}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-700 font-medium">交叉驗證折數</p>
                    <p className="text-gray-900 font-semibold mt-1">
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
      <div className="bg-white rounded-lg border">
        <div className="p-4 border-b">
          <h2 className="text-lg font-bold text-gray-900">
            樣式規則 {pattern.rules && pattern.rules.length > 0 ? `(共 ${pattern.rules.length} 條)` : ''}
          </h2>
        </div>
        
        {!pattern.rules || pattern.rules.length === 0 ? (
          <div className="p-8 text-center text-gray-700">
            <p>無規則資料</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-gray-900 font-semibold">#</th>
                  <th className="px-4 py-2 text-left text-gray-900 font-semibold">特徵</th>
                  <th className="px-4 py-2 text-left text-gray-900 font-semibold">條件</th>
                  <th className="px-4 py-2 text-left text-gray-900 font-semibold">閾值</th>
                  <th className="px-4 py-2 text-left text-gray-900 font-semibold">說明</th>
                </tr>
              </thead>
              <tbody>
                {pattern.rules.map((rule, index) => (
                  <tr key={index} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-2 text-gray-900">{index + 1}</td>
                    <td className="px-4 py-2 font-mono text-xs text-gray-900">{rule.feature}</td>
                    <td className="px-4 py-2">
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded font-semibold">
                        {rule.operator}
                      </span>
                    </td>
                    <td className="px-4 py-2 font-semibold text-gray-900">{rule.threshold}</td>
                    <td className="px-4 py-2 text-gray-900">{rule.description || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      
      {/* 刪除確認對話框 */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md">
            <h3 className="text-lg font-bold mb-2 text-gray-900">確認刪除</h3>
            <p className="text-gray-900 mb-4">
              確定要刪除樣式「{pattern.name}」嗎？此操作無法復原。
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 border rounded hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:bg-gray-300"
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

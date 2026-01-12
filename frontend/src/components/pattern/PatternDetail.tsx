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
            <h1 className="text-2xl font-bold mb-2">{pattern.name}</h1>
            <p className="text-gray-600">{pattern.description}</p>
            
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
            <p className="text-sm text-gray-500">案例 ID</p>
            <p className="font-semibold">{pattern.case_id}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">建立時間</p>
            <p className="font-semibold">{new Date(pattern.created_at).toLocaleDateString()}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">最後更新</p>
            <p className="font-semibold">{new Date(pattern.updated_at).toLocaleDateString()}</p>
          </div>
        </div>
      </div>
      
      {/* 效能指標 */}
      <div className="bg-white rounded-lg border p-6">
        <h2 className="text-lg font-bold mb-4">效能指標</h2>
        <div className="grid grid-cols-4 gap-4">
          <div className="text-center p-4 bg-gray-50 rounded">
            <p className="text-sm text-gray-500 mb-1">準確度</p>
            <p className="text-2xl font-bold text-blue-600">
              {(pattern.performance_metrics.accuracy * 100).toFixed(1)}%
            </p>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded">
            <p className="text-sm text-gray-500 mb-1">精確度</p>
            <p className="text-2xl font-bold text-green-600">
              {(pattern.performance_metrics.precision * 100).toFixed(1)}%
            </p>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded">
            <p className="text-sm text-gray-500 mb-1">召回率</p>
            <p className="text-2xl font-bold text-yellow-600">
              {(pattern.performance_metrics.recall * 100).toFixed(1)}%
            </p>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded">
            <p className="text-sm text-gray-500 mb-1">F1 分數</p>
            <p className="text-2xl font-bold text-purple-600">
              {pattern.performance_metrics.f1_score.toFixed(3)}
            </p>
          </div>
        </div>
        
        {/* 樣本數 */}
        <div className="grid grid-cols-2 gap-4 mt-4">
          <div className="text-center p-3 bg-blue-50 rounded">
            <p className="text-sm text-gray-600">訓練樣本</p>
            <p className="text-xl font-semibold">{pattern.performance_metrics.sample_count}</p>
          </div>
          {pattern.performance_metrics.profitable_count !== undefined && (
            <div className="text-center p-3 bg-green-50 rounded">
              <p className="text-sm text-gray-600">盈利樣本</p>
              <p className="text-xl font-semibold">{pattern.performance_metrics.profitable_count}</p>
            </div>
          )}
        </div>
      </div>
      
      {/* 規則列表 */}
      <div className="bg-white rounded-lg border">
        <div className="p-4 border-b">
          <h2 className="text-lg font-bold">樣式規則 (共 {pattern.rules.length} 條)</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left">#</th>
                <th className="px-4 py-2 text-left">特徵</th>
                <th className="px-4 py-2 text-left">條件</th>
                <th className="px-4 py-2 text-left">閾值</th>
                <th className="px-4 py-2 text-left">說明</th>
              </tr>
            </thead>
            <tbody>
              {pattern.rules.map((rule, index) => (
                <tr key={index} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-2">{index + 1}</td>
                  <td className="px-4 py-2 font-mono text-xs">{rule.feature}</td>
                  <td className="px-4 py-2">
                    <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded font-semibold">
                      {rule.operator}
                    </span>
                  </td>
                  <td className="px-4 py-2 font-semibold">{rule.threshold}</td>
                  <td className="px-4 py-2 text-gray-600">{rule.description || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* 刪除確認對話框 */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md">
            <h3 className="text-lg font-bold mb-2">確認刪除</h3>
            <p className="text-gray-600 mb-4">
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

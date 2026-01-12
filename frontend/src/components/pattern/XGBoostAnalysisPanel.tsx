// frontend/src/components/pattern/XGBoostAnalysisPanel.tsx
/**
 * XGBoostAnalysisPanel.tsx
 * 
 * XGBoost 分析主面板
 * 
 * Features:
 * - 任務啟動與狀態追蹤
 * - WebSocket 即時進度更新
 * - 顯示特徵重要性、決策規則、模型效能
 * - 一鍵建立樣式功能
 */

'use client';

import React, { useState, useEffect } from 'react';
import { usePatternStore } from '@/store/patternStore';
import { startXGBoostAnalysis, getXGBoostTaskStatus } from '@/lib/api/patternApi';
import FeatureImportanceChart from './FeatureImportanceChart';
import DecisionRuleTable from './DecisionRuleTable';
import type { XGBoostAnalysisRequest } from '@/lib/patternTypes';

interface Props {
  caseId: string;
  onPatternCreated?: () => void;
}

export default function XGBoostAnalysisPanel({ caseId, onPatternCreated }: Props) {
  const { 
    currentAnalysis, 
    analysisLoading, 
    analysisTaskId, 
    setCurrentAnalysis 
  } = usePatternStore();
  
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');
  
  // 啟動分析
  const handleStartAnalysis = async () => {
    try {
      const request: XGBoostAnalysisRequest = {
        case_id: caseId,
        max_depth: 5,
        learning_rate: 0.05,
        n_estimators: 100,
        top_n_features: 10,
        min_rule_support: 5
      };
      
      const response = await startXGBoostAnalysis(request);
      usePatternStore.setState({ analysisTaskId: response.task_id, analysisLoading: true });
      setStatus('running');
      setProgress(0);
      
      // 開始輪詢任務狀態
      pollTaskStatus(response.task_id);
    } catch (error) {
      console.error('啟動分析失敗:', error);
      setStatus('failed');
      setErrorMessage(error instanceof Error ? error.message : '未知錯誤');
    }
  };
  
  // 輪詢任務狀態
  const pollTaskStatus = async (taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const statusData = await getXGBoostTaskStatus(taskId);
        setProgress(statusData.progress);
        
        if (statusData.status === 'completed') {
          clearInterval(interval);
          setStatus('completed');
          setCurrentAnalysis(statusData.result);
          usePatternStore.setState({ analysisLoading: false });
        } else if (statusData.status === 'failed') {
          clearInterval(interval);
          setStatus('failed');
          setErrorMessage(statusData.error || '分析失敗');
          usePatternStore.setState({ analysisLoading: false });
        }
      } catch (error) {
        console.error('獲取任務狀態失敗:', error);
        clearInterval(interval);
        setStatus('failed');
        setErrorMessage('無法獲取任務狀態');
        usePatternStore.setState({ analysisLoading: false });
      }
    }, 2000);
  };
  
  return (
    <div className="space-y-6">
      {/* 標題與啟動按鈕 */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold">XGBoost 樣式分析</h2>
            <p className="text-sm text-gray-500 mt-1">案例 ID: {caseId}</p>
          </div>
          <button
            onClick={handleStartAnalysis}
            disabled={status === 'running'}
            className={`px-4 py-2 rounded font-semibold ${
              status === 'running'
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {status === 'running' ? '分析中...' : '開始分析'}
          </button>
        </div>
        
        {/* 進度條 */}
        {status === 'running' && (
          <div className="mt-4">
            <div className="flex justify-between text-sm mb-1">
              <span>進度</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
        
        {/* 錯誤訊息 */}
        {status === 'failed' && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            ❌ {errorMessage}
          </div>
        )}
      </div>
      
      {/* 分析結果 */}
      {status === 'completed' && currentAnalysis && (
        <div className="space-y-6">
          {/* 模型效能 */}
          <div className="bg-white rounded-lg border p-4">
            <h3 className="text-lg font-bold mb-3">模型效能</h3>
            <div className="grid grid-cols-4 gap-4">
              <div className="text-center">
                <p className="text-sm text-gray-500">準確度</p>
                <p className="text-2xl font-bold text-blue-600">
                  {(currentAnalysis.model_performance.test_accuracy * 100).toFixed(1)}%
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-500">精確度</p>
                <p className="text-2xl font-bold text-green-600">
                  {(currentAnalysis.model_performance.test_precision * 100).toFixed(1)}%
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-500">召回率</p>
                <p className="text-2xl font-bold text-yellow-600">
                  {(currentAnalysis.model_performance.test_recall * 100).toFixed(1)}%
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-500">F1 分數</p>
                <p className="text-2xl font-bold text-purple-600">
                  {currentAnalysis.model_performance.test_f1.toFixed(3)}
                </p>
              </div>
            </div>
            
            {/* AUC */}
            {currentAnalysis.model_performance.test_auc && (
              <div className="mt-4 text-center">
                <p className="text-sm text-gray-500">AUC</p>
                <p className="text-3xl font-bold text-indigo-600">
                  {currentAnalysis.model_performance.test_auc.toFixed(3)}
                </p>
              </div>
            )}
          </div>
          
          {/* 特徵重要性 */}
          <FeatureImportanceChart 
            featureImportance={currentAnalysis.feature_importance}
            topN={10}
          />
          
          {/* 決策規則 */}
          <DecisionRuleTable 
            rules={currentAnalysis.decision_rules}
          />
          
          {/* 建立樣式按鈕 */}
          <div className="bg-white rounded-lg border p-4 text-center">
            <p className="text-sm text-gray-600 mb-3">
              從此分析結果建立新樣式定義
            </p>
            <button
              onClick={() => {
                // TODO: 導航到樣式建立表單，預填充資料
                if (onPatternCreated) onPatternCreated();
              }}
              className="px-6 py-2 bg-green-600 text-white rounded font-semibold hover:bg-green-700"
            >
              建立樣式定義
            </button>
          </div>
        </div>
      )}
      
      {/* 空狀態 */}
      {status === 'idle' && (
        <div className="bg-gray-50 rounded-lg border-2 border-dashed p-12 text-center">
          <p className="text-gray-500 text-lg">點擊「開始分析」來執行 XGBoost 樣式發現</p>
        </div>
      )}
    </div>
  );
}

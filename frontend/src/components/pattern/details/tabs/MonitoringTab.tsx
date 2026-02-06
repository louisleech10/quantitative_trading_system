'use client';

import React, { useState } from 'react';
import { usePatternStore } from '@/store/patternStore';
import { getStrategyEquity } from '@/lib/api/patternApi';
import RollingAUCChart from '../charts/RollingAUCChart';
import NaiveStrategyEquityChart from '../charts/NaiveStrategyEquityChart';
import RegimeRadarChart from '../charts/RegimeRadarChart';

interface MonitoringTabProps {
  taskId: string;
}

export default function MonitoringTab({ taskId }: MonitoringTabProps) {
  const { rollingAUC, strategyEquity, regimeAnalysis, deepAnalysisLoading, setStrategyEquity } = usePatternStore();
  const [threshold, setThreshold] = useState(0.75);

  const handleThresholdChange = async (newThreshold: number) => {
    setThreshold(newThreshold);
    try {
      const response = await getStrategyEquity(taskId, newThreshold);
      setStrategyEquity(response.data);
    } catch (error) {
      console.error('策略權益曲線更新失敗:', error);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="glass-panel rounded-xl p-4">
        <h3 className="text-lg font-medium text-slate-100 mb-4">滾動 AUC 監控</h3>
        <RollingAUCChart data={rollingAUC} loading={deepAnalysisLoading.rollingAuc} />
        {!!rollingAUC?.warning_zones?.length && (
          <div className="mt-2 p-2 bg-rose-400/10 rounded text-sm text-rose-400">
            ⚠️ 偵測到 {rollingAUC?.warning_zones?.length} 個 AUC 警戒區間
          </div>
        )}
      </div>

      <div className="glass-panel rounded-xl p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium text-slate-100">策略權益曲線</h3>
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400">閾值:</span>
            <input
              type="range"
              min="0.5"
              max="0.95"
              step="0.05"
              value={threshold}
              onChange={(e) => handleThresholdChange(parseFloat(e.target.value))}
              className="w-24"
            />
            <span className="text-sm font-medium text-slate-100">{threshold.toFixed(2)}</span>
          </div>
        </div>
        <NaiveStrategyEquityChart data={strategyEquity} loading={deepAnalysisLoading.equity} />
      </div>

      <div className="glass-panel rounded-xl p-4">
        <h3 className="text-lg font-medium text-slate-100 mb-4">市場體制表現</h3>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <RegimeRadarChart data={regimeAnalysis} loading={deepAnalysisLoading.regime} />
          <div className="space-y-2">
            {regimeAnalysis?.phase_metrics?.map((phase) => (
              <div key={phase.phase} className="flex justify-between p-2 bg-white/5 border border-white/10 rounded">
                <span>{phase.phase}</span>
                <span className={phase.recommendation.includes('建議') ? 'text-emerald-400' : 'text-rose-400'}>
                  AUC: {phase.auc?.toFixed(3) || 'N/A'} | {phase.recommendation}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

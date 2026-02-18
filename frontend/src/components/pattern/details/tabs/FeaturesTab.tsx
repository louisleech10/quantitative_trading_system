'use client';

import React, { useState } from 'react';
import { usePatternStore } from '@/store/patternStore';
import SHAPSummaryChart from '../charts/SHAPSummaryChart';
import FeatureImportanceComparison from '../charts/FeatureImportanceComparison';
import PSIComparisonChart from '../charts/PSIComparisonChart';
import ExportButton from '@/components/common/ExportButton';

interface FeaturesTabProps {
  taskId: string;
}

export default function FeaturesTab({ taskId }: FeaturesTabProps) {
  const { shapGlobal, featureImportanceAll, driftReport, deepAnalysisLoading } = usePatternStore();
  const [selectedFeature, setSelectedFeature] = useState<string | null>(null);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <ExportButton modelTaskId={taskId} scope="features" availableFormats={['csv', 'json', 'markdown']} />
      </div>

      <div className="glass-panel rounded-xl p-4">
        <h3 className="text-lg font-medium text-slate-100 mb-4">SHAP 特徵重要性</h3>
        <SHAPSummaryChart
          data={shapGlobal}
          loading={deepAnalysisLoading.shap}
          onFeatureClick={(feature) => setSelectedFeature(feature)}
        />
      </div>

      <div className="glass-panel rounded-xl p-4">
        <h3 className="text-lg font-medium text-slate-100 mb-4">特徵重要性對比 (Gain/Cover/Weight)</h3>
        <FeatureImportanceComparison data={featureImportanceAll} loading={deepAnalysisLoading.shap} />
      </div>

      <div className="glass-panel rounded-xl p-4">
        <h3 className="text-lg font-medium text-slate-100 mb-4">特徵飄移分析 (PSI)</h3>
        <PSIComparisonChart
          data={driftReport}
          loading={deepAnalysisLoading.drift}
          selectedFeature={selectedFeature || driftReport?.severe_features?.[0]}
          onFeatureSelect={setSelectedFeature}
        />
      </div>
    </div>
  );
}

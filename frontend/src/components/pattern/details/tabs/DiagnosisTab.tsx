'use client';

import React, { useState } from 'react';
import { usePatternStore } from '@/store/patternStore';
import TopFalsePositivesTable from '../tables/TopFalsePositivesTable';
import SingleCaseSHAPPanel from '../panels/SingleCaseSHAPPanel';

interface DiagnosisTabProps {
  taskId: string;
}

export default function DiagnosisTab({ taskId }: DiagnosisTabProps) {
  const { topFalsePositives, deepAnalysisLoading } = usePatternStore();
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

  return (
    <div className="p-6 space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-medium mb-4">Top False Positives</h3>
          <TopFalsePositivesTable
            data={topFalsePositives}
            loading={deepAnalysisLoading.falsePositives}
            onCaseClick={(caseId) => setSelectedCaseId(caseId)}
          />
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-medium mb-4">
            案例 SHAP 分析
            {selectedCaseId && <span className="text-sm text-gray-500 ml-2">({selectedCaseId})</span>}
          </h3>
          <SingleCaseSHAPPanel taskId={taskId} caseId={selectedCaseId} />
        </div>
      </div>
    </div>
  );
}

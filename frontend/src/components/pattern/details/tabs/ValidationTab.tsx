'use client';

import React from 'react';
import { usePatternStore } from '@/store/patternStore';
import OOTValidationPanel from '../panels/OOTValidationPanel';
import CalibrationCurveChart from '../charts/CalibrationCurveChart';
import PRCurveChart from '../charts/PRCurveChart';
import ProbabilityDensityChart from '../charts/ProbabilityDensityChart';
import MetricCard from '../shared/MetricCard';

export default function ValidationTab() {
  const {
    ootValidation,
    calibrationCurve,
    prCurve,
    probabilityDensity,
    deepAnalysisLoading
  } = usePatternStore();

  return (
    <div className="p-6 space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <OOTValidationPanel data={ootValidation} loading={deepAnalysisLoading.oot} />
        <div className="grid grid-cols-2 gap-4">
          <MetricCard title="CV AUC Mean" value={ootValidation?.cv_auc_mean} format="percent" status={ootValidation?.cv_auc_mean && ootValidation.cv_auc_mean >= 0.7 ? 'good' : 'warning'} />
          <MetricCard title="CV-OOT Gap" value={ootValidation?.cv_oot_gap} format="percent" status={ootValidation?.gap_status} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-medium mb-4">校準曲線</h3>
          <CalibrationCurveChart data={calibrationCurve} loading={deepAnalysisLoading.calibration} />
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-medium mb-4">PR 曲線</h3>
          <PRCurveChart data={prCurve} loading={deepAnalysisLoading.pr} />
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-medium mb-4">機率分佈密度</h3>
        <ProbabilityDensityChart data={probabilityDensity} loading={deepAnalysisLoading.density} />
      </div>
    </div>
  );
}

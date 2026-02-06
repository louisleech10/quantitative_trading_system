'use client';

import React, { useEffect } from 'react';
import { useParams } from 'next/navigation';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { usePatternStore } from '@/store/patternStore';
import DetailsHeader from '@/components/pattern/details/DetailsHeader';
import ValidationTab from '@/components/pattern/details/tabs/ValidationTab';
import FeaturesTab from '@/components/pattern/details/tabs/FeaturesTab';
import MonitoringTab from '@/components/pattern/details/tabs/MonitoringTab';
import DiagnosisTab from '@/components/pattern/details/tabs/DiagnosisTab';

export default function XGBoostDetailsPage() {
  const params = useParams<{ task_id: string }>();
  const taskId = params.task_id;
  const { loadDeepAnalysis, clearDeepAnalysis } = usePatternStore();

  useEffect(() => {
    if (taskId) {
      loadDeepAnalysis(taskId);
    }
    return () => {
      clearDeepAnalysis();
    };
  }, [taskId, loadDeepAnalysis, clearDeepAnalysis]);

  if (!taskId) return null;

  return (
    <div className="min-h-screen bg-slate-950/40">
      <DetailsHeader taskId={taskId} />

      <div className="max-w-7xl mx-auto px-6 py-6">
        <Tabs defaultValue="validation">
          <TabsList className="grid grid-cols-4 w-full max-w-2xl bg-slate-900/60 border border-slate-800/80">
            <TabsTrigger value="validation">模型驗證</TabsTrigger>
            <TabsTrigger value="features">特徵分析</TabsTrigger>
            <TabsTrigger value="monitoring">時序監控</TabsTrigger>
            <TabsTrigger value="diagnosis">錯誤診斷</TabsTrigger>
          </TabsList>

          <TabsContent value="validation">
            <ValidationTab />
          </TabsContent>
          <TabsContent value="features">
            <FeaturesTab />
          </TabsContent>
          <TabsContent value="monitoring">
            <MonitoringTab taskId={taskId} />
          </TabsContent>
          <TabsContent value="diagnosis">
            <DiagnosisTab taskId={taskId} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

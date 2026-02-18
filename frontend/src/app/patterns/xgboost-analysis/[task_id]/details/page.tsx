'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { usePatternStore } from '@/store/patternStore';
import DetailsHeader from '@/components/pattern/details/DetailsHeader';
import ValidationTab from '@/components/pattern/details/tabs/ValidationTab';
import FeaturesTab from '@/components/pattern/details/tabs/FeaturesTab';
import MonitoringTab from '@/components/pattern/details/tabs/MonitoringTab';
import DiagnosisTab from '@/components/pattern/details/tabs/DiagnosisTab';
import { getBatchTaskStatus } from '@/lib/api/patternApi';

export default function XGBoostDetailsPage() {
  const params = useParams<{ task_id: string }>();
  const taskId = params.task_id;
  const { loadDeepAnalysis, clearDeepAnalysis } = usePatternStore();
  const [engineType, setEngineType] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (taskId) {
      loadDeepAnalysis(taskId);

      getBatchTaskStatus(taskId)
        .then((task) => {
          const taskResult = task.result as { engine_type?: string } | undefined;
          const type = taskResult?.engine_type;
          if (type) setEngineType(String(type));
        })
        .catch(() => {
          setEngineType(undefined);
        });
    }
    return () => {
      clearDeepAnalysis();
    };
  }, [taskId, loadDeepAnalysis, clearDeepAnalysis]);

  if (!taskId) return null;

  return (
    <div className="min-h-screen bg-slate-950/40">
      <DetailsHeader taskId={taskId} engineType={engineType} />

      <div className="max-w-7xl mx-auto px-6 py-6">
        <Tabs defaultValue="validation">
          <TabsList className="grid grid-cols-4 w-full max-w-2xl bg-slate-900/60 border border-slate-800/80">
            <TabsTrigger value="validation">模型驗證</TabsTrigger>
            <TabsTrigger value="features">特徵分析</TabsTrigger>
            <TabsTrigger value="monitoring">時序監控</TabsTrigger>
            <TabsTrigger value="diagnosis">錯誤診斷</TabsTrigger>
          </TabsList>

          <TabsContent value="validation">
            <ValidationTab taskId={taskId} />
          </TabsContent>
          <TabsContent value="features">
            <FeaturesTab taskId={taskId} />
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

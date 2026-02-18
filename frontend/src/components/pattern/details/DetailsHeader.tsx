'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft } from 'lucide-react';
import ExportButton from '@/components/common/ExportButton';

interface DetailsHeaderProps {
  taskId: string;
  engineType?: string;
}

export default function DetailsHeader({ taskId, engineType }: DetailsHeaderProps) {
  const router = useRouter();

  return (
    <div className="glass-panel border-b border-white/10">
      <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-medium text-slate-100">XGBoost 深度分析儀表板</h1>
          <div className="text-sm text-slate-400 mt-1 flex items-center gap-2">
            <span>Task ID: {taskId}</span>
            {engineType && <Badge className="bg-slate-900/60 border border-slate-700 text-slate-200">{engineType}</Badge>}
          </div>
        </div>
        <Button variant="outline" onClick={() => router.push('/patterns/xgboost-analysis')}
          className="border-white/10 text-slate-200 hover:bg-white/5">
          <ArrowLeft className="w-4 h-4 mr-2" />
          返回分析頁
        </Button>
        <ExportButton
          modelTaskId={taskId}
          scope="full"
          availableFormats={['csv', 'json', 'markdown']}
        />
      </div>
    </div>
  );
}

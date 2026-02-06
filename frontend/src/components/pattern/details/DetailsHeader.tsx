'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';

interface DetailsHeaderProps {
  taskId: string;
}

export default function DetailsHeader({ taskId }: DetailsHeaderProps) {
  const router = useRouter();

  return (
    <div className="glass-panel border-b border-white/10">
      <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-medium text-slate-100">XGBoost 深度分析儀表板</h1>
          <p className="text-sm text-slate-400 mt-1">Task ID: {taskId}</p>
        </div>
        <Button variant="outline" onClick={() => router.push('/patterns/xgboost-analysis')}
          className="border-white/10 text-slate-200 hover:bg-white/5">
          <ArrowLeft className="w-4 h-4 mr-2" />
          返回分析頁
        </Button>
      </div>
    </div>
  );
}

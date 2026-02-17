'use client';

import { ReactNode } from 'react';
import { ErrorBoundary } from '@/components/ErrorBoundary';

interface ChartErrorBoundaryProps {
  title: string;
  children: ReactNode;
}

export default function ChartErrorBoundary({ title, children }: ChartErrorBoundaryProps) {
  return (
    <ErrorBoundary
      fallback={
        <div className="glass-panel rounded-2xl border border-rose-400/30 p-4 text-sm text-rose-200">
          {title} 渲染失敗，請檢查該模組輸入資料。
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  );
}

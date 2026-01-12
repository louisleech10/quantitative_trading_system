// frontend/src/app/patterns/analysis/[caseId]/page.tsx
/**
 * XGBoost 分析頁面
 */

'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import XGBoostAnalysisPanel from '@/components/pattern/XGBoostAnalysisPanel';
import Link from 'next/link';

export default function AnalysisPage() {
  const params = useParams();
  const caseId = params.caseId as string;
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* 頁面標題 */}
      <div className="bg-white border-b">
        <div className="max-w-6xl mx-auto px-6 py-6">
          <div className="flex items-center gap-4">
            <Link 
              href="/patterns"
              className="text-gray-500 hover:text-gray-700"
            >
              ← 返回
            </Link>
            <div className="border-l h-6" />
            <div>
              <h1 className="text-2xl font-bold">XGBoost 樣式分析</h1>
              <p className="text-sm text-gray-600 mt-1">案例: {caseId}</p>
            </div>
          </div>
        </div>
      </div>
      
      {/* 分析面板 */}
      <div className="max-w-6xl mx-auto px-6 py-6">
        <XGBoostAnalysisPanel 
          caseId={caseId}
          onPatternCreated={() => {
            // 導航到樣式建立頁面
            window.location.href = '/patterns/create';
          }}
        />
      </div>
    </div>
  );
}

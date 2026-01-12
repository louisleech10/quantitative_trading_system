// frontend/src/app/patterns/create/page.tsx
/**
 * 建立新樣式頁面
 */

'use client';

import React from 'react';
import CreatePatternForm from '@/components/pattern/CreatePatternForm';
import Link from 'next/link';

export default function CreatePatternPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* 頁面標題 */}
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-6 py-6">
          <div className="flex items-center gap-4">
            <Link 
              href="/patterns"
              className="text-gray-500 hover:text-gray-700"
            >
              ← 返回列表
            </Link>
            <div className="border-l h-6" />
            <div>
              <h1 className="text-2xl font-bold">建立新樣式</h1>
              <p className="text-sm text-gray-600 mt-1">定義交易樣式規則與效能指標</p>
            </div>
          </div>
        </div>
      </div>
      
      {/* 表單 */}
      <div className="max-w-4xl mx-auto px-6 py-6">
        <CreatePatternForm />
      </div>
    </div>
  );
}

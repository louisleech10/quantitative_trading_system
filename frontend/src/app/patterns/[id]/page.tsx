// frontend/src/app/patterns/[id]/page.tsx
/**
 * 樣式詳情頁面
 */

'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getPattern } from '@/lib/api/patternApi';
import PatternDetail from '@/components/pattern/PatternDetail';
import Link from 'next/link';
import type { Pattern } from '@/lib/patternTypes';

export default function PatternDetailPage() {
  const params = useParams();
  const router = useRouter();
  const patternId = params.id as string;
  
  const [pattern, setPattern] = useState<Pattern | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  
  useEffect(() => {
    loadPattern();
  }, [patternId]);
  
  const loadPattern = async () => {
    try {
      setLoading(true);
      const data = await getPattern(patternId);
      setPattern(data);
    } catch (err) {
      console.error('載入樣式失敗:', err);
      setError(err instanceof Error ? err.message : '載入失敗');
    } finally {
      setLoading(false);
    }
  };
  
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500 text-lg">載入中...</p>
      </div>
    );
  }
  
  if (error || !pattern) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 text-lg mb-4">❌ {error || '樣式不存在'}</p>
          <Link 
            href="/patterns"
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            返回列表
          </Link>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* 頁面標題 */}
      <div className="bg-white border-b">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <Link 
            href="/patterns"
            className="text-blue-600 hover:text-blue-700 text-sm"
          >
            ← 返回樣式列表
          </Link>
        </div>
      </div>
      
      {/* 內容 */}
      <div className="max-w-6xl mx-auto px-6 py-6">
        <PatternDetail pattern={pattern} onUpdate={loadPattern} />
      </div>
    </div>
  );
}

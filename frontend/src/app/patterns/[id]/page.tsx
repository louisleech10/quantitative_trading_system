// frontend/src/app/patterns/[id]/page.tsx
/**
 * 樣式詳情頁面
 */

'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getPattern } from '@/lib/api/patternApi';
import PatternDetail from '@/components/pattern/PatternDetail';
import Link from 'next/link';
import type { Pattern } from '@/lib/patternTypes';

export default function PatternDetailPage() {
  const params = useParams();
  const router = useRouter();
  void router;
  const patternId = params.id as string;
  
  const [pattern, setPattern] = useState<Pattern | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  
  const loadPattern = useCallback(async () => {
    try {
      setLoading(true);
      const response = await getPattern(patternId);
      if (response.success && response.pattern) {
        setPattern(response.pattern);
      } else {
        setError(response.error || '載入樣式失敗');
      }
    } catch (err) {
      console.error('載入樣式失敗:', err);
      setError(err instanceof Error ? err.message : '載入失敗');
    } finally {
      setLoading(false);
    }
  }, [patternId]);

  useEffect(() => {
    loadPattern();
  }, [loadPattern]);
  
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950/40 flex items-center justify-center">
        <p className="text-slate-400 text-lg">載入中...</p>
      </div>
    );
  }
  
  if (error || !pattern) {
    return (
      <div className="min-h-screen bg-slate-950/40 flex items-center justify-center">
        <div className="text-center">
          <p className="text-rose-300 text-lg mb-4">❌ {error || '樣式不存在'}</p>
          <Link 
            href="/patterns"
            className="px-4 py-2 bg-emerald-500/20 text-emerald-100 rounded border border-emerald-400/40 hover:bg-emerald-500/30"
          >
            返回列表
          </Link>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-slate-950/40">
      {/* 頁面標題 */}
      <div className="bg-slate-950/80 border-b border-slate-800/80">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <Link 
            href="/patterns"
            className="text-emerald-300 hover:text-emerald-200 text-sm"
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

'use client';

import React from 'react';
import type { FalsePositiveCase } from '@/lib/patternTypes';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';

interface TopFalsePositivesTableProps {
  data: FalsePositiveCase[] | null;
  loading?: boolean;
  onCaseClick?: (caseId: string) => void;
}

export default function TopFalsePositivesTable({ data, loading, onCaseClick }: TopFalsePositivesTableProps) {
  if (loading) return <LoadingState />;
  if (!data || data.length === 0) return <EmptyState message="沒有 False Positive 資料" />;

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left text-gray-600 border-b">
            <th className="py-2">時間</th>
            <th className="py-2">Symbol</th>
            <th className="py-2">機率</th>
            <th className="py-2">報酬</th>
            <th className="py-2">操作</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item) => (
            <tr key={item.case_id} className="border-b last:border-b-0">
              <td className="py-2 text-gray-700">{item.timestamp}</td>
              <td className="py-2 text-gray-700">{item.symbol}</td>
              <td className="py-2 text-gray-700">{item.predicted_proba.toFixed(4)}</td>
              <td className={`py-2 ${item.actual_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {item.actual_return.toFixed(4)}
              </td>
              <td className="py-2">
                <button
                  onClick={() => onCaseClick?.(item.case_id)}
                  className="text-blue-600 hover:underline"
                >
                  查看
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

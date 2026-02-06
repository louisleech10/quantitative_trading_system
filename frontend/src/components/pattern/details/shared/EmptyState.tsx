import React from 'react';

interface EmptyStateProps {
  message?: string;
}

export default function EmptyState({ message = '沒有資料' }: EmptyStateProps) {
  return (
    <div className="text-center py-8 text-slate-400">
      {message}
    </div>
  );
}

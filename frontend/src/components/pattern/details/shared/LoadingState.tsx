import React from 'react';

interface LoadingStateProps {
  message?: string;
}

export default function LoadingState({ message = '載入中...' }: LoadingStateProps) {
  return (
    <div className="text-center py-8 text-slate-400">
      {message}
    </div>
  );
}

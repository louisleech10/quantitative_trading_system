import React from 'react';

interface ErrorStateProps {
  message?: string;
}

export default function ErrorState({ message = '載入失敗' }: ErrorStateProps) {
  return (
    <div className="text-center py-8 text-red-600">
      {message}
    </div>
  );
}

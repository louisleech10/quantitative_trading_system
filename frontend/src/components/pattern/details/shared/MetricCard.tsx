import React from 'react';

interface MetricCardProps {
  title: string;
  value?: number | null;
  format?: 'number' | 'percent';
  status?: 'good' | 'acceptable' | 'warning' | 'unknown' | string | null;
}

export default function MetricCard({ title, value, format = 'number', status }: MetricCardProps) {
  const renderValue = () => {
    if (value === undefined || value === null || Number.isNaN(value)) return 'N/A';
    if (format === 'percent') return `${(value * 100).toFixed(2)}%`;
    return value.toFixed(4);
  };

  const statusColor = () => {
    switch (status) {
      case 'good':
        return 'text-green-600';
      case 'acceptable':
        return 'text-yellow-600';
      case 'warning':
        return 'text-red-600';
      default:
        return 'text-gray-800';
    }
  };

  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <div className="text-sm text-gray-600 mb-1">{title}</div>
      <div className={`text-2xl font-bold ${statusColor()}`}>
        {renderValue()}
      </div>
      {status && (
        <div className="text-xs text-gray-500 mt-1">狀態：{status}</div>
      )}
    </div>
  );
}

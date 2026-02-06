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
        return 'text-emerald-400';
      case 'acceptable':
        return 'text-amber-400';
      case 'warning':
        return 'text-rose-400';
      default:
        return 'text-slate-100';
    }
  };

  return (
    <div className="bg-white/5 border border-white/10 rounded-lg p-4">
      <div className="text-sm text-slate-400 mb-1">{title}</div>
      <div className={`text-2xl font-semibold ${statusColor()}`}>
        {renderValue()}
      </div>
      {status && (
        <div className="text-xs text-slate-400 mt-1">狀態：{status}</div>
      )}
    </div>
  );
}

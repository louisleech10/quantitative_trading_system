import React from 'react';

interface DateRangePickerProps {
  label: string;
  startDate: string;
  endDate: string;
  onChange: (start: string, end: string) => void;
  minDate?: string;
  maxDate?: string;
  description?: string;
  error?: string;
  className?: string;
  disabled?: boolean;
}

export function DateRangePicker({
  label,
  startDate,
  endDate,
  onChange,
  minDate,
  maxDate,
  description,
  error,
  className = '',
  disabled = false,
}: DateRangePickerProps) {
  const handleStartChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const nextStart = event.target.value;
    if (endDate && nextStart && nextStart > endDate) {
      onChange(nextStart, nextStart);
      return;
    }
    onChange(nextStart, endDate);
  };

  const handleEndChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const nextEnd = event.target.value;
    if (startDate && nextEnd && nextEnd < startDate) {
      onChange(nextEnd, nextEnd);
      return;
    }
    onChange(startDate, nextEnd);
  };

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      <label className={`text-sm font-medium ${disabled ? 'text-slate-500' : 'text-slate-200'}`}>
        {label}
      </label>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="flex flex-col gap-1">
          <span className="text-xs text-slate-400">起始日期</span>
          <input
            type="date"
            value={startDate}
            onChange={handleStartChange}
            min={minDate}
            max={maxDate}
            disabled={disabled}
            className={`rounded-md border px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 ${
              disabled
                ? 'border-white/10 bg-white/5 text-slate-500'
                : 'border-white/10 bg-white/5 text-slate-100'
            }`}
          />
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-slate-400">結束日期</span>
          <input
            type="date"
            value={endDate}
            onChange={handleEndChange}
            min={minDate}
            max={maxDate}
            disabled={disabled}
            className={`rounded-md border px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 ${
              disabled
                ? 'border-white/10 bg-white/5 text-slate-500'
                : 'border-white/10 bg-white/5 text-slate-100'
            }`}
          />
        </div>
      </div>
      {description && <p className="text-xs text-slate-400">{description}</p>}
      {error && <p className="text-xs text-rose-400">{error}</p>}
    </div>
  );
}
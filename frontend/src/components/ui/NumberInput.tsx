import React from 'react';
import { Minus, Plus } from 'lucide-react';

interface NumberInputProps {
  label: string;
  value: number;
  onChange: (next: number) => void;
  min?: number;
  max?: number;
  step?: number;
  suffix?: string;
  description?: string;
  error?: string;
  className?: string;
  disabled?: boolean;
}

export function NumberInput({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  suffix,
  description,
  error,
  className = '',
  disabled = false,
}: NumberInputProps) {
  const clampValue = (val: number) => {
    let next = val;
    if (typeof min === 'number') {
      next = Math.max(min, next);
    }
    if (typeof max === 'number') {
      next = Math.min(max, next);
    }
    return next;
  };

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = event.target.value;

    // Allow empty input (user is clearing the field)
    if (inputValue === '') {
      onChange(min ?? 0);
      return;
    }

    const parsed = Number(inputValue);
    if (Number.isNaN(parsed)) {
      // Don't update if input is invalid (e.g., partial negative sign)
      return;
    }

    // Don't clamp during typing - allow user to input freely
    onChange(parsed);
  };

  const handleBlur = () => {
    // Apply clamping only when user finishes editing
    onChange(clampValue(value));
  };

  const handleStep = (direction: 'inc' | 'dec') => {
    const delta = direction === 'inc' ? step : -step;
    onChange(clampValue(value + delta));
  };

  const isMinReached = typeof min === 'number' ? value <= min : false;
  const isMaxReached = typeof max === 'number' ? value >= max : false;

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label className={`text-sm font-medium ${disabled ? 'text-gray-400' : 'text-gray-700'}`}>
        {label}
      </label>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => handleStep('dec')}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-gray-300 bg-white text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          disabled={disabled || isMinReached}
        >
          <Minus className="h-4 w-4" />
        </button>
        <div className="relative flex-1">
          <input
            type="number"
            value={value}
            onChange={handleInputChange}
            onBlur={handleBlur}
            min={min}
            max={max}
            step={step}
            disabled={disabled}
            className={`w-full rounded-md border px-3 py-2 text-center text-base font-semibold text-gray-900 shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
              disabled
                ? 'border-gray-200 bg-gray-50 text-gray-400'
                : 'border-gray-300 bg-white'
            }`}
          />
          {suffix && (
            <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-sm text-gray-500">
              {suffix}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => handleStep('inc')}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-gray-300 bg-white text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          disabled={disabled || isMaxReached}
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
      {description && <p className="text-xs text-gray-500">{description}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
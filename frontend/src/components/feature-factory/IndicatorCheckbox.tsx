'use client';

import React from 'react';

interface IndicatorCheckboxProps {
  name: string;
  enabled: boolean;
  description?: string;
  disabled?: boolean;
  onChange: (enabled: boolean) => void;
}

export default function IndicatorCheckbox({
  name,
  enabled,
  description,
  disabled = false,
  onChange,
}: IndicatorCheckboxProps) {
  return (
    <label
      className={`flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs transition cursor-pointer select-none ${
        disabled
          ? 'opacity-40 cursor-not-allowed'
          : enabled
            ? 'bg-cyan-400/10 text-slate-100'
            : 'text-slate-400 hover:bg-white/5'
      }`}
      title={description || name}
    >
      <input
        type="checkbox"
        checked={enabled}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="h-3.5 w-3.5 rounded border-white/20 bg-white/5 accent-cyan-400"
      />
      <span className="truncate">{name}</span>
    </label>
  );
}

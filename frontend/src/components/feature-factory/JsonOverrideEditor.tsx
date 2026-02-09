'use client';

import { useState } from 'react';

interface JsonOverrideEditorProps {
  onApply: (override: Record<string, unknown>) => void;
}

export default function JsonOverrideEditor({ onApply }: JsonOverrideEditorProps) {
  const [value, setValue] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleApply = () => {
    if (!value.trim()) {
      setError(null);
      return;
    }

    try {
      const parsed = JSON.parse(value);
      if (parsed && typeof parsed === 'object') {
        onApply(parsed);
        setError(null);
      } else {
        setError('JSON 必須是物件');
      }
    } catch {
      setError('JSON 格式錯誤');
    }
  };

  return (
    <div className="space-y-3">
      <label className="text-xs uppercase tracking-[0.2em] text-slate-400">進階覆寫</label>
      <textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        rows={5}
        placeholder='例如: {"atomic_indicators": {"momentum": {"enabled": false}}}'
        className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-100 font-[var(--font-ff-mono)] focus:outline-none focus:ring-2 focus:ring-cyan-300/40"
      />
      {error && <div className="text-xs text-rose-300">{error}</div>}
      <button
        type="button"
        onClick={handleApply}
        className="w-full rounded-xl border border-cyan-300/30 bg-cyan-400/10 px-3 py-2 text-xs text-cyan-100 hover:bg-cyan-400/20 transition"
      >
        套用覆寫
      </button>
    </div>
  );
}

'use client';

import { useEffect, useMemo, useState } from 'react';
import { FeatureSegmentKey, parseFeatureNameSegments } from '@/lib/featureNameParser';

interface FeatureNameSegmentFilterProps {
  features: string[];
  onFilteredFeaturesChange: (features: string[]) => void;
}

type SelectMode = 'single' | 'multi';

const SEGMENT_DEFS: Array<{ key: FeatureSegmentKey; label: string }> = [
  { key: 'source', label: 'Source' },
  { key: 'category', label: 'Category' },
  { key: 'indicator', label: 'Indicator' },
  { key: 'params', label: 'Params' },
  { key: 'operator', label: 'Operator' },
  { key: 'opParams', label: 'OpParams' },
  { key: 'window', label: 'Window' },
  { key: 'suffix', label: 'Suffix' },
];

function emptySelectionMap<T>(value: T): Record<FeatureSegmentKey, T> {
  return {
    source: value,
    category: value,
    indicator: value,
    params: value,
    operator: value,
    opParams: value,
    window: value,
    suffix: value,
  };
}

export default function FeatureNameSegmentFilter({ features, onFilteredFeaturesChange }: FeatureNameSegmentFilterProps) {
  const [freeText, setFreeText] = useState('');
  const [selected, setSelected] = useState<Record<FeatureSegmentKey, string[]>>(emptySelectionMap<string[]>([]));
  const [modes, setModes] = useState<Record<FeatureSegmentKey, SelectMode>>(emptySelectionMap<SelectMode>('multi'));

  const parsed = useMemo(
    () => features.map((name) => ({ name, segments: parseFeatureNameSegments(name) })),
    [features]
  );

  const optionsBySegment = useMemo(() => {
    const result = emptySelectionMap<string[]>([]);
    for (const item of parsed) {
      for (const seg of SEGMENT_DEFS) {
        const value = item.segments[seg.key];
        if (!value) continue;
        if (!result[seg.key].includes(value)) {
          result[seg.key] = [...result[seg.key], value];
        }
      }
    }

    for (const seg of SEGMENT_DEFS) {
      result[seg.key].sort((a, b) => a.localeCompare(b));
    }
    return result;
  }, [parsed]);

  const filtered = useMemo(() => {
    const lower = freeText.trim().toLowerCase();
    return parsed
      .filter((item) => {
        if (lower && !item.name.toLowerCase().includes(lower)) return false;
        for (const seg of SEGMENT_DEFS) {
          const picked = selected[seg.key];
          if (picked.length === 0) continue;
          if (!picked.includes(item.segments[seg.key])) return false;
        }
        return true;
      })
      .map((item) => item.name);
  }, [parsed, freeText, selected]);

  useEffect(() => {
    onFilteredFeaturesChange(filtered);
  }, [filtered, onFilteredFeaturesChange]);

  const toggle = (key: FeatureSegmentKey, value: string) => {
    setSelected((prev) => {
      const current = prev[key];
      const mode = modes[key];
      if (mode === 'single') {
        return { ...prev, [key]: current[0] === value ? [] : [value] };
      }
      if (current.includes(value)) {
        return { ...prev, [key]: current.filter((v) => v !== value) };
      }
      return { ...prev, [key]: [...current, value] };
    });
  };

  const setAll = (key: FeatureSegmentKey) => {
    setSelected((prev) => {
      const all = optionsBySegment[key];
      if (modes[key] === 'single') {
        return { ...prev, [key]: all.slice(0, 1) };
      }
      return { ...prev, [key]: all };
    });
  };

  const clearAll = (key: FeatureSegmentKey) => {
    setSelected((prev) => ({ ...prev, [key]: [] }));
  };

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-3 space-y-2">
      <div className="text-xs text-slate-300">特徵命名規範段落篩選</div>
      <input
        value={freeText}
        onChange={(e) => setFreeText(e.target.value)}
        placeholder="自由輸入（保留）..."
        className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-100"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
        {SEGMENT_DEFS.map((seg) => {
          const options = optionsBySegment[seg.key];
          const picked = selected[seg.key];
          const mode = modes[seg.key];
          return (
            <details key={seg.key} className="rounded-lg border border-white/10 bg-slate-900/30 px-2 py-1">
              <summary className="cursor-pointer text-xs text-slate-200 flex items-center justify-between">
                <span>{seg.label}</span>
                <span className="text-slate-400">{picked.length}/{options.length}</span>
              </summary>
              <div className="mt-2 space-y-2">
                <div className="flex flex-wrap gap-1">
                  <button
                    onClick={() => setModes((prev) => ({ ...prev, [seg.key]: 'single' }))}
                    className={`text-[11px] px-2 py-1 rounded border ${
                      mode === 'single' ? 'border-cyan-300/50 text-cyan-200' : 'border-white/10 text-slate-300'
                    }`}
                    type="button"
                  >
                    單選
                  </button>
                  <button
                    onClick={() => setModes((prev) => ({ ...prev, [seg.key]: 'multi' }))}
                    className={`text-[11px] px-2 py-1 rounded border ${
                      mode === 'multi' ? 'border-cyan-300/50 text-cyan-200' : 'border-white/10 text-slate-300'
                    }`}
                    type="button"
                  >
                    複選
                  </button>
                  <button onClick={() => setAll(seg.key)} className="text-[11px] px-2 py-1 rounded border border-white/10 text-slate-300" type="button">
                    全選
                  </button>
                  <button onClick={() => clearAll(seg.key)} className="text-[11px] px-2 py-1 rounded border border-white/10 text-slate-300" type="button">
                    全取消
                  </button>
                </div>

                <div className="max-h-36 overflow-auto space-y-1 pr-1">
                  {options.map((option) => (
                    <label key={option} className="flex items-center gap-2 text-xs text-slate-200">
                      <input
                        type="checkbox"
                        checked={picked.includes(option)}
                        onChange={() => toggle(seg.key, option)}
                      />
                      <span className="truncate">{option}</span>
                    </label>
                  ))}
                  {options.length === 0 && <div className="text-[11px] text-slate-500">無可用項目</div>}
                </div>
              </div>
            </details>
          );
        })}
      </div>

      <div className="text-[11px] text-slate-400">篩選後特徵數：{filtered.length.toLocaleString()}</div>
    </div>
  );
}

'use client';

import { FeatureFactoryConfig } from '@/lib/types';

interface IndicatorSelectorProps {
  indicators: FeatureFactoryConfig['atomic_indicators'];
  onChange: (next: FeatureFactoryConfig['atomic_indicators']) => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  trend: '趨勢',
  momentum: '動量',
  volatility: '波動',
  volume: '量能',
  cycle: '週期',
  pattern: '型態',
  statistics: '統計',
};

export default function IndicatorSelector({ indicators, onChange }: IndicatorSelectorProps) {
  const toggleCategory = (key: keyof FeatureFactoryConfig['atomic_indicators']) => {
    onChange({
      ...indicators,
      [key]: {
        ...indicators[key],
        enabled: !indicators[key]?.enabled,
      },
    });
  };

  return (
    <div className="space-y-3">
      <label className="text-xs uppercase tracking-[0.2em] text-slate-400">指標類別</label>
      <div className="grid grid-cols-2 gap-2">
        {(Object.keys(CATEGORY_LABELS) as Array<keyof FeatureFactoryConfig['atomic_indicators']>).map(
          (key) => {
            const active = indicators[key]?.enabled ?? false;
            return (
              <button
                key={key}
                type="button"
                onClick={() => toggleCategory(key)}
                className={`rounded-xl border px-3 py-2 text-xs text-left transition ${
                  active
                    ? 'bg-cyan-400/15 text-cyan-100 border-cyan-300/40'
                    : 'bg-white/5 text-slate-400 border-white/10 hover:border-cyan-300/40'
                }`}
              >
                <div className="font-medium">{CATEGORY_LABELS[key]}</div>
                <div className="text-[11px] text-slate-500 mt-1">{key}</div>
              </button>
            );
          }
        )}
      </div>
    </div>
  );
}

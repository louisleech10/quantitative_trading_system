'use client';

import { FeatureFactoryConfig } from '@/lib/types';

interface TimeframeSelectorProps {
  timeframes: FeatureFactoryConfig['timeframes'];
  onChange: (next: FeatureFactoryConfig['timeframes']) => void;
}

const AVAILABLE_TFS = ['1h', '4h', '12h', '1d'];

export default function TimeframeSelector({ timeframes, onChange }: TimeframeSelectorProps) {
  const toggleTraining = (tf: string) => {
    const nextTraining = timeframes.training.includes(tf)
      ? timeframes.training.filter((item) => item !== tf)
      : [...timeframes.training, tf];

    onChange({
      ...timeframes,
      training: nextTraining,
    });
  };

  return (
    <div className="space-y-3">
      <label className="text-xs uppercase tracking-[0.2em] text-slate-400">時間框架</label>
      <div className="space-y-3">
        <div>
          <div className="text-xs text-slate-400 mb-2">主框架</div>
          <select
            value={timeframes.primary}
            onChange={(event) =>
              onChange({
                ...timeframes,
                primary: event.target.value,
              })
            }
            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100"
          >
            {AVAILABLE_TFS.map((tf) => (
              <option key={tf} value={tf}>
                {tf}
              </option>
            ))}
          </select>
        </div>

        <div>
          <div className="text-xs text-slate-400 mb-2">訓練框架</div>
          <div className="flex flex-wrap gap-2">
            {AVAILABLE_TFS.map((tf) => {
              const active = timeframes.training.includes(tf);
              return (
                <button
                  key={tf}
                  type="button"
                  onClick={() => toggleTraining(tf)}
                  className={`px-3 py-1 rounded-full text-xs border transition ${
                    active
                      ? 'bg-amber-400/20 text-amber-100 border-amber-300/40'
                      : 'bg-white/5 text-slate-400 border-white/10 hover:border-amber-300/40'
                  }`}
                >
                  {tf}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

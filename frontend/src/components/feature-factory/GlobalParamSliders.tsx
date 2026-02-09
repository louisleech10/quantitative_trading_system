'use client';

import { FeatureFactoryConfig } from '@/lib/types';

interface GlobalParamSlidersProps {
  globalSettings: FeatureFactoryConfig['global_settings'];
  onChange: (next: FeatureFactoryConfig['global_settings']) => void;
}

export default function GlobalParamSliders({
  globalSettings,
  onChange,
}: GlobalParamSlidersProps) {
  return (
    <div className="space-y-4">
      <label className="text-xs uppercase tracking-[0.2em] text-slate-400">全域參數</label>

      <div>
        <div className="flex items-center justify-between text-xs text-slate-300">
          <span>Sequence Length</span>
          <span className="text-amber-200">{globalSettings.sequence_length}</span>
        </div>
        <input
          type="range"
          min={20}
          max={300}
          step={10}
          value={globalSettings.sequence_length}
          onChange={(event) =>
            onChange({
              ...globalSettings,
              sequence_length: Number(event.target.value),
            })
          }
          className="w-full mt-2 accent-amber-300"
        />
      </div>

      <div>
        <div className="flex items-center justify-between text-xs text-slate-300">
          <span>Max Lag Ratio</span>
          <span className="text-amber-200">{globalSettings.max_lag_ratio.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min={0.1}
          max={0.9}
          step={0.05}
          value={globalSettings.max_lag_ratio}
          onChange={(event) =>
            onChange({
              ...globalSettings,
              max_lag_ratio: Number(event.target.value),
            })
          }
          className="w-full mt-2 accent-amber-300"
        />
      </div>
    </div>
  );
}

'use client';

import { FeatureFactoryPreset } from '@/lib/types';

interface PresetSelectorProps {
  presets: FeatureFactoryPreset[];
  selectedPreset: string | null;
  onPresetChange: (
    presetName: string,
    presetConfig?: FeatureFactoryPreset['config']
  ) => void;
}

export default function PresetSelector({
  presets,
  selectedPreset,
  onPresetChange,
}: PresetSelectorProps) {
  return (
    <div className="space-y-3">
      <label className="text-xs uppercase tracking-[0.2em] text-slate-400">Preset</label>
      <select
        value={selectedPreset ?? ''}
        onChange={(event) => {
          const presetName = event.target.value;
          const preset = presets.find((item) => item.name === presetName);
          onPresetChange(presetName, preset?.config);
        }}
        className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-300/40"
      >
        <option value="">選擇 Preset</option>
        {presets.map((preset) => (
          <option key={preset.name} value={preset.name}>
            {preset.name}
          </option>
        ))}
      </select>
      <div className="text-xs text-slate-400">
        預設方案會覆蓋目前設定，可再透過覆寫微調。
      </div>
    </div>
  );
}

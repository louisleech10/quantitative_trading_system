'use client';

import { useMemo } from 'react';
import { SlidersHorizontal, Database } from 'lucide-react';
import { FeatureFactoryConfig, FeatureFactoryPreset } from '@/lib/types';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import PresetSelector from './PresetSelector';
import DataSourceSelector from './DataSourceSelector';
import IndicatorSelector from './IndicatorSelector';
import GlobalParamSliders from './GlobalParamSliders';
import TimeframeSelector from './TimeframeSelector';
import JsonOverrideEditor from './JsonOverrideEditor';

interface ConfigPanelProps {
  config: FeatureFactoryConfig | null;
  presets: FeatureFactoryPreset[];
  dataSources: string[];
  symbol: string;
  timeframe: string;
  onSymbolChange: (value: string) => void;
  onTimeframeChange: (value: string) => void;
}

export default function ConfigPanel({
  config,
  presets,
  dataSources,
  symbol,
  timeframe,
  onSymbolChange,
  onTimeframeChange,
}: ConfigPanelProps) {
  const {
    selectedPreset,
    setSelectedPreset,
    setConfig,
    updateConfigPartial,
    setAlignmentMode,
    setTrainingTimeframes,
  } =
    useFeatureFactoryStore();

  const availableSources = useMemo(() => {
    if (dataSources.length > 0) {
      return dataSources;
    }

    return config?.data_sources?.enabled_sources ?? [];
  }, [dataSources, config]);

  const handlePresetChange = (
    presetName: string,
    presetConfig?: FeatureFactoryConfig
  ) => {
    setSelectedPreset(presetName);
    if (presetConfig) {
      setConfig(presetConfig);
      return;
    }

    if (config) {
      setConfig(config);
    }
  };

  const handleConfigOverride = (override: Record<string, unknown>) => {
    updateConfigPartial(override);
  };

  if (!config) {
    return (
      <div className="glass-panel rounded-2xl p-6">
        <div className="text-sm text-slate-400">設定載入中...</div>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-6">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-xl bg-amber-400/15 flex items-center justify-center">
          <SlidersHorizontal className="w-5 h-5 text-amber-200" />
        </div>
        <div>
          <div className="text-lg font-semibold text-slate-100">設定面板</div>
          <div className="text-xs text-slate-400">快速建立研究設定與覆寫參數</div>
        </div>
      </div>

      <div className="space-y-4">
        <label className="text-xs uppercase tracking-[0.2em] text-slate-400">目標標的</label>
        <div className="grid grid-cols-1 gap-3">
          <input
            value={symbol}
            onChange={(event) => onSymbolChange(event.target.value.toUpperCase())}
            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-300/40"
            placeholder="例如: BTCUSDT"
          />
          <div className="relative">
            <Database className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              value={timeframe}
              onChange={(event) => onTimeframeChange(event.target.value)}
              className="w-full rounded-xl border border-white/10 bg-white/5 px-9 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-300/40"
              placeholder="12h"
            />
          </div>
        </div>
      </div>

      <PresetSelector
        presets={presets}
        selectedPreset={selectedPreset}
        onPresetChange={handlePresetChange}
      />

      <DataSourceSelector
        enabledSources={config.data_sources?.enabled_sources ?? []}
        availableSources={availableSources}
        onChange={(next) =>
          setConfig({
            ...config,
            data_sources: {
              ...config.data_sources,
              enabled_sources: next,
            },
          })
        }
      />

      <IndicatorSelector
        indicators={config.atomic_indicators}
        onChange={(next) =>
          setConfig({
            ...config,
            atomic_indicators: next,
          })
        }
      />

      <GlobalParamSliders
        globalSettings={config.global_settings}
        onChange={(next) =>
          setConfig({
            ...config,
            global_settings: next,
          })
        }
      />

      <TimeframeSelector
        timeframes={config.timeframes}
        onChange={(next) => {
          setAlignmentMode(next.alignment_mode ?? 'open_minus');
          setTrainingTimeframes(next.training);
          setConfig({
            ...config,
            timeframes: next,
          });
        }}
      />

      <JsonOverrideEditor onApply={handleConfigOverride} />
    </div>
  );
}

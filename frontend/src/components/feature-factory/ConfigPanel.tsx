'use client';

import { useMemo } from 'react';
import { Database } from 'lucide-react';
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
  importedSymbols: string[];
  isImportedSymbolsLoading?: boolean;
  lockSymbolInput?: boolean;
  symbol: string;
  timeframe: string;
  startDate: string;
  endDate: string;
  onSymbolChange: (value: string) => void;
  onTimeframeChange: (value: string) => void;
  onStartDateChange: (value: string) => void;
  onEndDateChange: (value: string) => void;
}

function parseSymbolsInput(value: string): string[] {
  return Array.from(
    new Set(
      value
        .split(/[\s,]+/)
        .map((item) => item.trim().toUpperCase())
        .filter((item) => item.length > 0)
    )
  );
}

export default function ConfigPanel({
  config,
  presets,
  dataSources,
  importedSymbols,
  isImportedSymbolsLoading = false,
  lockSymbolInput = false,
  symbol,
  timeframe,
  startDate,
  endDate,
  onSymbolChange,
  onTimeframeChange,
  onStartDateChange,
  onEndDateChange,
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

  const selectedSymbols = useMemo(() => parseSymbolsInput(symbol), [symbol]);

  const toggleImportedSymbol = (target: string) => {
    const next = selectedSymbols.includes(target)
      ? selectedSymbols.filter((item) => item !== target)
      : [...selectedSymbols, target];
    onSymbolChange(next.join(', '));
  };

  const selectAllImportedSymbols = () => {
    onSymbolChange(importedSymbols.join(', '));
  };

  const clearAllImportedSymbols = () => {
    onSymbolChange('');
  };

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
      <div className="px-6 pb-6 space-y-4">
      <details open className="rounded-xl border border-white/10 bg-white/5">
        <summary className="cursor-pointer px-4 py-2 text-sm text-slate-200">目標標的</summary>
        <div className="px-4 pb-4">
        <div className="grid grid-cols-1 gap-3">
          <input
            value={symbol}
            onChange={(event) => onSymbolChange(event.target.value.toUpperCase())}
            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-300/40"
            placeholder="例如: BTCUSDT 或 BTCUSDT,ETHUSDT,SOLUSDT"
            disabled={lockSymbolInput}
          />
          <div className="text-xs text-slate-400">
            {'單一標的會執行一般生成；輸入多標的（逗號或空白分隔）會自動啟用批次生成。'}
          </div>

          <div className="rounded-xl border border-white/10 bg-white/5 p-3 space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-xs text-slate-300">快速填入：從已下載的 K 線標的選取</div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={selectAllImportedSymbols}
                  disabled={importedSymbols.length === 0}
                  className="rounded-md border border-white/15 px-2 py-1 text-[11px] text-slate-200 disabled:opacity-50"
                >
                  全選
                </button>
                <button
                  type="button"
                  onClick={clearAllImportedSymbols}
                  disabled={selectedSymbols.length === 0}
                  className="rounded-md border border-white/15 px-2 py-1 text-[11px] text-slate-200 disabled:opacity-50"
                >
                  全取消
                </button>
              </div>
            </div>

            <div className="text-[11px] text-slate-400">
              {isImportedSymbolsLoading
                ? '載入已下載標的中...'
                : `可勾選 ${importedSymbols.length} 個，已選 ${selectedSymbols.length} 個`}
            </div>

            <div className="max-h-32 overflow-auto rounded-lg border border-white/10 bg-black/10 p-2 grid grid-cols-2 gap-1.5">
              {importedSymbols.map((item) => {
                const checked = selectedSymbols.includes(item);
                return (
                  <label key={item} className="flex items-center gap-2 rounded px-1.5 py-1 text-[11px] text-slate-200 hover:bg-white/5">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleImportedSymbol(item)}
                      className="accent-amber-300"
                    />
                    <span>{item}</span>
                  </label>
                );
              })}

              {!isImportedSymbolsLoading && importedSymbols.length === 0 && (
                <div className="col-span-2 text-[11px] text-slate-400">尚未下載任何 K 線資料（請先使用上方的「K 線下載」下載標的資料）。</div>
              )}
            </div>
          </div>

          <div className="relative">
            <Database className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              value={timeframe}
              onChange={(event) => onTimeframeChange(event.target.value)}
              className="w-full rounded-xl border border-white/10 bg-white/5 px-9 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-300/40"
              placeholder="12h"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.2em] text-slate-400">時間範圍（可選）</label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="text-[11px] text-slate-500 mb-1">開始日期</div>
                <input
                  type="date"
                  value={startDate}
                  onChange={(event) => onStartDateChange(event.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-300/40 [color-scheme:dark]"
                />
              </div>
              <div>
                <div className="text-[11px] text-slate-500 mb-1">結束日期</div>
                <input
                  type="date"
                  value={endDate}
                  onChange={(event) => onEndDateChange(event.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-300/40 [color-scheme:dark]"
                />
              </div>
            </div>
            <div className="text-[11px] text-slate-500">
              留空則使用 K 線全部資料範圍
            </div>
          </div>
        </div>
        </div>
      </details>

      <details open className="rounded-xl border border-white/10 bg-white/5">
        <summary className="cursor-pointer px-4 py-2 text-sm text-slate-200">Preset</summary>
        <div className="px-4 pb-4">
          <PresetSelector
            presets={presets}
            selectedPreset={selectedPreset}
            onPresetChange={handlePresetChange}
          />
        </div>
      </details>

      <details open className="rounded-xl border border-white/10 bg-white/5">
        <summary className="cursor-pointer px-4 py-2 text-sm text-slate-200">數據源</summary>
        <div className="px-4 pb-4">
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
        </div>
      </details>

      <details open className="rounded-xl border border-white/10 bg-white/5">
        <summary className="cursor-pointer px-4 py-2 text-sm text-slate-200">指標類別</summary>
        <div className="px-4 pb-4">
          <IndicatorSelector
            indicators={config.atomic_indicators}
            onChange={(next) =>
              setConfig({
                ...config,
                atomic_indicators: next,
              })
            }
          />
        </div>
      </details>

      <details className="rounded-xl border border-white/10 bg-white/5">
        <summary className="cursor-pointer px-4 py-2 text-sm text-slate-200">全域參數</summary>
        <div className="px-4 pb-4">
          <GlobalParamSliders
            globalSettings={config.global_settings}
            onChange={(next) =>
              setConfig({
                ...config,
                global_settings: next,
              })
            }
          />
        </div>
      </details>

      <details className="rounded-xl border border-white/10 bg-white/5">
        <summary className="cursor-pointer px-4 py-2 text-sm text-slate-200">時間框架</summary>
        <div className="px-4 pb-4">
          <TimeframeSelector
            timeframes={config.timeframes}
            onChange={(next) => {
              setAlignmentMode(next.alignment_mode ?? 'open_minus');
              setTrainingTimeframes(next.training);
              // Sync the outer timeframe text input so it always matches config.timeframes.primary.
              // This prevents the API call from using a stale timeframe value.
              if (next.primary !== timeframe) {
                onTimeframeChange(next.primary);
              }
              setConfig({
                ...config,
                timeframes: next,
              });
            }}
          />
        </div>
      </details>

      <details className="rounded-xl border border-white/10 bg-white/5">
        <summary className="cursor-pointer px-4 py-2 text-sm text-slate-200">進階覆寫</summary>
        <div className="px-4 pb-4">
          <JsonOverrideEditor onApply={handleConfigOverride} />
        </div>
      </details>
      </div>
  );
}

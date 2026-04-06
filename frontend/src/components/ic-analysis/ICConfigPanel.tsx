'use client';

import { useMemo } from 'react';
import { ICAnalysisConfig } from '@/lib/types';
import { FeatureTierLevel } from '@/lib/types';
import { FeatureRegistryEntry } from '@/lib/types';
import FeatureTierPanel from '@/components/ic-analysis/FeatureTierPanel';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { NumberInput } from '@/components/ui/NumberInput';
import { MultiSelect } from '@/components/ui/MultiSelect';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface ICConfigPanelProps {
  config: ICAnalysisConfig;
  registryEntries?: FeatureRegistryEntry[];
  crossSectionalFeatureCount?: number;
  featureTier: FeatureTierLevel;
  featureToggles: Record<string, boolean>;
  onChangeFeatureTier: (tier: FeatureTierLevel) => void;
  onToggleFeature: (key: string) => void;
  onConfigChange: (next: ICAnalysisConfig) => void;
  onRunAnalysis: () => void;
  isRunning: boolean;
}

type ICConfigPatch = Partial<Omit<ICAnalysisConfig, 'thresholds'>> & {
  thresholds?: Partial<ICAnalysisConfig['thresholds']>;
};

const horizonOptions = [1, 2, 3, 5, 8, 13, 21].map((value) => ({
  value: String(value),
  label: `${value} 根`,
}));

export default function ICConfigPanel({
  config,
  registryEntries = [],
  crossSectionalFeatureCount = 0,
  featureTier,
  featureToggles,
  onChangeFeatureTier,
  onToggleFeature,
  onConfigChange,
  onRunAnalysis,
  isRunning,
}: ICConfigPanelProps) {
  const horizonValues = useMemo(() => config.horizons.map((value) => String(value)), [config.horizons]);
  const symbolOptions = useMemo(
    () => Array.from(new Set(registryEntries.map((entry) => entry.symbol))).sort(),
    [registryEntries]
  );
  const timeframeOptions = useMemo(() => {
    if (config.mode === 'cross_sectional') {
      const selectedSymbols = config.cross_sectional_symbols || [];
      if (selectedSymbols.length === 0) {
        return Array.from(new Set(registryEntries.map((entry) => entry.timeframe))).sort();
      }

      const timeframeSets = selectedSymbols.map(
        (symbol) =>
          new Set(
            registryEntries
              .filter((entry) => entry.symbol === symbol)
              .map((entry) => entry.timeframe)
          )
      );

      const [firstSet, ...restSets] = timeframeSets;
      if (!firstSet) {
        return [];
      }

      return Array.from(firstSet)
        .filter((timeframe) => restSets.every((set) => set.has(timeframe)))
        .sort();
    }

    if (!config.symbol) {
      return Array.from(new Set(registryEntries.map((entry) => entry.timeframe))).sort();
    }
    return Array.from(
      new Set(
        registryEntries
          .filter((entry) => entry.symbol === config.symbol)
          .map((entry) => entry.timeframe)
      )
    ).sort();
  }, [config.mode, config.symbol, config.cross_sectional_symbols, registryEntries]);

  const crossSymbolOptions = useMemo(
    () => symbolOptions.map((symbol) => ({ value: symbol, label: symbol })),
    [symbolOptions]
  );

  const isCrossSectionalMode = config.mode === 'cross_sectional';
  const selectedCrossSymbols = config.cross_sectional_symbols || [];
  const crossSymbolInsufficient = isCrossSectionalMode && selectedCrossSymbols.length < 2;
  const crossFeatureOverflow = isCrossSectionalMode && crossSectionalFeatureCount > 50;
  const noAvailableSymbols = isCrossSectionalMode && symbolOptions.length === 0;
  const crossTimeframeInvalid =
    isCrossSectionalMode &&
    Boolean(config.timeframe) &&
    !timeframeOptions.includes(config.timeframe as string);

  const runDisabled =
    isRunning ||
    (isCrossSectionalMode && (
      crossSymbolInsufficient ||
      !config.timeframe ||
      crossTimeframeInvalid ||
      crossFeatureOverflow ||
      noAvailableSymbols
    ));

  const updateConfig = (patch: ICConfigPatch) => {
    onConfigChange({
      ...config,
      ...patch,
      thresholds: {
        ...config.thresholds,
        ...(patch.thresholds || {}),
      },
    });
  };

  return (
    <div className="glass-panel rounded-2xl border border-white/10 p-6 space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.25em] text-cyan-200">IC Gatekeeper</p>
        <h2 className="mt-2 text-xl font-semibold text-slate-100">分析配置</h2>
        <p className="text-sm text-slate-400 mt-1">調整門檻後將自動重新篩選。</p>
      </div>

      <FeatureTierPanel
        featureTier={featureTier}
        featureToggles={featureToggles}
        onChangeTier={onChangeFeatureTier}
        onToggleFeature={onToggleFeature}
      />

      <div className="space-y-4">
        <Input
          placeholder="data_cache/features/{symbol}_{tf}_factory.h5"
          value={config.features_path}
          onChange={(event) => updateConfig({ features_path: event.target.value })}
        />
        <Input
          placeholder="data_cache/features/{symbol}_{tf}_labels.h5"
          value={config.labels_path}
          onChange={(event) => updateConfig({ labels_path: event.target.value })}
        />
        <Input
          placeholder="data_cache/features/{symbol}_{tf}_meta.json"
          value={config.meta_path}
          onChange={(event) => updateConfig({ meta_path: event.target.value })}
        />

        <div className="rounded-lg border border-white/10 p-3 space-y-3">
          <p className="text-xs text-slate-400">或從 Feature Library 選擇</p>
          {!isCrossSectionalMode ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <Select
                value={config.symbol}
                onValueChange={(value) => updateConfig({ symbol: value, timeframe: undefined })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="選擇 Symbol" />
                </SelectTrigger>
                <SelectContent>
                  {symbolOptions.map((symbol) => (
                    <SelectItem key={symbol} value={symbol}>{symbol}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select
                value={config.timeframe}
                onValueChange={(value) => updateConfig({ timeframe: value })}
                disabled={!config.symbol}
              >
                <SelectTrigger>
                  <SelectValue placeholder="選擇 Timeframe" />
                </SelectTrigger>
                <SelectContent>
                  {timeframeOptions.map((timeframe) => (
                    <SelectItem key={timeframe} value={timeframe}>{timeframe}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : (
            <div className="space-y-3">
              <MultiSelect
                label="截面 Symbol 多選"
                options={crossSymbolOptions}
                value={selectedCrossSymbols}
                onChange={(values) =>
                  updateConfig({
                    cross_sectional_symbols: values,
                    timeframe: undefined,
                  })
                }
                placeholder={noAvailableSymbols ? '無可用標的' : '請選擇至少 2 個 Symbol'}
                description="資料來源：Feature Library registry"
                disabled={noAvailableSymbols}
              />
              <Select
                value={config.timeframe}
                onValueChange={(value) => updateConfig({ timeframe: value })}
                disabled={timeframeOptions.length === 0}
              >
                <SelectTrigger>
                  <SelectValue placeholder={timeframeOptions.length === 0 ? '無可用 Timeframe' : '選擇共同 Timeframe'} />
                </SelectTrigger>
                <SelectContent>
                  {timeframeOptions.map((timeframe) => (
                    <SelectItem key={timeframe} value={timeframe}>{timeframe}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>
      </div>

      <div className="space-y-3">
        <label className="text-sm font-medium text-slate-200">分析模式</label>
        <Select
          value={config.mode}
          onValueChange={(value) => updateConfig({ mode: value as ICAnalysisConfig['mode'] })}
        >
          <SelectTrigger>
            <SelectValue placeholder="選擇模式" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="global">Global 模式</SelectItem>
            <SelectItem value="event">Event-Driven 模式</SelectItem>
            <SelectItem value="cross_sectional">截面 IC</SelectItem>
          </SelectContent>
        </Select>

        {config.mode === 'event' && (
          <Textarea
            placeholder="例如: (close > close_EMA_55) & (close_ADX_14 > 25)"
            value={config.event_query || ''}
            onChange={(event) => updateConfig({ event_query: event.target.value })}
            rows={4}
          />
        )}

        {isCrossSectionalMode && (
          <div className="space-y-2 text-xs">
            {crossSymbolInsufficient && (
              <p className="text-amber-300">請至少選擇 2 個 Symbol</p>
            )}
            {crossFeatureOverflow && (
              <p className="text-amber-300">截面 IC 最多支援 50 個因子，請先在 Feature Browser 篩選</p>
            )}
            {crossTimeframeInvalid && (
              <p className="text-amber-300">目前 Timeframe 與已選 Symbol 不相容，請重新選擇共同 Timeframe</p>
            )}
            {noAvailableSymbols && (
              <p className="text-amber-300">無可用標的</p>
            )}
            <p className="text-slate-400">目前預估分析因子數：{crossSectionalFeatureCount}</p>
          </div>
        )}
      </div>

      <div className="space-y-4">
        <NumberInput
          label="IC Mean 最小值"
          value={config.thresholds.ic_mean_min}
          onChange={(value) => updateConfig({ thresholds: { ic_mean_min: value } })}
          min={-1}
          max={1}
          step={0.01}
        />
        <NumberInput
          label="ICIR 最小值"
          value={config.thresholds.icir_min}
          onChange={(value) => updateConfig({ thresholds: { icir_min: value } })}
          min={-2}
          max={3}
          step={0.05}
        />
        <NumberInput
          label="P-Value 最大值"
          value={config.thresholds.p_value_max}
          onChange={(value) => updateConfig({ thresholds: { p_value_max: value } })}
          min={0.001}
          max={0.5}
          step={0.005}
        />
        <NumberInput
          label="單調性分數"
          value={config.thresholds.monotonicity_score_min ?? 0.6}
          onChange={(value) => updateConfig({ thresholds: { monotonicity_score_min: value } })}
          min={0}
          max={1}
          step={0.05}
        />
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-slate-200">相關性閾值</label>
          <span className="text-xs text-slate-400">{config.thresholds.correlation_threshold.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min={0.3}
          max={0.95}
          step={0.01}
          value={config.thresholds.correlation_threshold}
          onChange={(event) =>
            updateConfig({
              thresholds: { correlation_threshold: Number(event.target.value) },
            })
          }
          className="w-full accent-cyan-400"
        />
      </div>

      <MultiSelect
        label="Horizon 多選"
        options={horizonOptions}
        value={horizonValues}
        onChange={(values) =>
          updateConfig({ horizons: values.map((value) => Number(value)).filter((value) => !Number.isNaN(value)) })
        }
        placeholder="選擇 horizon"
      />

      <Button
        onClick={onRunAnalysis}
        disabled={runDisabled}
        className="w-full bg-cyan-500/20 text-cyan-100 border border-cyan-300/30 hover:bg-cyan-500/30"
      >
        {isRunning ? '分析執行中...' : '啟動 IC 分析'}
      </Button>
    </div>
  );
}

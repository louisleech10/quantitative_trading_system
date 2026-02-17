'use client';

import { useMemo } from 'react';
import { ICAnalysisConfig } from '@/lib/types';
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
  onConfigChange,
  onRunAnalysis,
  isRunning,
}: ICConfigPanelProps) {
  const horizonValues = useMemo(() => config.horizons.map((value) => String(value)), [config.horizons]);

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
      </div>

      <div className="space-y-3">
        <label className="text-sm font-medium text-slate-200">分析模式</label>
        <Select
          value={config.mode}
          onValueChange={(value) => updateConfig({ mode: value as 'global' | 'event' })}
        >
          <SelectTrigger>
            <SelectValue placeholder="選擇模式" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="global">Global 模式</SelectItem>
            <SelectItem value="event">Event-Driven 模式</SelectItem>
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
        disabled={isRunning}
        className="w-full bg-cyan-500/20 text-cyan-100 border border-cyan-300/30 hover:bg-cyan-500/30"
      >
        {isRunning ? '分析執行中...' : '啟動 IC 分析'}
      </Button>
    </div>
  );
}

'use client';

import React from 'react';
import { FeatureFactoryConfig } from '@/lib/types';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';

interface IndicatorSelectorProps {
  indicators: FeatureFactoryConfig['atomic_indicators'];
  onChange: (next: FeatureFactoryConfig['atomic_indicators']) => void;
}

type EngineLevel = 'L1' | 'L2' | 'L3';

type AtomicEngineKey =
  | 'trend'
  | 'momentum'
  | 'volatility'
  | 'volume'
  | 'statistics'
  | 'cycle'
  | 'pattern'
  | 'tail_risk'
  | 'microstructure'
  | 'entropy';

interface EngineDefinition {
  key: AtomicEngineKey;
  label: string;
  description: string;
  level: EngineLevel;
  levelLabel: string;
  color: 'emerald' | 'amber' | 'rose';
  previewKey?: string;
}

const ENGINE_DEFINITIONS: EngineDefinition[] = [
  {
    key: 'trend',
    label: '趨勢',
    description: 'EMA、SMA、SAR、BBANDS、DEMA',
    level: 'L1',
    levelLabel: 'Layer 1 · 基礎',
    color: 'emerald',
    previewKey: 'trend',
  },
  {
    key: 'momentum',
    label: '動量',
    description: 'RSI、MACD、ADX、Stochastic、ROC、CCI',
    level: 'L1',
    levelLabel: 'Layer 1 · 基礎',
    color: 'emerald',
    previewKey: 'momentum',
  },
  {
    key: 'volatility',
    label: '波動',
    description: 'ATR、Keltner、Donchian',
    level: 'L1',
    levelLabel: 'Layer 1 · 基礎',
    color: 'emerald',
    previewKey: 'volatility',
  },
  {
    key: 'volume',
    label: '量能',
    description: 'OBV、AD、ADOSC、VWAP',
    level: 'L1',
    levelLabel: 'Layer 1 · 基礎',
    color: 'emerald',
    previewKey: 'volume',
  },
  {
    key: 'statistics',
    label: '統計',
    description: 'LinearReg、STDDEV、CORREL、BETA',
    level: 'L2',
    levelLabel: 'Layer 1 · 中階',
    color: 'amber',
    previewKey: 'statistics',
  },
  {
    key: 'cycle',
    label: '週期',
    description: 'Hilbert Transform、HT_SINE、HT_DCPERIOD',
    level: 'L2',
    levelLabel: 'Layer 1 · 中階',
    color: 'amber',
    previewKey: 'cycle',
  },
  {
    key: 'pattern',
    label: '型態',
    description: 'Doji、Hammer、Engulfing 等型態',
    level: 'L2',
    levelLabel: 'Layer 1 · 中階',
    color: 'amber',
    previewKey: 'pattern',
  },
  {
    key: 'tail_risk',
    label: '尾部風險',
    description: 'CVaR、RV 分解、GPR、MDD',
    level: 'L2',
    levelLabel: 'Layer 1 · 中階',
    color: 'amber',
    previewKey: 'tail_risk',
  },
  {
    key: 'microstructure',
    label: '微觀結構',
    description: 'Amihud、Kyle Lambda、VPIN、OFI',
    level: 'L3',
    levelLabel: 'Layer 1 · 高階',
    color: 'rose',
    previewKey: 'microstructure',
  },
  {
    key: 'entropy',
    label: '資訊理論',
    description: 'Shannon、ApEn、SampEn、Hurst',
    level: 'L3',
    levelLabel: 'Layer 1 · 高階',
    color: 'rose',
    previewKey: 'entropy',
  },
];

const LEVEL_COLORS: Record<EngineDefinition['color'], { badge: string; active: string }> = {
  emerald: {
    badge: 'bg-emerald-400/15 text-emerald-200 border border-emerald-300/30',
    active: 'bg-emerald-400/10 border-emerald-300/40',
  },
  amber: {
    badge: 'bg-amber-400/15 text-amber-200 border border-amber-300/30',
    active: 'bg-amber-400/10 border-amber-300/40',
  },
  rose: {
    badge: 'bg-rose-400/15 text-rose-200 border border-rose-300/30',
    active: 'bg-rose-400/10 border-rose-300/40',
  },
};

export default function IndicatorSelector({ indicators, onChange }: IndicatorSelectorProps) {
  const { preview } = useFeatureFactoryStore();

  const [activeLevel, setActiveLevel] =
    React.useState<'ALL' | EngineLevel>('ALL');

  const toggleCategory = (key: AtomicEngineKey) => {
    onChange({
      ...indicators,
      [key]: {
        ...indicators[key],
        enabled: !indicators[key]?.enabled,
      },
    });
  };

  const applyBulkEnable = (levels: EngineLevel[]) => {
    const next = { ...indicators };

    ENGINE_DEFINITIONS.forEach((engine) => {
      next[engine.key] = {
        ...(next[engine.key] ?? { enabled: false }),
        enabled: levels.includes(engine.level),
      };
    });

    onChange(next);
  };

  const tabs = [
    { key: 'ALL' as const, label: '全部', count: ENGINE_DEFINITIONS.length },
    { key: 'L1' as const, label: '🟢 基礎', count: ENGINE_DEFINITIONS.filter((e) => e.level === 'L1').length },
    { key: 'L2' as const, label: '🟡 中階', count: ENGINE_DEFINITIONS.filter((e) => e.level === 'L2').length },
    { key: 'L3' as const, label: '🔴 高階', count: ENGINE_DEFINITIONS.filter((e) => e.level === 'L3').length },
  ];

  const filteredEngines =
    activeLevel === 'ALL'
      ? ENGINE_DEFINITIONS
      : ENGINE_DEFINITIONS.filter((engine) => engine.level === activeLevel);

  return (
    <div className="space-y-3">
      <label className="text-xs uppercase tracking-[0.2em] text-slate-400">指標類別</label>
      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveLevel(tab.key)}
            className={`rounded-lg border px-3 py-1.5 text-xs transition ${
              activeLevel === tab.key
                ? 'bg-cyan-400/15 text-cyan-100 border-cyan-300/40'
                : 'bg-white/5 text-slate-400 border-white/10 hover:border-cyan-300/40'
            }`}
          >
            {tab.label}({tab.count})
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 min-[1440px]:grid-cols-4 gap-2">
        {filteredEngines.map((engine) => {
          const active = indicators[engine.key]?.enabled ?? false;
          const color = LEVEL_COLORS[engine.color];
          const featureCount =
            engine.previewKey && preview?.breakdown
              ? preview.breakdown[engine.previewKey]
              : undefined;

          return (
            <button
              key={engine.key}
              type="button"
              onClick={() => toggleCategory(engine.key)}
              className={`rounded-xl border px-3 py-2 text-xs text-left transition ${
                active
                  ? `${color.active} text-slate-100`
                  : 'bg-white/5 text-slate-400 border-white/10 hover:border-cyan-300/40'
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="font-medium">{engine.label}</div>
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${color.badge}`}>
                  {engine.levelLabel}
                </span>
              </div>
              <div className="text-[11px] text-slate-400 mt-1 line-clamp-2">{engine.description}</div>
              <div className="mt-2 flex items-center justify-between text-[11px]">
                <span className="text-slate-500">
                  {typeof featureCount === 'number' ? `${featureCount.toLocaleString('en-US')} features` : '—'}
                </span>
                <span className={active ? 'text-cyan-200' : 'text-slate-500'}>{active ? '✓ 已啟用' : '○ 未啟用'}</span>
              </div>
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap gap-2 pt-1">
        <button
          type="button"
          onClick={() => applyBulkEnable(['L1'])}
          className="rounded-lg border border-emerald-300/30 bg-emerald-400/10 px-3 py-1.5 text-xs text-emerald-100"
        >
          一鍵啟用所有基礎
        </button>
        <button
          type="button"
          onClick={() => applyBulkEnable(['L1', 'L2'])}
          className="rounded-lg border border-amber-300/30 bg-amber-400/10 px-3 py-1.5 text-xs text-amber-100"
        >
          啟用基礎+中階
        </button>
        <button
          type="button"
          onClick={() => applyBulkEnable(['L1', 'L2', 'L3'])}
          className="rounded-lg border border-rose-300/30 bg-rose-400/10 px-3 py-1.5 text-xs text-rose-100"
        >
          全部啟用
        </button>
      </div>
    </div>
  );
}

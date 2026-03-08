'use client';

import React, { useState, useCallback } from 'react';
import { Layers, Search, X } from 'lucide-react';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import { FeaturePreview, FeatureSchema, SchemaIndicator } from '@/lib/types';
import CategorySection from './CategorySection';
import IndicatorCheckbox from './IndicatorCheckbox';

type LayerKey = 'layer1' | 'layer2' | 'layer3' | 'layer4' | 'layer5' | 'layer6' | 'layer6_5';

const LAYER_TABS: { key: LayerKey; label: string; shortLabel: string }[] = [
  { key: 'layer1', label: 'Layer 1', shortLabel: 'L1' },
  { key: 'layer2', label: 'Layer 2', shortLabel: 'L2' },
  { key: 'layer3', label: 'Layer 3', shortLabel: 'L3' },
  { key: 'layer4', label: 'Layer 4', shortLabel: 'L4' },
  { key: 'layer5', label: 'Layer 5', shortLabel: 'L5' },
  { key: 'layer6', label: 'Layer 6', shortLabel: 'L6' },
  { key: 'layer6_5', label: 'Layer 6.5', shortLabel: '6.5' },
];

interface LayerPanelProps {
  schema: FeatureSchema | null;
}

export default function LayerPanel({ schema }: LayerPanelProps) {
  const [activeLayer, setActiveLayer] = useState<LayerKey>('layer1');

  const {
    config,
    preview,
    indicatorSearch,
    setIndicatorSearch,
    toggleIndicator,
    toggleAllInCategory,
    toggleCategory,
    toggleAggregator,
    toggleAllAggregators,
    toggleMetaSubEngine,
    toggleCrossFeature,
    toggleOperator,
    updateConfigPartial,
  } = useFeatureFactoryStore();

  // Layer 1 toggle
  const handleLayerToggle = useCallback(
    (layerKey: LayerKey, enabled: boolean) => {
      switch (layerKey) {
        case 'layer3':
          updateConfigPartial({ rolling_aggregation: { ...(config?.rolling_aggregation ?? {}), enabled } });
          break;
        case 'layer4':
          updateConfigPartial({ lag_features: { ...(config?.lag_features ?? {}), enabled } });
          break;
        case 'layer5':
          updateConfigPartial({ cross_sectional: { ...(config?.cross_sectional ?? {}), enabled } });
          break;
        case 'layer6':
          updateConfigPartial({ meta_features: { ...(config?.meta_features ?? {}), enabled } });
          break;
        case 'layer6_5':
          updateConfigPartial({ preprocessing: { ...(config?.preprocessing ?? {}), enabled } });
          break;
        default:
          break;
      }
    },
    [config, updateConfigPartial]
  );

  const isLayerEnabled = useCallback(
    (layerKey: LayerKey): boolean => {
      if (!schema) return true;
      const layer = schema.layers[layerKey];
      if (!layer) return true;
      if (layerKey === 'layer3') return config?.rolling_aggregation?.enabled !== false;
      if (layerKey === 'layer4') return config?.lag_features?.enabled !== false;
      if (layerKey === 'layer5') return config?.cross_sectional?.enabled === true;
      if (layerKey === 'layer6') return config?.meta_features?.enabled !== false;
      if (layerKey === 'layer6_5') return config?.preprocessing?.enabled === true;
      return layer.enabled;
    },
    [schema, config]
  );

  if (!schema) {
    return (
      <div className="glass-panel rounded-2xl p-6">
        <div className="text-sm text-slate-400">載入 Schema 中...</div>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-2xl p-4 space-y-4 border border-white/10">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 rounded-lg bg-violet-400/15 flex items-center justify-center">
          <Layers className="w-4 h-4 text-violet-200" />
        </div>
        <div>
          <div className="text-sm font-semibold text-slate-100">細粒度指標控制</div>
          <div className="text-[11px] text-slate-400">逐層配置每個指標的啟用狀態</div>
        </div>
      </div>

      {/* Search bar (C6) */}
      <div className="relative">
        <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={indicatorSearch}
          onChange={(e) => setIndicatorSearch(e.target.value)}
          placeholder="搜尋指標名稱..."
          className="w-full rounded-lg border border-white/10 bg-white/5 pl-8 pr-8 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-300/40"
        />
        {indicatorSearch && (
          <button
            type="button"
            onClick={() => setIndicatorSearch('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Tab navigation */}
      <div className="flex flex-wrap gap-1">
        {LAYER_TABS.map((tab) => {
          const layerEnabled = isLayerEnabled(tab.key);
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveLayer(tab.key)}
              className={`rounded-md px-2.5 py-1 text-[11px] transition border ${
                activeLayer === tab.key
                  ? 'bg-cyan-400/15 text-cyan-100 border-cyan-300/40'
                  : 'bg-white/5 text-slate-400 border-white/10 hover:border-cyan-300/30'
              } ${!layerEnabled ? 'opacity-50' : ''}`}
            >
              {tab.shortLabel}
            </button>
          );
        })}
      </div>

      {/* Layer content */}
      <LayerContent
        schema={schema}
        layerKey={activeLayer}
        layerEnabled={isLayerEnabled(activeLayer)}
        searchFilter={indicatorSearch}
        preview={preview}
        onLayerToggle={(enabled) => handleLayerToggle(activeLayer, enabled)}
        onCategoryToggle={toggleCategory}
        onItemToggle={toggleIndicator}
        onSelectAll={toggleAllInCategory}
        onAggregatorToggle={toggleAggregator}
        onAllAggregatorsToggle={toggleAllAggregators}
        onMetaToggle={toggleMetaSubEngine}
        onCrossFeatureToggle={toggleCrossFeature}
        onOperatorToggle={toggleOperator}
      />
    </div>
  );
}

// ─── Layer Content Renderer ─────────────────────────────────────────

interface LayerContentProps {
  schema: FeatureSchema;
  layerKey: LayerKey;
  layerEnabled: boolean;
  searchFilter: string;
  preview: FeaturePreview | null;
  onLayerToggle: (enabled: boolean) => void;
  onCategoryToggle: (cat: string, enabled: boolean) => void;
  onItemToggle: (cat: string, name: string, enabled: boolean) => void;
  onSelectAll: (cat: string, enabled: boolean) => void;
  onAggregatorToggle: (name: string, enabled: boolean) => void;
  onAllAggregatorsToggle: (enabled: boolean) => void;
  onMetaToggle: (name: string, enabled: boolean) => void;
  onCrossFeatureToggle: (name: string, enabled: boolean) => void;
  onOperatorToggle: (name: string, enabled: boolean) => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  trend: '趨勢', momentum: '動量', volatility: '波動', volume: '量能',
  cycle: '週期', pattern: '型態', statistics: '統計',
  microstructure: '微觀結構', entropy: '資訊熵', tail_risk: '尾部風險',
};

function LayerContent({
  schema,
  layerKey,
  layerEnabled,
  searchFilter,
  preview,
  onLayerToggle,
  onCategoryToggle,
  onItemToggle,
  onSelectAll,
  onAggregatorToggle,
  onAllAggregatorsToggle,
  onMetaToggle,
  onCrossFeatureToggle,
  onOperatorToggle,
}: LayerContentProps) {
  const layer = schema.layers[layerKey];
  if (!layer) return <div className="text-xs text-slate-500">未知 Layer</div>;

  const showLayerToggle = ['layer3', 'layer4', 'layer5', 'layer6', 'layer6_5'].includes(layerKey);

  return (
    <div className="space-y-3">
      {/* Layer-level toggle */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-200">{layer.name}</span>
        {showLayerToggle && (
          <button
            type="button"
            onClick={() => onLayerToggle(!layerEnabled)}
            className={`rounded-md border px-2 py-1 text-[10px] transition ${
              layerEnabled
                ? 'bg-cyan-400/15 text-cyan-100 border-cyan-300/40'
                : 'bg-white/5 text-slate-500 border-white/10'
            }`}
          >
            {layerEnabled ? '● 啟用' : '○ 停用'}
          </button>
        )}
      </div>

      {/* Per-layer content */}
      {layerKey === 'layer1' && (
        <Layer1Content
          categories={schema.layers.layer1.categories}
          layerDisabled={!layerEnabled}
          searchFilter={searchFilter}
          preview={preview}
          onCategoryToggle={onCategoryToggle}
          onItemToggle={onItemToggle}
          onSelectAll={onSelectAll}
        />
      )}
      {layerKey === 'layer2' && (
        <Layer2Content
          operators={schema.layers.layer2.operators}
          layerDisabled={!layerEnabled}
          onOperatorToggle={onOperatorToggle}
        />
      )}
      {layerKey === 'layer3' && (
        <Layer3Content
          aggregators={schema.layers.layer3.aggregators}
          windows={schema.layers.layer3.windows}
          layerDisabled={!layerEnabled}
          onAggregatorToggle={onAggregatorToggle}
          onAllToggle={onAllAggregatorsToggle}
        />
      )}
      {layerKey === 'layer4' && (
        <Layer4Content layer={schema.layers.layer4} layerDisabled={!layerEnabled} />
      )}
      {layerKey === 'layer5' && (
        <Layer5Content
          features={schema.layers.layer5.features}
          layerDisabled={!layerEnabled}
          onFeatureToggle={onCrossFeatureToggle}
        />
      )}
      {layerKey === 'layer6' && (
        <Layer6Content
          subEngines={schema.layers.layer6.sub_engines}
          layerDisabled={!layerEnabled}
          onToggle={onMetaToggle}
        />
      )}
      {layerKey === 'layer6_5' && (
        <Layer65Content layer={schema.layers.layer6_5} layerDisabled={!layerEnabled} />
      )}
    </div>
  );
}

// ─── Layer 1 ────────────────────────────────────────────────────

function Layer1Content({
  categories,
  layerDisabled,
  searchFilter,
  preview,
  onCategoryToggle,
  onItemToggle,
  onSelectAll,
}: {
  categories: FeatureSchema['layers']['layer1']['categories'];
  layerDisabled: boolean;
  searchFilter: string;
  preview: FeaturePreview | null;
  onCategoryToggle: (cat: string, enabled: boolean) => void;
  onItemToggle: (cat: string, name: string, enabled: boolean) => void;
  onSelectAll: (cat: string, enabled: boolean) => void;
}) {
  const categoryOrder = [
    'trend', 'momentum', 'volatility', 'volume',
    'statistics', 'cycle', 'pattern',
    'tail_risk', 'microstructure', 'entropy',
  ];

  return (
    <div className="space-y-2">
      {categoryOrder.map((catKey) => {
        const cat = categories[catKey];
        if (!cat) return null;
        const items: SchemaIndicator[] = cat.indicators || cat.features || [];
        return (
          <CategorySection
            key={catKey}
            categoryKey={catKey}
            label={CATEGORY_LABELS[catKey] || catKey}
            description={cat.description}
            level={cat.level}
            enabled={cat.enabled}
            items={items}
            layerDisabled={layerDisabled}
            featureCount={preview?.breakdown?.[catKey]}
            searchFilter={searchFilter}
            onCategoryToggle={(enabled) => onCategoryToggle(catKey, enabled)}
            onItemToggle={(name, enabled) => onItemToggle(catKey, name, enabled)}
            onSelectAll={() => onSelectAll(catKey, true)}
            onDeselectAll={() => onSelectAll(catKey, false)}
          />
        );
      })}
    </div>
  );
}

// ─── Layer 2 ────────────────────────────────────────────────────

function Layer2Content({
  operators,
  layerDisabled,
  onOperatorToggle,
}: {
  operators: FeatureSchema['layers']['layer2']['operators'];
  layerDisabled: boolean;
  onOperatorToggle: (name: string, enabled: boolean) => void;
}) {
  return (
    <div className={`space-y-1 ${layerDisabled ? 'opacity-50 pointer-events-none' : ''}`}>
      {Object.entries(operators).map(([name, op]) => (
        <label
          key={name}
          className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs transition cursor-pointer ${
            op.enabled ? 'bg-cyan-400/10 text-slate-100' : 'text-slate-400 hover:bg-white/5'
          }`}
        >
          <input
            type="checkbox"
            checked={op.enabled}
            disabled={layerDisabled}
            onChange={(e) => onOperatorToggle(name, e.target.checked)}
            className="h-3.5 w-3.5 rounded border-white/20 bg-white/5 accent-cyan-400"
          />
          <span className="font-medium">{name}</span>
          <span className="text-[10px] text-slate-500 ml-auto">{op.description}</span>
        </label>
      ))}
    </div>
  );
}

// ─── Layer 3 ────────────────────────────────────────────────────

function Layer3Content({
  aggregators,
  windows,
  layerDisabled,
  onAggregatorToggle,
  onAllToggle,
}: {
  aggregators: FeatureSchema['layers']['layer3']['aggregators'];
  windows: number[];
  layerDisabled: boolean;
  onAggregatorToggle: (name: string, enabled: boolean) => void;
  onAllToggle: (enabled: boolean) => void;
}) {
  const allEnabled = Object.values(aggregators).every((a) => a.enabled);

  return (
    <div className={`space-y-2 ${layerDisabled ? 'opacity-50 pointer-events-none' : ''}`}>
      <div className="flex items-center gap-2 text-[10px]">
        <span className="text-slate-400">Windows: {windows.join(', ')}</span>
        <span className="ml-auto text-cyan-300 cursor-pointer hover:text-cyan-100" onClick={() => onAllToggle(!allEnabled)}>
          {allEnabled ? '全取消' : '全選'}
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-1">
        {Object.entries(aggregators).map(([name, agg]) => (
          <IndicatorCheckbox
            key={name}
            name={name}
            enabled={agg.enabled}
            description={agg.description}
            disabled={layerDisabled}
            onChange={(val) => onAggregatorToggle(name, val)}
          />
        ))}
      </div>
    </div>
  );
}

// ─── Layer 4 ────────────────────────────────────────────────────

function Layer4Content({
  layer,
  layerDisabled,
}: {
  layer: FeatureSchema['layers']['layer4'];
  layerDisabled: boolean;
}) {
  return (
    <div className={`text-xs space-y-1 ${layerDisabled ? 'opacity-50' : ''}`}>
      <div className="text-slate-400">
        套用範圍: <span className="text-slate-200">{layer.apply_to}</span>
      </div>
      {layer.exclude_patterns.length > 0 && (
        <div className="text-slate-400">
          排除: <span className="text-slate-200">{layer.exclude_patterns.join(', ')}</span>
        </div>
      )}
      <div className="text-[10px] text-slate-500">Layer 4 控制由全域設定管理</div>
    </div>
  );
}

// ─── Layer 5 ────────────────────────────────────────────────────

function Layer5Content({
  features,
  layerDisabled,
  onFeatureToggle,
}: {
  features: FeatureSchema['layers']['layer5']['features'];
  layerDisabled: boolean;
  onFeatureToggle: (name: string, enabled: boolean) => void;
}) {
  return (
    <div className={`space-y-1 ${layerDisabled ? 'opacity-50 pointer-events-none' : ''}`}>
      {Object.entries(features).map(([name, feat]) => (
        <IndicatorCheckbox
          key={name}
          name={name}
          enabled={feat.enabled}
          description={feat.description}
          disabled={layerDisabled}
          onChange={(val) => onFeatureToggle(name, val)}
        />
      ))}
    </div>
  );
}

// ─── Layer 6 ────────────────────────────────────────────────────

function Layer6Content({
  subEngines,
  layerDisabled,
  onToggle,
}: {
  subEngines: FeatureSchema['layers']['layer6']['sub_engines'];
  layerDisabled: boolean;
  onToggle: (name: string, enabled: boolean) => void;
}) {
  return (
    <div className={`space-y-1 ${layerDisabled ? 'opacity-50 pointer-events-none' : ''}`}>
      {Object.entries(subEngines).map(([name, engine]) => (
        <label
          key={name}
          className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs transition cursor-pointer ${
            engine.enabled ? 'bg-cyan-400/10 text-slate-100' : 'text-slate-400 hover:bg-white/5'
          }`}
        >
          <input
            type="checkbox"
            checked={engine.enabled}
            disabled={layerDisabled}
            onChange={(e) => onToggle(name, e.target.checked)}
            className="h-3.5 w-3.5 rounded border-white/20 bg-white/5 accent-cyan-400"
          />
          <span className="font-medium">{name}</span>
          <span className="text-[10px] text-slate-500 ml-auto">{engine.description}</span>
        </label>
      ))}
    </div>
  );
}

// ─── Layer 6.5 ──────────────────────────────────────────────────

function Layer65Content({
  layer,
  layerDisabled,
}: {
  layer: FeatureSchema['layers']['layer6_5'];
  layerDisabled: boolean;
}) {
  return (
    <div className={`text-xs space-y-1 ${layerDisabled ? 'opacity-50' : ''}`}>
      <div className="text-slate-400">
        模式: <span className="text-slate-200">{layer.mode}</span>
      </div>
      <div className="space-y-1">
        {Object.entries(layer.methods).map(([name, method]) => (
          <div
            key={name}
            className={`flex items-center gap-2 rounded-lg px-3 py-2 ${
              method.enabled ? 'bg-cyan-400/10 text-slate-100' : 'text-slate-400'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${method.enabled ? 'bg-cyan-400' : 'bg-slate-600'}`} />
            <span className="font-medium">{name}</span>
            <span className="text-[10px] text-slate-500 ml-auto">{method.description}</span>
          </div>
        ))}
      </div>
      <div className="text-[10px] text-slate-500">Layer 6.5 的方法控制在前處理面板中操作</div>
    </div>
  );
}

'use client';

import React, { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import IndicatorCheckbox from './IndicatorCheckbox';
import { SchemaIndicator } from '@/lib/types';

interface CategorySectionProps {
  label: string;
  description: string;
  level: string;
  enabled: boolean;
  /** Indicators list for TA-Lib categories, or features list for special categories */
  items: SchemaIndicator[];
  /** Category-level disabled (e.g., whole layer disabled) */
  layerDisabled?: boolean;
  /** Feature count from preview */
  featureCount?: number;
  /** Search filter string */
  searchFilter?: string;
  onCategoryToggle: (enabled: boolean) => void;
  onItemToggle: (name: string, enabled: boolean) => void;
  onSelectAll: () => void;
  onDeselectAll: () => void;
}

const LEVEL_STYLE: Record<string, { badge: string; border: string }> = {
  L1: {
    badge: 'bg-emerald-400/15 text-emerald-200 border-emerald-300/30',
    border: 'border-emerald-300/20',
  },
  L2: {
    badge: 'bg-amber-400/15 text-amber-200 border-amber-300/30',
    border: 'border-amber-300/20',
  },
  L3: {
    badge: 'bg-rose-400/15 text-rose-200 border-rose-300/30',
    border: 'border-rose-300/20',
  },
};

export default function CategorySection({
  label,
  description,
  level,
  enabled,
  items,
  layerDisabled = false,
  featureCount,
  searchFilter,
  onCategoryToggle,
  onItemToggle,
  onSelectAll,
  onDeselectAll,
}: CategorySectionProps) {
  // Default all categories to collapsed for cleaner initial view.
  const [expanded, setExpanded] = useState(false);

  const filteredItems = useMemo(() => {
    if (!searchFilter) return items;
    const lower = searchFilter.toLowerCase();
    return items.filter(
      (item) =>
        item.name.toLowerCase().includes(lower) ||
        (item.description && item.description.toLowerCase().includes(lower))
    );
  }, [items, searchFilter]);

  const allEnabled = items.length > 0 && items.every((i) => i.enabled);
  const noneEnabled = items.every((i) => !i.enabled);
  const indeterminate = !allEnabled && !noneEnabled;

  const style = LEVEL_STYLE[level] || LEVEL_STYLE.L1;
  const isDisabled = layerDisabled || !enabled;

  return (
    <div className={`rounded-xl border ${style.border} bg-white/[0.02] overflow-hidden`}>
      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-2 cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
        onKeyDown={(e) => e.key === 'Enter' && setExpanded(!expanded)}
        role="button"
        tabIndex={0}
      >
        {expanded ? (
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
        )}

        {/* Category checkbox (3-state) */}
        <input
          ref={(el) => {
            if (el) el.indeterminate = indeterminate;
          }}
          type="checkbox"
          checked={enabled && allEnabled}
          disabled={layerDisabled}
          onChange={() => onCategoryToggle(!enabled)}
          onClick={(e) => e.stopPropagation()}
          className="h-3.5 w-3.5 rounded border-white/20 bg-white/5 accent-cyan-400"
        />

        <span className="text-xs font-medium text-slate-100 flex-1">{label}</span>
        <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${style.badge}`}>
          {level}
        </span>
        <span className="text-[10px] text-slate-500">
          {items.filter((i) => i.enabled).length}/{items.length}
        </span>
        {typeof featureCount === 'number' && (
          <span className="text-[10px] text-slate-500">
            {featureCount.toLocaleString('en-US')} feat
          </span>
        )}
      </div>

      {/* Body */}
      {expanded && (
        <div className={`px-3 pb-3 space-y-2 ${isDisabled ? 'opacity-50 pointer-events-none' : ''}`}>
          {/* Select All / Deselect All buttons */}
          <div className="flex items-center gap-2 pt-1">
            <button
              type="button"
              onClick={onSelectAll}
              className="text-[10px] text-cyan-300 hover:text-cyan-100 transition"
            >
              全選
            </button>
            <span className="text-slate-600">|</span>
            <button
              type="button"
              onClick={onDeselectAll}
              className="text-[10px] text-slate-400 hover:text-slate-200 transition"
            >
              全取消
            </button>
            {description && (
              <span className="text-[10px] text-slate-500 ml-auto truncate" title={description}>
                {description}
              </span>
            )}
          </div>

          {/* Indicator grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-0.5">
            {filteredItems.map((item) => (
              <IndicatorCheckbox
                key={item.name}
                name={item.name}
                enabled={item.enabled}
                description={item.description}
                disabled={isDisabled}
                onChange={(val) => onItemToggle(item.name, val)}
              />
            ))}
          </div>

          {filteredItems.length === 0 && (
            <div className="text-[11px] text-slate-500 py-2">無符合搜尋的指標</div>
          )}
        </div>
      )}
    </div>
  );
}

'use client';

import { useMemo, useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { FeatureFilterConfig, FeatureListItem } from '@/lib/types';
import { MultiSelect } from '@/components/ui/MultiSelect';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface FeatureFilterPanelProps {
  availableFeatures: FeatureListItem[];
  filter: FeatureFilterConfig;
  onFilterChange: (filter: FeatureFilterConfig) => void;
  onFilteredFeaturesChange: (features: string[]) => void;
}

export default function FeatureFilterPanel({
  availableFeatures,
  filter,
  onFilterChange,
  onFilteredFeaturesChange,
}: FeatureFilterPanelProps) {
  const [collapsed, setCollapsed] = useState(true);

  const categoryOptions = useMemo(() => {
    const values = [...new Set(availableFeatures.map((item) => item.category).filter(Boolean))] as string[];
    return values.map((value) => ({ value, label: value }));
  }, [availableFeatures]);

  const dataSourceOptions = useMemo(() => {
    const values = [...new Set(availableFeatures.map((item) => item.data_source).filter(Boolean))] as string[];
    return values.map((value) => ({ value, label: value }));
  }, [availableFeatures]);

  const filteredFeatures = useMemo(() => {
    const keyword = (filter.include_pattern || '').trim();
    let regex: RegExp | null = null;
    if (keyword) {
      try {
        regex = new RegExp(keyword, 'i');
      } catch {
        regex = null;
      }
    }

    const matched = availableFeatures.filter((item) => {
      const categoryPass =
        !filter.include_categories ||
        filter.include_categories.length === 0 ||
        (item.category && filter.include_categories.includes(item.category));

      const sourcePass =
        !filter.include_data_sources ||
        filter.include_data_sources.length === 0 ||
        (item.data_source && filter.include_data_sources.includes(item.data_source));

      const textPass = !keyword || (regex ? regex.test(item.feature_name) : item.feature_name.includes(keyword));
      return Boolean(categoryPass && sourcePass && textPass);
    });

    const maxFeatures = filter.max_features && filter.max_features > 0 ? filter.max_features : matched.length;
    return matched.slice(0, maxFeatures).map((item) => item.feature_name);
  }, [availableFeatures, filter]);

  const invalidRegex = useMemo(() => {
    const keyword = (filter.include_pattern || '').trim();
    if (!keyword) return false;
    try {
      new RegExp(keyword);
      return false;
    } catch {
      return true;
    }
  }, [filter.include_pattern]);

  return (
    <Card className="glass-panel rounded-2xl border border-white/10">
      <CardHeader className="pb-3">
        <button
          type="button"
          onClick={() => setCollapsed((prev) => !prev)}
          className="w-full flex items-center justify-between"
        >
          <CardTitle className="text-base text-slate-100">Feature 預過濾</CardTitle>
          {collapsed ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronUp className="h-4 w-4 text-slate-400" />}
        </button>
      </CardHeader>
      {!collapsed && (
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            <Input
              value={filter.include_pattern || ''}
              onChange={(event) => onFilterChange({ include_pattern: event.target.value })}
              placeholder="關鍵字 / 正則"
            />
            <Input
              type="number"
              min={1}
              max={500}
              value={filter.max_features ?? 30}
              onChange={(event) => onFilterChange({ max_features: Number(event.target.value) })}
              placeholder="最大因子數"
            />
            <div className="text-xs text-slate-300 flex items-center rounded-md border border-white/10 px-3 py-2 bg-white/5">
              匹配數量：{filteredFeatures.length}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <MultiSelect
              label="類別"
              options={categoryOptions}
              value={filter.include_categories || []}
              onChange={(value) => onFilterChange({ include_categories: value })}
              placeholder="選擇類別"
            />
            <MultiSelect
              label="資料源"
              options={dataSourceOptions}
              value={filter.include_data_sources || []}
              onChange={(value) => onFilterChange({ include_data_sources: value })}
              placeholder="選擇資料源"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              className="px-3 py-2 text-sm rounded-md bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-100 border border-cyan-400/20"
              onClick={() => onFilteredFeaturesChange(filteredFeatures)}
            >
              套用預過濾
            </button>
            {invalidRegex && <span className="text-xs text-rose-300">正則格式錯誤，已改用一般文字匹配</span>}
          </div>
        </CardContent>
      )}
    </Card>
  );
}

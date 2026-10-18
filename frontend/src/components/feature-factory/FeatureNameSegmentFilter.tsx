'use client';

import { useEffect, useMemo, useState } from 'react';
import { useFeatureDescriptor } from '@/lib/featureDescriptor';
import type { FeatureDescriptor } from '@/lib/types';

/**
 * 命名段落篩選（FF-NAME Task 3.3）：段落值一律取自後端描述（經共享 map），
 * 不解析欄名字串；map 查無或版本／kind 不符之欄名歸 unsupported，不參與段落選項。
 */
interface FeatureNameSegmentFilterProps {
  /** 共享描述 map 所屬 task。 */
  taskId: string;
  /** 欄名清單（原樣；語意一律經 hook 查 map）。 */
  features: string[];
  /** 篩選結果：回傳欄名。 */
  onFilteredFeaturesChange: (features: string[]) => void;
}

type SelectMode = 'single' | 'multi';

type FeatureSegmentKey = 'kind' | 'source' | 'timeframe' | 'category' | 'indicator' | 'params' | 'operator';

interface ParsedFeatureItem {
  name: string;
  /** 描述有效（status ok）才有段落值；unsupported 為 null。 */
  segments: Record<FeatureSegmentKey, string[]> | null;
  /** params 文字搜尋用之扁平字串（取自描述 params，非欄名）。 */
  paramsText: string;
}

const SEGMENT_DEFS: Array<{ key: FeatureSegmentKey; label: string }> = [
  { key: 'kind', label: 'Kind' },
  { key: 'source', label: 'Source' },
  { key: 'timeframe', label: 'Timeframe' },
  { key: 'category', label: 'Category' },
  { key: 'indicator', label: 'Indicator' },
  { key: 'params', label: 'Params' },
  { key: 'operator', label: 'Operator' },
];

function buildSegmentMap<T>(factory: () => T): Record<FeatureSegmentKey, T> {
  return {
    kind: factory(),
    source: factory(),
    timeframe: factory(),
    category: factory(),
    indicator: factory(),
    params: factory(),
    operator: factory(),
  };
}

function nonEmpty(value: string | undefined): string[] {
  return value ? [value] : [];
}

function segmentsOf(d: FeatureDescriptor): Record<FeatureSegmentKey, string[]> {
  return {
    kind: nonEmpty(d.kind),
    source: nonEmpty(d.source),
    timeframe: nonEmpty(d.tf),
    category: nonEmpty(d.category),
    indicator: nonEmpty(d.indicator),
    params: [],
    operator: (d.ops ?? []).filter((op) => op.length > 0),
  };
}

function paramsTextOf(d: FeatureDescriptor): string {
  const layers = Array.isArray(d.params) ? d.params : [];
  return layers.map((layer) => (Array.isArray(layer) ? layer.join('-') : String(layer))).join('~');
}

export default function FeatureNameSegmentFilter({ taskId, features, onFilteredFeaturesChange }: FeatureNameSegmentFilterProps) {
  const { resolve } = useFeatureDescriptor(taskId);
  const [freeText, setFreeText] = useState('');
  const [selected, setSelected] = useState<Record<FeatureSegmentKey, string[]>>(
    buildSegmentMap<string[]>(() => []),
  );
  const [modes, setModes] = useState<Record<FeatureSegmentKey, SelectMode>>(
    buildSegmentMap<SelectMode>(() => 'multi'),
  );
  const [openMap, setOpenMap] = useState<Record<FeatureSegmentKey, boolean>>(
    buildSegmentMap<boolean>(() => false),
  );
  const [indicatorSearch, setIndicatorSearch] = useState('');
  const [paramsSearch, setParamsSearch] = useState('');

  const parsed = useMemo<ParsedFeatureItem[]>(
    () =>
      features.map((itemName) => {
        const result = resolve(itemName);
        if (result.status !== 'ok') return { name: itemName, segments: null, paramsText: '' };
        return { name: itemName, segments: segmentsOf(result.descriptor), paramsText: paramsTextOf(result.descriptor) };
      }),
    [features, resolve],
  );

  const unsupportedCount = useMemo(() => parsed.filter((item) => item.segments === null).length, [parsed]);

  const optionsBySegment = useMemo(() => {
    const sets = buildSegmentMap<Set<string>>(() => new Set<string>());
    for (const item of parsed) {
      if (!item.segments) continue;
      for (const seg of SEGMENT_DEFS) {
        for (const value of item.segments[seg.key]) sets[seg.key].add(value);
      }
    }

    const result = buildSegmentMap<string[]>(() => []);
    for (const seg of SEGMENT_DEFS) {
      result[seg.key] = Array.from(sets[seg.key]).sort((a, b) => a.localeCompare(b));
    }

    return result;
  }, [parsed]);

  const filtered = useMemo(() => {
    const lower = freeText.trim().toLowerCase();
    const paramsLower = paramsSearch.trim().toLowerCase();
    return parsed
      .filter((item) => {
        if (lower && !item.name.toLowerCase().includes(lower)) return false;
        for (const seg of SEGMENT_DEFS) {
          if (seg.key === 'params') continue; // params uses text search instead
          const picked = selected[seg.key];
          if (picked.length === 0) continue;
          // unsupported（無有效描述）於任一段落選取時一律排除，不猜測其段落
          if (!item.segments) return false;
          if (!item.segments[seg.key].some((v) => picked.includes(v))) return false;
        }
        if (paramsLower) {
          if (!item.segments) return false;
          if (!item.paramsText.toLowerCase().includes(paramsLower)) return false;
        }
        return true;
      })
      .map((item) => item.name);
  }, [parsed, freeText, selected, paramsSearch]);

  useEffect(() => {
    onFilteredFeaturesChange(filtered);
  }, [filtered, onFilteredFeaturesChange]);

  const toggle = (key: FeatureSegmentKey, value: string) => {
    setSelected((prev) => {
      const current = prev[key];
      const mode = modes[key];
      if (mode === 'single') {
        return { ...prev, [key]: current[0] === value ? [] : [value] };
      }
      if (current.includes(value)) {
        return { ...prev, [key]: current.filter((v) => v !== value) };
      }
      return { ...prev, [key]: [...current, value] };
    });
  };

  const setAll = (key: FeatureSegmentKey) => {
    setSelected((prev) => {
      const all = optionsBySegment[key];
      if (modes[key] === 'single') {
        return { ...prev, [key]: all.slice(0, 1) };
      }
      return { ...prev, [key]: all };
    });
  };

  const clearAll = (key: FeatureSegmentKey) => {
    setSelected((prev) => ({ ...prev, [key]: [] }));
  };

  const [panelOpen, setPanelOpen] = useState(true);

  return (
    <div className="rounded-xl border border-white/10 bg-white/5">
      <div
        className="flex items-center justify-between px-3 py-2 cursor-pointer select-none"
        onClick={() => setPanelOpen((v) => !v)}
      >
        <div className="flex items-center gap-1.5 text-xs text-slate-300">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${panelOpen ? 'rotate-90' : 'rotate-0'}`}
            viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          >
            <polyline points="9 18 15 12 9 6" />
          </svg>
          特徵命名規範段落篩選
        </div>
        {panelOpen && (
          <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              onClick={() => setOpenMap(buildSegmentMap<boolean>(() => true))}
              className="text-xs px-2 py-0.5 rounded border border-white/10 text-slate-300 hover:bg-white/5"
            >
              全部展開
            </button>
            <button
              type="button"
              onClick={() => setOpenMap(buildSegmentMap<boolean>(() => false))}
              className="text-xs px-2 py-0.5 rounded border border-white/10 text-slate-300 hover:bg-white/5"
            >
              全部折疊
            </button>
          </div>
        )}
      </div>
      {panelOpen && <div className="px-3 pb-3 space-y-2">
      <input
        value={freeText}
        onChange={(e) => setFreeText(e.target.value)}
        placeholder="自由輸入（保留）..."
        className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-100"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
        {SEGMENT_DEFS.map((seg) => {
          const options = optionsBySegment[seg.key];
          const picked = selected[seg.key];
          const mode = modes[seg.key];

          // Auto-hide empty panels (except params which uses text search)
          if (options.length === 0 && seg.key !== 'params') return null;

          // For indicator: filter display options by indicatorSearch
          const displayOptions =
            seg.key === 'indicator' && indicatorSearch.trim()
              ? options.filter((o) =>
                  o.toLowerCase().includes(indicatorSearch.trim().toLowerCase()),
                )
              : options;

          const badgeCount =
            seg.key === 'indicator' && indicatorSearch.trim()
              ? `${picked.length}/${displayOptions.length} (共 ${options.length})`
              : seg.key === 'params'
                ? paramsSearch.trim()
                  ? '文字篩選'
                  : '全部'
                : `${picked.length}/${options.length}`;

          return (
            <details
            key={seg.key}
            open={openMap[seg.key]}
            onToggle={(e) => { const isOpen = (e.currentTarget as HTMLDetailsElement).open; setOpenMap((prev) => ({ ...prev, [seg.key]: isOpen })); }}
            className="rounded-lg border border-white/10 bg-slate-900/30 px-2 py-1"
          >
              <summary className="cursor-pointer text-xs text-slate-200 flex items-center justify-between">
                <span>{seg.label}</span>
                <span className="text-slate-400">{badgeCount}</span>
              </summary>
              <div className="mt-2 space-y-2">
                {seg.key === 'params' ? (
                  /* Params panel: text search only */
                  <input
                    value={paramsSearch}
                    onChange={(e) => setParamsSearch(e.target.value)}
                    placeholder="輸入參數關鍵字（如 10-100）..."
                    className="w-full rounded border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-100"
                  />
                ) : (
                  <>
                    {/* Indicator panel: search box above checkbox list */}
                    {seg.key === 'indicator' && (
                      <input
                        value={indicatorSearch}
                        onChange={(e) => setIndicatorSearch(e.target.value)}
                        placeholder="搜尋指標名稱..."
                        className="w-full rounded border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-100"
                      />
                    )}
                    <div className="flex flex-wrap gap-1">
                      <button
                        onClick={() => setModes((prev) => ({ ...prev, [seg.key]: 'single' }))}
                        className={`text-[11px] px-2 py-1 rounded border ${
                          mode === 'single' ? 'border-cyan-300/50 text-cyan-200' : 'border-white/10 text-slate-300'
                        }`}
                        type="button"
                      >
                        單選
                      </button>
                      <button
                        onClick={() => setModes((prev) => ({ ...prev, [seg.key]: 'multi' }))}
                        className={`text-[11px] px-2 py-1 rounded border ${
                          mode === 'multi' ? 'border-cyan-300/50 text-cyan-200' : 'border-white/10 text-slate-300'
                        }`}
                        type="button"
                      >
                        複選
                      </button>
                      <button onClick={() => setAll(seg.key)} className="text-[11px] px-2 py-1 rounded border border-white/10 text-slate-300" type="button">
                        全選
                      </button>
                      <button onClick={() => clearAll(seg.key)} className="text-[11px] px-2 py-1 rounded border border-white/10 text-slate-300" type="button">
                        全取消
                      </button>
                    </div>

                    <div className="max-h-36 overflow-auto space-y-1 pr-1">
                      {displayOptions.map((option) => (
                        <label key={option} className="flex items-center gap-2 text-xs text-slate-200">
                          <input
                            type="checkbox"
                            checked={picked.includes(option)}
                            onChange={() => toggle(seg.key, option)}
                          />
                          <span className="truncate">{option}</span>
                        </label>
                      ))}
                      {displayOptions.length === 0 && (
                        <div className="text-[11px] text-slate-500">
                          {seg.key === 'indicator' && indicatorSearch ? '無符合項目' : '無可用項目'}
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            </details>
          );
        })}
      </div>

      <div className="text-[11px] text-slate-400">
        篩選後特徵數：{filtered.length.toLocaleString()}
        {unsupportedCount > 0 && `（輸入中有 ${unsupportedCount.toLocaleString()} 個欄名 unsupported：無有效描述，不參與段落篩選）`}
      </div>
      </div>}
    </div>
  );
}

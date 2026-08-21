'use client';

import { useEffect, useState } from 'react';
import { eventT0MsToIcTimestamps, getEventImport, listEventImports } from '@/lib/api';
import type { EventImportSummary } from '@/lib/types';

interface EventImportPickerProps {
  value?: string;
  onPick: (importId: string, icTimestamps: number[]) => void;
  /** 測試注入：略過後端列表 */
  imports?: EventImportSummary[];
}

/**
 * GAP-3 B5.2「從已匯入案例選事件」入口（S3.9-5）：只在事件模式渲染。
 * 選一批 ⇒ 以該批 t0（ms→秒）帶入 IC 主線 event_timestamps；未匯入任何事件 ⇒ empty state。
 */
export default function EventImportPicker({ value, onPick, imports }: EventImportPickerProps) {
  const [items, setItems] = useState<EventImportSummary[]>(imports ?? []);
  const [loading, setLoading] = useState(imports === undefined);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (imports !== undefined) {
      setItems(imports);
      setLoading(false);
      return;
    }
    let cancelled = false;
    listEventImports()
      .then((r) => {
        if (!cancelled) setItems(r.imports);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : '載入事件批失敗');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [imports]);

  const handleChange = async (importId: string) => {
    if (!importId) {
      onPick('', []);
      return;
    }
    try {
      const detail = await getEventImport(importId);
      onPick(importId, eventT0MsToIcTimestamps(detail.records));
    } catch (err) {
      setError(err instanceof Error ? err.message : '讀取事件批失敗');
    }
  };

  return (
    <div className="space-y-1" data-testid="event-import-picker">
      <label className="text-xs text-slate-300">從已匯入案例選事件（GAP-3）</label>
      {loading && <p className="text-xs text-slate-500">載入事件批…</p>}
      {error && <p className="text-xs text-rose-300" data-testid="event-import-picker-error">{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p className="text-xs text-amber-300" data-testid="event-import-picker-empty">
          尚未匯入任何事件批——請先到「數據準備」用新契約匯入。
        </p>
      )}
      {items.length > 0 && (
        <select
          className="w-full rounded border border-slate-700 bg-slate-900/70 px-2 py-1 text-xs text-slate-200"
          value={value ?? ''}
          data-testid="event-import-select"
          onChange={(e) => void handleChange(e.target.value)}
        >
          <option value="">（不使用匯入批；沿用上方 query）</option>
          {items.map((it) => (
            <option key={it.import_id} value={it.import_id}>
              {it.import_id} · {it.symbols.join('/')} {it.timeframes.join('/')} · {it.n_events} 筆
              {it.direction ? ` · ${it.direction}` : ''}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
